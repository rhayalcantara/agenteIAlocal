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
    """Obtiene el servicio de Gmail autenticado.

    Sale RÁPIDO (exit 2 = token expirado) si las credenciales están muertas,
    en vez de dejar que el agente queme 5 min interpretando un traceback.
    Visto 24-may con Promerica id=7: 'creds.refresh(Request())' lanzó
    RefreshError sin capturar → traceback feo → timeout del scheduler.
    """
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google.auth.exceptions import RefreshError
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: Instala google-api-python-client y google-auth-oauthlib")
        sys.exit(1)

    if not os.path.exists(TOKEN_FILE):
        print("ERROR: TOKEN_GMAIL_EXPIRADO — no existe token. Ejecuta: python reauth_gmail.py")
        sys.exit(2)

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w") as f:
                    f.write(creds.to_json())
            except RefreshError as e:
                # El refresh token también murió (revocado/expirado en el lado de Google).
                # Salir YA con mensaje único y corto — sin esto el agente queda 5 min.
                print(f"ERROR: TOKEN_GMAIL_EXPIRADO — el refresh_token también falló ({e}). "
                      "Ejecuta: python reauth_gmail.py")
                sys.exit(2)
            except Exception as e:
                print(f"ERROR: TOKEN_GMAIL_EXPIRADO — fallo en refresh ({type(e).__name__}: {e}). "
                      "Ejecuta: python reauth_gmail.py")
                sys.exit(2)
        else:
            print("ERROR: TOKEN_GMAIL_EXPIRADO — sin refresh_token. Ejecuta: python reauth_gmail.py")
            sys.exit(2)

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


def _extraer_adjuntos(service, msg_id: str, payload: dict, carpeta: str) -> list:
    """Recorre el payload de un correo, descarga todos los adjuntos a `carpeta`.
    Retorna lista de rutas guardadas."""
    rutas = []

    def _recorrer(partes):
        for parte in partes:
            filename = parte.get("filename", "")
            body = parte.get("body", {}) or {}
            if parte.get("parts"):
                _recorrer(parte["parts"])
            if filename and body.get("size", 0) > 0:
                attachment_id = body.get("attachmentId")
                data = body.get("data")
                if attachment_id:
                    att = service.users().messages().attachments().get(
                        userId="me", messageId=msg_id, id=attachment_id
                    ).execute()
                    data = att.get("data", "")
                if data:
                    file_data = base64.urlsafe_b64decode(data + "==")
                    # Sanitizar filename
                    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)
                    ruta = os.path.join(carpeta, safe_name)
                    # Si ya existe, prefijar con msg_id corto
                    if os.path.exists(ruta):
                        base, ext = os.path.splitext(safe_name)
                        ruta = os.path.join(carpeta, f"{base}_{msg_id[:8]}{ext}")
                    with open(ruta, "wb") as f:
                        f.write(file_data)
                    rutas.append(ruta)

    _recorrer(payload.get("parts", []))
    return rutas


def cmd_descargar_adjuntos(args):
    """Descarga adjuntos de los correos que coincidan con --query, a la carpeta dada."""
    service = _get_service()
    from googleapiclient.errors import HttpError

    # Resolver carpeta destino
    carpeta = args.carpeta
    if not os.path.isabs(carpeta):
        carpeta = os.path.join(_ROOT, carpeta)
    os.makedirs(carpeta, exist_ok=True)

    # Tracking de IDs procesados (para no re-descargar)
    tracking_file = os.path.join(carpeta, ".procesados.json")
    procesados = set()
    if os.path.exists(tracking_file):
        try:
            with open(tracking_file, "r", encoding="utf-8") as f:
                procesados = set(json.load(f))
        except Exception:
            procesados = set()

    try:
        # Buscar correos que coincidan
        ids = []
        page_token = None
        while True:
            resp = service.users().messages().list(
                userId="me", q=args.query, maxResults=100, pageToken=page_token,
            ).execute()
            ids.extend([m["id"] for m in resp.get("messages", [])])
            page_token = resp.get("nextPageToken")
            if not page_token or (args.limite and len(ids) >= args.limite):
                break
        if args.limite:
            ids = ids[: args.limite]

        # Filtrar los que ya procesamos (a menos que --reprocesar)
        if not args.reprocesar:
            ids = [i for i in ids if i not in procesados]

        if not ids:
            print(json.dumps({
                "descargados": 0,
                "carpeta": carpeta,
                "mensaje": "Sin correos nuevos para procesar (todos ya procesados o sin coincidencias).",
            }, ensure_ascii=False, indent=2))
            return

        def _persistir_tracking():
            with open(tracking_file, "w", encoding="utf-8") as f:
                json.dump(sorted(procesados), f, ensure_ascii=False, indent=2)

        resultados = []
        nuevos = 0
        errores = []
        for msg_id in ids:
            try:
                msg = service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()
                headers = msg["payload"].get("headers", [])
                de = _get_header(headers, "From")
                asunto = _get_header(headers, "Subject")
                fecha = _get_header(headers, "Date")
                adjuntos = _extraer_adjuntos(service, msg_id, msg["payload"], carpeta)
                if adjuntos:
                    resultados.append({
                        "id": msg_id, "de": de, "asunto": asunto, "fecha": fecha,
                        "adjuntos": adjuntos,
                    })
                # Marcar procesado y persistir tras cada uno (resiliente a crashes)
                procesados.add(msg_id)
                _persistir_tracking()
                nuevos += 1
            except Exception as e:
                errores.append({"id": msg_id, "error": str(e)})
                # No abortar el loop entero por un error puntual de red
                continue

        total_archivos = sum(len(r["adjuntos"]) for r in resultados)
        salida = {
            "correos_procesados": nuevos,
            "correos_con_adjuntos": len(resultados),
            "total_archivos": total_archivos,
            "carpeta": carpeta,
            "detalle": resultados,
        }
        if errores:
            salida["errores"] = errores
        print(json.dumps(salida, ensure_ascii=False, indent=2))
    except HttpError as e:
        print(f"ERROR Gmail API: {e}")
        sys.exit(1)


