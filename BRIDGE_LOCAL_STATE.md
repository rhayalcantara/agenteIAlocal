# BRIDGE_LOCAL_STATE.md — Handoff para próximo Claude-local

Documento para que el próximo Claude que arranque en esta PC retome donde quedó esta sesión sin perder contexto.

**Última actualización:** 2026-05-14
**Sesión actual:** rama `/btw` de `b2f6b9e3-25a7-406f-8796-781ce87daa02`

---

## 1. Identidad y rol

- **Soy Claude-local** corriendo en la PC personal de Rhay (Windows 11, hostname `claude-local` en el tailnet)
- Mi par es **Claude-Ranger** en un Mac Studio M2 Ultra del cliente (`Mac-Studio-de-SIT.local`)
- Comunicación bidireccional via bridge HTTP sobre **Tailscale** (red privada, no expuesta a internet)
- Comunicación adicional con Rhay via **Telegram MCP** (bot `@bobito_rhay_bot`, chat_id `5483766132`)
- Comunicación con clientes via **WhatsApp** (proceso `whatsapp_monitor.js` corriendo, grupo prioritario "SISTEMA RAY" `120363424666838458@g.us`)

## 2. Red — Tailscale

- **Mi IP tailnet:** `100.89.251.75` (hostname `claude-local`)
- **IP de Claude-Ranger:** `100.91.126.66` (hostname `mac-studio-de-sit`)
- **Cuenta Tailscale:** la de Rhay (`rhayalcantara@`)
- **Binario:** `C:\Program Files\Tailscale\tailscale.exe`
- **Verificar:** `& "C:\Program Files\Tailscale\tailscale.exe" status`
- Otro nodo histórico: `nvsync-lpco010` (offline desde hace ~58 días, no es Ranger)

## 3. Bridge — variables de entorno

Están en `.env` raíz del proyecto (gitignored). Valores actuales:

```
BRIDGE_TOKEN=<32 chars urlsafe — ya en .env, NO escribir literal aquí>
BRIDGE_PORT=8765
BRIDGE_NODE=local
BRIDGE_LOCAL_URL=http://localhost:8765
BRIDGE_REMOTE_URL=  # nunca lo seteé aquí; uso to_url= en send() apuntando a 100.91.126.66:8765
```

El token DEBE coincidir literal con el `BRIDGE_TOKEN` en el .env de Ranger.

## 4. Código del bridge

Ubicación: `bridge/` (commiteado en `c05f15e`).

```
bridge/
├── __init__.py        # vacío
├── .gitignore         # excluye bridge_inbox.json + __pycache__/
├── server.py          # FastAPI, listening en 0.0.0.0:8765
├── client.py          # helpers send() poll() health()
├── poll_loop.py       # loop persistente que emite BRIDGE|from|text por stdout
├── requirements.txt
└── README.md
```

**Levantar server:** `python -m bridge.server` (lee .env)

**Levantar Monitor del inbox:** la herramienta `Monitor` con comando `python -u bridge/poll_loop.py`, descripción "Bridge inbox (mensajes de Claude-Ranger)", persistent=true, timeout_ms=3600000.

## 5. Cómo verificar que está vivo

```bash
# mi server
curl http://localhost:8765/health
# → {"ok":true,"node":"local","pending":N}

# server de Ranger (vía tailnet)
curl http://100.91.126.66:8765/health
# → {"ok":true,"node":"ranger","pending":N}

# tailnet
"C:\Program Files\Tailscale\tailscale.exe" status | grep -E "claude-local|mac-studio"
```

## 6. Cómo mandar mensajes a Claude-Ranger

```python
python -c "
import sys; sys.path.insert(0, '.')
from bridge.client import send
print(send('<texto>', to_url='http://100.91.126.66:8765', from_='claude-local'))
"
```

## 7. Cómo leer mensajes que Ranger me haya mandado

Si el Monitor está corriendo: aparecen automáticamente como `BRIDGE|claude-ranger|<texto>` en las notificaciones del chat.

Si no está corriendo (post-reinicio):

```python
python -c "
import sys; sys.path.insert(0, '.')
from bridge.client import poll
for m in poll():
    print(m)
"
```

## 8. Persistencia

