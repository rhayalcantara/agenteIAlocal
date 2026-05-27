# Skill: WMI Event Listener

Patrón reutilizable para escribir **listeners event-driven** en Windows que reaccionan a cambios de hardware/SO sin polling propio. Construido a partir del refactor del monitor de batería el 27-may-2026 (`bateria_event_listener.py`).

> *Rhay prefiere event-driven sobre schtasks/cron periódicos. Si llega un pedido de "alertame cuando X cambie", primero evaluar esta skill antes de un loop.*

## Cuándo usarla

- "Alertame cuando X cambie / pase de Y a Z"
- "No quiero que estés verificando cada 5 minutos"
- "Si Y baja del umbral, avisame al toque"
- "Detectá si el servicio Z se cae / si el disco se llena / si entra un USB"
- Cualquier caso donde la **latencia** del schtask cada N min sea inaceptable.

## Cuándo NO usarla

- El recurso NO expone evento de WMI (ej. API REST externa sin webhook → usar polling con cadencia justificada).
- Cambios en archivos/directorios → usar `FileSystemWatcher` (PowerShell) o `watchdog` (Python), NO WMI.
- Linux/macOS → usar `inotify` / `FSEvents` / `journalctl --follow`, NO WMI.
- La frecuencia natural es muy baja (cada hora o más) y un schtask resuelve sin overhead.

## Catálogo de observables WMI (Windows)

| Clase WMI | Caso de uso | Ya implementado |
|-----------|-------------|-----------------|
| `Win32_Battery` | Batería + AC plug status | ✅ `bateria_event_listener.py` |
| `MSAcpi_ThermalZoneTemperature` | CPU/GPU temp | — |
| `Win32_NetworkAdapter` | Adapter up/down | — |
| `Win32_Service` | Servicio Windows iniciado/detenido | — |
| `Win32_USBHub` / `Win32_DeviceChangeEvent` | USB plug | — |
| `Win32_LogicalDisk` | Disco lleno (`FreeSpace`) | — |
| `Win32_PerfFormattedData_PerfOS_Processor` | CPU load sostenido | — |
| `Win32_Process` (creation/deletion) | Proceso arrancó/murió | — |

## Procedimiento para crear un listener nuevo

### Paso 1 — verificar deps

```powershell
# en el venv del proyecto
.\venv\Scripts\pip.exe install wmi pywin32
```

Si `requirements.txt` aún no las tiene, agregar `wmi>=1.5.1` (pywin32 suele estar ya).

### Paso 2 — escribir el listener Python

Copiar este esqueleto a `<nombre>_event_listener.py` en la raíz del repo. Sustituir:
- `Win32_Battery` → la clase WMI que aplica
- `_procesar_lectura(...)` → tu lógica de evaluación
- Lógica de Telegram / acción → ajustar al caso

```python
"""<nombre>_event_listener.py — push de eventos via WMI.

Reacciona a cambios de <clase WMI> sin polling propio.
"""
from __future__ import annotations
import os, signal, sys, time
from pathlib import Path

import pythoncom
import wmi
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

# Reusa funciones de scripts existentes para evitar duplicación:
# from monitor_bateria import telegram_send, log

_running = True

def _signal_handler(signum, _frame):
    global _running
    _running = False

def _procesar_lectura(obj) -> None:
    """Lógica del caso de uso: evaluar el objeto WMI y disparar acción."""
    # ... ej:
    # if obj.AlgunaPropiedad <= UMBRAL:
    #     telegram_send(f"⚠️ ...")
    pass

def _loop() -> int:
    pythoncom.CoInitialize()
    try:
        c = wmi.WMI()
        # Lectura inicial (procesa estado actual antes del primer cambio):
        items = c.Win32_Battery()  # cambiar por la clase del caso
        if not items:
            print("No hay instancias. Listener termina.")
            return 0
        _procesar_lectura(items[0])

        # Suscripción a modificaciones:
        watcher = c.Win32_Battery.watch_for(
            notification_type="modification",
            delay_secs=int(os.getenv("WMI_POLL_SECS", "5")),
        )
        while _running:
            try:
                ev = watcher(timeout_ms=2000)  # ojo: timeout obligatorio
            except wmi.x_wmi_timed_out:
                continue
            except Exception as e:
                print(f"WMI error transitorio: {e}", flush=True)
                time.sleep(5)
                continue
            _procesar_lectura(ev)
        return 0
    finally:
        try: pythoncom.CoUninitialize()
        except Exception: pass

def main() -> int:
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    return _loop()

if __name__ == "__main__":
    sys.exit(main())
```

