# Backlog — Agente IA Local

**Abierto:** 2026-05-25 (tras cerrar el plan May 11 → Jun 18 en `AGENDA_PENDIENTES.md`).
**Filosofía:** sin fechas obligatorias, sin sesiones fijas. Lista priorizada; cuando Rhay tenga rato, atacar lo que toque. Si urge algo no listado, se mete y se ajusta.

---

## 🔴 P1 — Residuales del plan viejo (cierre real)

| # | Item | Estimación | Notas |
|---|------|-----------|-------|
| ~~1~~ | ~~**Wiki 4 páginas para skill `buscar-noticias`**~~ | ✅ DONE 25-may | `wiki/proyectos/buscar-noticias.md`, `wiki/conceptos/scraping-noticias.md`, `wiki/configuracion/agenda-noticias.md`, `wiki/noticias/diariolibre.md` + index actualizado. |
| ~~2~~ | ~~**Cloudflare Tunnel para Gateway**~~ | ✅ DONE 25-may (pivot) | Reemplazado por **Tailscale tailnet** (ya estaba montado para Claude-Ranger). Gateway en `100.89.251.75:8400`, auth con `ANTHROPIC_GATEWAY_API_KEY`, launcher `iniciar_gateway.ps1`. Wiki `configuracion/gateway-anthropic.md`. Regla firewall 8400: pendiente correr el comando elevado (8500 ya hecho). |

## 🟡 P2 — Mejoras del agente (memoria, skills)

| # | Item | Estimación | Notas |
|---|------|-----------|-------|
| ~~3~~ | ~~**Resúmenes rodantes en `memoria_retrieval`** (Fase 1.5)~~ | ✅ DONE 25-may | Tabla `bloques` agregada + nueva op `ingestar_bloque` + `buscar(tipo=ambos|msg|bloque)` + hook en `compactar_historial` via daemon thread. Smoke E2E: 40 msgs → compactador llama qwen3.6:27b vía hub → resumen indexado → búsqueda semántica devuelve score 0.85. Bonus: fix de `LMSTUDIO_API_KEY` (ahora = hub key) + nueva `LMSTUDIO_REMOTO_API_KEY` para no chocar. |
| 4 | **Refiner Continual Harness (Fase 2 memoria)** | ~3-5 sesiones | Sobre el POC ya pusheado, agregar un refiner que mire trayectorias y reescriba skills/memoria. Paper Karten et al. (ver `reference_continual_harness.md` en memoria). Necesita modelo frontera para outer loop. |
| 5 | **Tool router con más keywords morfológicas** | ad-hoc | Cuando aparezca un caso donde el router no detecte una tool relevante, agregar variantes (igual que hicimos con `buscar_en_internet` el 23-may). |

## 🟢 P3 — Polish opcionales

| # | Item | Estimación | Notas |
|---|------|-----------|-------|
| ~~6~~ | ~~**Probar otras voces piper**~~ | ✅ DONE 25-may | Comparado Daniela vs Davefx (es_ES) vs Ald (es_MX) via 3 muestras Telegram con misma frase. Rhay confirmó: **mantiene Daniela** (default actual). Cero cambios al código. |
| 7 | **Panel TV: vista C mix rotativo** (operaciones + agenda + alertas) | ~2h | Diseño ya en `MOCKUP_PANEL_TV.html`. Si Rhay quiere más info en la TV cuando esté siempre encendida. |
| 8 | **`claude-server` multi-dispositivo** | ~varias sesiones | Memoria `project_claude_server.md` — FastAPI :8200 con inbox+SSE para chatear con Claude desde móvil/PC vía Tailscale. Quedó a medias. |
| 9 | **Sumar PC con RTX 3060 al `worker_hub` como worker** | ~30 min cuando esté lista | Instalar LM Studio, exponer `0.0.0.0:1234`, agregar Tailscale, sumar entrada en `worker_hub/workers.json` (priority entre 7 y 9: local con GPU > remoto ntempurl, pero <= Ranger M2 Ultra según modelo). Rhay anunciará cuando la PC esté disponible. |

