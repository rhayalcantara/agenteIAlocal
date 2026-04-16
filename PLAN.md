# Plan: Arreglar inconsistencias y completar sistema multi-proveedor

## Fecha: 2026-04-13

---

## Problema central

El proyecto tiene una "capa nueva" (`agente_core/main.py`, `telegram_bridge.py`)
que espera una API de `Agent` con `chat()`, `limpiar_historial()` y constructor
con `model/api_key/base_url/provider` — pero `agent.py` todavía tiene la API
vieja (sin esos métodos ni esos parámetros).

Adicionalmente, `telegram_agente.py` usa variables de entorno viejas
(`MODEL_NAME`, `OPENAI_API_KEY`) en lugar del sistema multi-proveedor.

---

## Diagnóstico de inconsistencias

| Archivo | Problema |
|---|---|
| `agente_core/agent.py` | `__init__` solo acepta `tool_profile`; falta `chat()` y `limpiar_historial()` |
| `agente_core/provider_config.py` | `obtener_configuracion()` retorna tupla; falta `LMSTUDIO_API_KEY`; falta Gemini |
| `telegram_agente.py` | Usa `MODEL_NAME`/`OPENAI_API_KEY` (variables viejas) en lugar de `provider_config` |
| `agente_core/main.py` | Llama `Agent(model=..., api_key=..., ...)` → falla porque Agent no acepta esos params |

---

## Plan de tareas

### Tarea 1 — Actualizar `provider_config.py`
- Agregar `LMSTUDIO_API_KEY` al proveedor `lmstudio` (`api_key_env: "LMSTUDIO_API_KEY"`)
- Agregar proveedor `gemini` (usa endpoint OpenAI-compat de Google o google-genai SDK)
- Cambiar `obtener_configuracion()` para retornar un dict:
  `{"model": ..., "api_key": ..., "base_url": ..., "provider": ..., "client": ...}`

### Tarea 2 — Actualizar `agent.py`
- Cambiar `__init__` para aceptar `model`, `api_key`, `base_url`, `provider`, `tool_profile`
- Crear cliente OpenAI internamente en `__init__`
- Auto-detectar `tool_profile` según el proveedor si no se especifica
- Agregar método `chat(mensaje, progress_callback=None) -> str`
  - Actualiza system prompt, agrega mensaje de usuario
  - Loop: llama `client.responses.create()`, llama `process_response()`
  - Sale cuando `process_response()` retorna False (no hay tool calls)
  - Retorna el texto final de la última respuesta
- Agregar método `limpiar_historial()`

### Tarea 3 — Actualizar `telegram_agente.py`
- Reemplazar `MODEL`, `API_KEY`, `BASE_URL`, `PROVIDER` (variables hardcodeadas con vars viejas)
  con una llamada a `provider_config.obtener_configuracion()`
- Pasar la configuración del proveedor al `obtener_bridge()`
- Actualizar `obtener_bridge()` en `telegram_bridge.py` si es necesario

### Tarea 4 — Validar `agente_core/main.py`
- Verificar que funciona con el nuevo `obtener_configuracion()` y el nuevo `Agent`
- Ajustar si hay discrepancias

---

## Pendientes futuros (fuera de scope de este plan)
- Agente WhatsApp
- Modo voz (STT/TTS)
- arXiv downloader/scheduler
- Gemini con SDK nativo (google-genai) como alternativa al modo OpenAI-compat
