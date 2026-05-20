# job_manager

Backend de encolamiento de procesos largos para el agente. Servicio FastAPI en `localhost:8090` con SQLite, dashboard web, y eventos en formato standard.

## Por qué existe

El bash persistente del agente bloquea cuando un comando tarda mucho (descarga, transcripción de 1h, doblaje). Mientras corre el comando, el agente no puede procesar otros mensajes ni reportar progreso. Solución: encolar el proceso aquí y consultar progreso por API.

## Arrancar

Lo lanza automáticamente el `supervisor_bot.py`. Manualmente:
```
python -m job_manager
```
Variables `.env`:
- `JOB_MANAGER_PORT` (default 8090)
- `JOB_MANAGER_HOST` (default 127.0.0.1)
- `JOB_MANAGER_WORKERS` (default 2, máximo concurrente)

## Endpoints

| Método | Path | Descripción |
|---|---|---|
| POST   | `/jobs` | Encola un job o pipeline |
| GET    | `/jobs?solo_roots=true&estado=...` | Lista jobs |
| GET    | `/jobs/{id}` | Detalle (incluye steps si es pipeline) |
| GET    | `/jobs/{id}/output?desde=N` | Tail incremental del log |
| DELETE | `/jobs/{id}` | Cancelar (SIGTERM grace 5s, luego SIGKILL) |
| DELETE | `/jobs?antes=YYYY-MM-DD` | Purga manual |
| GET    | `/pipelines/{id}` | Vista del DAG |
| GET    | `/events?desde=N` | Lectura incremental del events.log |
| GET    | `/stats` | Conteo por estado |
| GET    | `/` | Dashboard HTML |
| GET/POST | `/qa` | Form Q&A (workaround para Q&A multipregunta) |
| GET    | `/docs` | Swagger UI auto-generado |

## Submitir un job simple

```bash
curl -X POST http://127.0.0.1:8090/jobs -H "Content-Type: application/json" -d '{
  "name": "descarga-video",
  "command": "yt-dlp -o out.mp4 https://..."
}'
```

## Submitir un pipeline (descarga → transcribe → doblar)

```bash
curl -X POST http://127.0.0.1:8090/jobs -H "Content-Type: application/json" -d '{
  "name": "video-doblaje-abril",
  "steps": [
    {"id": "descarga",   "command": "yt-dlp -o out.mp4 ..."},
    {"id": "transcribe", "command": "whisper out.mp4 ...",      "depends_on": ["descarga"]},
    {"id": "doblar",     "command": "python doblador.py ...",   "depends_on": ["transcribe"]}
  ]
}'
```

Si `descarga` falla, los demás se marcan `cancelled` y el pipeline padre se agrega a `failed`.

## Eventos standard (logs/jobs/events.log)

Una línea por evento, formato:
```
<timestamp> JOB|<evento>|<id>|<name>|<estado>|<k=v>...
```

Eventos: `submitted`, `started`, `step_started`, `step_done`, `step_failed`, `done`, `failed`, `cancelled`.

Pensado para ser tail-eable por `monitor_hub` o `Monitor` de Claude para emitir notificaciones.

## Tools del agente

El agente tiene 4 nuevas tools en `agent.py`:

- `execute_long(name, command|steps, cwd?)` — encola un job/pipeline
- `job_status(job_id, incluir_output?, lineas?)` — consulta estado
- `job_list(estado?, limite?)` — lista jobs
- `job_cancel(job_id)` — cancela

Además, `execute_bash` tiene un guardrail que rechaza comandos largos (yt-dlp, ffmpeg, whisper, etc.) y empuja al LLM a usar `execute_long`.

## Estructura

```
job_manager/
├── __init__.py
├── __main__.py        # entry point: python -m job_manager
├── server.py          # FastAPI app
├── worker.py          # ThreadPoolExecutor + subprocess runner
├── db.py              # SQLite helpers
├── events.py          # event emitter
├── dashboard.html     # UI principal
├── qa.html            # form Q&A
├── jobs.db            # SQLite (auto-creado)
└── qa_inbox/          # respuestas Q&A (auto-creado)

agente_core/
└── job_client.py      # cliente HTTP del agente

agente_core/logs/jobs/
├── events.log         # event stream
└── <job_id>.log       # stdout/stderr por job
```

## Decisiones de diseño

- **Servicio aparte** del agente (sobrevive `/reiniciar` del supervisor).
- **FastAPI** (async + Swagger auto).
- **2 workers max** por default (configurable).
- **SQLite** con WAL — sin Redis, sin Celery.
- **No auto-purga** del histórico (acumulativo para evaluaciones).
- **SIGTERM con grace de 5s**, luego SIGKILL en cancelación.
- **Reúso de filtros** `bash_terminal.es_comando_peligroso` antes de spawn.
