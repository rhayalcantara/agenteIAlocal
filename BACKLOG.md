# Backlog — Agente IA Local

**Abierto:** 2026-05-25 (tras cerrar el plan May 11 → Jun 18 en `AGENDA_PENDIENTES.md`).
**Filosofía:** sin fechas obligatorias, sin sesiones fijas. Lista priorizada; cuando Rhay tenga rato, atacar lo que toque. Si urge algo no listado, se mete y se ajusta.

---

## 🔴 P1 — Residuales del plan viejo (cierre real)

| # | Item | Estimación | Notas |
|---|------|-----------|-------|
| 1 | **Wiki 4 páginas para skill `buscar-noticias`** | ~30 min | El skill ya funciona (genera el resumen diario). Falta documentar uso/decisiones en `wiki/`. |
| 2 | **Cloudflare Tunnel para Gateway anthropic-compatible** | ~1h | `anthropic_gateway/` ya sirve `/v1/messages`. Falta exponerlo seguro a internet con Cloudflare Tunnel (`cloudflared`) para que un PC remoto le pueda mandar. |

## 🟡 P2 — Mejoras del agente (memoria, skills)

| # | Item | Estimación | Notas |
|---|------|-----------|-------|
| 3 | **Resúmenes rodantes en `memoria_retrieval`** (Fase 1.5 del POC) | ~1h | Tabla `bloques` + hook al compactador existente para que cada resumen también se indexe semánticamente. Documentado en el plan original. |
| 4 | **Refiner Continual Harness (Fase 2 memoria)** | ~3-5 sesiones | Sobre el POC ya pusheado, agregar un refiner que mire trayectorias y reescriba skills/memoria. Paper Karten et al. (ver `reference_continual_harness.md` en memoria). Necesita modelo frontera para outer loop. |
| 5 | **Tool router con más keywords morfológicas** | ad-hoc | Cuando aparezca un caso donde el router no detecte una tool relevante, agregar variantes (igual que hicimos con `buscar_en_internet` el 23-may). |

## 🟢 P3 — Polish opcionales

| # | Item | Estimación | Notas |
|---|------|-----------|-------|
| 6 | **Probar otras voces piper** (es_MX-ald, es_ES-davefx alternancia) | ~15 min | Models descargados, basta cambiar `PIPER_VOICE_MODEL` env. Daniela quedó como default. |
| 7 | **Panel TV: vista C mix rotativo** (operaciones + agenda + alertas) | ~2h | Diseño ya en `MOCKUP_PANEL_TV.html`. Si Rhay quiere más info en la TV cuando esté siempre encendida. |
| 8 | **`claude-server` multi-dispositivo** | ~varias sesiones | Memoria `project_claude_server.md` — FastAPI :8200 con inbox+SSE para chatear con Claude desde móvil/PC vía Tailscale. Quedó a medias. |

## 🔵 P4 — Diferidos (esperan condición externa)

| # | Item | Bloqueador |
|---|------|-----------|
| 9 | **Presencia (9 sub-tareas)** | Esperan llegada de ESP32-S3 + cámaras |
| 10 | **App Android terminales** | Proyecto grande; abrir cuando lo demás esté estable y haya energía |
| 11 | **Claude Ranger bot servidor** | Coordinar con Claude-Ranger primero (su sesión tiene que estar disponible) |

## ⚫ Bugs conocidos / mantenimiento

| # | Item | Acción |
|---|------|--------|
| 12 | `gmail_manager/auth.py` tiene imports inválidos (`google.auth.transport.sidecar`) | Probablemente borrar el archivo si nada lo importa (el flow real usa `skills/gmail-reader/run.py`). |
| 13 | Acción 7 agenda "Verificar con María" sigue pausada | Asunto resuelto fuera de la agenda; eliminar entrada o dejar como histórico. |
| 14 | TV Habitación Principal: Quick Start desactivado | Para que WoL la despierte tras "apagado profundo", activar en ajustes TV cuando convenga. |

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
