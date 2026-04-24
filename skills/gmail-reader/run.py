"""
Skill gmail-reader: Lee y busca correos de Gmail via API OAuth2.

Uso (via ejecutar_script_skill o directo):
    python run.py leer [--cantidad N]
    python run.py buscar --query "from:amazon.com"
    python run.py resumen
    python run.py ver --id <message_id>
"""
import os
import sys
import json
import argparse
import base64
import re

# Rutas de credenciales — siempre relativas al root del proyecto
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_FILE = os.path.join(_ROOT, "gmail_manager", "credentials.json")
TOKEN_FILE = os.path.join(_ROOT, "gmail_manager", "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _get_service():
    """Obtiene el servicio de Gmail autenticado."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: Instala google-api-python-client y google-auth-oauthlib")
        sys.exit(1)

    if not os.path.exists(TOKEN_FILE):
        print(f"ERROR: No existe token de autenticación en {TOKEN_FILE}")
        print("Ejecuta primero: python gmail_manager/main.py")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            print("ERROR: Token expirado. Ejecuta: python gmail_manager/main.py")
            sys.exit(1)

    from googleapiclient.discovery import build
    return build("gmail", "v1", credentials=creds)


def _extract_body(payload) -> str:
    """Extrae el cuerpo del mensaje (texto plano preferido)."""
    if "parts" in payload:
        for part in payload["parts"]:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        # Si no hay text/plain, buscar recursivo
        for part in payload["parts"]:
            text = _extract_body(part)
            if text:
                return text
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
    return ""


def _get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _format_message(service, msg_id: str, incluir_cuerpo: bool = False) -> dict:
    """Obtiene y formatea un mensaje por ID."""
    from googleapiclient.errors import HttpError
    try:
        msg = service.users().messages().get(
            userId="me", id=msg_id, format="full"
        ).execute()
        headers = msg["payload"]["headers"]
        data = {
            "id": msg_id,
            "de": _get_header(headers, "From"),
            "asunto": _get_header(headers, "Subject"),
            "fecha": _get_header(headers, "Date"),
            "snippet": msg.get("snippet", ""),
        }
        if incluir_cuerpo:
            data["cuerpo"] = _extract_body(msg["payload"])[:3000]
        return data
    except HttpError as e:
        return {"id": msg_id, "error": str(e)}


# ── Comandos ──────────────────────────────────────────────────────────────────

def cmd_leer(args):
    """Lee los últimos N correos del inbox."""
    service = _get_service()
    from googleapiclient.errors import HttpError
    try:
        resp = service.users().messages().list(
            userId="me",
            labelIds=["INBOX"],
            maxResults=args.cantidad
        ).execute()
        mensajes = resp.get("messages", [])
        if not mensajes:
            print("No hay correos en el inbox.")
            return

        resultados = []
        for m in mensajes:
            resultados.append(_format_message(service, m["id"], incluir_cuerpo=args.cuerpo))

        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    except HttpError as e:
        print(f"ERROR Gmail API: {e}")
        sys.exit(1)


def cmd_buscar(args):
    """Busca correos con query de Gmail."""
    service = _get_service()
    from googleapiclient.errors import HttpError
    try:
        resp = service.users().messages().list(
            userId="me",
            q=args.query,
            maxResults=args.cantidad
        ).execute()
        mensajes = resp.get("messages", [])
        if not mensajes:
            print(f"Sin resultados para: {args.query}")
            return

        resultados = []
        for m in mensajes:
            resultados.append(_format_message(service, m["id"], incluir_cuerpo=args.cuerpo))

        print(json.dumps(resultados, ensure_ascii=False, indent=2))
    except HttpError as e:
        print(f"ERROR Gmail API: {e}")
        sys.exit(1)


def cmd_resumen(args):
    """Muestra conteo de correos no leídos y remitentes frecuentes."""
    service = _get_service()
    from googleapiclient.errors import HttpError
    try:
        # No leídos
        resp_unread = service.users().messages().list(
            userId="me", labelIds=["UNREAD", "INBOX"], maxResults=50
        ).execute()
        no_leidos = resp_unread.get("resultSizeEstimate", 0)
        mensajes_unread = resp_unread.get("messages", [])

        # Remitentes frecuentes en no leídos
        from collections import Counter
        remitentes = Counter()
        for m in mensajes_unread[:20]:
            info = _format_message(service, m["id"])
            # Extraer solo el dominio/nombre del remitente
            de = info.get("de", "")
            remitentes[de] += 1

        resumen = {
            "no_leidos_inbox": no_leidos,
            "muestra_remitentes": [
                {"remitente": r, "cantidad": c}
                for r, c in remitentes.most_common(10)
            ],
        }
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
    except HttpError as e:
        print(f"ERROR Gmail API: {e}")
        sys.exit(1)


def cmd_ver(args):
    """Ver un correo completo por ID."""
    service = _get_service()
    info = _format_message(service, args.id, incluir_cuerpo=True)
    print(json.dumps(info, ensure_ascii=False, indent=2))


def cmd_enviar(args):
    """Envía un correo desde la cuenta de Gmail autenticada."""
    import base64
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from googleapiclient.errors import HttpError

    service = _get_service()

    # Construir mensaje
    msg = MIMEMultipart("alternative")
    msg["To"] = args.para
    msg["Subject"] = args.asunto

    # Cuerpo en texto plano
    cuerpo_txt = args.cuerpo
    parte_txt = MIMEText(cuerpo_txt, "plain", "utf-8")
    msg.attach(parte_txt)

    # Cuerpo HTML opcional (si el texto tiene saltos de línea, hacerlo legible)
    cuerpo_html = cuerpo_txt.replace("\n", "<br>")
    parte_html = MIMEText(
        f"<html><body style='font-family:sans-serif;line-height:1.6'>{cuerpo_html}</body></html>",
        "html", "utf-8"
    )
    msg.attach(parte_html)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        sent = service.users().messages().send(
            userId="me", body={"raw": raw}
        ).execute()
        print(f"Correo enviado OK. ID: {sent['id']} para: {args.para}")
    except HttpError as e:
        print(f"ERROR al enviar: {e}")
        sys.exit(1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Skill gmail-reader")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # leer
    p_leer = sub.add_parser("leer", help="Lee correos del inbox")
    p_leer.add_argument("--cantidad", type=int, default=10)
    p_leer.add_argument("--cuerpo", action="store_true", help="Incluir cuerpo completo")
    p_leer.set_defaults(func=cmd_leer)

    # buscar
    p_buscar = sub.add_parser("buscar", help="Busca correos por query Gmail")
    p_buscar.add_argument("--query", "-q", required=True)
    p_buscar.add_argument("--cantidad", type=int, default=10)
    p_buscar.add_argument("--cuerpo", action="store_true")
    p_buscar.set_defaults(func=cmd_buscar)

    # resumen
    p_res = sub.add_parser("resumen", help="Conteo de no leídos y remitentes")
    p_res.set_defaults(func=cmd_resumen)

    # ver
    p_ver = sub.add_parser("ver", help="Ver correo completo por ID")
    p_ver.add_argument("--id", required=True)
    p_ver.set_defaults(func=cmd_ver)

    # enviar
    p_env = sub.add_parser("enviar", help="Envía un correo")
    p_env.add_argument("--para", required=True, help="Destinatario (email)")
    p_env.add_argument("--asunto", required=True, help="Asunto del correo")
    p_env.add_argument("--cuerpo", required=True, help="Cuerpo del correo (texto plano)")
    p_env.set_defaults(func=cmd_enviar)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
