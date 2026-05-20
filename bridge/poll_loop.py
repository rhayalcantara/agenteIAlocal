"""Loop de polling al inbox local del bridge — emite cada mensaje como linea para Monitor.

Stdout format: BRIDGE|from|text   (truncado a 8000 chars; la notificacion del harness
               puede recortar, pero la linea completa queda en el .output del Monitor)
Errores:       BRIDGE_ERR|<msg>
"""
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.getenv("BRIDGE_TOKEN", "")
URL = os.getenv("BRIDGE_LOCAL_URL", "http://localhost:8765").rstrip("/") + "/poll"
INTERVAL = int(os.getenv("BRIDGE_POLL_INTERVAL", "8"))

if not TOKEN:
    print("BRIDGE_ERR|BRIDGE_TOKEN no configurado", flush=True)
    sys.exit(1)

print(f"BRIDGE_READY|polling {URL} cada {INTERVAL}s", flush=True)

while True:
    try:
        r = requests.get(
            URL,
            params={"consume": "true"},
            headers={"X-Bridge-Token": TOKEN},
            timeout=6,
        )
        if r.status_code != 200:
            print(f"BRIDGE_ERR|HTTP {r.status_code} {r.text[:200]}", flush=True)
        else:
            for m in r.json().get("messages", []):
                src = m.get("from", "?")
                txt = (m.get("text", "") or "")[:8000].replace("\n", " ")
                print(f"BRIDGE|{src}|{txt}", flush=True)
    except Exception as e:
        print(f"BRIDGE_ERR|{type(e).__name__}: {e}", flush=True)
    time.sleep(INTERVAL)
