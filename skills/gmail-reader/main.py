import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json
import datetime

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

CREDENTIALS_FILE = 'gmail_manager/credentials.json'
TOKEN_FILE = 'gmail_manager/token.json'

def get_credentials():
    """Obtiene credenciales OAuth2 para Gmail."""
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    else:
        creds = None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def list_messages(service, label_id='INBOX', max_results=10):
    """Lista mensajes de Gmail con filtro por etiqueta."""
    try:
        message_list = service.users().messages().list(
            userId='me',
            labelIds=[label_id],
            maxResults=max_results
        ).execute()
        return message_list.get('messages', [])
    except HttpError as error:
        print(f'Error al listar mensajes: {error}')
        return []

def get_message(service, msg_id):
    """Obtiene el contenido de un mensaje por ID."""
    try:
        message = service.users().messages().get(userId='me', id=msg_id).execute()
        return message
    except HttpError as error:
        print(f'Error al obtener mensaje: {error}')
        return None

def extract_message_data(message):
    """Extrae datos clave de un mensaje."""
    headers = message['payload']['headers']
    from_header = next(h['value'] for h in headers if h['name'] == 'From')
    subject_header = next(h['value'] for h in headers if h['name'] == 'Subject')
    date_header = next(h['value'] for h in headers if h['name'] == 'Date')
    snippet = message['snippet']
    msg_id = message['id']
    return {
        'id': msg_id,
        'from': from_header,
        'subject': subject_header,
        'date': date_header,
        'snippet': snippet
    }

def main(label='INBOX', max_results=10):
    """Función principal de la skill."""
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)
    messages = list_messages(service, label, max_results)
    if not messages:
        print('No se encontraron correos.')
        return
    result = []
    for msg in messages:
        message = get_message(service, msg['id'])
        if message:
            data = extract_message_data(message)
            result.append(data)
    # Guardar resultados en archivo
    output = 'gmail_reader_output.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f'✅ {len(result)} correos leídos. Guardado en {output}')
    return result

if __name__ == '__main__':
    main()