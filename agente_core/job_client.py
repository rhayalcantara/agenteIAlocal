"""Cliente HTTP para el job_manager.

Usado por el agente desde tools.py / agent.py. NO lanza excepciones — siempre
retorna un dict con `ok` boolean y `error` si aplica, para que el LLM tenga
una salida estructurada.
"""
import os
import json
import requests

JOB_MANAGER_URL = os.environ.get("JOB_MANAGER_URL", "http://127.0.0.1:8090")
TIMEOUT = 5


def _post(path: str, payload: dict) -> dict:
    try:
        r = requests.post(f"{JOB_MANAGER_URL}{path}", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return {"ok": True, **r.json()}
    except requests.RequestException as e:
        return {"ok": False, "error": f"job_manager no responde: {e}"}


def _get(path: str) -> dict:
    try:
        r = requests.get(f"{JOB_MANAGER_URL}{path}", timeout=TIMEOUT)
        r.raise_for_status()
        return {"ok": True, "data": r.json()}
    except requests.RequestException as e:
        return {"ok": False, "error": f"job_manager no responde: {e}"}


def _delete(path: str) -> dict:
    try:
        r = requests.delete(f"{JOB_MANAGER_URL}{path}", timeout=TIMEOUT)
        r.raise_for_status()
        return {"ok": True, **r.json()}
    except requests.RequestException as e:
        return {"ok": False, "error": f"job_manager no responde: {e}"}


# ── API pública ──────────────────────────────────────────────────────────────

def submit_job(name: str, command: str, cwd: str = None) -> dict:
    """Encola un job simple. Retorna {ok, id, name, estado}."""
    payload = {"name": name, "command": command}
    if cwd:
        payload["cwd"] = cwd
    return _post("/jobs", payload)


def submit_pipeline(name: str, steps: list, cwd: str = None) -> dict:
    """Encola un pipeline.
    `steps` = lista de {id, command, depends_on?: [step_ids]}.
    Retorna {ok, id, name, tipo: 'pipeline', steps: N, estado}."""
    payload = {"name": name, "steps": steps}
    if cwd:
        payload["cwd"] = cwd
    return _post("/jobs", payload)


def status(job_id: str, incluir_output: bool = False, lineas: int = 30) -> dict:
    """Estado actual + opcionalmente últimas N líneas de output."""
    info = _get(f"/jobs/{job_id}")
    if not info["ok"]:
        return info
    data = info["data"]
    if incluir_output and data.get("log_file"):
        out = _get(f"/jobs/{job_id}/output?desde=0&max_lineas={lineas}")
        if out["ok"]:
            data["output_tail"] = out["data"]["lineas"]
    return {"ok": True, "data": data}


def list_jobs(estado: str = None, limite: int = 20) -> dict:
    """Lista jobs (solo roots por defecto)."""
    qs = f"?solo_roots=true&limite={limite}"
    if estado:
        qs += f"&estado={estado}"
    return _get(f"/jobs{qs}")


def cancel(job_id: str) -> dict:
    return _delete(f"/jobs/{job_id}")


# ── Q&A (preguntas al usuario) ─────────────────────────────────────────────

def qa_ask(questions: list, context: str = None) -> dict:
    """Pide al usuario una o varias preguntas via el form /qa.

    `questions` = lista de dicts { text, type?: "text"|"options"|"yesno", options?: [str], id?: str }.
    Retorna {ok, id} con el id del set para correlacionar respuestas.
    """
    payload = {"questions": questions, "from": "claude"}
    if context:
        payload["context"] = context
    return _post("/qa/ask", payload)


def qa_answers(consume: bool = True) -> dict:
    """Lee respuestas pendientes que el usuario envió.
    Con consume=true (default) las archiva tras leerlas.
    Retorna {ok, data: {count, items, consumed}}.
    """
    qs = "?consume=true" if consume else "?consume=false"
    return _get(f"/qa/answers{qs}")
