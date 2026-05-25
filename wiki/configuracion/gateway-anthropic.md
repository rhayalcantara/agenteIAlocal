# Gateway Anthropic-compatible expuesto al tailnet

`anthropic_gateway/` (FastAPI :8400) traduce `POST /v1/messages` (Anthropic) ↔ `POST /chat/completions` (OpenAI). Permite usar el SDK oficial de Anthropic apuntando a un backend OpenAI-compatible (en este caso, LM Studio remoto).

## Decisión: Tailscale, NO Cloudflare Tunnel

Inicialmente el BACKLOG pedía Cloudflare Tunnel. **Se descartó** porque ya tenemos Tailscale corriendo (ver `BRIEFING_RANGER_BRIDGE.md`) y todos los consumidores potenciales del gateway viven en el tailnet:

- `claude-local` (esta PC) — `100.89.251.75`
- `mac-studio-de-sit` (Ranger) — `100.91.126.66`
- `a36-de-rhay` (móvil) — `100.122.63.59`

Tailscale ya da:
- Conexión cifrada peer-to-peer (WireGuard).
- IPs estables que solo conocen los nodos autorizados.
- Cero exposición a internet pública.
- Cero costo extra (CF Tunnel free tier vs Tailscale free tier — ya está montado).

Si en algún momento un consumidor **fuera del tailnet** necesita el gateway (ej. un servicio cloud), se reabre CF Tunnel como capa adicional. Hoy no.

## URLs

| Desde | URL |
|-------|-----|
| Esta máquina | `http://127.0.0.1:8400/v1/messages` |
| Cualquier nodo del tailnet | `http://100.89.251.75:8400/v1/messages` |
| MagicDNS (si está activo) | `http://claude-local:8400/v1/messages` |

`GET /health` responde `{"ok":true}` sin auth — útil para healthchecks de uptime.

## Autenticación

Por header `x-api-key` o `Authorization: Bearer <key>`. La key se valida contra `ANTHROPIC_GATEWAY_API_KEY` del `.env` (44 chars urlsafe, generada con `secrets.token_urlsafe(32)`).

Si la env está vacía, el gateway acepta cualquier request — **no dejarla vacía** mientras el puerto esté en el tailnet.

## Arranque / parada

```powershell
# arrancar (idempotente, no duplica si ya corre)
.\iniciar_gateway.ps1

# estado + health
.\iniciar_gateway.ps1 -Status

# parar
.\iniciar_gateway.ps1 -Stop

# reiniciar
.\iniciar_gateway.ps1 -Force
```

Logs en `anthropic_gateway/data/uvicorn.log` (stdout) y `uvicorn.log.err` (stderr de uvicorn).

**Modo de uso:** on-demand. No se arranca con Windows; Rhay lo levanta cuando va a usar el SDK de Anthropic desde otra PC del tailnet. Para 99% del tiempo está apagado.

## Regla de firewall Windows (requiere admin)

Sin esta regla, conexiones inbound desde otros nodos del tailnet a `:8400` pueden ser bloqueadas por el firewall de Windows. Para abrir SOLO al rango CGNAT de Tailscale (NO a LAN ni internet):

```powershell
# PowerShell elevado (Run as Administrator)
New-NetFirewallRule -DisplayName "anthropic_gateway 8400 tailnet" `
    -Description "Inbound al gateway anthropic-compatible desde tailnet" `
    -Direction Inbound -Protocol TCP -LocalPort 8400 `
    -RemoteAddress 100.0.0.0/8 -Action Allow -Profile Any
```

Borrar regla si hace falta:
```powershell
Remove-NetFirewallRule -DisplayName "anthropic_gateway 8400 tailnet"
```

## Uso desde otra PC del tailnet

**SDK oficial Anthropic (Python):**
```python
import os
os.environ["ANTHROPIC_API_KEY"]  = "<key del .env del host>"
os.environ["ANTHROPIC_BASE_URL"] = "http://100.89.251.75:8400"

from anthropic import Anthropic
client = Anthropic()
resp = client.messages.create(
    model="liquid/lfm2-24b-a2b",
    max_tokens=50,
    messages=[{"role": "user", "content": "hola"}],
)
print(resp.content[0].text)
```

**curl directo:**
```bash
curl http://100.89.251.75:8400/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: <key del .env>" \
  -d '{"model":"liquid/lfm2-24b-a2b","max_tokens":50,
       "messages":[{"role":"user","content":"di pong"}]}'
```

## Verificación end-to-end (25-may-2026)

| Test | Resultado |
|------|-----------|
| `/health` localhost | 200 `{"ok":true}` |
| `/health` IP tailnet `100.89.251.75:8400` | 200 `{"ok":true}` |
| `/v1/messages` SIN `x-api-key` | 401 (esperado) |
| `/v1/messages` CON key correcta | 200 + respuesta Anthropic-shape |

Falta validar conectividad desde **otro nodo del tailnet** (la Mac de Ranger). Para hacerlo: desde ahí, `curl http://100.89.251.75:8400/health` debe devolver `{"ok":true}` una vez que la regla de firewall esté aplicada en esta PC.

## Backend del gateway

A partir de 25-may, el `LMSTUDIO_BASE_URL` original (`ntempurl/api/v1`) se reemplazó por **el `worker_hub` local en `http://127.0.0.1:8500/v1`**. El gateway sigue traduciendo Anthropic↔OAI; el routing a Ranger / remoto / etc. lo hace el hub.

Env vars que controlan el backend del gateway (con precedencia sobre `LMSTUDIO_*` legacy):
- `ANTHROPIC_GATEWAY_BACKEND_URL=http://127.0.0.1:8500/v1`
- `ANTHROPIC_GATEWAY_BACKEND_KEY=<WORKER_HUB_API_KEY>` (literal, no expansion)

Si el hub está abajo, el gateway responderá 502/upstream unreachable. Para evitarlo, arrancar el hub primero (`.\iniciar_worker_hub.ps1`).

Ver [worker_hub](worker-hub.md) para detalles del pool.

## Relacionado

- `BRIEFING_RANGER_BRIDGE.md` — setup del bridge Tailscale entre Claude-local y Claude-Ranger (mismo modelo, otro servicio en :8765).
- `anthropic_gateway/README.md` — detalles del proxy y endpoints.
- [worker_hub](worker-hub.md) — el pool de LLMs que ahora sirve de backend.
