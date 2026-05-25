"""monitor_bateria.py — Alerta por Telegram si la batería de la laptop baja.

Diseñado para ser ejecutado por Windows Task Scheduler cada N minutos. Cada
ejecución es rápida (carga psutil + request HTTP a Telegram si hace falta).

Lógica con histéresis para NO spamear:
    bateria <= UMBRAL_BAJO (15%) y NO enchufado-cargando-bien
       -> si no se había alertado: enviar Telegram + crear flag-file.
    bateria > UMBRAL_RECUPERADO (20%) Y enchufado
       -> si había flag: borrar flag (próximo bajón vuelve a alertar).

Considera que "enchufado=True" puede mentir si el cable está malo. Cuando
secsleft < 0 y enchufado=True pero la bateria está cayendo, también alertamos
(detección de "enchufado pero no cargando").

Uso manual (debug):
    venv\\Scripts\\python.exe monitor_bateria.py [--force]
        --force  envía la alerta aunque no haya cruzado umbrales (test)
"""
import argparse
import os
import sys
import time
from pathlib import Path

import psutil
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

UMBRAL_BAJO         = int(os.getenv("BATERIA_UMBRAL_BAJO", "15"))
UMBRAL_RECUPERADO   = int(os.getenv("BATERIA_UMBRAL_RECUPERADO", "20"))
FLAG_PATH           = ROOT / ".monitor_bateria_alertado.flag"
LOGFILE             = ROOT / "monitor_bateria.log"

TG_TOKEN  = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT   = int(os.getenv("TELEGRAM_CHAT_ID", "5483766132"))  # Rhay


def log(msg: str) -> None:
    """Append a monitor_bateria.log con timestamp."""
    import datetime as _dt
    ts = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {msg}"
    print(line, flush=True)
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def telegram_send(text: str) -> bool:
    """Envía un mensaje al chat de Rhay vía Bot API. True si OK."""
    if not TG_TOKEN:
        log("ERROR: TELEGRAM_TOKEN no configurado en .env")
        return False
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        r = requests.post(
            url, json={"chat_id": TG_CHAT, "text": text, "parse_mode": "Markdown"},
            timeout=10,
        )
        if r.status_code == 200:
            return True
        log(f"ERROR Telegram {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        log(f"ERROR enviando Telegram: {e}")
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="enviar alerta aunque no aplique (debug)")
    args = ap.parse_args()

    bat = psutil.sensors_battery()
    if bat is None:
        log("Sin info de batería (¿es desktop?). Salgo silenciosamente.")
        return 0

    pct = round(bat.percent, 1)
    enchufado = bool(bat.power_plugged)
    secsleft = bat.secsleft  # -2 = unlimited (cargando) / -1 = unknown / >0 = segundos hasta vaciar
    cargando_real = enchufado and secsleft in (psutil.POWER_TIME_UNLIMITED, -2)

    alertado = FLAG_PATH.exists()

    # Caso "enchufado pero secsleft>0 y bajando" = cable está conectado pero no carga.
    enchufado_pero_no_carga = enchufado and isinstance(secsleft, int) and secsleft > 0

    # Política: si % bajo, alertar — porque el caso de Rhay es exactamente
    # "enchufado=True con secsleft=-2 pero el cable no carga bien y la batería
    # sigue cayendo". Confiar en `cargando_real` aquí daría falso positivo.
    debe_alertar = (pct <= UMBRAL_BAJO) or args.force

    if pct >= UMBRAL_RECUPERADO and cargando_real and alertado:
        FLAG_PATH.unlink(missing_ok=True)
        log(f"recuperado: {pct}% enchufado y cargando — flag borrado")
        return 0

    if debe_alertar and (not alertado or args.force):
        if enchufado_pero_no_carga:
            estado_extra = f"\n⚠️ Está enchufado pero NO está cargando (secsleft={secsleft}s). Revisa el cable."
        elif enchufado and cargando_real:
            estado_extra = f"\nℹ️ psutil dice que SÍ está cargando, pero el % está bajo. Si el cable está malo, ojo igual."
        else:
            estado_extra = f"\nℹ️ No está enchufado."
        msg = (
            f"🔋 *BATERÍA BAJA — {pct}%* (umbral {UMBRAL_BAJO}%)\n"
            f"Enchufado: {enchufado} | secsleft: {secsleft}s{estado_extra}\n\n"
            f"Te aviso una sola vez hasta que vuelva a >{UMBRAL_RECUPERADO}% cargando bien."
        )
        if telegram_send(msg):
            FLAG_PATH.touch()
            log(f"ALERTA enviada: pct={pct}% enchufado={enchufado} secsleft={secsleft}")
        else:
            log(f"alerta fallida al enviar Telegram")
        return 0

    # Estado normal
    log(f"OK: pct={pct}% enchufado={enchufado} secsleft={secsleft} alertado={alertado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