## 🔵 P4 — Diferidos (esperan condición externa)

| # | Item | Bloqueador |
|---|------|-----------|
| 10 | **Presencia (9 sub-tareas)** | Esperan llegada de ESP32-S3 + cámaras |
| 11 | **App Android terminales** | Proyecto grande; abrir cuando lo demás esté estable y haya energía |
| 12 | **Claude Ranger bot servidor** | Coordinar con Claude-Ranger primero (su sesión tiene que estar disponible) |

## ⚫ Bugs conocidos / mantenimiento

| # | Item | Acción |
|---|------|--------|
| ~~13~~ | ~~`gmail_manager/auth.py` imports inválidos~~ | ✅ DONE 25-may: borrado. Nadie lo importaba. El flow real sigue siendo `skills/gmail-reader/run.py`. |
| ~~14~~ | ~~Acción agenda "Verificar con María"~~ | ✅ DONE 25-may: eliminada de `agenda.json` (id=8). Quedan acciones 1-3, 5-7. Backup en `agenda.json.bak.*`. |
| 15 | TV Habitación Principal: Quick Start desactivado | Para que WoL la despierte tras "apagado profundo", activar en ajustes TV cuando convenga. |

---

## 🔄 Reglas del backlog

1. **Sin fechas obligatorias.** Se ataca cuando hay ganas/tiempo. P1 antes que P2 antes que P3.
2. **Diferidos no abren** hasta que se cumpla la condición.
3. **Si surge un bug urgente** (en uso real), se mete en P1 al momento.
4. **Cada cierto tiempo**, revisar y mover items entre P si cambian las prioridades.
5. **Cuando Rhay diga "qué tenemos pendiente"** → este archivo es la fuente única.

---

## 🎁 Logros recientes (no del plan, completados de bonus)

- ✅ Bridge Claude-local↔Claude-Ranger vía Tailscale (mayo 14)
- ✅ Backup BD Ranger restaurado localmente (mayo 23)
- ✅ POC memoria retrieval (mayo 23)
- ✅ Voz piper Daniela (femenino argentino) como default TTS (mayo 25)
- ✅ Panel TV definitivo + auto-arranque vía cron Windows (mayo 24)
- ✅ Monitor batería con alertas Telegram (mayo 25)
- ✅ Transcripción automática de voz en `telegram_push.py` (mayo 24)
- ✅ Skill `manejo-tv` con operación `youtube` + presets de noticias (mayo 22)
- ✅ Rotación token telegram-ranger end-to-end + scrub de tokens en repo (mayo 23)
- ✅ Fix Gmail token timeout (de 5min → 6s) (mayo 25)
- ✅ Fix `consultar_memoria` ante kwargs alucinados (mayo 25)
- ✅ Wiki 4 páginas skill `buscar-noticias` (mayo 25)
- ✅ Gateway Anthropic-compat expuesto al tailnet con auth + launcher on-demand (mayo 25) — pivot desde CF Tunnel
- ✅ **worker_hub :8500** — pool de LLMs detrás de endpoint OAI único, routing por modelo + failover, 2 workers iniciales (ranger Mac M2 + remoto ntempurl, total 36 modelos únicos), streaming SSE end-to-end (mayo 25)
- ✅ **Resúmenes rodantes Fase 1.5** — `memoria_retrieval` ahora indexa los resúmenes del compactador en tabla `bloques`. Búsqueda unificada msg+bloque con score. Smoke E2E con qwen3.6:27b vía hub (mayo 25)
- ✅ **Bugs limpiados:** `gmail_manager/auth.py` borrado (imports rotos, nadie lo importaba); acción agenda "Verificar con María" eliminada (mayo 25)
- ✅ **Comparativa voces piper** — Daniela vs Davefx vs Ald via 3 muestras, Rhay mantuvo Daniela (mayo 25)
- ✅ **RemoteAny integrado al tailnet bidireccional** — Mac host con LaunchAgent persistente (`com.rhay.remoteany`), Windows host on-demand, sin password ni relay Oracle, validado E2E con mouse+click (mayo 25)
