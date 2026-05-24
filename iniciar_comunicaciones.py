"""Arranque idempotente de las comunicaciones (WhatsApp + Telegram) en modo push.

Levanta, como procesos sueltos (detached) que sobreviven a la sesión de Claude:
  - whatsapp_monitor.js "SISTEMA RAY"  -> escribe a whatsapp_monitor.log
  - telegram_push.py                    -> escribe a telegram_monitor.log

Es idempotente: si un proceso ya está corriendo (detectado por su línea de comando)
NO lo vuelve a arrancar. Esto es CRÍTICO para Telegram: dos pollers de getUpdates a la
vez se roban mensajes (el bot tiene una sola cola).

Uso:
    python iniciar_comunicaciones.py

Después de correrlo, la sesión de Claude solo tiene que armar dos Monitors:
    tail -n 0 -f whatsapp_monitor.log | grep "SISTEMA RAY"
    tail -n 0 -f telegram_monitor.log
y NO llamar mcp__telegram__leer_mensajes mientras el poller corra.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP -> el hijo sobrevive aunque este script termine.
DETACHED = 0x00000008 | 0x00000200


def _esta_corriendo(substr: str, nombre_proceso: str) -> bool:
    """True si existe un proceso `nombre_proceso` cuya línea de comando contiene `substr`.

    Filtra por nombre de proceso (p.ej. python.exe / node.exe) para que el propio
    powershell que corre este query NO se detecte a sí mismo: su CommandLine contiene
    el patrón buscado, pero su nombre es powershell.exe, así que queda excluido.
    """
    ps = (
        f"Get-CimInstance Win32_Process -Filter \"Name='{nombre_proceso}'\" | "
        f"Where-Object {{ $_.CommandLine -like '*{substr}*' }} | "
        "Select-Object -First 1 -ExpandProperty ProcessId"
    )
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=30,
        )
        return out.stdout.strip() != ""
    except Exception:
        return False  # ante la duda, intentamos arrancar (peor caso: el propio script lo verá)


def _arrancar(nombre: str, args: list[str], logfile: str) -> None:
    log_path = os.path.join(ROOT, logfile)
    logf = open(log_path, "ab")
    subprocess.Popen(
        args,
        cwd=ROOT,
        stdout=logf,
        stderr=logf,
        stdin=subprocess.DEVNULL,
        creationflags=DETACHED,
        close_fds=True,
    )
    print(f"[OK] {nombre} arrancado (stdout -> {logfile})")


def main() -> None:
    # --- WhatsApp ---
    if _esta_corriendo("whatsapp_monitor.js", "node.exe"):
        print("[skip] whatsapp_monitor.js ya está corriendo")
    else:
        _arrancar(
            "WhatsApp monitor",
            ["node", "whatsapp_monitor.js", "SISTEMA RAY"],
            "whatsapp_monitor.stdout.log",
        )

    # --- Telegram ---
    if _esta_corriendo("telegram_push.py", "python.exe"):
        print("[skip] telegram_push.py ya está corriendo")
    else:
        _arrancar(
            "Telegram push",
            [sys.executable, "telegram_push.py"],
            "telegram_push.stdout.log",
        )

    # --- TV Panel Server (sirve http://<lan-ip>:8095 para la TV) ---
    if _esta_corriendo("tv_panel_server.py", "python.exe"):
        print("[skip] tv_panel_server.py ya está corriendo")
    else:
        _arrancar(
            "TV panel server",
            [sys.executable, "tv_panel_server.py"],
            "tv_panel_server.stdout.log",
        )

    print()
    print("LISTO. Si arrancó WhatsApp por primera vez tras logout, revisa whatsapp_qr.png para re-vincular.")
    print("Ahora arma los Monitors (tail de whatsapp_monitor.log y telegram_monitor.log) y NO llames leer_mensajes.")


if __name__ == "__main__":
    main()
