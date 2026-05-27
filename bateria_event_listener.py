"""bateria_event_listener.py — push de eventos de batería via WMI.

Reemplaza al schtask `RangerMonitorBateria` que corría cada 5 min.
Se suscribe a Win32_Battery modifications y dispara cuando hay cambio real
(porcentaje, BatteryStatus). Bajo el capó WMI sondea al kernel a ~2s, pero
el código del agente NO hace polling — reacciona a eventos.

Comportamiento:
  - pct ≤ UMBRAL_BAJO (15%) y NO cargando bien → alerta Telegram (única vez,
    flag file de histéresis).
  - pct ≥ UMBRAL_RECUPERADO (20%) Y cargando bien → limpia flag (próxima caída
    vuelve a alertar).
  - Cambio AC ↔ Discharging → alerta Telegram (debounce 5s para evitar spam
    si el cable malo fluctúa).

Reusa `monitor_bateria.telegram_send`, `log`, constantes (UMBRAL_*, FLAG_PATH).
Tolerante a desconexión transitoria de WMI (reintenta con backoff).

Lanzar via launcher con Startup folder. SIGINT/SIGTERM = exit limpio.
"""
from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

import psutil
import pythoncom
import wmi
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Reusa la lógica del schtask viejo (constantes + telegram_send + log)
sys.path.insert(0, str(ROOT))
from monitor_bateria import (  # noqa: E402
    UMBRAL_BAJO,
    UMBRAL_RECUPERADO,
    FLAG_PATH,
    log,
    telegram_send,
)

# BatteryStatus values (Win32_Battery)
# 1=Discharging, 2=On AC, 3=Fully Charged, 4=Low, 5=Critical,
# 6=Charging, 7=Charging+High, 8=Charging+Low, 9=Charging+Critical,
# 10=Undefined, 11=Partially Charged
_DISCHARGING = {1, 4, 5}
_AC_PLUGGED  = {2, 3, 6, 7, 8, 9, 11}

_running = True

# Debounce para evitar spam de avisos enchufado/desenchufado si el cable
# fluctúa. Solo notifica si han pasado >FUENTE_DEBOUNCE_SECS desde la última.
FUENTE_DEBOUNCE_SECS = int(os.getenv("BATERIA_FUENTE_DEBOUNCE_SECS", "5"))


def _signal_handler(signum, _frame):
    global _running
    log(f"listener recibido signal {signum} — saliendo limpio")
    _running = False


def _es_ac(status: int) -> bool:
    """True si el estado WMI indica fuente AC (enchufado, sea cargando o no)."""
    return status in _AC_PLUGGED


def _notificar_cambio_fuente(prev_status: int, new_status: int, pct: float) -> None:
    """Manda Telegram cuando cambia de AC a Discharging o viceversa."""
    prev_ac = _es_ac(prev_status)
    new_ac  = _es_ac(new_status)
    if prev_ac == new_ac:
        return  # cambio dentro de la misma clase (ej. charging → fully charged)
    if new_ac:
        msg = (f"🔌 *Cable enchufado* (batería {pct}%)\n"
               f"BatteryStatus: {prev_status} → {new_status}")
    else:
        msg = (f"🔋 *Cable desenchufado* (batería {pct}%)\n"
               f"BatteryStatus: {prev_status} → {new_status}\n"
               f"Ojo si no fue intencional.")
    if telegram_send(msg):
        log(f"AVISO fuente enviado: {prev_status}→{new_status}")
    else:
        log(f"AVISO fuente fallo Telegram: {prev_status}→{new_status}")


