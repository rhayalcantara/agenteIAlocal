#!/usr/bin/env bash
# SessionStart hook — agenteIAlocal
# Idempotente: arranca whatsapp_monitor.js si no corre, deja un mensaje
# para Claude en additionalContext con los siguientes pasos.

set -uo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR" || exit 0

monitor_status="unknown"

# Detectar proceso whatsapp_monitor.js (en Windows via PowerShell)
existing_pid=$(powershell.exe -NoProfile -Command "
  try {
    (Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" |
       Where-Object { \$_.CommandLine -match 'whatsapp_monitor' } |
       Select-Object -First 1).ProcessId
  } catch { }
" 2>/dev/null | tr -d '\r\n ' | head -c 10)

if [ -n "$existing_pid" ] && [ "$existing_pid" -gt 0 ] 2>/dev/null; then
  monitor_status="running PID $existing_pid"
else
  # Limpiar lockfile huérfano antes de arrancar
  rm -f .wwebjs_auth/session/lockfile 2>/dev/null || true
  nohup node whatsapp_monitor.js >> whatsapp_monitor.log 2>&1 &
  monitor_status="started PID $!"
fi

# Mensaje para Claude vía additionalContext
python -c "
import json, sys
msg = '''WhatsApp monitor: ${monitor_status}.

PASOS A EJECUTAR EN ESTA SESIÓN:
1. Armar Monitor persistente con: tail -F whatsapp_monitor.log filtrado por '^MSG|' — recibe DMs y grupos en tiempo real.
2. Crear cron Telegram cada 5 min (CronCreate */5 * * * *) que ejecute mcp__telegram__leer_mensajes. Tras recibir un mensaje, cambiar a 30 min. Tras 8 ciclos vacíos en 30 min, volver a 5 min.
3. Backend Ranger (3333) y frontend Angular (4200) NO se arrancan automáticamente — los lanza el usuario si los necesita.

Refs: SESION_INICIO.md, skills/whatsapp-listener/, skills/telegram-agent-monitor/'''
print(json.dumps({
  'hookSpecificOutput': {
    'hookEventName': 'SessionStart',
    'additionalContext': msg
  }
}))
"
