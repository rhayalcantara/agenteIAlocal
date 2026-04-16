"""
Terminal bash persistente con filtro de comandos peligrosos.

El agente puede ejecutar comandos, pero ciertos patrones destructivos
están bloqueados para evitar pérdida accidental de datos o del proyecto.
"""
import re
import subprocess
import threading
from logger import get_logger

logger = get_logger("bash_terminal")

# ── Patrones de comandos BLOQUEADOS ───────────────────────────────────────────
# Cualquier comando que coincida con alguno de estos patrones será rechazado
# antes de ejecutarse. Agregar aquí si aparecen nuevos patrones peligrosos.
_PATRONES_BLOQUEADOS = [
    # Borrado masivo / recursivo
    r"\brm\s+.*-[a-z]*r[a-z]*f",       # rm -rf, rm -fr, rm -r -f ...
    r"\brm\s+.*-[a-z]*f[a-z]*r",       # rm -fr
    r"\brm\s+-rf\b",
    r"\brm\s+-fr\b",
    r"\brmdir\s+/",                     # rmdir sobre rutas absolutas raíz
    # Git destructivo
    r"\bgit\s+clean\s+.*-[a-z]*f",     # git clean -f, -fd, -fdx
    r"\bgit\s+reset\s+--hard",
    r"\bgit\s+checkout\s+--\s*\.",      # git checkout -- . (descarta cambios)
    r"\bgit\s+push\s+.*--force",        # force push
    # Formateo / discos
    r"\bmkfs\b",
    r"\bdd\s+.*of=/dev",
    r"\bfdisk\b",
    r"\bparted\b",
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

# Longitud máxima de un comando (evita payloads gigantes)
MAX_COMANDO_LEN = 2000


def es_comando_peligroso(comando: str) -> tuple[bool, str]:
    """Verifica si un comando coincide con patrones peligrosos.

    Returns:
        (True, razon) si es peligroso, (False, "") si es seguro.
    """
    if len(comando) > MAX_COMANDO_LEN:
        return True, f"Comando demasiado largo ({len(comando)} chars > {MAX_COMANDO_LEN})"

    for regex in _REGEX_BLOQUEADOS:
        if regex.search(comando):
            return True, f"Patrón bloqueado: {regex.pattern!r}"

    return False, ""


class BashTerminal:
    """Terminal bash persistente — mantiene estado entre llamadas."""

    def __init__(self):
        self._lock = threading.Lock()
        self._proceso = None
        self._iniciar()

    def _iniciar(self):
        import os
        try:
            env = os.environ.copy()
            # Inyectar el venv del proyecto para que python3/pip usen el entorno correcto
            _project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            _venv_bin = os.path.join(_project_root, ".venv", "bin")
            env["PATH"] = _venv_bin + ":/usr/local/bin:" + env.get("PATH", "")
            env["VIRTUAL_ENV"] = os.path.join(_project_root, ".venv")
            self._proceso = subprocess.Popen(
                ["/bin/bash"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                cwd=_project_root,
            )
            logger.info("Terminal bash persistente iniciada")
        except Exception as e:
            logger.error(f"No se pudo iniciar terminal bash: {e}")
            self._proceso = None

    def ejecutar(self, comando: str, timeout: float = 120) -> str:
        """Ejecuta un comando en la terminal persistente.

        Primero verifica que no sea un comando peligroso.
        """
        # ── Filtro de seguridad ───────────────────────────────────────────────
        peligroso, razon = es_comando_peligroso(comando)
        if peligroso:
            msg = f"🚫 COMANDO BLOQUEADO por seguridad: {razon}\nComando: {comando[:200]}"
            logger.warning(f"Comando bloqueado: {razon} | cmd: {comando[:200]}")
            return msg

        # ── Ejecución normal ──────────────────────────────────────────────────
        if self._proceso is None or self._proceso.poll() is not None:
            logger.warning("Terminal bash caída, reiniciando...")
            self._iniciar()

        if self._proceso is None:
            return "Error: No se pudo iniciar la terminal bash."

        SENTINEL = "__CMD_DONE__"

        with self._lock:
            try:
                self._proceso.stdin.write(comando + "\n")
                self._proceso.stdin.write(f"echo {SENTINEL}\n")
                self._proceso.stdin.flush()

                lines = []
                import select
                while True:
                    ready, _, _ = select.select([self._proceso.stdout], [], [], timeout)
                    if not ready:
                        return f"Error: Timeout ({timeout}s) esperando resultado del comando."
                    line = self._proceso.stdout.readline()
                    if SENTINEL in line:
                        break
                    lines.append(line)

                return "".join(lines).rstrip()

            except Exception as e:
                logger.error(f"Error ejecutando comando: {e}")
                self._proceso = None
                return f"Error en terminal bash: {e}"

    def cerrar(self):
        if self._proceso and self._proceso.poll() is None:
            try:
                self._proceso.stdin.write("exit\n")
                self._proceso.stdin.flush()
                self._proceso.wait(timeout=5)
            except Exception:
                self._proceso.kill()
        logger.info("Terminal bash cerrada")
