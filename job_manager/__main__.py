"""Entry point: `python -m job_manager`.

Levanta el servidor FastAPI en el puerto configurado (default 8090) y arranca
el worker thread automáticamente vía evento startup de FastAPI.
"""
import os
import sys

# Cargar .env del proyecto
try:
    from dotenv import load_dotenv
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass


def main():
    import uvicorn
    port = int(os.environ.get("JOB_MANAGER_PORT", "8090"))
    host = os.environ.get("JOB_MANAGER_HOST", "127.0.0.1")
    print(f"[job_manager] Iniciando en http://{host}:{port}", flush=True)
    uvicorn.run(
        "job_manager.server:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
        reload=False,
    )


if __name__ == "__main__":
    main()
