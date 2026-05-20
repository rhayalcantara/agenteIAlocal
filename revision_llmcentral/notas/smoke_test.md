# Smoke test — Fase 2

**Fecha:** 2026-05-06
**Topología:**

```
[ Cliente curl (Win :anywhere) ]
            ↓ HTTP
[ Gateway llm-gateway (Win 127.0.0.1:3500) ]
            ↓ WebSocket
[ Worker (Win, conectado al gateway) ]
            ↓ HTTP
[ LM Studio (Mac 192.168.1.54:1234) ]
```

## Prerequisitos verificados

- Node v24.14.0 ✓
- Mac alcanzable: ping 3-5ms, TCP 1234 OK, `GET /v1/models` retorna 6 modelos
- Wi-Fi 2 (192.168.1.105) reconectado a la red de la Mac
- Gateway `.env` con `PORT=3500` (3000 estaba libre, pero usé 3500 para no chocar con futuros usos)
- Bug B1 + B2 arreglados (LMStudioClient y OllamaClient ahora respetan `LMSTUDIO_URL`/`OLLAMA_URL`)

## Modelos disponibles en la Mac

| Modelo | Tipo |
|---|---|
| `gemma-4-e4b-it` | text |
| `qwen3-tts-12hz-1.7b-voicedesign` | TTS |
| `zai-org/glm-4.6v-flash` | vision/multimodal |
| `text-embedding-nomic-embed-text-v1.5` | embeddings |
| `qwen/qwen3-vl-8b` | vision |
| `deepseek-r1-distill-qwen-7b` | reasoning |

## Resultados

| Test | Cliente | Endpoint | Resultado |
|---|---|---|---|
| **Health** | PowerShell | `GET /health` | `{"status":"ok","workers":1}` ✓ |
| **List models** | PowerShell | `GET /v1/models` | 6 modelos listados desde Mac vía worker ✓ |
| **Worker debug** | PowerShell | `GET /debug/workers` | worker `worker-edb0dd86 (mac-rhay)` listed ✓ |
| **Chat completion (non-stream)** | curl | `POST /v1/chat/completions` | ✅ HTTP 200, 3.2s, respuesta correcta del modelo |
| **Streaming SSE** | curl | `POST /v1/chat/completions stream:true` | ❌ timeout (cuerpo vacío) — confirma **B3** |
| **Responses API** | curl | `POST /v1/responses` | ✅ HTTP 200, 0.7s |
| **PowerShell con UTF-8** | PowerShell | `POST /v1/chat/completions` | ⚠️ `FST_ERR_CTP_INVALID_CONTENT_LENGTH` — bug del cliente, no del gateway |

## Hallazgos

### Confirmados

- **B3 (streaming sin handler en worker)** se reproduce fácil: gateway abre SSE, envía `stream_request` al worker, worker lo ignora, cliente queda esperando hasta timeout. Para producción **es bloqueante** — habría que implementar el handler antes de prometer streaming.
- **B1/B2 arreglados:** confirmar empíricamente que `LMSTUDIO_URL=http://192.168.1.54:1234` se respeta. Antes del fix esto sería ignorado.

### Nuevos

- **N1 (cliente PowerShell):** `Invoke-WebRequest` con body que tenga UTF-8 multibyte → Content-Length cuenta caracteres en vez de bytes → Fastify rechaza con 400. **No es bug del gateway** sino de cómo PowerShell construye el request, pero vale la pena documentarlo (los devs en Windows van a chocar). Workaround: enviar body como bytes UTF-8 explícitos o usar curl/HTTPie.
- **N2 (Responses API funciona):** vale la pena confirmar formato. La respuesta sigue el shape moderno de OpenAI Responses API (`output` array con `message` items, `output_text`, `usage` con `input_tokens_details`).
- **Latencias razonables:** chat completion 3.2s para gemma-4-e4b-it con 80 tokens, responses 0.7s para 20 tokens. No hay overhead apreciable del gateway (los tiempos son los del modelo).

## Conclusión

**Fase 2 superada.** El gateway + worker funcionan end-to-end con LM Studio remoto (caso real de uso del proyecto). Los bugs B1+B2 quedaron arreglados. B3 (streaming) sigue pendiente — no afecta non-stream.

**Listo para Fase 3 (Anthropic)** una vez confirmadas las decisiones de diseño con Rhay.

## Comandos útiles para reproducir

```bash
# Gateway
cd revision_llmcentral/repo/llm-gateway
npm install
npm run dev   # corre en :3500 según .env

# Worker
GATEWAY_WS_URL=ws://127.0.0.1:3500/ws/worker \
  LMSTUDIO_URL=http://192.168.1.54:1234 \
  OLLAMA_ENABLED=false \
  WORKER_NAME=mac-rhay \
  python worker.py

# Cliente
curl -X POST http://127.0.0.1:3500/v1/chat/completions \
  -H "Content-Type: application/json" \
  --data-binary '{"model":"gemma-4-e4b-it","messages":[{"role":"user","content":"hola"}],"max_tokens":50}'
```
