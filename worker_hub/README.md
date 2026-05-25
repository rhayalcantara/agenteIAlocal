# worker_hub

Pool de workers LLM detrás de un endpoint OpenAI-compatible único. Centraliza acceso a múltiples backends OAI (LM Studio Mac, LM Studio Windows, proxies remotos…) y rutea por **nombre de modelo**.

## Arquitectura

```
Cliente (cualquier nodo tailnet)
    │ GET  /v1/models             ← unión de catálogos
    │ POST /v1/chat/completions   ← sync o streaming
    │ POST /v1/embeddings
    ▼
worker_hub :8500 (esta PC, Windows)
    │  - Carga workers.json al boot.
    │  - Probe GET /v1/models a cada worker cada 30s.
    │  - Selecciona por body.model (worker con más prioridad y que lo tenga).
    │  - Header `x-worker: <name>` fuerza un worker específico.
    │  - Failover en 5xx (intenta siguiente worker con el modelo).
    │
    ├──▶ ranger  : http://100.91.126.66:1234/v1   (LM Studio Mac M2)
    └──▶ remoto  : https://rhayalcantara-002-site2.ntempurl.com/api/v1
```

## Endpoints

| Método | Path | Auth | Descripción |
|---|---|---|---|
| GET | `/` | no | metadata + lista de endpoints |
| GET | `/health` | no | liveness del hub (`workers_total`, `workers_healthy`) |
| GET | `/v1/models` | sí | catálogo unificado, cada modelo con `workers: [name1, name2…]` |
| POST | `/v1/chat/completions` | sí | sync o streaming SSE (según `body.stream`) |
| POST | `/v1/completions` | sí | legacy completions (no chat) |
| POST | `/v1/embeddings` | sí | embeddings (un solo worker, sin stream) |
| GET | `/workers` | sí | snapshot detallado (debugging) |

**Auth:** header `x-api-key: <key>` o `Authorization: Bearer <key>`. Validada contra `WORKER_HUB_API_KEY` del `.env`.

## Selección de worker

1. Si llega header `x-worker: <name>` → se usa ese worker (override; no se valida que tenga el modelo, el cliente "sabe lo que hace").
2. Si no, se buscan workers `enabled=true && healthy=true && model in workers.models`, ordenados por `priority` descendente.
3. Si la lista es vacía → 404 `ningún worker tiene el modelo 'X'`.
4. Si el worker elegido devuelve 5xx → failover automático al siguiente. Si todos fallan → último error propagado.

**Streaming (`body.stream=true`):** NO hay failover mid-stream. Se envía al primer candidato, si falla la conexión se cierra con un evento de error.

## Config workers (`workers.json`)

```json
{
  "workers": [
    {
      "name": "ranger",
      "base_url": "http://100.91.126.66:1234/v1",
      "priority": 10,
      "enabled": true,
      "api_key_env": null,
      "notes": "LM Studio Mac M2 (tailnet)."
    },
    {
      "name": "remoto",
      "base_url": "https://rhayalcantara-002-site2.ntempurl.com/api/v1",
      "priority": 5,
      "enabled": true,
      "api_key_env": "LMSTUDIO_API_KEY",
      "notes": "Backend OAI publico."
    }
  ]
}
```

**Para agregar un worker nuevo:** editar `workers.json`, reiniciar el hub con `.\iniciar_worker_hub.ps1 -Force`. El probe inicial descubre los modelos cargados.

## Comportamiento del probe

Cada 30s (`WORKER_HUB_HEALTH_INTERVAL` env) hace `GET {base_url}/models`:

- **HTTP 2xx con JSON `{data: [{id: ...}]}`** → healthy + catálogo actualizado.
- **HTTP 2xx con body que no es JSON** (ej. reverse-proxy que solo expone POST y sirve HTML en GET) → healthy con catálogo vacío. Worker no es candidato automático por modelo, pero sí accesible con `x-worker: <name>` explícito.
- **HTTP 4xx/5xx o timeout** → unhealthy. No es candidato.

## Arranque / parada (Windows)

