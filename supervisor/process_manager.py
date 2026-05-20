"""
Process Manager — lanza y controla el proceso de agente_core.

La salida del agente se imprime en consola con prefijo [AGENTE] y
también se guarda en el archivo de log.
"""
import os
import sys
import shlex
import time
import threading
import subprocess
from datetime import datetime
from supervisor.config import ROOT, AGENTE_COMMAND, AGENTE_LOG_FILE, LOG_DIR

_proceso: "subprocess.Popen | None" = None
_inicio_agente: "datetime | None" = None   # cuándo se inició el agente

# Archivo PID para rastrear el proceso incluso si el supervisor se reinicia
_PID_FILE = ROOT / "agente.pid"


def _matar_huerfanos():
    """Mata cualquier instancia de telegram_agente.py que no sea la actual."""
    # Leer PID del archivo si existe
    if _PID_FILE.exists():
        try:
            pid = int(_PID_FILE.read_text().strip())
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
            else:
                subprocess.run(
                    ["kill", "-9", str(pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
        except Exception:
            pass
        try:
            _PID_FILE.unlink()
        except Exception:
            pass

    # Barrido por línea de comandos (mata instancias huérfanas no rastreadas)
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-WmiObject Win32_Process | "
                 "Where-Object {$_.CommandLine -like '*telegram_agente*'} | "
                 "Select-Object -ExpandProperty ProcessId"],
                capture_output=True, text=True
            )
            for line in result.stdout.splitlines():
                pid = line.strip()
                if pid.isdigit():
                    subprocess.run(
                        ["taskkill", "/F", "/PID", pid],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
        else:
            subprocess.run(
                ["pkill", "-f", "telegram_agente.py"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
    except Exception:
        pass


def _leer_salida(stream, log_file):
    """
    Hilo que lee línea a línea el stdout/stderr del agente,
    imprime en consola con prefijo y guarda en el log.
    """
    try:
        for linea in iter(stream.readline, ""):
            if not linea:
                break
            linea = linea.rstrip("\n")
            print(f"[AGENTE] {linea}", flush=True)
            try:
                log_file.write(linea + "\n")
                log_file.flush()
            except Exception:
                pass
    except Exception:
        pass


def iniciar() -> tuple[bool, str]:
    """Inicia el agente como subprocess. Retorna (éxito, mensaje)."""
    global _proceso
    if _proceso is not None and _proceso.poll() is None:
        return False, "El agente ya estaba en ejecución."

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = open(AGENTE_LOG_FILE, "a", encoding="utf-8")

        cmd = shlex.split(AGENTE_COMMAND)
        # Usar el mismo Python del venv actual
        if cmd and cmd[0].lower() in ("python", "python3"):
            cmd[0] = sys.executable

        # Forzar UTF-8 en el subprocess (necesario en Windows para emojis)
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"

        # En Windows, leer el PATH actualizado del registro para capturar
        # programas instalados después de que este proceso arrancó (ej: ffmpeg)
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment")
                user_path, _ = winreg.QueryValueEx(key, "Path")
                winreg.CloseKey(key)
                # Expandir variables como %USERPROFILE%
                user_path = os.path.expandvars(user_path)
                current = env.get("PATH", "")
                # Añadir entradas del registro que no estén ya en el PATH actual
                extras = [p for p in user_path.split(";")
                          if p.strip() and p.strip() not in current]
                if extras:
                    env["PATH"] = current + ";" + ";".join(extras)
            except Exception:
                pass

        kwargs = dict(
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # mezclar stderr con stdout
            stdin=subprocess.DEVNULL,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        _proceso = subprocess.Popen(cmd, **kwargs)
        _inicio_agente = datetime.now()

        # Guardar PID para poder matar el proceso aunque el supervisor se reinicie
        try:
            _PID_FILE.write_text(str(_proceso.pid))
        except Exception:
            pass

        # Hilo daemon que imprime la salida en tiempo real
        t = threading.Thread(
            target=_leer_salida,
            args=(_proceso.stdout, log_file),
            daemon=True,
            name="agente-output",
        )
        t.start()

        return True, f"Agente iniciado (PID {_proceso.pid})."
    except Exception as e:
        return False, f"Error al iniciar el agente: {e}"


def detener(timeout: int = 10) -> tuple[bool, str]:
    """Detiene el proceso limpiamente. Retorna (éxito, mensaje)."""
    global _proceso

    # Matar huérfanos antes de verificar _proceso (cubre reinicios del supervisor)
    _matar_huerfanos()

    if _proceso is None or _proceso.poll() is not None:
        return True, "Agente detenido (instancias huérfanas eliminadas)."

    try:
        _proceso.terminate()
        try:
            _proceso.wait(timeout=timeout)
            return True, "Agente detenido correctamente."
        except subprocess.TimeoutExpired:
            _proceso.kill()
            return True, f"Agente forzado a terminar (no respondió en {timeout}s)."
    except Exception as e:
        return False, f"Error al detener el agente: {e}"


def reiniciar(espera: int = 3) -> tuple[bool, str]:
    """Detiene e inicia el agente. Retorna (éxito, mensaje combinado)."""
    ok_det, msg_det = detener()
    time.sleep(espera)
    ok_ini, msg_ini = iniciar()
    return ok_ini, f"{msg_det} {msg_ini}".strip()


def esta_corriendo() -> bool:
    return _proceso is not None and _proceso.poll() is None


def obtener_proceso() -> "subprocess.Popen | None":
    return _proceso


def obtener_inicio() -> "datetime | None":
    return _inicio_agente


def ultimos_logs(n: int = 30) -> str:
    """Lee las últimas n líneas del archivo de log."""
    if not AGENTE_LOG_FILE.exists():
        return "(sin logs todavía)"
    try:
        lines = AGENTE_LOG_FILE.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-n:]) or "(log vacío)"
    except Exception as e:
        return f"(error leyendo logs: {e})"
