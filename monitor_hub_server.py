"""Inicia el Monitor Hub con Dashboard web.

Uso:
    python monitor_hub_server.py
    python monitor_hub_server.py --port 8080
"""
import os
import sys
import threading
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agente_core"))

from dotenv import load_dotenv
load_dotenv()

from monitor_hub.hub import MonitorHub
from monitor_hub.dashboard.app import app, set_hub


def main():
    parser = argparse.ArgumentParser(description="Monitor Hub + Dashboard")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--config", default=None)
    args = parser.parse_args()

    hub = MonitorHub(config_path=args.config)
    set_hub(hub)

    # Hub en thread separado
    hub_thread = threading.Thread(target=hub.run, daemon=True)
    hub_thread.start()

    # Dashboard en main thread
    import uvicorn
    print(f"Dashboard: http://localhost:{args.port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
