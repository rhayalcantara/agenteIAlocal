"""SQLite helpers para job_manager.

Tabla `jobs`:
- id            UUID (str)
- name          nombre legible (e.g., "video-doblaje-X")
- command       comando shell a ejecutar (NULL si es pipeline padre)
- parent_id     id del job padre (NULL si es root)
- step_id       nombre del step dentro del pipeline (NULL si no aplica)
- depends_on    JSON array de step_ids del mismo pipeline que deben terminar OK antes
- estado        queued | running | done | failed | cancelled | blocked
- exit_code     int (NULL hasta que termina)
- pid           int (NULL hasta que arranca)
- log_file      ruta absoluta al .log de stdout/stderr
- cwd           directorio donde se ejecuta (default: ROOT del proyecto)
- env_extra     JSON dict de variables extra (heredadas + estas)
- error         mensaje de error (NULL si OK)
- created_at    iso 8601 utc
- started_at    iso 8601 utc (NULL hasta arranque)
- finished_at   iso 8601 utc (NULL hasta fin)
"""
import os
import json
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
DB_PATH = os.path.join(_ROOT, "job_manager", "jobs.db")
LOGS_DIR = os.path.join(_ROOT, "agente_core", "logs", "jobs")
EVENTS_LOG = os.path.join(LOGS_DIR, "events.log")

ESTADOS = ("queued", "running", "done", "failed", "cancelled", "blocked")
ESTADOS_TERMINALES = ("done", "failed", "cancelled")

_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    with _connect() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id           TEXT PRIMARY KEY,
                name         TEXT NOT NULL,
                command      TEXT,
                parent_id    TEXT,
                step_id      TEXT,
                depends_on   TEXT,
                estado       TEXT NOT NULL,
                exit_code    INTEGER,
                pid          INTEGER,
                log_file     TEXT,
                cwd          TEXT,
                env_extra    TEXT,
                error        TEXT,
                created_at   TEXT NOT NULL,
                started_at   TEXT,
                finished_at  TEXT
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS ix_jobs_estado ON jobs(estado)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_jobs_parent ON jobs(parent_id)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_jobs_created ON jobs(created_at)")


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict:
    if row is None:
        return None
    d = dict(row)
    if d.get("depends_on"):
        try:
            d["depends_on"] = json.loads(d["depends_on"])
        except Exception:
            d["depends_on"] = []
    else:
        d["depends_on"] = []
    if d.get("env_extra"):
        try:
            d["env_extra"] = json.loads(d["env_extra"])
        except Exception:
            d["env_extra"] = {}
    else:
        d["env_extra"] = {}
    return d


# ── Operaciones ──────────────────────────────────────────────────────────────

