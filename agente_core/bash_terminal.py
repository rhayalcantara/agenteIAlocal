"""
Terminal persistente con filtro de comandos peligrosos.

Usa cmd.exe en Windows y bash en Linux/Mac.
"""
import os
import re
import sys
import queue
import threading
import subprocess
from datetime import datetime
from logger import get_logger

logger = get_logger("bash_terminal")

_IS_WINDOWS = sys.platform == "win32"

# ── Patrones de comandos BLOQUEADOS ───────────────────────────────────────────
_PATRONES_BLOQUEADOS = [
    # Borrado masivo / recursivo
    r"\brm\s+.*-[a-z]*r[a-z]*f",
    r"\brm\s+.*-[a-z]*f[a-z]*r",
    r"\brm\s+-rf\b",
    r"\brm\s+-fr\b",
    r"\brmdir\s+/",
    r"\brd\s+/s\s+/q\b",               # Windows: rd /s /q (equivalente a rm -rf)
    r"\bdel\s+/[sf]",                   # Windows: del /f /s
    # Git destructivo
    r"\bgit\s+clean\s+.*-[a-z]*f",
    r"\bgit\s+reset\s+--hard",
    r"\bgit\s+checkout\s+--\s*\.",
    r"\bgit\s+push\s+.*--force",
    # Formateo / discos
    r"\bmkfs\b",
    r"\bdd\s+.*of=/dev",
    r"\bfdisk\b",
    r"\bparted\b",
    r"\bformat\s+[a-z]:",               # Windows: format C:
    # Permisos peligrosos
    r"\bchmod\s+777\s+/",
    r"\bchown\s+.*\s+/",
    # Shutdown / reboot
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bhalt\b",
    r"\bpoweroff\b",
    # Borrado del proyecto (rutas críticas)
    r"rm\s+.*agente_core",
    r"rm\s+.*telegram_agente",
    r"rm\s+.*\.env\b",
    r"rm\s+.*\.git\b",
    # Python destructivo
    r"shutil\.rmtree",
    r"os\.remove.*\.py",
]

_REGEX_BLOQUEADOS = [re.compile(p, re.IGNORECASE) for p in _PATRONES_BLOQUEADOS]

MAX_COMANDO_LEN = 2000


def es_comando_peligroso(comando: str) -> tuple[bool, str]:
    if len(comando) > MAX_COMANDO_LEN:
        return True, f"Comando demasiado largo ({len(comando)} chars > {MAX_COMANDO_LEN})"
    for regex in _REGEX_BLOQUEADOS:
        if regex.search(comando):
            return True, f"Patrón bloqueado: {regex.pattern!r}"
    return False, ""


