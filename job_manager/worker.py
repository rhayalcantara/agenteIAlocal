"""Worker pool — corre los jobs queued.

Loop principal:
    1) Cada `tick_seconds`, consulta jobs listos para correr (deps OK, slots libres)
    2) Por cada uno, lanza subprocess.Popen en hilo
    3) Stdout/stderr → log_file del job
    4) Al terminar, actualiza estado y emite evento
    5) Si era step de pipeline, recalcula estado del padre

Cancelación:
    Otro hilo (la API) marca estado='cancelled' o registra el job_id en _cancel_requests.
    El worker que lo está corriendo detecta y manda SIGTERM, espera 5s, luego SIGKILL.
"""
import os
import sys
import time
import shlex
import signal
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor

from . import db
from . import events


def _path_enriquecido_desde_registry() -> str:
    """En Windows, lee el PATH del registry (User+System) y lo combina con el actual,
    para capturar binarios instalados después de que arrancó el job_manager (ej: ffmpeg
    via winget). En no-Windows, retorna el PATH actual sin cambios."""
    actual = os.environ.get("PATH", "")
    if sys.platform != "win32":
        return actual
    try:
        import winreg
        extras = []
        for hkey, sub in [
            (winreg.HKEY_CURRENT_USER, r"Environment"),
            (winreg.HKEY_LOCAL_MACHINE,
             r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        ]:
            try:
                k = winreg.OpenKey(hkey, sub)
                val, _ = winreg.QueryValueEx(k, "Path")
                winreg.CloseKey(k)
                val = os.path.expandvars(val or "")
                for p in val.split(";"):
                    p = p.strip()
                    if p and p not in actual and p not in extras:
                        extras.append(p)
            except Exception:
                continue
        if extras:
            return actual + ";" + ";".join(extras)
    except Exception:
        pass
    return actual

# Filtros de seguridad — reusa el mismo del bash_terminal
_AGENTE_CORE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agente_core")
sys.path.insert(0, _AGENTE_CORE)
try:
    from bash_terminal import es_comando_peligroso
except Exception:
    def es_comando_peligroso(_cmd: str):
        return False, ""

# Estado global
_cancel_requests: set = set()
_cancel_lock = threading.Lock()
_running_procs: dict = {}        # job_id -> Popen
_running_procs_lock = threading.Lock()
_stop_event = threading.Event()
_grace_seconds = 5


def solicitar_cancelacion(job_id: str):
    """Marca un job para cancelación (lo recoge el worker que lo corre, o lo descarta si está queued)."""
    with _cancel_lock:
        _cancel_requests.add(job_id)


def _aplicar_cancelaciones_pendientes():
    """Para jobs en 'queued' marcados para cancelar — los pasamos a cancelled directo.
    Para jobs en 'running' — mandamos SIGTERM al subproceso."""
    with _cancel_lock:
        pendientes = list(_cancel_requests)
    for job_id in pendientes:
        job = db.obtener_job(job_id)
        if not job:
            with _cancel_lock:
                _cancel_requests.discard(job_id)
            continue
        if job["estado"] == "queued":
            db.actualizar_estado(job_id, "cancelled", error="Cancelado antes de arrancar",
                                 mark_finished=True)
            events.emit("cancelled", db.obtener_job(job_id), signal="none")
            with _cancel_lock:
                _cancel_requests.discard(job_id)
        elif job["estado"] == "running":
            with _running_procs_lock:
                proc = _running_procs.get(job_id)
            if proc and proc.poll() is None:
                try:
                    proc.terminate()  # SIGTERM
                    # NO descartamos del set aún — el hilo del worker lo procesará
                except Exception:
                    pass


def _ejecutar_job(job: dict):
    """Corre un job individual. Asume que está marcado 'running' o lo marcamos."""
    job_id = job["id"]
    cmd = job["command"]
    log_file = job["log_file"]
    cwd = job["cwd"] or os.getcwd()
    env = dict(os.environ)
    # Refrescar PATH desde el registry (Windows) — captura ffmpeg, etc., instalados
    # después de que el job_manager arrancó.
    env["PATH"] = _path_enriquecido_desde_registry()
    if job.get("env_extra"):
        env.update(job["env_extra"])

    # Filtro de seguridad
    peligroso, razon = es_comando_peligroso(cmd or "")
    if peligroso:
        db.actualizar_estado(job_id, "failed",
                             error=f"COMANDO BLOQUEADO: {razon}",
                             exit_code=-1, mark_started=True, mark_finished=True)
        events.emit("failed", db.obtener_job(job_id), err=f"bloqueado:{razon}")
        return

    # Marcar started (si no lo está ya)
    if job["estado"] != "running":
        db.actualizar_estado(job_id, "running", mark_started=True)
    if job.get("parent_id"):
        events.emit("step_started", db.obtener_job(job_id), step=job.get("step_id", ""))
    else:
        events.emit("started", db.obtener_job(job_id))

    # Asegurar log file
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # Spawn subprocess. shell=True para que el LLM pueda mandar pipes/redirects
    try:
        with open(log_file, "ab", buffering=0) as logfp:
            proc = subprocess.Popen(
                cmd, shell=True, cwd=cwd, env=env,
                stdout=logfp, stderr=subprocess.STDOUT,
                start_new_session=True if os.name != "nt" else False,
            )
            with _running_procs_lock:
                _running_procs[job_id] = proc
            db.actualizar_estado(job_id, "running", pid=proc.pid)

            # Esperar finalización con polling para soportar cancelación
            cancelado = False
            while True:
                rc = proc.poll()
                if rc is not None:
                    break
                with _cancel_lock:
                    si_cancelar = job_id in _cancel_requests
                if si_cancelar and not cancelado:
                    cancelado = True
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    # Espera grace, luego kill duro
                    deadline = time.time() + _grace_seconds
                    while proc.poll() is None and time.time() < deadline:
                        time.sleep(0.2)
                    if proc.poll() is None:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                if _stop_event.is_set() and not cancelado:
                    cancelado = True
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                time.sleep(0.5)
            exit_code = proc.returncode

        with _running_procs_lock:
            _running_procs.pop(job_id, None)

        if cancelado:
            db.actualizar_estado(job_id, "cancelled", exit_code=exit_code,
                                 mark_finished=True, error="Cancelado por usuario")
            events.emit("cancelled", db.obtener_job(job_id), exit=exit_code, signal="SIGTERM")
            with _cancel_lock:
                _cancel_requests.discard(job_id)
        elif exit_code == 0:
            db.actualizar_estado(job_id, "done", exit_code=0, mark_finished=True)
            if job.get("parent_id"):
                events.emit("step_done", db.obtener_job(job_id),
                            step=job.get("step_id", ""), exit=0)
            else:
                events.emit("done", db.obtener_job(job_id), exit=0)
        else:
            db.actualizar_estado(job_id, "failed", exit_code=exit_code, mark_finished=True,
                                 error=f"Exit code {exit_code}")
            if job.get("parent_id"):
                events.emit("step_failed", db.obtener_job(job_id),
                            step=job.get("step_id", ""), exit=exit_code)
            else:
                events.emit("failed", db.obtener_job(job_id), exit=exit_code)

    except Exception as e:
        db.actualizar_estado(job_id, "failed", error=f"Excepción: {e}", mark_finished=True)
        events.emit("failed", db.obtener_job(job_id), err=str(e)[:80])
        with _running_procs_lock:
            _running_procs.pop(job_id, None)

    # Recalcular estado del pipeline padre, si aplica
    if job.get("parent_id"):
        _recalcular_pipeline(job["parent_id"])


def _recalcular_pipeline(parent_id: str):
    parent = db.obtener_job(parent_id)
    if not parent or parent["estado"] in db.ESTADOS_TERMINALES:
        # No emitir evento si ya estaba terminal
        return
    estado = db.aggregate_pipeline_state(parent_id)
    if estado is None:
        return
    if estado in db.ESTADOS_TERMINALES:
        db.actualizar_estado(parent_id, estado, mark_finished=True)
        evt = estado  # done | failed | cancelled
        events.emit(evt, db.obtener_job(parent_id))
    elif estado != parent["estado"]:
        db.actualizar_estado(parent_id, estado, mark_started=True)


def loop_principal(max_workers: int = 2, tick_seconds: float = 1.0):
    """Loop del scheduler. Mientras no se pida stop, despacha jobs listos."""
    db.init_db()
    pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="job-worker")
    print(f"[job_manager] Worker loop iniciado. max_workers={max_workers}", flush=True)
    try:
        while not _stop_event.is_set():
            _aplicar_cancelaciones_pendientes()
            listos, parents_recalc = db.jobs_listos_para_correr(max_workers)
            for parent_id in parents_recalc:
                _recalcular_pipeline(parent_id)
                # Emitir evento step_failed/cancelled aquí también para visibilidad
                # (el step ya quedó cancelled en DB)
            for job in listos:
                # Marcar running antes del submit para evitar doble-pickup
                db.actualizar_estado(job["id"], "running", mark_started=True)
                pool.submit(_ejecutar_job, db.obtener_job(job["id"]))
            time.sleep(tick_seconds)
    finally:
        _stop_event.set()
        pool.shutdown(wait=True)
        print("[job_manager] Worker loop detenido.", flush=True)


def detener():
    _stop_event.set()
    # Mandar SIGTERM a todos los corriendo
    with _running_procs_lock:
        for jid, proc in list(_running_procs.items()):
            try:
                proc.terminate()
            except Exception:
                pass