def _decidir_alerta(pct: float, status: int) -> tuple[bool, str]:
    """Devuelve (debe_alertar, mensaje). Misma lógica de histéresis que el
    `monitor_bateria.main()` pero con datos WMI + psutil.
    """
    # psutil para complementar (detecta "enchufado pero no carga")
    bat = psutil.sensors_battery()
    secsleft = bat.secsleft if bat else -1
    enchufado = status in _AC_PLUGGED
    cargando_real = status in {2, 3, 6, 7, 11}  # AC + no low/critical durante carga
    enchufado_pero_no_carga = enchufado and isinstance(secsleft, int) and secsleft > 0

    alertado = FLAG_PATH.exists()

    # Recuperación: bateria buena + cargando + ya alertamos → limpiar flag
    if pct >= UMBRAL_RECUPERADO and cargando_real and alertado:
        FLAG_PATH.unlink(missing_ok=True)
        log(f"recuperado: pct={pct}% cargando bien — flag borrado")
        return False, ""

    # Alerta: % bajo + no alertado todavía
    if pct <= UMBRAL_BAJO and not alertado:
        if enchufado_pero_no_carga:
            estado_extra = f"\n⚠️ Enchufado pero NO carga (secsleft={secsleft}s). Revisa el cable."
        elif cargando_real:
            estado_extra = "\nℹ️ El sistema reporta que SÍ está cargando. Ojo igual si el cable está malo."
        else:
            estado_extra = "\nℹ️ No está enchufado."
        msg = (
            f"🔋 *BATERÍA BAJA — {pct}%* (umbral {UMBRAL_BAJO}%)\n"
            f"BatteryStatus={status} | secsleft={secsleft}s{estado_extra}\n\n"
            f"Te aviso una sola vez hasta que vuelva a >{UMBRAL_RECUPERADO}% cargando bien."
        )
        return True, msg

    return False, ""


def _procesar_lectura(pct: float, status: int) -> None:
    """Evalúa una lectura de batería y manda Telegram si aplica."""
    debe, msg = _decidir_alerta(pct, status)
    if debe:
        if telegram_send(msg):
            FLAG_PATH.touch()
            log(f"ALERTA enviada: pct={pct}% status={status}")
        else:
            log(f"ALERTA fallo Telegram: pct={pct}% status={status}")


def _loop() -> int:
    """Loop principal: suscribe + procesa eventos hasta SIGTERM."""
    pythoncom.CoInitialize()
    try:
        c = wmi.WMI()
        # Lectura inicial para validar setup y procesar estado actual una vez
        # (sin esperar al primer cambio).
        baterias = c.Win32_Battery()
        if not baterias:
            log("No hay Win32_Battery (¿es desktop?). Listener termina.")
            return 0
        b0 = baterias[0]
        pct0 = float(b0.EstimatedChargeRemaining or 0)
        st0 = int(b0.BatteryStatus or 0)
        log(f"listener arrancado — lectura inicial pct={pct0}% status={st0}")
        _procesar_lectura(pct0, st0)

        # Suscripción a modificaciones. delay_secs es el polling interno de WMI.
        # Mantener pequeño (2-5s) para reaccionar rápido sin gastar CPU.
        watcher = c.Win32_Battery.watch_for(
            notification_type="modification",
            delay_secs=int(os.getenv("BATERIA_WMI_POLL_SECS", "5")),
        )

        last_status = st0
        last_fuente_change_ts = 0.0  # epoch del último notificación de fuente
        while _running:
            try:
                # Timeout corto para chequear _running periódicamente.
                bat = watcher(timeout_ms=2000)
            except wmi.x_wmi_timed_out:
                continue
            except Exception as e:
                log(f"WMI watcher error transitorio: {type(e).__name__}: {e}")
                time.sleep(5)
                continue

            try:
                pct = float(bat.EstimatedChargeRemaining or 0)
                status = int(bat.BatteryStatus or 0)
            except Exception as e:
                log(f"lectura malformada: {e}")
                continue

            if status != last_status:
                log(f"BatteryStatus cambió: {last_status} → {status} (pct={pct}%)")
                # Solo notificar si el cambio cruza AC↔Discharging y pasó el debounce
                if _es_ac(last_status) != _es_ac(status):
                    now = time.time()
                    if now - last_fuente_change_ts >= FUENTE_DEBOUNCE_SECS:
                        _notificar_cambio_fuente(last_status, status, pct)
                        last_fuente_change_ts = now
                    else:
                        log(f"  (debounce: cambio dentro de {FUENTE_DEBOUNCE_SECS}s, silenciado)")
                last_status = status

            _procesar_lectura(pct, status)

        log("listener terminado limpio")
        return 0
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def main() -> int:
    signal.signal(signal.SIGINT, _signal_handler)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _signal_handler)
    try:
        return _loop()
    except Exception as e:
        log(f"FATAL: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
