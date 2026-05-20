# Misión 1 — Verificar `llmcentral` con Anthropic + Ollama + LM Studio (OpenAI)

**Repo:** https://github.com/rhayalcantara/llmcentral
**Carpeta local:** `revision_llmcentral/repo/`
**Fecha inicio:** 2026-05-06

## Objetivo

Validar que el gateway nuevo `llmcentral` cumpla con tres backends:

1. **OpenAI / LM Studio** — protocolo OpenAI-compatible (LM Studio ya está soportado según README)
2. **Ollama** — soportado según README
3. **Anthropic API** — **no aparece en README**, hay que confirmar y, si falta, agregar

## Lo que sé hoy (de leer README)

- Gateway en Node.js 20 / TypeScript / Fastify v5, expone `/v1/chat/completions`, `/v1/responses`, `/v1/models`
- Worker en Python 3.11+, conecta vía WebSocket
- LM Studio tiene prioridad si un modelo existe en ambos backends
- Streaming SSE soportado en `chat/completions`, no aún en `/v1/responses`
- Heartbeat ping/pong y reconexión con backoff exponencial

## Lo que falta verificar empíricamente

- ¿El worker tiene cliente Anthropic? Si no — diseñar e implementar
- ¿El routing en el gateway sabe enviar request a Anthropic vs local según el `model`?
- ¿`/v1/models` lista correctamente modelos remotos como `claude-*`?
- ¿Streaming Anthropic funcionará? (Anthropic usa SSE distinto al de OpenAI)

## Estrategia (4 fases)

| Fase | Qué | Output |
|---|---|---|
| **1. Auditoría** | Leer código de gateway y worker. Mapear backends y hooks de extensión. | `notas/auditoria.md` |
| **2. Smoke test** | Levantar gateway + 1 worker local. Probar LM Studio + Ollama con cliente OpenAI SDK. | `notas/smoke_test.md` |
| **3. Anthropic** | Implementar `anthropic_client.py` siguiendo patrón existente. Routing por nombre de modelo (`claude-*`). Pruebas. | Código + tests |
| **4. Documentar** | Actualizar README. Ejemplo cliente combinado (mismo SDK, distintos modelos). | README + ejemplo |

Las fases son secuenciales. **Nada de la fase 3 se toca hasta que la fase 1 esté firmada por ti.** Si en la fase 1 descubrimos que ya existe soporte Anthropic, saltamos directo a probarlo.

## Riesgos / decisiones a tomar

- **Anthropic streaming:** SSE de Anthropic es distinto al de OpenAI (eventos `content_block_delta` vs `delta.content`). Hay que decidir si el gateway hace la traducción o si el worker emite ya formato OpenAI.
- **Manejo de tools:** OpenAI usa `tool_calls` array, Anthropic usa `tool_use` blocks. Si quieres usar tools con Claude desde el gateway, requiere capa de traducción.
- **Modelos por config vs descubrimiento:** Anthropic no expone `/v1/models` con tu API key — los modelos válidos son lista hardcoded. Decidir cómo declararlos.
- **Costos:** OpenAI/Anthropic son de pago. Conviene un flag de límite en el worker para evitar runaway.

## Convención de archivos

- `PLAN.md` — este archivo, vista alto nivel
- `TAREAS.md` — checklist ejecutable
- `notas/auditoria.md` — hallazgos al leer código
- `notas/smoke_test.md` — resultados de pruebas locales
- `notas/anthropic_design.md` — diseño antes de codear
- `repo/` — clon del repo (no editar fuera de fase 3+)
