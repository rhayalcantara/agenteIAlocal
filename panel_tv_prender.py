"""panel_tv_prender.py — Prende la TV principal y abre el panel de operaciones.

Uso:
    venv\\Scripts\\python.exe panel_tv_prender.py

Pasos:
  1. Asegurar tv_panel_server.py vivo (corre el launcher idempotente).
  2. Wake-on-LAN al MAC de la TV (sirve aunque ADB esté apagado completamente).
  3. ADB connect + KEYCODE_WAKEUP (despierta la pantalla).
  4. Detectar IP LAN de la PC (la que el adapter activo usa).
  5. ADB am start VIEW intent con la URL del panel → el navegador de la TV
     abre http://<lan-ip>:8095/

Pensado para ser ejecutado por Windows Task Scheduler en horarios fijos
(el "morning briefing" de Rhay). Loggea a panel_tv_prender.log.
"""
import datetime as _dt
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TV_IP = "192.168.1.182"
TV_MAC = "ee:f2:ff:a3:f8:5a"
PANEL_PORT = 8095
ADB = r"C:\Users\rhay_\platform-tools\adb.exe"
LOGFILE = ROOT / "panel_tv_prender.log"


def log(msg: str) -> None:
    """Print + append a panel_tv_prender.log con timestamp."""
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def lan_ip() -> str:
    """IP LAN del adapter activo (la que usaría para internet)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()


def wol(mac: str) -> None:
    """Envía paquete Wake-on-LAN al MAC en puertos 9 y 7, broadcast."""
    b = bytes.fromhex(mac.replace(":", ""))
    pkt = b"\xff" * 6 + b * 16
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    for port in (9, 7):
        s.sendto(pkt, ("255.255.255.255", port))
        try:
            s.sendto(pkt, ("192.168.1.255", port))
        except Exception:
            pass
    s.close()


def adb_run(*args, timeout: int = 10) -> subprocess.CompletedProcess:
    cmd = [ADB] + list(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def main() -> int:
    log("=== panel_tv_prender.py start ===")

    # 1) launcher idempotente (asegura tv_panel_server.py vivo)
    log("[1/5] launcher idempotente (ensure tv_panel_server.py)")
    try:
        venv_py = ROOT / "venv" / "Scripts" / "python.exe"
        py = str(venv_py) if venv_py.exists() else sys.executable
        r = subprocess.run(
            [py, str(ROOT / "iniciar_comunicaciones.py")],
            cwd=str(ROOT), capture_output=True, text=True, timeout=30,
        )
        # solo loggeamos línea relevante del launcher
        for ln in (r.stdout or "").splitlines():
            if "tv_panel_server" in ln:
                log(f"    launcher: {ln.strip()}")
    except Exception as e:
        log(f"    WARN launcher: {e} (sigo, asumiendo que el server estará vivo)")

    # 2) WoL al MAC de la TV (despierta la red aunque esté completamente off)
    log(f"[2/5] Wake-on-LAN al TV ({TV_MAC})")
    try:
        wol(TV_MAC)
        time.sleep(3)  # darle tiempo a la red de la TV
    except Exception as e:
        log(f"    WARN WoL: {e}")

    # 3) ADB connect (idempotente)
    log(f"[3/5] ADB connect {TV_IP}:5555")
    try:
        r = adb_run("connect", f"{TV_IP}:5555", timeout=15)
        log(f"    {(r.stdout or '').strip()}")
        time.sleep(2)
    except Exception as e:
        log(f"    WARN adb connect: {e}")

    # 4) ADB wakeup pantalla
    log("[4/5] ADB wakeup pantalla")
    try:
        adb_run("-s", f"{TV_IP}:5555", "shell", "input", "keyevent", "KEYCODE_WAKEUP", timeout=10)
        time.sleep(1)
    except Exception as e:
        log(f"    WARN wakeup: {e}")

    # 5) abrir URL del panel en el navegador de la TV
    try:
        ip = lan_ip()
    except Exception as e:
        log(f"    ERROR detectando LAN IP: {e}")
        return 2
    url = f"http://{ip}:{PANEL_PORT}/"
    log(f"[5/5] abrir {url} en TV (am start VIEW)")
    try:
        r = adb_run(
            "-s", f"{TV_IP}:5555", "shell",
            "am", "start", "-a", "android.intent.action.VIEW", "-d", url,
            timeout=15,
        )
        stdout = (r.stdout or "").strip()
        stderr = (r.stderr or "").strip()
        if stdout:
            log(f"    {stdout[:200]}")
        if stderr:
            log(f"    err: {stderr[:200]}")
        if r.returncode != 0 or "offline" in stderr.lower() or "error" in stderr.lower():
            log(f"    WARN am start exit={r.returncode} -- TV no recibió el panel")
            log("    Causa típica: TV apagada con el control (modo profundo que WoL no despierta)")
            log("    Acción: encender TV físicamente y re-ejecutar este script")
            log("=== FIN sin abrir panel en TV (server local sí está arriba) ===")
            return 4
    except Exception as e:
        log(f"    ERROR am start: {e}")
        return 3

    log("=== OK panel arriba en TV ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
