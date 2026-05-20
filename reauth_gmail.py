"""Re-autenticación de Gmail OAuth.

1. Intenta refrescar el token existente con refresh_token.
2. Si falla, hace backup y abre el flow OAuth en el navegador
   (run_local_server en puerto 8765, fijo, para reproducibilidad).

Uso:
    python reauth_gmail.py            # intenta refresh, fallback a flow
    python reauth_gmail.py --force    # salta refresh y va directo al flow
"""
import os
import sys
import shutil
import argparse
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = os.path.dirname(os.path.abspath(__file__))
GM_DIR = os.path.join(ROOT, "gmail_manager")
CREDENTIALS_FILE = os.path.join(GM_DIR, "credentials.json")
TOKEN_FILE = os.path.join(GM_DIR, "token.json")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _backup_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = f"{TOKEN_FILE}.bak.{ts}"
    shutil.copy2(TOKEN_FILE, bak)
    return bak


def try_refresh() -> bool:
    if not os.path.exists(TOKEN_FILE):
        print("[refresh] token.json no existe — saltando refresh")
        return False
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    except Exception as e:
        print(f"[refresh] no se pudo leer token.json: {e}")
        return False
    if creds.valid:
        print("[refresh] token aún válido — nada que hacer")
        return True
    if not creds.refresh_token:
        print("[refresh] sin refresh_token — flow interactivo requerido")
        return False
    try:
        creds.refresh(Request())
    except Exception as e:
        print(f"[refresh] refresh falló: {e}")
        return False
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print(f"[refresh] OK — token renovado, expira {creds.expiry}")
    return True


def run_flow() -> bool:
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"[flow] ERROR: falta {CREDENTIALS_FILE}", flush=True)
        return False
    bak = _backup_token()
    if bak:
        print(f"[flow] backup token previo: {bak}", flush=True)

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    prompt_msg = (
        "\n" + "=" * 70 +
        "\nSI EL NAVEGADOR NO SE ABRE, COPIA ESTA URL:\n{url}\n" +
        "=" * 70 + "\n"
    )
    kwargs = dict(
        open_browser=True,
        authorization_prompt_message=prompt_msg,
        access_type="offline",
        prompt="consent",
    )
    try:
        creds = flow.run_local_server(port=8765, **kwargs)
    except (PermissionError, OSError) as e:
        print(f"[flow] puerto 8765 no disponible ({e}) — usando puerto aleatorio", flush=True)
        creds = flow.run_local_server(port=0, **kwargs)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print(f"[flow] OK — token nuevo guardado, expira {creds.expiry}", flush=True)
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Saltar refresh, ir directo al flow OAuth")
    args = parser.parse_args()

    if not args.force and try_refresh():
        return 0
    if run_flow():
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