def cmd_borrar(args):
    """Mueve correos a la papelera (recuperables 30 días). Requiere scope gmail.modify."""
    service = _get_service()
    from googleapiclient.errors import HttpError
    try:
        # Si vino --id directo, lo usamos; sino, buscamos por query
        if args.id:
            ids = [args.id]
        else:
            if not args.query:
                print("ERROR: debes pasar --query o --id")
                sys.exit(1)

            ids = []
            page_token = None
            while True:
                resp = service.users().messages().list(
                    userId="me",
                    q=args.query,
                    maxResults=500,
                    pageToken=page_token,
                ).execute()
                ids.extend([m["id"] for m in resp.get("messages", [])])
                page_token = resp.get("nextPageToken")
                if not page_token or (args.limite and len(ids) >= args.limite):
                    break

            if args.limite:
                ids = ids[: args.limite]

        if not ids:
            print(json.dumps({"borrados": 0, "mensaje": "Sin coincidencias para borrar."}, ensure_ascii=False))
            return

        if args.dry_run:
            print(json.dumps({
                "dry_run": True,
                "encontrados": len(ids),
                "ids_muestra": ids[:5],
                "mensaje": f"Se moverían {len(ids)} correo(s) a la papelera. Re-ejecuta sin --dry-run.",
            }, ensure_ascii=False, indent=2))
            return

        # batchModify acepta hasta 1000 ids por llamada
        borrados = 0
        for i in range(0, len(ids), 500):
            lote = ids[i:i + 500]
            service.users().messages().batchModify(
                userId="me",
                body={"ids": lote, "addLabelIds": ["TRASH"], "removeLabelIds": ["INBOX", "UNREAD"]},
            ).execute()
            borrados += len(lote)

        print(json.dumps({
            "borrados": borrados,
            "destino": "TRASH (recuperable 30 días)",
            "query": args.query or f"id={args.id}",
        }, ensure_ascii=False, indent=2))
    except HttpError as e:
        print(f"ERROR Gmail API: {e}")
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

    # borrar — mueve a TRASH (recuperable 30 días)
    p_borrar = sub.add_parser("borrar", help="Mueve correos a la papelera (recuperable 30 días)")
    p_borrar.add_argument("--query", "-q", help="Query Gmail (e.g. 'from:foo@bar.com')")
    p_borrar.add_argument("--id", help="ID específico de un correo (alternativa a --query)")
    p_borrar.add_argument("--limite", type=int, help="Tope de correos a procesar")
    p_borrar.add_argument("--dry-run", action="store_true", help="Solo muestra cuántos se borrarían, no borra")
    p_borrar.set_defaults(func=cmd_borrar)

    # descargar_adjuntos — guarda adjuntos de correos que coincidan con --query
    p_adj = sub.add_parser("descargar_adjuntos",
                           help="Descarga adjuntos de correos que coincidan, evita duplicados")
    p_adj.add_argument("--query", "-q", required=True,
                       help="Query Gmail (e.g. 'from:avdmail@avdinternacional.com')")
    p_adj.add_argument("--carpeta", required=True,
                       help="Carpeta destino (relativa al root o absoluta)")
    p_adj.add_argument("--limite", type=int, help="Tope de correos a procesar")
    p_adj.add_argument("--reprocesar", action="store_true",
                       help="Re-descargar incluso si el correo ya fue procesado antes")
    p_adj.set_defaults(func=cmd_descargar_adjuntos)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