```powershell
.\iniciar_worker_hub.ps1            # idempotente
.\iniciar_worker_hub.ps1 -Status    # estado + health
.\iniciar_worker_hub.ps1 -Stop
.\iniciar_worker_hub.ps1 -Force     # reinicio
```

Logs: `worker_hub/data/uvicorn.log` (stdout) y `uvicorn.log.err` (todo lo que loggea registry/proxy).

## Variables de entorno

| Var | Default | Uso |
|---|---|---|
| `WORKER_HUB_API_KEY` | "" | auth de clientes; vacío = auth abierta (⚠️ no en tailnet) |
| `WORKER_HUB_HEALTH_INTERVAL` | 30 | segundos entre probes |
| `WORKER_HUB_HEALTH_TIMEOUT` | 5 | timeout del probe HTTP |
| `WORKER_HUB_PROXY_TIMEOUT` | 300 | timeout de las peticiones LLM (modelos grandes tardan) |
| `WORKER_HUB_LOG` | INFO | nivel de logging |

API keys de cada worker se referencian por nombre de env via `api_key_env` en `workers.json` (ej. `"api_key_env": "LMSTUDIO_API_KEY"`).

## Ejemplos de uso

**1) OpenAI SDK:**
```python
from openai import OpenAI
client = OpenAI(
    base_url="http://100.89.251.75:8500/v1",
    api_key="<WORKER_HUB_API_KEY>",
)
r = client.chat.completions.create(
    model="liquid/lfm2-24b-a2b",
    messages=[{"role": "user", "content": "di hola"}],
)
print(r.choices[0].message.content)
```

**2) Forzar worker específico (header `x-worker`):**
```python
client = OpenAI(
    base_url="http://100.89.251.75:8500/v1",
    api_key="<WORKER_HUB_API_KEY>",
    default_headers={"x-worker": "remoto"},
)
```

**3) Catálogo unificado:**
```bash
curl -s http://100.89.251.75:8500/v1/models -H "x-api-key: <key>" | jq '.data[] | "\(.id) -> \(.workers)"'
```

**4) Vía `anthropic_gateway` (clientes Anthropic SDK):**
El gateway `:8400` apunta su backend a este hub en `127.0.0.1:8500`. Ver `wiki/configuracion/gateway-anthropic.md`.

## Estructura

```
worker_hub/
├── workers.json         # registro de workers
├── main.py              # FastAPI app + lifespan + /, /health, /workers
├── core/
│   ├── registry.py      # Registry + health-check loop
│   └── proxy.py         # forward sync + streaming + failover
├── routes/
│   ├── auth.py          # require_api_key dep
│   ├── models.py        # GET /v1/models
│   ├── chat.py          # POST /v1/chat/completions, /v1/completions
│   └── embeddings.py    # POST /v1/embeddings
└── data/                # logs uvicorn
```

## Pendiente / futuro

- ⚠️ **Auto-register endpoint** — workers se anuncian con `POST /register` en vez de estar hard-coded en `workers.json`. Requiere que cada LM Studio tenga un sidecar que haga el registro (LM Studio nativo no lo hace).
- ⚠️ **Métricas Prometheus** — requests/worker, latencia, errores. Hoy solo logs.
- ⚠️ **Rate limiting por API key** — si en algún momento se comparten keys con terceros.
- ⚠️ **Cache de `/v1/models`** — hoy se recalcula en cada GET. Trivial pero N=2 workers no es problema.

## Verificación end-to-end (2026-05-25)

| Test | Resultado |
|------|-----------|
| `/health` localhost | 200, workers_healthy=2 |
| `/health` IP tailnet `100.89.251.75:8500` | 200 |
| `/v1/models` autenticado | 36 modelos únicos (ranger 7 + remoto 31, solapan `liquid/lfm2-24b-a2b` y `text-embedding-nomic-embed-text-v1.5`) |
| `/v1/models` sin auth | 401 |
| `/v1/chat/completions` modelo solo-ranger | 200, ruteado a ranger |
| `/v1/chat/completions` modelo solo-remoto | 200, ruteado a remoto |
| `/v1/chat/completions` con `x-worker: remoto` | 200, forzado a remoto |
| Streaming SSE vía gateway `:8400` → hub `:8500` → ranger | eventos Anthropic-shape OK |
