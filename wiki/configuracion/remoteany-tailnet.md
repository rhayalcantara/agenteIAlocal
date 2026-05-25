# RemoteAny sobre Tailscale (bidireccional)

`remoteany` (`C:\remoteany` aquí; `/Users/sitservidorranger/sistemas/remoteany` en Mac) es el escritorio-remoto-DIY de Rhay tipo AnyDesk: captura pantalla con `mss`, simula mouse/teclado con `pyautogui` + `pynput`, transporta frames JPEG vía WebSocket.

Originalmente diseñado con un **relay público** en Oracle Cloud (`140.238.181.102:9877`) para puentear NAT. **Decisión del 25-may-2026:** descartar el relay para uso interno y usar Tailscale como transporte. Mejor cifrado (WireGuard end-to-end vs `ws://` plano), mejor auth (identidad de nodo vs password compartido), menor latencia (peer-to-peer, no Sao Paulo).

## Arquitectura

```
Mac Studio M2 (Ranger)               Windows (claude-local)
100.91.126.66                        100.89.251.75
─────────────────                    ─────────────────
host_headless :9876   ◀── ws ──▶     agent_client.py / GUI viewer
viewer / agent_client ◀── ws ──▶     host (GUI "Start Sharing") :9876
        ▲                                     ▲
        └── via tailnet WireGuard, NO relay Oracle ──┘
```

Cualquier nodo del tailnet puede ser **host** (ofrece su pantalla), **viewer** (controla otro), o ambos. Hoy ambas máquinas son ambos roles según necesidad.

## Setup Mac (host persistente)

Hecho por Claude-Ranger el 25-may. Resumen para futura referencia:

- **Repo:** `/Users/sitservidorranger/sistemas/remoteany` branch `main`.
- **Venv:** `venv/` con Python 3.13. Deps mínimas (sin PyQt6, headless): `mss`, `Pillow`, `pyautogui`, `pynput`, `websockets`, `numpy`, `pyobjc-*`.
- **Wrapper headless:** `host_headless.py` (49 líneas, NO en repo). Lee env vars `REMOTEANY_HOST`, `REMOTEANY_PORT`, `REMOTEANY_FPS`, `REMOTEANY_QUALITY`, `REMOTEANY_PASSWORD`. Usa `HostServer` directo, sin GUI ni registro al relay.
- **LaunchAgent:** `~/Library/LaunchAgents/com.rhay.remoteany.plist`.
  - `RunAtLoad: true` — arranca al login.
  - `KeepAlive: SuccessfulExit=false` — resucita si crashea, respeta stop manual con SIGTERM.
  - `ThrottleInterval: 10s` — evita crash-loop infinito.
  - `EnvironmentVariables`: `REMOTEANY_HOST=100.91.126.66` (bind tailnet-only).
  - `StdOut/StdErr: /tmp/remoteany_host.log`.
  - Cargado con: `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/com.rhay.remoteany.plist`.
- **Verificación bind:** `lsof -i :9876` → LISTEN solo en `100.91.126.66:9876` (loopback y `*` no responden).
- **Permisos macOS** (concedidos por Rhay manualmente):
  - System Settings → Privacy & Security → **Screen Recording** → `python3` del venv. Sin esto: frames negros.
  - System Settings → Privacy & Security → **Accessibility** → `python3` del venv. Sin esto: clicks/keys ignorados.
  - Después de conceder permisos, el LaunchAgent los hereda sin reiniciar.

**Kill-survive test (pasado):**
- `SIGTERM` → launchd NO reinicia (correcto: stop manual cuenta como `SuccessfulExit=true`).
- `SIGKILL -9` → resucita en ~10s con PID nuevo, `/health` responde 426 OK.

## Setup Windows local (esta PC)

- **Repo:** `C:\remoteany`.
- **Venv:** `.venv\Scripts\python.exe` con todas las deps + `PyQt6` (para GUI).
- **Launcher GUI:** `C:\remoteany\iniciar_viewer.ps1` — abre la app PyQt6 para conectarte a cualquier host del tailnet.
- **Modo host** (cuando querés que la Mac controle esta PC): abrir GUI normalmente con `iniciar_viewer.ps1`, dentro click "Start Sharing". Esta PC empieza a escuchar en `0.0.0.0:9876`.
- **Modo agent CLI** (para mí, Claude): `python src/agent_client.py start --host <ip> --port 9876`.

