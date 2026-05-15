"""FastAPI server — endpoints REST + dashboard del job_manager.

Endpoints principales:
    POST   /jobs                     submit job o pipeline
    GET    /jobs                     listar (filtros)
    GET    /jobs/{id}                detalle
    GET    /jobs/{id}/output         tail del log
    DELETE /jobs/{id}                cancelar
    DELETE /jobs?antes=YYYY-MM-DD    purga manual
    GET    /pipelines/{id}           detalle de pipeline (parent + steps)
    GET    /events                   eventos crudos (con offset)
    GET    /stats                    contadores por estado
    GET    /                         dashboard HTML
    GET    /qa                       form Q&A (HTML dinamico)
    GET    /qa/pending               JSON con preguntas pendientes
    POST   /qa/ask                   Claude deposita una pregunta nueva
    POST   /qa                       guardar respuestas
    GET    /qa/answers               leer respuestas (?consume=true las archiva)
"""
import hashlib
import os
import json
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from . import db, events, worker

_HERE = os.path.dirname(os.path.abspath(__file__))
DASHBOARD_HTML = os.path.join(_HERE, "dashboard.html")
QA_HTML = os.path.join(_HERE, "qa.html")
QA_INBOX = os.path.join(_HERE, "qa_inbox")
QA_PENDING_DIR = os.path.join(QA_INBOX, "_pending")
QA_ANSWERED_DIR = os.path.join(QA_INBOX, "_answered")
QA_ARCHIVED_DIR = os.path.join(QA_INBOX, "_archived")

# Rate limit + queue cap (ENV-configurables)
MAX_QUEUED = int(os.environ.get("JOB_MANAGER_MAX_QUEUED", "20"))
RATE_WINDOW_SEC = int(os.environ.get("JOB_MANAGER_RATE_WINDOW", "60"))
RATE_MAX_SUBMITS = int(os.environ.get("JOB_MANAGER_RATE_MAX_SUBMITS", "10"))

_recent_submits: list[float] = []
_recent_submits_lock = threading.Lock()

app = FastAPI(
    title="job_manager",
    description="Backend de encolamiento de procesos largos para el agente.",
    version="0.1.0",
)

# Worker thread arranca al startup
_worker_thread: Optional[threading.Thread] = None


def _generar_nombre_default(job_in: "JobIn") -> str:
    """Genera un nombre legible cuando el cliente no provee uno bueno."""
    if job_in.command and job_in.command.strip():
        primer = job_in.command.strip().split()[0]
        primer = primer.split("/")[-1].split("\\")[-1][:24] or "cmd"
        src = job_in.command
    elif job_in.steps:
        primer = "pipeline"
        src = json.dumps([s.model_dump() for s in job_in.steps], sort_keys=True)
    else:
        primer = "job"
        src = str(time.time())
    h = hashlib.sha256(src.encode("utf-8", errors="replace")).hexdigest()[:6]
    return f"{primer}-{h}"


def _check_rate_limit():
    """Lanza 429 si se excede submits/ventana o queue cap."""
    now = time.time()
    with _recent_submits_lock:
        _recent_submits[:] = [t for t in _recent_submits if now - t < RATE_WINDOW_SEC]
        if len(_recent_submits) >= RATE_MAX_SUBMITS:
            raise HTTPException(
                status_code=429,
                detail=f"rate limit: max {RATE_MAX_SUBMITS} submits cada {RATE_WINDOW_SEC}s",
            )
        try:
            counts = db.stats()
        except Exception:
            counts = {}
        activos = counts.get("queued", 0) + counts.get("running", 0)
        if activos >= MAX_QUEUED:
            raise HTTPException(
                status_code=429,
                detail=f"queue cap: {activos} jobs activos (queued+running), max {MAX_QUEUED}",
            )
        _recent_submits.append(now)


class StepIn(BaseModel):
    id: str = Field(..., description="ID local del step dentro del pipeline (e.g. 'descarga')")
    command: str
    depends_on: Optional[List[str]] = None


class JobIn(BaseModel):
    name: Optional[str] = None          # si viene vacío/default, se autogenera del command
    command: Optional[str] = None       # si es pipeline, puede ir vacío
    steps: Optional[List[StepIn]] = None  # si vienen steps, es pipeline
    cwd: Optional[str] = None
    env: Optional[dict] = None


@app.on_event("startup")
def on_startup():
    db.init_db()
    for d in (QA_INBOX, QA_PENDING_DIR, QA_ANSWERED_DIR, QA_ARCHIVED_DIR):
        os.makedirs(d, exist_ok=True)
    global _worker_thread
    max_workers = int(os.environ.get("JOB_MANAGER_WORKERS", "2"))
    _worker_thread = threading.Thread(
        target=worker.loop_principal,
        kwargs={"max_workers": max_workers},
        daemon=True,
        name="job-scheduler",
    )
    _worker_thread.start()


