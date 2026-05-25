# worker_hub — pool de LLMs detrás de un endpoint único

`worker_hub/` (FastAPI :8500) recibe peticiones OpenAI-compatible y las rutea al worker LLM que tenga el modelo solicitado. Permite usar **todos los modelos de cualquier servidor del tailnet** como si fuera una sola URL.

## Por qué existe

Antes del 25-may había dos puntos de entrada para inferencia LLM:
- `anthropic_gateway` :8400 traduciendo Anthropic↔OAI contra UN backend hardcoded.
- Nada para clientes OAI puros.

Y además: Ranger tiene una **Mac Studio M2 Ultra** corriendo LM Studio con modelos grandes (35B). Esta PC (i7 + GPU modesta) puede hospedar modelos chicos cuando se quiera. El backend remoto público también tiene su propio catálogo. Sin un hub, los clientes tendrían que saber qué modelo vive dónde.

El hub centraliza: **el cliente solo conoce una URL** (`http://100.89.251.75:8500/v1`) y un nombre de modelo. El hub busca, despacha, propaga.

## Workers actuales

| Nombre | URL | Prioridad | Modelos | Notas |
|--------|-----|-----------|---------|-------|
| `ranger` | `http://100.91.126.66:1234/v1` | 10 | 7 (qwen3.6-35b, qwen3.6-27b, lfm2-24b, qwen3-30b-a3b, qwen3.5-27b, qwen3-tts, nomic-embed) | Sin auth. Mac Studio M2 Ultra. |
| `remoto` | `https://rhayalcantara-002-site2.ntempurl.com/api/v1` | 5 | 31 (nemotron, gemma-3/4, mistral-large, qwen3 varios, gpt-oss…) | Bearer `LMSTUDIO_API_KEY`. |

`liquid/lfm2-24b-a2b` y `text-embedding-nomic-embed-text-v1.5` están en ambos — ranger gana por prioridad, remoto es failover automático.

## Flujo de selección

```
POST /v1/chat/completions {model: "qwen3.5-27b", ...}
                    │
                    ▼
1. ¿header x-worker presente? → SÍ → usa ese worker (override)
                                NO ↓
2. Workers enabled + healthy + (model in workers.models),
   ordenados por priority DESC, name ASC
                    │
                    ▼
3. ¿Lista vacía? → 404 "ningún worker tiene el modelo"
                   NO ↓
4. POST al primero. Si 5xx → reintento al siguiente. Si 4xx → se propaga.
   Si streaming → SOLO el primero, sin failover mid-stream.
```

## Acceso

| Desde | URL |
|-------|-----|
| Esta máquina | `http://127.0.0.1:8500/v1/*` |
| Cualquier nodo tailnet | `http://100.89.251.75:8500/v1/*` |

Auth: header `x-api-key` o `Authorization: Bearer` con el valor de `WORKER_HUB_API_KEY` del `.env`.

`GET /health` es público (para uptime checks); todo lo demás requiere la key.

## Cómo encaja con `anthropic_gateway`

Diagrama actualizado:

```
Cliente Anthropic SDK ──▶ :8400 anthropic_gateway (traduce)
                              │
                              ▼  (backend = hub local)
Cliente OAI SDK ──────────▶ :8500 worker_hub (rutea por modelo)
                              │
                              ├──▶ ranger 100.91.126.66:1234
                              └──▶ remoto ntempurl
```

El gateway en `.env` apunta a `ANTHROPIC_GATEWAY_BACKEND_URL=http://127.0.0.1:8500/v1` con `ANTHROPIC_GATEWAY_BACKEND_KEY=<WORKER_HUB_API_KEY>`. Si querés que el gateway hable directo a un backend específico sin pasar por el hub, basta cambiar esas dos vars.

## Arranque

```powershell
.\iniciar_worker_hub.ps1            # idempotente
.\iniciar_worker_hub.ps1 -Status
.\iniciar_worker_hub.ps1 -Stop
.\iniciar_worker_hub.ps1 -Force
```

**Orden recomendado al iniciar sesión:**
1. `.\iniciar_worker_hub.ps1` (primero)
2. `.\iniciar_gateway.ps1` (después, así si el gateway hace probe inmediato al hub, ya responde)

Si el hub está abajo y el gateway intenta responder, el cliente verá un 502/connection refused. Esperable.

## Agregar un worker nuevo

1. Editar `worker_hub/workers.json`:
   ```json
   {
     "name": "claude-local-gpu",
     "base_url": "http://127.0.0.1:1234/v1",
     "priority": 7,
     "enabled": true,
     "api_key_env": null,
     "notes": "LM Studio en esta PC con GPU."
   }
   ```
2. Si la `api_key_env` apunta a una var nueva, agregarla al `.env`.
3. `.\iniciar_worker_hub.ps1 -Force` para recargar config.
4. Verificar con `GET /workers`:
   ```powershell
   $key = (Select-String -Path .env -Pattern "^WORKER_HUB_API_KEY=(.+)").Matches[0].Groups[1].Value
   curl http://127.0.0.1:8500/workers -H "x-api-key: $key" | ConvertFrom-Json
   ```

## Reglas de firewall

Igual que el gateway, falta abrir 8500 al rango CGNAT en sesión elevada:

```powershell
New-NetFirewallRule -DisplayName "worker_hub 8500 tailnet" `
    -Direction Inbound -Protocol TCP -LocalPort 8500 `
    -RemoteAddress 100.0.0.0/8 -Action Allow -Profile Any
```

## Diferencias con LiteLLM / vLLM Router / OpenRouter

Esto es un componente **mínimo intencionalmente**. No es un reemplazo de LiteLLM. Decisiones que SÍ se tomaron:
- Routing por nombre exacto de modelo (no por capability tags).
- Sin cache de respuestas.
- Sin rate-limiting.
- Sin métricas Prometheus.
- Sin model aliases (`gpt-4` → `qwen3.6-35b`).
- Config estática en JSON (no auto-register).

Si en algún momento estos requisitos aparecen, vale la pena considerar swapeo a LiteLLM antes que extender este componente.

## Verificación end-to-end (2026-05-25)

| Test | Resultado |
|------|-----------|
| Hub `/health` localhost + tailnet | 200, 2/2 healthy |
| `/v1/models` catálogo unificado | 36 modelos únicos |
| Chat a modelo solo-ranger | ruteado a ranger ✅ |
| Chat a modelo solo-remoto | ruteado a remoto ✅ |
| `x-worker` override | respetado ✅ |
| Streaming SSE vía gateway → hub → ranger | eventos Anthropic OK |

## Relacionado

- [Gateway Anthropic-compatible](gateway-anthropic.md) — traductor que ahora tiene al hub como backend.
- `worker_hub/README.md` — detalles técnicos del módulo.
- `BRIEFING_RANGER_BRIDGE.md` — Tailscale base que permite todo esto.