**Persistencia en esta PC:** NO hay LaunchAgent equivalente todavía. Si querés que el host arranque con Windows, opciones:
1. Atajo de inicio (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`) apuntando a `iniciar_viewer.ps1` (pero requiere desktop logged in).
2. Tarea programada `schtasks /create /sc onlogon` con `iniciar_host_headless.ps1` (sin GUI). Hay que escribir el equivalente `host_headless.py` para Windows si querés sin GUI — el actual del Mac es portable, debería funcionar.

Hoy: arrancar manualmente cuando se necesite. Si el caso de uso crece (Rhay quiere conectar desde el celular al desktop), montamos persistencia tipo schtask.

## Cómo conectar desde A → B

Donde A es el viewer, B es el host con `host_headless` o GUI en "Start Sharing".

```python
# Vía GUI (PyQt6, cualquier nodo)
# Abrir RemoteAny → Connect → IP del host (100.x.y.z) → Port 9876 → sin password

# Vía CLI (cualquier nodo con Python + remoteany clonado)
python src/agent_client.py start --host 100.91.126.66 --port 9876 --fps 5 --quality 50
python src/agent_client.py screenshot   # guarda frame.jpg
python src/agent_client.py move --x 960 --y 540
python src/agent_client.py click --x 500 --y 300
python src/agent_client.py type --text "hola"
python src/agent_client.py stop
```

## Decisiones tomadas

| Decisión | Estado | Por qué |
|----------|--------|---------|
| Sin relay Oracle | ✅ | Tailscale ya provee transporte cifrado P2P. Menos infra que mantener. |
| Bind tailnet-only (`100.91.126.66`) en Mac | ✅ | Firewall macOS está off → con `0.0.0.0` se exponía a la LAN entera. Cerrar a tailnet limita superficie. |
| Sin password al stream | ✅ | Tailnet ya es red de confianza (solo nodos autorizados de Rhay). Si en algún momento se agregan nodos compartidos, se reabrirá password. |
| LaunchAgent persistente en Mac | ✅ | Sobrevive reboot + crash. |
| Persistencia en Windows | ⏳ pendiente | Arrancar manual hoy. Schtask si se vuelve crítico. |

## Verificación end-to-end (25-may-2026)

| Test | Resultado |
|------|-----------|
| Mac host alcanzable desde esta PC via tailnet | ✅ TCP `100.91.126.66:9876` SUCCESS |
| Stream Mac → esta PC (frame_count=425) | ✅ Frames con contenido (no negros) |
| `agent_client move 960,540` desde esta PC | ✅ Cursor saltó en Mac (validado por Rhay visualmente) |
| `agent_client move 1500,200` desde esta PC | ✅ Cursor saltó en Mac |
| Esta PC host + Mac viewer + Rhay click desde Mac | ✅ Funciona bi-direccional |
| LaunchAgent kill-survive (SIGKILL → resucita) | ✅ Validado por Claude-Ranger antes del handover |

## Limitaciones conocidas

- **mss en macOS NO captura el cursor** en los frames. El cursor en el host SÍ se mueve cuando llega el comando, pero la captura para el viewer no lo dibuja. Workaround mental: confiar en `OK` de los `move`/`click`. Si en algún momento se quiere ver el cursor remoto, hay que dibujarlo en el cliente con `pyautogui.position()` post-comando.
- **`ws://` plano dentro del tailnet** — cifrado por WireGuard a nivel transporte, pero el header WebSocket en sí no es TLS. Para un atacante que ya esté dentro del tailnet, esto es irrelevante; para defense-in-depth contra exfiltración futura, agregar `wss://` (issue anotado en `C:\remoteany\Docs\plan mejoras.md`).
- **Sin auth en LAN directa** — si en algún momento se desactiva el bind tailnet-only y se expone `0.0.0.0`, agregar password antes de eso.

## Relacionado

- `BRIEFING_RANGER_BRIDGE.md` — el bridge HTTP `:8765` que usamos para coordinar Claude-local ↔ Claude-Ranger durante la integración.
- [worker-hub](worker-hub.md) — otro servicio del tailnet (LLM pool).
- [gateway-anthropic](gateway-anthropic.md) — otro servicio del tailnet (proxy Anthropic).
- `C:\remoteany\CLAUDE.md`, `C:\remoteany\AGENT_GUIDE.md` — docs del proyecto remoteany propiamente.