class BashTerminal:
    """Terminal persistente — mantiene estado entre llamadas."""

    def __init__(self):
        self._lock = threading.Lock()
        self._proceso = None
        self._output_queue: queue.Queue = queue.Queue()
        self._reader_thread: threading.Thread | None = None
        self.proceso_activo: dict | None = None
        self._iniciar()

    def _iniciar(self):
        try:
            env = os.environ.copy()
            _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            if _IS_WINDOWS:
                # En Windows usamos cmd.exe e inyectamos el venv en el PATH
                shell_cmd = ["cmd.exe"]
                env["PYTHONUTF8"] = "1"
                env["PYTHONIOENCODING"] = "utf-8"
                # Buscar el venv en orden: venv/, .venv/
                _venv_dir = None
                for _candidate in ("venv", ".venv"):
                    _candidate_path = os.path.join(_project_root, _candidate, "Scripts", "python.exe")
                    if os.path.exists(_candidate_path):
                        _venv_dir = os.path.join(_project_root, _candidate)
                        break
                if _venv_dir:
                    _venv_scripts = os.path.join(_venv_dir, "Scripts")
                    env["PATH"] = _venv_scripts + ";" + env.get("PATH", "")
                    env["VIRTUAL_ENV"] = _venv_dir
                    env["VIRTUAL_ENV_PROMPT"] = os.path.basename(_venv_dir)
                # Inyectar ffmpeg de winget si existe
                _ffmpeg_dir = os.path.join(
                    os.path.expanduser("~"),
                    "AppData", "Local", "Microsoft", "WinGet", "Packages",
                    "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
                    "ffmpeg-8.1-full_build", "bin"
                )
                if os.path.isdir(_ffmpeg_dir):
                    env["PATH"] = _ffmpeg_dir + ";" + env.get("PATH", "")
            else:
                # Linux / Mac: bash con venv inyectado
                shell_cmd = ["/bin/bash"]
                _venv_dir = None
                for _candidate in ("venv", ".venv"):
                    _candidate_path = os.path.join(_project_root, _candidate, "bin", "python")
                    if os.path.exists(_candidate_path):
                        _venv_dir = os.path.join(_project_root, _candidate)
                        break
                if _venv_dir:
                    _venv_bin = os.path.join(_venv_dir, "bin")
                    env["PATH"] = _venv_bin + ":/usr/local/bin:" + env.get("PATH", "")
                    env["VIRTUAL_ENV"] = _venv_dir

            self._proceso = subprocess.Popen(
                shell_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=_project_root,
                encoding="utf-8",
                errors="replace",
            )

            # Hilo lector de output (evita select.select que no funciona en Windows)
            self._output_queue = queue.Queue()
            self._reader_thread = threading.Thread(
                target=self._leer_output,
                daemon=True,
                name="bash-reader",
            )
            self._reader_thread.start()

            logger.info(f"Terminal {'cmd.exe' if _IS_WINDOWS else 'bash'} persistente iniciada")

            # Drenar banner inicial (cmd.exe imprime version + prompt)
            self._drenar_banner()
        except Exception as e:
            logger.error(f"No se pudo iniciar terminal: {e}")
            self._proceso = None

    def _drenar_banner(self):
        """Envía un comando dummy para drenar el banner inicial de cmd.exe/bash."""
        import time
        SENTINEL = "__BANNER_DONE__"
        try:
            if _IS_WINDOWS:
                self._proceso.stdin.write(f"echo {SENTINEL}\r\n")
            else:
                self._proceso.stdin.write(f"echo {SENTINEL}\n")
            self._proceso.stdin.flush()

            deadline = time.time() + 10
            while time.time() < deadline:
                try:
                    line = self._output_queue.get(timeout=1.0)
                    if line is None:
                        break
                    if SENTINEL in line and not line.strip().startswith("echo"):
                        break
                except queue.Empty:
                    continue
            logger.info("Banner inicial drenado OK")
        except Exception as e:
            logger.warning(f"Error drenando banner: {e}")

    def _leer_output(self):
        """Hilo daemon que lee stdout línea a línea y lo pone en la cola."""
        try:
            for line in iter(self._proceso.stdout.readline, ""):
                self._output_queue.put(line)
        except Exception:
            pass
        self._output_queue.put(None)  # señal de fin

    def ejecutar(self, comando: str, timeout: float = 180, cwd: str | None = None) -> str:
        """Ejecuta un comando en la terminal persistente.

        Args:
            comando: comando shell a ejecutar
            timeout: segundos antes de devolver Error de timeout (default 180)
            cwd: directorio donde correr el comando (sin cambiar el cwd del shell)
                 — usa pushd/popd en Windows, subshell en bash. Si None, se usa
                 el cwd actual del shell persistente.
        """
        peligroso, razon = es_comando_peligroso(comando)
        if peligroso:
            msg = f"🚫 COMANDO BLOQUEADO por seguridad: {razon}\nComando: {comando[:200]}"
            logger.warning(f"Comando bloqueado: {razon} | cmd: {comando[:200]}")
            return msg

        if self._proceso is None or self._proceso.poll() is not None:
            logger.warning("Terminal caída, reiniciando...")
            # Limpiar cola vieja antes de reiniciar
            while not self._output_queue.empty():
                try:
                    self._output_queue.get_nowait()
                except queue.Empty:
                    break
            self._iniciar()

        if self._proceso is None:
            return "Error: No se pudo iniciar la terminal."

        # Wrapper para correr el comando en `cwd` sin afectar el shell persistente.
        comando_efectivo = comando
        if cwd:
            if not os.path.isdir(cwd):
                return f"Error: cwd no existe o no es directorio: {cwd}"
            if _IS_WINDOWS:
                # pushd / popd preserva el cwd del shell despues de correr
                comando_efectivo = f'pushd "{cwd}" && ({comando}) & popd'
            else:
                # Subshell con cd: no modifica el cwd padre
                comando_efectivo = f'(cd "{cwd}" && {comando})'

        SENTINEL = "__CMD_DONE_AGENTE__"
        debug = os.environ.get("BASH_TERMINAL_DEBUG", "").lower() in ("1", "true", "yes")

        with self._lock:
            self.proceso_activo = {
                "comando": comando,
                "inicio": datetime.now(),
                "pid": self._proceso.pid,
            }
            try:
                if _IS_WINDOWS:
                    self._proceso.stdin.write(comando_efectivo + "\r\n")
                    self._proceso.stdin.write(f"echo {SENTINEL}\r\n")
                else:
                    self._proceso.stdin.write(comando_efectivo + "\n")
                    self._proceso.stdin.write(f"echo {SENTINEL}\n")
                self._proceso.stdin.flush()

                if debug:
                    logger.info(f"[bash_terminal] STDIN: {comando_efectivo!r}")

                lines = []
                import time
                deadline = time.time() + timeout
                # Filtros precalculados — el comando puede ser multilinea
                cmd_first = comando.split("\n")[0].strip()
                cmd_eff_first = comando_efectivo.split("\n")[0].strip()
                while True:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        return f"Error: Timeout ({timeout}s) esperando resultado del comando."
                    try:
                        line = self._output_queue.get(timeout=min(remaining, 2.0))
                    except queue.Empty:
                        if time.time() >= deadline:
                            return f"Error: Timeout ({timeout}s) esperando resultado del comando."
                        continue
                    if line is None:
                        break

                    # Normalizar: quitar \r colgantes (Windows mete \r en el medio del stream)
                    if _IS_WINDOWS:
                        line = line.replace("\r", "")
                    if debug:
                        logger.info(f"[bash_terminal] STDOUT: {line!r}")

                    if SENTINEL in line:
                        # Ignorar el eco del comando "echo SENTINEL"
                        if line.strip().startswith("echo") or line.strip().startswith(">echo"):
                            continue
                        break
                    # Filtrar ecos de los comandos en cmd.exe (líneas con prompt>comando)
                    stripped = line.strip()
                    if stripped.endswith(f"echo {SENTINEL}"):
                        continue
                    if stripped.endswith(cmd_first):
                        continue
                    if cmd_eff_first != cmd_first and stripped.endswith(cmd_eff_first):
                        continue
                    print(f"│ {line}", end="", flush=True)
                    lines.append(line)

                return "".join(lines).rstrip()

            except Exception as e:
                logger.error(f"Error ejecutando comando: {e}")
                self._proceso = None
                return f"Error en terminal: {e}"
            finally:
                self.proceso_activo = None

    def cerrar(self):
        if self._proceso and self._proceso.poll() is None:
            try:
                cmd = "exit\r\n" if _IS_WINDOWS else "exit\n"
                self._proceso.stdin.write(cmd)
                self._proceso.stdin.flush()
                self._proceso.wait(timeout=5)
            except Exception:
                self._proceso.kill()
        logger.info("Terminal cerrada")
