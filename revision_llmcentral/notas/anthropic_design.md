# Diseño Anthropic-compat — MVP (PIVOTADO)

> **Cambio de dirección 2026-05-06:** mi diseño inicial era usar Anthropic como
> backend (cliente OpenAI → gateway → Anthropic API real). El usuario aclaró
> que quería lo opuesto: que el gateway **exponga formato Anthropic** para
> que Claude Code CLI lo pueda usar contra modelos locales.
>
> Diseño viejo descartado. Código del worker revertido. Branch sigue siendo
> `feat/anthropic-support` pero solo toca el gateway.

## Objetivo real

```
Claude Code CLI                    Gateway (nuevo endpoint)         Worker          LM Studio
   │  POST /v1/messages                │                              │                │
   │  formato Anthropic                │                              │                │
   ├─────────────────────────────────►│                              │                │
   │                                   │ traduce Anthropic→OpenAI     │                │
   │                                   ├─────────────────────────────►│                │
   │                                   │  inference_request (WS)      │ /v1/chat/comp  │
   │                                   │                              ├───────────────►│
   │                                   │                              │◄───────────────│
   │                                   │  inference_response (WS)     │                │
   │                                   │◄─────────────────────────────│                │
   │                                   │ traduce OpenAI→Anthropic     │                │
   │◄─────────────────────────────────│                              │                │
   │  formato Anthropic                │                              │                │
```

Cliente típico:
```bash
ANTHROPIC_BASE_URL=http://localhost:3500
ANTHROPIC_AUTH_TOKEN=cualquier-cosa  # el gateway lo ignora si CLIENT_API_KEY está vacío
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
claude  # arranca el CLI
```

## Decisiones MVP

| Tema | Decisión |
|---|---|
| Endpoint | `POST /v1/messages` en `llm-gateway` |
| Auth | Reuso `requireClientApiKey` (acepta header `x-api-key` o `Authorization: Bearer ...`) |
| Mapeo de modelos | Variable env `ANTHROPIC_MODEL_MAP` con sintaxis `claude-haiku-*=gemma-4-e4b-it,claude-opus-*=deepseek-r1-distill-qwen-7b`. Match por glob. Default: variable `ANTHROPIC_DEFAULT_MODEL` |
| Streaming | **A definir con Rhay** — sin streaming Claude Code probablemente no funciona (siempre pide `stream:true`); con streaming, el MVP crece pero queda usable |
| Tools | **NO** en este MVP. Si llegan, se ignoran y respondemos sin invocarlas (el modelo local no las verá). |
| Visión / multimodal | **NO** en este MVP. Bloques con `type: image` → error 400. |
| `/v1/messages/count_tokens` | **NO** en este MVP. Anthropic-SDK puede pedirlo; retornar 404. |

## Traducciones bidireccionales

### Request: Anthropic Messages → OpenAI Chat Completions

```jsonc
// IN (Anthropic)
{
  "model": "claude-haiku-4-5-20251001",
  "system": "You are helpful",
  "messages": [{"role":"user","content":"hola"}],
  "max_tokens": 1024,
  "temperature": 0.7
}
```
↓ traducir
```jsonc
// OUT (OpenAI Chat) — el gateway delega esto al worker
{
  "model": "gemma-4-e4b-it",     // ← mapeado vía ANTHROPIC_MODEL_MAP
  "messages": [
    {"role":"system","content":"You are helpful"},
    {"role":"user","content":"hola"}
  ],
  "max_tokens": 1024,
  "temperature": 0.7
}
```

Reglas:
- `system` (string o array de blocks) → `messages[0]` con `role:system`
- `messages[].content` puede ser string o array `[{type:"text",text:"..."}]` → aplanar a string
- `max_tokens` obligatorio — pasarlo tal cual
- `temperature`, `top_p`, `top_k` (k no existe en OpenAI: ignorar), `stop_sequences` → `stop`

### Response: OpenAI Chat Completion → Anthropic Messages