@app.on_event("shutdown")
def on_shutdown():
    worker.detener()


# ── Jobs ─────────────────────────────────────────────────────────────────────

@app.post("/jobs")
def crear(job_in: JobIn):
    if not job_in.command and not job_in.steps:
        raise HTTPException(400, "Debes proveer 'command' o 'steps'")

    # Gap 1: si el nombre es vacio/default generico, generar uno legible
    if not job_in.name or job_in.name.strip() in ("", "tarea-sin-nombre", "job", "pipeline"):
        job_in.name = _generar_nombre_default(job_in)

    # Gap 2: rate limit + queue cap antes de aceptar
    _check_rate_limit()

    if job_in.steps:
        # Pipeline padre (sin command). Steps con parent_id apuntando al padre.
        parent = db.crear_job(
            name=job_in.name, command=None,
            cwd=job_in.cwd, env_extra=job_in.env,
            estado_inicial="queued",
        )
        events.emit("submitted", parent, steps=len(job_in.steps))
        for step in job_in.steps:
            db.crear_job(
                name=f"{job_in.name}::{step.id}",
                command=step.command,
                parent_id=parent["id"],
                step_id=step.id,
                depends_on=step.depends_on,
                cwd=job_in.cwd, env_extra=job_in.env,
                estado_inicial="queued",
            )
        return {"id": parent["id"], "name": parent["name"], "tipo": "pipeline",
                "steps": len(job_in.steps), "estado": "queued"}

    # Job simple
    job = db.crear_job(
        name=job_in.name, command=job_in.command,
        cwd=job_in.cwd, env_extra=job_in.env,
        estado_inicial="queued",
    )
    events.emit("submitted", job)
    return {"id": job["id"], "name": job["name"], "tipo": "job", "estado": "queued"}


@app.get("/jobs")
def listar(estado: Optional[str] = None, name: Optional[str] = None,
           solo_roots: bool = True, limite: int = 50):
    return db.listar_jobs(estado=estado, name_like=name,
                          solo_roots=solo_roots, limite=limite)


@app.get("/jobs/{job_id}")
def detalle(job_id: str):
    job = db.obtener_job(job_id)
    if not job:
        raise HTTPException(404, "job no encontrado")
    if not job["parent_id"]:
        # Si es pipeline (sin command pero tiene steps hijos), incluye steps
        steps = db.listar_steps(job_id)
        if steps:
            job["steps"] = steps
    return job


@app.get("/jobs/{job_id}/output")
def output(job_id: str, desde: int = 0, max_lineas: int = 200):
    job = db.obtener_job(job_id)
    if not job:
        raise HTTPException(404, "job no encontrado")
    log_file = job.get("log_file")
    if not log_file or not os.path.exists(log_file):
        return {"lineas": [], "total": 0, "siguiente": desde}
    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
        todas = f.readlines()
    total = len(todas)
    chunk = todas[desde:desde + max_lineas]
    return {
        "lineas": [l.rstrip("\n") for l in chunk],
        "total": total,
        "siguiente": min(desde + len(chunk), total),
    }


@app.delete("/jobs/{job_id}")
def cancelar(job_id: str):
    job = db.obtener_job(job_id)
    if not job:
        raise HTTPException(404, "job no encontrado")
    if job["estado"] in db.ESTADOS_TERMINALES:
        return {"id": job_id, "estado": job["estado"], "mensaje": "ya estaba en estado terminal"}
    worker.solicitar_cancelacion(job_id)
    return {"id": job_id, "estado": "cancelacion_solicitada"}