- **Bridge server (`claude-bridge`):** **servicio Windows vía NSSM**, SERVICE_AUTO_START, AppExit Restart, AppRestartDelay 3000ms, AppThrottle 5000ms. Sobrevive reinicio del PC y crash del proceso.
  - NSSM binary: `C:\Users\rhay_\AppData\Local\Microsoft\WinGet\Packages\NSSM.NSSM_Microsoft.Winget.Source_8wekyb3d8bbwe\nssm-2.24-101-g897c7ad\win64\nssm.exe`
  - Python wrapper: `C:\proyectos\agenteIAlocal\venv\Scripts\python.exe -m bridge.server`
  - Logs: `C:\proyectos\agenteIAlocal\bridge\logs\bridge-stdout.log` y `bridge-stderr.log` (rotación 1MB)
  - Kill-survive verificado 2026-05-14: PID 15472 → kill → resucitado como PID 8636 en ~10s, /health respondió.
  - **Comandos de operación** (requieren elevación):
    - Estado: `Get-Service claude-bridge`
    - Arrancar: `& "<nssm.exe>" start claude-bridge`
    - Parar: `& "<nssm.exe>" stop claude-bridge`
    - Reinstalar: `bridge\install_service_windows.ps1` (script idempotente que detecta servicio existente y reinstala)
    - Test kill-survive: `bridge\test_killsurvive_windows.ps1`
    - Remover: `& "<nssm.exe>" remove claude-bridge confirm`
- **Monitor del inbox (Claude session):** task `bmtdybqby` en esta sesión, NO sobrevive cierre de Claude. Re-armar al inicio con `Monitor` tool + comando `python -u bridge/poll_loop.py`.
- **WhatsApp monitor (`whatsapp_monitor.js`):** proceso independiente Node.js (nohup). PID al momento: 16556. Verificar con: `Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -like '*whatsapp_monitor*' }`.
- **Tailscale:** servicio Windows persistente, sobrevive todo.
- **Cron Telegram + Monitor WhatsApp tail:** son cron/monitor de Claude session, NO sobreviven. Hay que rearmarlos al inicio (lo hace el hook SessionStart con instrucciones en `SESION_INICIO.md`).

## 9. Estado al cierre de esta sesión

- Round-trip live bridge ↔ Ranger **confirmado** (14 may 2026)
  - Ranger respondió: `host=Mac-Studio-de-SIT.local | when=2026-05-14 12:04:27 PDT | uptime=12:04 up 30 days, 4:23, 4 users | bridge-ranger PID 93050 | tailnet 100.91.126.66`
- Le pedí a Ranger que escriba su propio `BRIDGE_RANGER_STATE.md` simétrico. **Pendiente confirmación.**
- Bridge files commiteados (`c05f15e`) y **pusheados** a `origin/main`.
- Servicio Windows `claude-bridge` instalado y kill-survive verificado.
- `.gitignore` raíz tiene cambios sin commitear (telegram_offsets + bridge_inbox.json mezclados con otros pendientes).
- Scripts nuevos en `bridge/`: `install_service_windows.ps1` y `test_killsurvive_windows.ps1` — pendiente commit.

## 10. Recovery — si algo no funciona al retomar

1. **PRIMERO:** leer este MD entero antes de actuar
2. **SEGUNDO:** correr los 3 `curl /health` del paso 5
3. **TERCERO:** si mi bridge muerto → `python -m bridge.server` en background
4. **CUARTO:** si Ranger no responde a `health` → verificar `tailscale status`, mensajar a Rhay
5. **QUINTO:** rearmar Monitor del inbox + cron Telegram (ver SESION_INICIO.md y hook session-start.sh)
6. **SEXTO:** si nada de lo anterior funciona, no improvisar — preguntar a Rhay específicamente qué falla

## 11. Referencias cruzadas

- `SESION_INICIO.md` — hook de arranque de sesión, indica qué armar al inicio
- `BRIEFING_RANGER_BRIDGE.md` — instrucciones que se le enviaron a Ranger para su setup
- `bridge/README.md` — documentación técnica del bridge
- `REPORTE_CLAUDE_RANGER_BRIDGE.md` — reporte inicial del análisis (anterior al pivot a Tailscale)
- `respuesta_bridge_roadmap.html` — visualización del estado y hitos
- `CLAUDE.md` raíz — instrucciones generales del proyecto
- Memoria persistente: `C:\Users\rhay_\.claude\projects\C--proyectos-agenteIAlocal\memory\` — preferencias de Rhay, contexto del proyecto. Ver especialmente:
  - `feedback_telegram_cadencia.md` — cron Telegram a 5 min, NO escalar
  - `feedback_respuestas_html.md` — respuestas sustantivas en HTML
  - `feedback_python_vs_node.md` — Python para procesos, Node para listeners
  - `feedback_whatsapp_no_responder.md` — NUNCA WhatsApp sin permiso
  - `feedback_tomar_mando.md` — cuando Rhay sobrecargado, decidir y ejecutar
  - `project_ranger_hardware.md` — Mac Studio M2 Ultra
  - `user_horario_remoto.md` — lun/mié/vie remotos, caminata 17-18 sagrada

## 12. Notas de seguridad

- `BRIDGE_TOKEN` es secreto compartido. Solo en `.env` (gitignored) en ambas PCs.
- Bridge solo accesible via Tailscale (red privada). No expuesto a internet.
- WhatsApp: NUNCA responder al cliente sin permiso explícito de Rhay.

— claude-local, sesión del 2026-05-14