```jsonc
// IN (OpenAI)
{
  "id":"chatcmpl-abc","model":"gemma-4-e4b-it",
  "choices":[{"message":{"role":"assistant","content":"hola!"},"finish_reason":"stop"}],
  "usage":{"prompt_tokens":10,"completion_tokens":3,"total_tokens":13}
}
```
↓ traducir
```jsonc
// OUT (Anthropic)
{
  "id":"msg_abc",
  "type":"message",
  "role":"assistant",
  "content":[{"type":"text","text":"hola!"}],
  "model":"claude-haiku-4-5-20251001",  // devolver el modelo que pidió el cliente, no el local
  "stop_reason":"end_turn",              // mapeado de finish_reason
  "stop_sequence":null,
  "usage":{"input_tokens":10,"output_tokens":3}
}
```

Mapeo de stop:
| OpenAI `finish_reason` | Anthropic `stop_reason` |
|---|---|
| `stop` | `end_turn` |
| `length` | `max_tokens` |
| `tool_calls` | `tool_use` (no aplica MVP) |
| `content_filter`/otro | `end_turn` (fallback) |

## Mapeo de modelos

Sintaxis env `ANTHROPIC_MODEL_MAP` (CSV con `pattern=local-model`):
```
ANTHROPIC_MODEL_MAP=claude-haiku-*=gemma-4-e4b-it,claude-sonnet-*=qwen/qwen3-vl-8b,claude-opus-*=deepseek-r1-distill-qwen-7b
ANTHROPIC_DEFAULT_MODEL=gemma-4-e4b-it
```

Algoritmo:
1. Recibir `body.model = "claude-haiku-4-5-20251001"`
2. Recorrer mapa, primer pattern que matchee (glob simple `*` y `?`)
3. Si no matchea → `ANTHROPIC_DEFAULT_MODEL`
4. Si tampoco hay default → 400 con `model_not_mapped`

## Cambios concretos

### Gateway (Node.js / TypeScript)
- **Nuevo:** `src/translators/anthropicMessages.ts` — funciones puras:
  - `anthropicToOpenAI(body): OpenAIChatRequest`
  - `openAIToAnthropic(resp, requestedModel): AnthropicMessageResponse`
  - `mapModelName(claudeName, mapEnv, defaultModel): string`
- **Nuevo:** `src/routes/messages.ts` — `POST /v1/messages`, MVP non-stream
- **Modificado:** `src/server.ts` — registra la nueva ruta
- **Modificado:** `src/config.ts` — agrega `ANTHROPIC_MODEL_MAP`, `ANTHROPIC_DEFAULT_MODEL`

### Worker (Python)
- **Sin cambios** — el worker no se entera de nada nuevo, sigue recibiendo `inference_request` con formato OpenAI estándar.

## Test plan

- [ ] Sin `ANTHROPIC_DEFAULT_MODEL` y sin mapeo: `POST /v1/messages` con cualquier modelo → 400 `model_not_mapped`
- [ ] Con default `gemma-4-e4b-it` y modelo `claude-X` arbitrario → traduce, llama al worker, responde con shape Anthropic
- [ ] `system` string + 2 messages user/assistant → preserva orden
- [ ] `system` como array de blocks → concatena
- [ ] `messages[].content` como `[{type:"text"}]` → aplana
- [ ] `messages[].content` como `[{type:"image"}]` → 400
- [ ] `tools:[...]` en request → ¿warning o silently drop? (decidir)
- [ ] `stream:true` → 501 `streaming_not_supported_mvp` (a menos que decidamos incluir streaming)
- [ ] Stop reasons mapeados (`stop` → `end_turn`, `length` → `max_tokens`)
- [ ] LM Studio + Ollama siguen funcionando en `/v1/chat/completions` (no romper Fase 2)
- [ ] **Test final:** Claude Code CLI con `ANTHROPIC_BASE_URL=http://127.0.0.1:3500` consume modelo local

## Pendiente confirmar con Rhay

> **¿Streaming en MVP?**
> - **Sí** → MVP usable con Claude Code de verdad, pero más código (~150 líneas extra para parsear OpenAI SSE chunk-by-chunk y emitir eventos Anthropic `message_start`/`content_block_delta`/`message_stop`).
> - **No** → Validamos solo arquitectura con curl. Claude Code real va a fallar por defecto. Sirve solo si después agregamos streaming.