@app.delete("/jobs")
def purgar(antes: str = Query(..., description="ISO date YYYY-MM-DD; borra jobs finalizados antes")):
    # Validar formato
    try:
        datetime.strptime(antes, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Formato de fecha invalido (esperado YYYY-MM-DD)")
    fecha_iso = f"{antes}T00:00:00Z"
    n = db.purgar_antes_de(fecha_iso)
    return {"purgados": n, "antes": fecha_iso}


# ── Pipelines ────────────────────────────────────────────────────────────────

@app.get("/pipelines/{parent_id}")
def pipeline(parent_id: str):
    parent = db.obtener_job(parent_id)
    if not parent:
        raise HTTPException(404, "pipeline no encontrado")
    steps = db.listar_steps(parent_id)
    return {"parent": parent, "steps": steps}


# ── Eventos / stats ──────────────────────────────────────────────────────────

@app.get("/events")
def lista_eventos(desde: int = 0, max_lineas: int = 500):
    total = events.total_eventos()
    lineas = events.leer_eventos(desde_linea=desde, max_lineas=max_lineas)
    return {"lineas": lineas, "total": total, "siguiente": min(desde + len(lineas), total)}


@app.get("/stats")
def stats():
    return {"counts_por_estado": db.stats()}


# ── Dashboard HTML ───────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def dashboard():
    if os.path.exists(DASHBOARD_HTML):
        with open(DASHBOARD_HTML, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>job_manager</h1><p>Falta dashboard.html</p>"


# ── Q&A bidireccional (Claude pregunta -> usuario responde -> Claude lee) ───
#
# Protocolo:
#   1. Claude llama POST /qa/ask con {questions: [...], context?: str}
#      -> server escribe qa_inbox/_pending/<question_id>.json
#   2. Usuario abre /qa en el browser -> qa.html fetches GET /qa/pending
#      -> renderiza form -> POST /qa con respuestas
#      -> server mueve a qa_inbox/_answered/<question_id>.json
#   3. Claude llama GET /qa/answers?consume=true para recoger respuestas
#      -> server las mueve a qa_inbox/_archived/ y las retorna.


class QAQuestion(BaseModel):
    text: str
    type: str = "text"      # "text" | "options" | "yesno"
    options: Optional[List[str]] = None
    id: Optional[str] = None  # local id dentro del set, opcional


class QAAsk(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    questions: List[QAQuestion]
    context: Optional[str] = None
    from_: Optional[str] = Field(default="claude", alias="from")


@app.get("/qa", response_class=HTMLResponse)
def qa_form():
    if not os.path.exists(QA_HTML):
        return "<h1>Q&A inbox</h1><p>qa.html no existe.</p>"
    with open(QA_HTML, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/qa/ask")
def qa_ask(body: QAAsk):
    """Claude pide al usuario una o varias preguntas; quedan en _pending/."""
    qid = uuid.uuid4().hex[:12]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "id": qid,
        "from": body.from_ or "claude",
        "context": body.context or "",
        "questions": [q.model_dump() for q in body.questions],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    out = os.path.join(QA_PENDING_DIR, f"{ts}_{qid}.json")
    os.makedirs(QA_PENDING_DIR, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return {"id": qid, "guardado": out, "pendientes": _count_pending()}


@app.get("/qa/pending")
def qa_pending():
    """Lista preguntas que el user aun no responde (sin consumir)."""
    os.makedirs(QA_PENDING_DIR, exist_ok=True)
    items = []
    for fn in sorted(os.listdir(QA_PENDING_DIR)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(QA_PENDING_DIR, fn), "r", encoding="utf-8") as f:
            items.append(json.load(f))
    return {"count": len(items), "items": items}


@app.post("/qa")
async def qa_submit(payload: dict):
    """Recibe respuestas del form HTML. Si trae 'id', encuentra el _pending/ y lo
    mueve a _answered/. Si no hay id, guarda como respuesta huerfana (legacy)."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    qid = payload.get("id") or payload.get("_id")
    record = {
        **payload,
        "_recibido_at": datetime.now(timezone.utc).isoformat(),
    }

    if qid:
        # buscar pendiente correspondiente y moverlo + grabar respuesta
        moved = False
        for fn in os.listdir(QA_PENDING_DIR):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(QA_PENDING_DIR, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    q = json.load(f)
            except Exception:
                continue
            if q.get("id") == qid:
                record["_pregunta_original"] = q
                ans_path = os.path.join(QA_ANSWERED_DIR, f"{ts}_{qid}.json")
                with open(ans_path, "w", encoding="utf-8") as f:
                    json.dump(record, f, ensure_ascii=False, indent=2)
                try:
                    os.remove(path)
                except OSError:
                    pass
                moved = True
                return {"ok": True, "guardado": ans_path, "pregunta_id": qid}
        if not moved:
            # id no encontrado, guardar igual como huerfano
            out = os.path.join(QA_ANSWERED_DIR, f"{ts}_{qid}_orphan.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            return {"ok": True, "guardado": out, "pregunta_id": qid, "orphan": True}

    # Legacy: sin id, guardar plano
    out = os.path.join(QA_ANSWERED_DIR, f"{ts}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return {"ok": True, "guardado": out}


@app.get("/qa/answers")
def qa_answers(consume: bool = False):
    """Lista respuestas en _answered/. Con consume=true las mueve a _archived/."""
    os.makedirs(QA_ANSWERED_DIR, exist_ok=True)
    os.makedirs(QA_ARCHIVED_DIR, exist_ok=True)
    items = []
    consumed = []
    for fn in sorted(os.listdir(QA_ANSWERED_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(QA_ANSWERED_DIR, fn)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        items.append({"_file": fn, **data})
        if consume:
            dest = os.path.join(QA_ARCHIVED_DIR, fn)
            try:
                os.replace(path, dest)
                consumed.append(fn)
            except OSError:
                pass
    return {"count": len(items), "items": items, "consumed": consumed}


def _count_pending() -> int:
    if not os.path.exists(QA_PENDING_DIR):
        return 0
    return sum(1 for fn in os.listdir(QA_PENDING_DIR) if fn.endswith(".json"))
