# Auditoría de `llmcentral` — Fase 1

**Fecha:** 2026-05-06
**Commit auditado:** `c4c25d8 cotizacion hosting`

## Resumen ejecutivo

| Backend | Estado | Detalle |
|---|---|---|
| **LM Studio (OpenAI-compatible)** | ✅ Implementado | `lmstudio_client.py` — forward directo, sin transformaciones |
| **Ollama (OpenAI-compatible)** | ✅ Implementado | `ollama_client.py` — forward directo + traducción `Responses API ↔ Chat Completions` |
| **Anthropic API** | ❌ NO implementado | Cero referencias en el repo (`grep -ri "anthropic\|claude"` → 0 matches) |

**Conclusión:** el repo no soporta Anthropic. Hay que añadirlo como backend nuevo siguiendo el patrón existente. La arquitectura es lo suficientemente modular para hacerlo limpiamente.

---

## Arquitectura observada

### Gateway (Node.js / Fastify v5)

```
src/
├── server.ts                   ← bootstrap Fastify
├── config.ts                   ← env vars con zod
├── auth/apiKey.ts              ← bearer auth opcional
├── routes/
│   ├── health.ts               ← GET /health, /debug/workers
│   ├── chatCompletions.ts      ← POST /v1/chat/completions (stream + non-stream)
│   ├── responses.ts            ← POST /v1/responses (NO stream aún)
│   ├── models.ts               ← GET /v1/models (union de workers)
│   └── workerWs.ts             ← GET /ws/worker (WebSocket entrante)
├── workers/
│   ├── connection.ts           ← clase WorkerConnection (in-flight tracking)
│   ├── registry.ts             ← workerRegistry singleton (byInternalId, byModel)
│   └── protocol.ts             ← schemas zod del protocolo WS
└── balancer/leastConnections.ts ← pickWorkerForModel()
```

**Routing por modelo:** el cliente envía `{model: "X"}` → gateway llama `pickWorkerForModel("X")` → si hay worker que sirve ese modelo → manda mensaje WS al worker. Si no hay worker → 503.

**Lo que el gateway no inspecciona:** el gateway **no toca el body** del request — lo pasa tal cual al worker. Toda la lógica de "cómo hablar con cada backend" está en el worker. Esto es bueno: implementar Anthropic NO requiere tocar el gateway en absoluto.

**Protocolo WS (worker ↔ gateway):**

| Mensaje | Dirección | Cuándo |
|---|---|---|
| `worker_register` | W → G | al conectar (envía lista de modelos + api_key) |
| `worker_registered` | G → W | confirmación |
| `ping` / `pong` | G ↔ W | heartbeat 30s |
| `inference_request` | G → W | para `/v1/chat/completions` non-stream |
| `inference_response` | W → G | respuesta |
| `stream_request` | G → W | para `/v1/chat/completions` con `stream:true` |
| `stream_chunk` / `stream_done` / `stream_error` | W → G | streaming SSE |
| `raw_request` | G → W | para `/v1/responses` |
| `raw_response` | W → G | respuesta |
| `cancel_request` | G → W | abortar request en vuelo |

### Worker (Python 3.11+)

```
llm-worker/
├── worker.py            ← GatewayWorker, loop WS, dispatch a clientes
├── config.py            ← env vars
├── lmstudio_client.py   ← LMStudioClient
├── ollama_client.py     ← OllamaClient (con conversión Responses↔Chat)
├── ejemplo_cliente.py   ← cliente de prueba
└── requirements.txt     ← websockets + httpx
```

**Patrón del worker:**
1. Conecta WS al gateway
2. **Descubre modelos** en cada backend habilitado, construye mapa `model → backend`
3. Envía `worker_register` con la unión de modelos
4. Loop de mensajes:
   - `inference_request` → `_get_client(model).chat_completion(request)` → `inference_response`
   - `raw_request` → `_get_client(model).raw_request(endpoint, request)` → `raw_response`
   - `ping` → `pong`

**Interfaz que cumple cada cliente** (LMStudioClient / OllamaClient):
```python
class XClient:
    async def get_models(self) -> list[str]: ...
    async def chat_completion(self, request: dict) -> dict: ...    # OpenAI Chat Completions IN/OUT
    async def raw_request(self, endpoint: str, request: dict) -> dict: ...  # /v1/responses u otro
    async def close(self) -> None: ...
```

**Prioridad de backends:** LM Studio gana sobre Ollama si un modelo existe en ambos.

