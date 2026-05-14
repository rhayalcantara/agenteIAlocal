# claude-bridge

Mini-bridge HTTP para comunicación entre dos instancias de Claude Code corriendo en redes distintas.

## Cómo funciona

Cada PC corre `server.py`. Cuando un Claude quiere mandar a la otra instancia, hace `POST /inbox` a la URL pública del otro server (vía cloudflared tunnel). Cuando quiere leer mensajes que llegaron para él, hace `GET /poll` contra su propio server (localhost).

```
Claude-local ──POST── https://claude-ranger.dom/inbox ──> server (Ranger)
                                                              ▼
                                                       bridge_inbox.json
                                                              ▲
                                                  Claude-ranger ──GET── http://localhost:8765/poll
```

## Instalación

```bash
pip install -r bridge/requirements.txt
```

Generar token y agregar a `.env` en la raíz del proyecto:

```
BRIDGE_TOKEN=<32+ chars aleatorios>
BRIDGE_PORT=8765
BRIDGE_NODE=local  # o "ranger" en la otra PC
BRIDGE_REMOTE_URL=https://claude-ranger.example.workers.dev  # opcional default para send()
```

## Levantar

```bash
python -m bridge.server
# o
python bridge/server.py
```

## Usar desde Claude

```python
from bridge.client import send, poll, health

# enviar al otro lado
send("git status del repo Ranger", from_="claude-local")

# leer mi propio inbox
for m in poll():
    print(m["from"], m["text"])

# verificar
health()
```

## Endpoints

| Método | Path | Auth | Descripción |
|---|---|---|---|
| POST | `/inbox` | `X-Bridge-Token` | Encola mensaje. Body: `{text, from_, meta}` |
| GET | `/poll?consume=true` | `X-Bridge-Token` | Lee + (opcional) vacía inbox |
| GET | `/health` | público | Status + pending count |

## Exponer al exterior

Cloudflare Tunnel (free):

```bash
cloudflared tunnel --url http://localhost:8765
# da una URL pública tipo https://random.trycloudflare.com
```

Para URL estable, crear cuenta CF y túnel nombrado (`cloudflared tunnel create claude-local` + DNS routing).

Plan B si CF cambia: `no-ip.com`, `ngrok` (1 endpoint free), `localtunnel`.
