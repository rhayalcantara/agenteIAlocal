# anthropic_gateway

Proxy Anthropic-compatible que traduce `POST /v1/messages` (schema Anthropic) a `POST /chat/completions` (schema OpenAI) y vuelve. Permite usar SDK Anthropic (Python / JS / etc.) apuntando a tu gateway LM Studio local en lugar de a `api.anthropic.com`.

## Arquitectura

```
Anthropic SDK ──POST /v1/messages──▶ anthropic_gateway :8400
                                              │
                                              ▼ translate (Anthropic → OAI)
                                       LMSTUDIO_BASE_URL/chat/completions
                                              ▼
                                       LM Studio gateway → worker LLM
                                              ▲
                                              ▼ translate (OAI → Anthropic)
Anthropic SDK ◀── JSON Anthropic ─── anthropic_gateway
```

## Arranque

```bash
venv/Scripts/python.exe -m uvicorn anthropic_gateway.main:app --host 0.0.0.0 --port 8400
```

Variables `.env`:
- `LMSTUDIO_BASE_URL` — backend OAI (default `https://rhayalcantara-002-site2.ntempurl.com/v1`)
- `LMSTUDIO_API_KEY` — Bearer del backend
- `ANTHROPIC_GATEWAY_API_KEY` — opcional, si lo setás, requiere `x-api-key` o `Authorization: Bearer` que coincida
- `ANTHROPIC_GATEWAY_TIMEOUT` — segundos (default 120)

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| GET | `/` | metadata |
| GET | `/health` | liveness |
| POST | `/v1/messages` | endpoint Anthropic (sync + stream) |

## Smoke tests verificados

**curl no-stream:**
```bash
curl http://127.0.0.1:8400/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"model":"liquid/lfm2-24b-a2b","max_tokens":50,
       "messages":[{"role":"user","content":"di pong"}]}'
```
Devuelve `{id, type:message, role:assistant, content:[{type:text, text:"pong"}], stop_reason:end_turn, usage:{input_tokens, output_tokens}}`.

**Anthropic SDK Python:**
```python
import os
os.environ["ANTHROPIC_API_KEY"] = "anything"
os.environ["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:8400"

from anthropic import Anthropic
client = Anthropic()
resp = client.messages.create(
    model="liquid/lfm2-24b-a2b",
    max_tokens=30,
    messages=[{"role": "user", "content": "di hola"}],
)
print(resp.content[0].text)  # → "hola"
```

**Streaming SSE:**
```bash
curl -N http://127.0.0.1:8400/v1/messages -H "Content-Type: application/json" \
  -d '{"model":"liquid/lfm2-24b-a2b","max_tokens":40,"stream":true,
       "messages":[{"role":"user","content":"cuenta 1 2 3"}]}'
```
Emite eventos Anthropic-style: `message_start`, `content_block_start`, `content_block_delta` (con `text_delta`), `content_block_stop`, `message_delta`, `message_stop`.

## Cubierto en fase 1 (este commit)

- ✅ Traductor request bidireccional (Anthropic ↔ OAI) para texto puro
- ✅ Respuesta sync (no-stream)
- ✅ Streaming SSE con eventos Anthropic
- ✅ System message → role:system
- ✅ Auth opcional con `x-api-key` o Bearer
- ✅ usage.input_tokens / output_tokens preservados
- ✅ stop_reason map (stop/length/tool_calls → end_turn/max_tokens/tool_use)
- ✅ Validación con SDK oficial `anthropic` Python

## Pendiente (fase 2)

- ⚠️ **Tool use translation** — Anthropic `tool_use` / `tool_result` blocks ↔ OpenAI `tool_calls` / `tool` role. Hoy se aplana como markers de texto (lossy).
- ⚠️ **Vision / image blocks** — Anthropic `image` blocks ↔ OpenAI `image_url`. No implementado.
- ⚠️ **Streaming tool calls** — chunks de tool_use mid-stream.
- ⚠️ **Cloudflare Tunnel** para exponer público bajo dominio propio.
- ⚠️ **NSSM service** para correr como servicio Windows.

## Estructura

```
anthropic_gateway/
├── __init__.py
├── main.py              # FastAPI app + /, /health
├── routes/
│   └── messages.py      # POST /v1/messages (sync + stream)
├── core/
│   ├── translator.py    # anthropic↔openai mappers
│   └── client.py        # httpx async client al backend OAI
└── data/                # logs uvicorn
```
