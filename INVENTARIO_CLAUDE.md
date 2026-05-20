# Inventario Claude — agenteIAlocal

> Snapshot del entorno activo. Generado 2026-05-17. Re-correr al cambiar MCPs, skills, gateway o procesos persistentes.

## Identidad

- **Modelo:** Claude Opus 4.7 (1M ctx) vía Claude Code CLI
- **Plataforma:** Windows 11, PowerShell + Bash
- **Working dir:** `C:\proyectos\agenteIAlocal` (rama `main`)
- **Usuario:** Rhay Alcantara · `rhayalcantara@gmail.com`

---

## Canales de comunicación

| Canal | Tool | Reglas |
|-------|------|--------|
| **Telegram** | `mcp__telegram__leer_mensajes`, `enviar_mensaje`, `enviar_voz`, `enviar_archivo`, `info_bot` | Cron 5 min (NO escalar a 30 — `feedback_telegram_cadencia`). Permitido responder. |
| **WhatsApp** | Monitor JS (`whatsapp_monitor.js`) → log filtrado por `^MSG\|` | **NUNCA escribir sin permiso explícito** (`feedback_whatsapp_no_responder`). Coexiste con grupo SISTEMA RAY del cliente Ranger. |

---

## MCP Servers (`.mcp.json`)

- **telegram** (`mcp_telegram.py`): texto + voz (Whisper STT embebido) + archivos. Es el único MCP configurado en el proyecto.

---

## Skills locales del agente (`skills/` — 19)

`agent-browser`, `alarma-inteligente`, `buscar-noticias`, `claude-auto-resolver`, `crear-skill`, `descargar-adjuntos-starlink`, `descargavideoytraduce`, `estado-clima`, `evaluar-llm`, `gmail-reader`, `manejo-tv`, `metodo-rhay`, `scraper-general`, `seguimiento`, `telegram-agent-monitor`, `web-fetch-compare`, `whatsapp-listener`, `youtube-downloader`, `youtube-download-translate`

---

## Skills de Claude Code (slash)

`/update-config`, `/simplify`, `/loop`, `/schedule`, `/claude-api`, `/init`, `/review`, `/security-review`, `/fewer-permission-prompts`, `/keybindings-help`

---

## LLM Gateway

- **URL:** `https://rhayalcantara-002-site2.ntempurl.com/v1` (OpenRouter propio)
- **API key:** `LMSTUDIO_API_KEY` en `.env`
- **Default:** `liquid/lfm2-24b-a2b`

**Modelos cargados (30+):**
qwen3.6 (8b · 27b · 35b · latest) · mistral-large 123b · gpt-oss (20b · 120b) · gemma-4 (4b · 26b-a4b · 31b · e4b) · gemma3 (4b) · nemotron-3-nano (30b · omni) · qwen2.5-coder (7b · 32b) · qwen/qwen3-coder-next · qwen/qwen3.5-35b-a3b · qwen3.5 (9b:2 · 27b) · qwen3:8b · liquid/lfm2-24b-a2b · ministral-3:8b · mistralai/ministral-3-14b-reasoning · mistral-nemo:12b · meta-llama-3-8b-instruct · phi4-mini:3.8b · command-r-plus:104b · gemma4:26b · text-embedding-nomic-embed-text-v1.5

**Política:** Python para procesos/alta demanda, Node para trabajos estables (`feedback_python_vs_node`).

---

## Procesos locales (al momento del inventario)

| PID | Proceso |
|-----|---------|
| 11608 → 3344 | `mcp_telegram.py` (parent + worker spawn) |
| 13772 → 8124 | `job_manager` (encolamiento procesos largos, puerto 8090) |
| 1268 → 9232 | `agente_core/telegram_agente.py` |
| (n/a) | `whatsapp_monitor.js` (Node, leyendo a `whatsapp_monitor.log`) |
| ✘ | `supervisor_bot.py` — apagado por Rhay |

Nota: parent+worker es el patrón `multiprocessing.spawn` de Windows. No hay duplicados.

---

## Subagentes Anthropic disponibles

- **Explore** — búsqueda read-only rápida en código
- **Plan** — diseño de implementación
- **general-purpose** — investigaciones multi-paso
- **claude-code-guide** — preguntas sobre Claude Code/SDK/API
- **statusline-setup** — configurar statusline

---

## Memoria persistente

`C:\Users\rhay_\.claude\projects\C--proyectos-agenteIAlocal\memory\` — 17 entries indexadas en `MEMORY.md`. Cubre: rol/horario, reglas WhatsApp, plan marketing Ranger, hardware Ranger (Mac Studio M2 Ultra), evaluación contextual LLMs, cadencias Telegram, Gmail reauth, job_manager, agenda 6 semanas, etc.

---

## Cron activo

- `25b7b20c` — lectura Telegram cada 5 min (session-only, expira en 7 días).

---

## Capacidades de ejecución

- **Shell:** PowerShell + Bash (POSIX)
- **Archivos:** Read · Edit · Write · Glob · Grep
- **Web:** WebFetch · WebSearch
- **Tareas:** TaskCreate/List/Get/Stop/Output/Update
- **Programación:** CronCreate/List/Delete (sesión) · `/schedule` (remoto persistente vía Anthropic)
- **Monitor:** stream de eventos desde scripts long-running
- **ToolSearch:** carga de schemas de tools diferidos bajo demanda
- **Audio:** TTS via `agente_core/voice_handler.sintetizar()` (gTTS → OGG/Opus); STT via Whisper embebido en MCP

---

## Datos persistentes del agente_core

`agente_core/data/` — JSON files con: agenda, memoria, permisos, contactos servicios, distribución casa, documentos, gastos, google_tvs, historial compras, historial presencia, imágenes casa/ubicaciones, lista compra, etc.
