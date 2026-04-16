import os
import os.path
import base64
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'token.json')


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds


def _extraer_adjuntos(service, msg_id, payload, guardar_en):
    """Extrae y descarga todos los adjuntos de un mensaje."""
    adjuntos = []

    def _recorrer_partes(partes):
        for parte in partes:
            filename = parte.get('filename', '')
            body = parte.get('body', {})
            sub_partes = parte.get('parts', [])

            if sub_partes:
                _recorrer_partes(sub_partes)

            if filename and body.get('size', 0) > 0:
                attachment_id = body.get('attachmentId')
                data = body.get('data')

                if attachment_id:
                    att = service.users().messages().attachments().get(
                        userId='me', messageId=msg_id, id=attachment_id
                    ).execute()
                    data = att.get('data', '')

                if data:
                    file_data = base64.urlsafe_b64decode(data + '==')
                    ruta = os.path.join(guardar_en, filename)
                    with open(ruta, 'wb') as f:
                        f.write(file_data)
                    adjuntos.append(ruta)
                    print(f"  Adjunto guardado: {ruta} ({len(file_data)} bytes)")

    _recorrer_partes(payload.get('parts', []))
    return adjuntos


def main():
    parser = argparse.ArgumentParser(description='Gmail Manager')
    parser.add_argument('--query', type=str, default='',
                        help='Query de búsqueda (ej: "from:Promerica after:2026/03/31")')
    parser.add_argument('--limit', type=int, default=10,
                        help='Máximo de correos a mostrar (default: 10)')
    parser.add_argument('--download-attachments', action='store_true',
                        help='Descarga adjuntos de los correos encontrados')
    parser.add_argument('--save-dir', type=str, default='/tmp',
                        help='Directorio donde guardar los adjuntos (default: /tmp)')
    args = parser.parse_args()

    creds = get_credentials()

    try:
        service = build('gmail', 'v1', credentials=creds)

        query = args.query if args.query else ''
        print(f"Buscando con query: '{query}'")

        messages = []
        next_page_token = None
        while True:
            results = service.users().messages().list(
                userId='me',
                q=query,
                maxResults=min(args.limit, 50),
                pageToken=next_page_token
            ).execute()
            batch = results.get('messages', [])
            messages.extend(batch)
            next_page_token = results.get('nextPageToken')
            if not next_page_token or len(messages) >= args.limit:
                break

        messages = messages[:args.limit]

        if not messages:
            print('No se encontraron mensajes.')
            return

        print(f"\nSe encontraron {len(messages)} mensaje(s).\n")

        todos_adjuntos = []

        for i, message in enumerate(messages, 1):
            msg = service.users().messages().get(
                userId='me', id=message['id'], format='full'
            ).execute()

            subject = sender = date_str = "?"
            for header in msg.get('payload', {}).get('headers', []):
                if header['name'] == 'Subject':
                    subject = header['value']
                elif header['name'] == 'From':
                    sender = header['value']
                elif header['name'] == 'Date':
                    date_str = header['value']

            snippet = msg.get('snippet', '')

            # Detectar si tiene adjuntos
            tiene_adjuntos = False
            def _buscar_adjuntos(partes):
                nonlocal tiene_adjuntos
                for p in partes:
                    if p.get('filename'):
                        tiene_adjuntos = True
                    if p.get('parts'):
                        _buscar_adjuntos(p['parts'])
            _buscar_adjuntos(msg.get('payload', {}).get('parts', []))

            print(f"--- CORREO #{i} ---")
            print(f"De: {sender}")
            print(f"Fecha: {date_str}")
            print(f"Asunto: {subject}")
            print(f"Resumen: {snippet[:150]}")
            print(f"Adjuntos: {'Sí' if tiene_adjuntos else 'No'}")
            print("-" * 40)

            if args.download_attachments and tiene_adjuntos:
                os.makedirs(args.save_dir, exist_ok=True)
                adjuntos = _extraer_adjuntos(
                    service, message['id'], msg['payload'], args.save_dir
                )
                todos_adjuntos.extend(adjuntos)

        if args.download_attachments:
            if todos_adjuntos:
                print(f"\n✅ {len(todos_adjuntos)} adjunto(s) descargado(s):")
                for a in todos_adjuntos:
                    print(f"  → {a}")
            else:
                print("\nNo se encontraron adjuntos en los correos seleccionados.")

    except HttpError as error:
        print(f'Error de Gmail API: {error}')


if __name__ == '__main__':
    main()