### Paso 3 — launcher PowerShell

Copiar `iniciar_bateria_listener.ps1` como template, cambiar nombre y rutas. Patrón con `-Status / -Stop / -Force`, idempotente, redirección stdout/stderr a `logs/<nombre>.stdout.log`. Ver `iniciar_bateria_listener.ps1` línea por línea — el archivo es genérico salvo el nombre.

### Paso 4 — atajo Startup para auto-arranque al login

```powershell
$Script = "C:\proyectos\agenteIAlocal\iniciar_<nombre>_listener.ps1"
$Startup = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$Cmd = Join-Path $Startup "Ranger<Nombre>Listener.cmd"
@"
@echo off
start "" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "$Script"
"@ | Set-Content -Path $Cmd -Encoding ASCII
```

**NO usar `schtasks /SC ONLOGON`** — requiere admin. La carpeta Startup no.

### Paso 5 — si reemplaza un schtask viejo: DISABLE no DELETE

```powershell
Disable-ScheduledTask -TaskName "RangerMonitor<X>"
```

Dejar `Disabled` (no borrado) por si hace falta revertir.

### Paso 6 — debounce si la fuente puede fluctuar

Si el observable puede dar cambios rápidos consecutivos (ej. cable malo, sensor ruidoso), agregar **debounce de N segundos** sobre el mismo tipo de transición. Sin esto: spam de mensajes.

```python
FUENTE_DEBOUNCE_SECS = int(os.getenv("MI_DEBOUNCE_SECS", "5"))
last_change_ts = 0.0

# dentro del loop, antes de notificar:
now = time.time()
if now - last_change_ts >= FUENTE_DEBOUNCE_SECS:
    notificar(...)
    last_change_ts = now
else:
    log(f"(debounce: silenciado)")
```

### Paso 7 — commit + memoria

- `git add` el `.py` + `.ps1` + `requirements.txt` + entrada en BACKLOG (logros recientes).
- Mensaje: `feat(<nombre>): listener event-driven via WMI (reemplaza ...)`.
- Si es un patrón realmente nuevo: actualizar memoria `project_wmi_event_listener.md` con el nuevo caso.

## Gotchas (descubiertos en el caso batería)

1. **`pythoncom.CoInitialize()` obligatorio.** Sin esto: `pywintypes.com_error -2147221008`.
2. **`delay_secs`** es polling INTERNO de WMI al kernel, no del código Python. Mantenerlo 2-5s.
3. **`timeout_ms` en `watcher()`** es crucial. Sin él, `watcher()` bloquea indefinidamente y SIGTERM no funciona.
4. **`x_wmi_timed_out`** se lanza cada `timeout_ms` si NO hubo evento. Capturar y `continue`.
5. **Latencia variable bajo ráfaga**: si llegan varios cambios en <2s, se encolan. Por eso el debounce protege Telegram, no el listener.
6. **WMI no es push puro**: bajo el capó WMI sondea al kernel. Pero el código del agente NO hace polling — solo reacciona a callbacks. Cumple la preferencia [[eventos-no-polling]].
7. **Lectura inicial antes del watch**: para procesar el estado actual, no esperar al primer cambio.

## Cómo operar un listener existente

```powershell
# Verificar estado
.\iniciar_<nombre>_listener.ps1 -Status

# Parar
.\iniciar_<nombre>_listener.ps1 -Stop

# Reiniciar
.\iniciar_<nombre>_listener.ps1 -Force

# Ver log en vivo (event stream)
Get-Content logs\<nombre>_listener.stdout.log -Wait -Tail 20
```

Y si Rhay quiere probar inmediatamente (caso batería): que enchufe/desenchufe el cable; los avisos deben llegar en ~1-3s.

## Referencias

- `bateria_event_listener.py` — implementación de referencia (180 líneas).
- `iniciar_bateria_listener.ps1` — template de launcher.
- `monitor_bateria.py` — script viejo (schtask), Disabled, mantenido por si hace falta revert.
- Memorias: `project_wmi_event_listener.md` (este patrón), `feedback_eventos_no_polling.md` (la preferencia general).
- Commits de referencia: `9c75fe1` (listener base), `73ee24a` (avisos enchufado/desenchufado con debounce).
