# Tareas — Misión 1 (`llmcentral`)

> Tachar con `[x]` al completar. Las fases son secuenciales — no avanzar hasta que la anterior esté ✅ y aprobada por Rhay.

## Fase 1 — Auditoría 🔎

- [x] **1.1** Leer `llm-worker/worker.py` y mapear: cómo carga clientes, cómo elige backend por modelo, hooks de extensión
- [x] **1.2** Leer `llm-worker/lmstudio_client.py` y `ollama_client.py` para entender el patrón
- [x] **1.3** Buscar referencias a `anthropic`, `claude` o `messages` en todo el repo (`grep -ri`) → **0 matches**
- [x] **1.4** Leer `llm-gateway/src/` — routing, balanceador, manejo de modelos
- [ ] **1.5** Leer `Doc/llm-worker.md` y `Doc/llm-gateway.md` para detalles de protocolo *(saltado — el código fue auto-explicativo)*
- [x] **1.6** Escribir `notas/auditoria.md` con: backends soportados hoy, dónde se enchufa uno nuevo, gaps respecto a Anthropic
- [ ] **1.7** ⏸️ **Checkpoint con Rhay** — confirmar hallazgos antes de fase 2

## Fase 2 — Smoke test backends actuales 🧪

- [x] **2.1** `cd repo/llm-gateway && npm install`
- [x] **2.2** Crear `.env` en gateway (PORT=3500, GATEWAY_API_KEY)
- [x] **2.3** `npm run dev` y verificar `GET http://127.0.0.1:3500/health` → `{"status":"ok","workers":0}`
- [x] **2.4** `cd repo/llm-worker && pip install -r requirements.txt`
- [x] **2.5** Worker arrancado: `LMSTUDIO_URL=http://192.168.1.54:1234` → registró 6 modelos
- [x] **2.6** `GET /debug/workers` lista `worker-edb0dd86 (mac-rhay)`
- [x] **2.7** `POST /v1/chat/completions` con `gemma-4-e4b-it` → ✅ HTTP 200, 3.2s
- [ ] **2.8** Ollama no disponible en este entorno *(OLLAMA_ENABLED=false)* — saltado
- [x] **2.9** Streaming: ❌ timeout (confirma bug B3 — worker sin handler `stream_request`)
- [x] **2.10** Documentado en `notas/smoke_test.md`
- [x] **2.X** **Bonus**: probado `/v1/responses` → ✅ HTTP 200, 0.7s
- [x] **2.X** **Bonus**: bugs B1+B2 arreglados (env vars `LMSTUDIO_URL` / `OLLAMA_URL` ahora se respetan)
- [ ] **2.11** ⏸️ **Checkpoint con Rhay** — pasamos a Anthropic si todo OK

## Fase 3 — Endpoint Anthropic-compat (PIVOTADO) 🤖

> Cambio de dirección: el objetivo real era exponer formato Anthropic
> en el gateway para Claude Code CLI, NO usar Anthropic API como backend.
> Diseño viejo descartado. Trabajo solo en gateway.

- [x] **3.1** Diseñar en `notas/anthropic_design.md` (versión pivotada)
- [x] **3.2** ⏸️ Checkpoint con Rhay — aprobado MVP con streaming, sin tools, sin visión
- [x] **3.3** `src/translators/anthropicMessages.ts` — traducción bidireccional + AnthropicStreamTranslator
- [x] **3.4** `src/routes/messages.ts` — POST /v1/messages con stream + non-stream
- [x] **3.5** `src/config.ts` + `src/server.ts` — env vars + registro
- [x] **3.6** B3 resuelto: handler `stream_request` en worker + `stream_completion()` en clientes
- [x] **3.7** Tests: non-stream OK, streaming OK con eventos correctos, mapeo OK, errores OK
- [x] **3.8** Commit `481a9fb` en branch `feat/anthropic-support`
- [ ] **3.9** Test final con Claude Code CLI real (ANTHROPIC_BASE_URL=http://127.0.0.1:3500)

## Fase 4 — Documentar 📚

- [ ] **4.1** Actualizar `README.md` con Anthropic en estado del proyecto y variables
- [ ] **4.2** Crear `Doc/anthropic.md` con detalles
- [ ] **4.3** Ejemplo `llm-worker/ejemplo_anthropic.py`
- [ ] **4.4** ⏸️ **Cierre con Rhay** — push y merge

---

**Estado actual:** Fase 1 — sin iniciar.
**Próxima acción al continuar:** ejecutar 1.1 a 1.6, luego pausar para checkpoint.