def crear_job(name: str, command: Optional[str], *, parent_id: Optional[str] = None,
              step_id: Optional[str] = None, depends_on: Optional[list] = None,
              cwd: Optional[str] = None, env_extra: Optional[dict] = None,
              estado_inicial: str = "queued") -> dict:
    """Crea un job (root o step). Retorna el job creado."""
    job_id = str(uuid.uuid4())[:8] + str(int(time.time() * 1000) % 10000).zfill(4)
    log_file = os.path.join(LOGS_DIR, f"{job_id}.log") if command else None
    with _lock, _connect() as c:
        c.execute("""
            INSERT INTO jobs
            (id, name, command, parent_id, step_id, depends_on, estado,
             log_file, cwd, env_extra, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, name, command, parent_id, step_id,
            json.dumps(depends_on) if depends_on else None,
            estado_inicial,
            log_file,
            cwd or _ROOT,
            json.dumps(env_extra) if env_extra else None,
            _now_iso(),
        ))
    return obtener_job(job_id)


def obtener_job(job_id: str) -> Optional[dict]:
    with _connect() as c:
        row = c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return _row_to_dict(row)


def listar_jobs(estado: Optional[str] = None, name_like: Optional[str] = None,
                solo_roots: bool = False, limite: int = 200) -> list:
    sql = "SELECT * FROM jobs WHERE 1=1"
    params = []
    if estado:
        sql += " AND estado = ?"
        params.append(estado)
    if name_like:
        sql += " AND name LIKE ?"
        params.append(f"%{name_like}%")
    if solo_roots:
        sql += " AND parent_id IS NULL"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limite)
    with _connect() as c:
        rows = c.execute(sql, params).fetchall()
    return [_row_to_dict(r) for r in rows]


def listar_steps(parent_id: str) -> list:
    with _connect() as c:
        rows = c.execute(
            "SELECT * FROM jobs WHERE parent_id = ? ORDER BY created_at ASC",
            (parent_id,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def actualizar_estado(job_id: str, estado: str, *, exit_code: Optional[int] = None,
                      pid: Optional[int] = None, error: Optional[str] = None,
                      mark_started: bool = False, mark_finished: bool = False):
    sets = ["estado = ?"]
    params = [estado]
    if exit_code is not None:
        sets.append("exit_code = ?")
        params.append(exit_code)
    if pid is not None:
        sets.append("pid = ?")
        params.append(pid)
    if error is not None:
        sets.append("error = ?")
        params.append(error)
    if mark_started:
        sets.append("started_at = ?")
        params.append(_now_iso())
    if mark_finished:
        sets.append("finished_at = ?")
        params.append(_now_iso())
    params.append(job_id)
    with _lock, _connect() as c:
        c.execute(f"UPDATE jobs SET {', '.join(sets)} WHERE id = ?", params)


def jobs_listos_para_correr(max_workers: int):
    """Retorna (listos, parents_a_recalcular).
    `listos`  = jobs queued con deps done, hasta max_workers - running.
    `parents_a_recalcular` = set de parent_ids cuyo agregado puede haber cambiado
    (porque cancelamos steps por dep fail durante este barrido)."""
    with _connect() as c:
        running = c.execute(
            "SELECT COUNT(*) AS n FROM jobs WHERE estado = 'running'"
        ).fetchone()["n"]
        slots = max(0, max_workers - running)
        candidatos = c.execute(
            "SELECT * FROM jobs WHERE estado = 'queued' ORDER BY created_at ASC"
        ).fetchall()
    listos = []
    parents_recalc: set = set()
    for r in candidatos:
        d = _row_to_dict(r)
        # Si no es step de pipeline o no tiene deps, está listo
        if not d.get("parent_id") or not d.get("depends_on"):
            if len(listos) < slots:
                listos.append(d)
            continue
        # Verificar deps (step_ids dentro del mismo pipeline)
        deps_ok = _deps_resueltas(d["parent_id"], d["depends_on"])
        if deps_ok == "ok":
            if len(listos) < slots:
                listos.append(d)
        elif deps_ok == "fail":
            # Una dep falló → cancelar este step (siempre, no consume slot)
            actualizar_estado(d["id"], "cancelled",
                              error=f"Dep falló dentro del pipeline {d['parent_id']}",
                              mark_finished=True)
            parents_recalc.add(d["parent_id"])
    return listos, parents_recalc


def _deps_resueltas(parent_id: str, deps: list) -> str:
    """Retorna 'ok' (todas done), 'fail' (alguna failed/cancelled), 'pending' (en curso)."""
    if not deps:
        return "ok"
    with _connect() as c:
        placeholders = ",".join(["?"] * len(deps))
        rows = c.execute(
            f"SELECT step_id, estado FROM jobs WHERE parent_id = ? AND step_id IN ({placeholders})",
            [parent_id] + deps,
        ).fetchall()
    encontrados = {r["step_id"]: r["estado"] for r in rows}
    for dep_step in deps:
        st = encontrados.get(dep_step)
        if st is None:
            return "pending"
        if st in ("failed", "cancelled"):
            return "fail"
        if st != "done":
            return "pending"
    return "ok"


def aggregate_pipeline_state(parent_id: str) -> Optional[str]:
    """Calcula el estado agregado de un pipeline desde sus steps.
    Retorna None si no aplica (job no es pipeline padre)."""
    steps = listar_steps(parent_id)
    if not steps:
        return None
    estados = [s["estado"] for s in steps]
    if any(s == "running" for s in estados) or any(s == "queued" for s in estados):
        return "running"
    if all(s == "done" for s in estados):
        return "done"
    if any(s == "failed" for s in estados):
        return "failed"
    if any(s == "cancelled" for s in estados) and not any(s in ("running", "queued") for s in estados):
        return "cancelled"
    return None


def purgar_antes_de(fecha_iso: str) -> int:
    """Borra jobs cuyo finished_at < fecha. Retorna cuántos borró."""
    with _lock, _connect() as c:
        cur = c.execute(
            "DELETE FROM jobs WHERE finished_at IS NOT NULL AND finished_at < ?",
            (fecha_iso,)
        )
        return cur.rowcount


def stats() -> dict:
    with _connect() as c:
        rows = c.execute(
            "SELECT estado, COUNT(*) AS n FROM jobs GROUP BY estado"
        ).fetchall()
    return {r["estado"]: r["n"] for r in rows}
