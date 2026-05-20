# Agenda — Pendientes Agente IA Local

**Creada:** 2026-05-08
**Horario:** 18:15 — 20:00 (después de la caminata de 5pm)
**Días:** Lunes, Miércoles, Jueves (días remotos)
**Duración por sesión:** 1h 45min
**Carga semanal:** ~5h 15min

> Decidido sin preguntar para no sobrecargar la cabeza. Si un día no
> aplica (presencial/Coopaspire/Ranger urgente), simplemente se salta y
> se corre el resto. No hay metas obligatorias por sesión — lo que se
> avanzó, se avanzó.

---

## Semana 1 (May 11–14) — Limpieza + arranque Monitor Hub

| Día | Fecha | Tema |
|-----|-------|------|
| Lun | 2026-05-11 | Bug `KeyError 'operacion'` en agenda + lectura del diseño Monitor Hub |
| Mié | 2026-05-13 | Monitor Hub Fase 1: refactor monitor → plugin |
| Jue | 2026-05-14 | Monitor Hub Fase 1: hub central + integración |

## Semana 2 (May 18–21) — Job Manager (parte 1)

| Día | Fecha | Tema |
|-----|-------|------|
| Lun | 2026-05-18 | Job Manager: estructura `job_manager/` + `db.py` (SQLite schema) |
| Mié | 2026-05-20 | Job Manager: `server.py` (FastAPI puerto 8090) + endpoints básicos |
| Jue | 2026-05-21 | Job Manager: `worker.py` (spawn + SIGTERM/SIGKILL) |

## Semana 3 (May 25–28) — Job Manager (parte 2)

| Día | Fecha | Tema |
|-----|-------|------|
| Lun | 2026-05-25 | Job Manager: pipelines DAG (`depends_on`) |
| Mié | 2026-05-27 | Job Manager: `agente_core/job_client.py` + tools (`job_submit`, etc.) |
| Jue | 2026-05-28 | Job Manager: `dashboard.html` + spawn desde supervisor |

## Semana 4 (Jun 1–4) — WhatsApp + Agente local

| Día | Fecha | Tema |
|-----|-------|------|
| Lun | 2026-06-01 | WhatsApp: pulir `execute_bash` (comillas en "SISTEMA RAY") |
| Mié | 2026-06-03 | WhatsApp: auto-guardado en `.md` desde el agente local |
| Jue | 2026-06-04 | Agente local: probar skill `buscar-noticias` + wiki 4 páginas |

## Semana 5 (Jun 8–11) — Monitor Hub fases avanzadas

| Día | Fecha | Tema |
|-----|-------|------|
| Lun | 2026-06-08 | Notificaciones cruzadas (WhatsApp urgente → Telegram) |
| Mié | 2026-06-10 | Monitor Hub Fase 2: plugin WhatsApp |
| Jue | 2026-06-11 | Monitor Hub Fase 3: dashboard web FastAPI |

## Semana 6 (Jun 15–18) — Gateway Anthropic-compatible

| Día | Fecha | Tema |
|-----|-------|------|
| Lun | 2026-06-15 | Monitor Hub Fase 4: plugin Gmail + prioridades |
| Mié | 2026-06-17 | Gateway: PC Worker LLM + endpoint `/v1/messages` |
| Jue | 2026-06-18 | Gateway: traducción a `/v1/chat/completions` + Cloudflare Tunnel |

---

## Bloques diferidos (no en la agenda — esperan condición externa)

- **Presencia (9 tareas):** esperan llegada de ESP32-S3 + cámaras
- **App Android terminales:** proyecto grande, abrir cuando lo demás esté estable
- **Claude Ranger bot Telegram servidor:** coordinar con Ranger primero

## Reglas de la agenda

1. **Lo que no se hace, no se hace.** No se acumula como deuda.
2. **Caminata 17:00–18:00 es sagrada.** No se mueve por trabajo.
3. **Si Coopaspire/Ranger explota:** se salta la sesión sin culpa.
4. **Cada jueves:** revisar avance y mover lo que corresponda.