---

## Cómo enchufar un backend nuevo (patrón observado)

Para agregar `Anthropic` (o cualquier otro), hay que tocar SOLO el worker:

1. **Crear** `llm-worker/anthropic_client.py` que cumpla la interfaz arriba.
2. **`config.py`:** añadir `ANTHROPIC_API_KEY`, `ANTHROPIC_ENABLED`, posiblemente `ANTHROPIC_MODELS` (lista) o `ANTHROPIC_BASE_URL`.
3. **`worker.py`:**
   - Constante `BACKEND_ANTHROPIC = "anthropic"`
   - Import + instancia condicional en `__init__`
   - Bloque en `_discover_models()` (Anthropic NO descubre por API — lista declarada)
   - Caso en `_get_client()` para devolver el cliente correcto

El gateway **no se toca**.

---

## Diferencias clave Anthropic vs OpenAI Chat Completions

| Concepto | OpenAI | Anthropic |
|---|---|---|
| Endpoint | `POST /v1/chat/completions` | `POST /v1/messages` |
| Auth | `Authorization: Bearer ...` | `x-api-key: ...` + `anthropic-version: 2023-06-01` |
| `system` | item dentro de `messages[]` | campo separado `system` |
| `content` | string (mostly) | array de blocks `[{type: "text"|"image"|"tool_use"|...}]` |
| `max_tokens` | opcional | **obligatorio** |
| Tools | `tools[]` con `function` schema | `tools[]` con `input_schema` |
| Tool calls | `assistant.tool_calls[]` | `content[]` con bloque `tool_use` |
| Stop | `finish_reason: "stop"|"length"|"tool_calls"` | `stop_reason: "end_turn"|"max_tokens"|"tool_use"` |
| Modelos | `/v1/models` API | hardcoded list |
| Streaming SSE | `delta: {content: "..."}` | eventos: `message_start`, `content_block_delta`, `message_delta`, `message_stop` |

**Implicación:** `anthropic_client.py` debe hacer traducción bidireccional. Ya hay precedente (`ollama_client._responses_to_chat`/`_chat_to_responses`).

---

## Bugs / observaciones colaterales (no bloqueantes para Anthropic)

| # | Severidad | Detalle |
|---|---|---|
| B1 | 🟡 medio | `LMStudioClient()` y `OllamaClient()` se instancian en `worker.py` sin pasar `base_url`. Los defaults del constructor (`http://localhost:1234`, `http://192.168.2.165:11434`) sobreescriben los `LMSTUDIO_URL` y `OLLAMA_URL` del config. Las env vars no se aplican. |
| B2 | 🟡 medio | `OllamaClient` tiene IP hardcoded `192.168.2.165` como default — sospechoso. Debería ser `localhost`. |
| B3 | 🟢 bajo | Worker no implementa handler `stream_request` (README lo confirma como ⏳). Sin esto, `chat/completions` con `stream:true` no funciona end-to-end. |
| B4 | 🟢 bajo | Worker no implementa `cancel_request`. El gateway lo manda en timeout, pero el worker lo ignora. |
| B5 | 🟢 bajo | Sin tests automatizados. |
| B6 | 🟢 bajo | Sin Dockerfile / no hay deploy declarado, aunque `Doc/hosting.md` puede tener pistas. |

---

## Decisiones que necesito de Rhay para Fase 3

1. **Lista de modelos Anthropic a soportar:** ¿hardcoded los 3 principales (`claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5-20251001`) o configurable via env (`ANTHROPIC_MODELS=claude-opus-4-7,claude-...`)?
2. **Tools en v1?** (formato muy distinto). Sí/no.
3. **Streaming Anthropic en v1?** (requiere antes implementar `stream_request` handler en worker — bug B3).
4. **Visión / imágenes en v1?** (Anthropic soporta imágenes inline base64; OpenAI también con formato distinto).
5. **¿Aprovechamos para arreglar B1+B2?** Es un fix de ~5 líneas y desbloquea que `OLLAMA_URL` funcione bien.

---

## Recomendación

**Fase 2 sigue siendo necesaria** para validar que el repo funciona end-to-end con LM Studio + Ollama antes de meter Anthropic. Si los smoke tests fallan por B1/B2, los arreglamos ahí mismo.

**Fase 3 mínima viable** sería: cliente Anthropic non-stream, sin tools, con lista hardcoded de los 3 modelos principales. Eso valida el patrón y deja la base para iterar (streaming, tools, visión).
