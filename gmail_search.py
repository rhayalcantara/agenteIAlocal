import os.path
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Si modificas estos SCOPES, elimina el archivo token.json para re-autenticarte.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_credentials():
    """Gestiona la autenticación OAuth2."""
    creds = None
    # El archivo token.json almacena el acceso del usuario.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Si no hay credenciales válidas, iniciar el flujo de autenticación.
    if not creds or not creds.valid:
        if creds and not creds.valid and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                raise FileNotFoundError("No se encontró 'credentials.json'. Por favor, descárgalo desde Google Cloud Console.")
            flow = InstalledAppFlow.from_client_import_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guardar las credenciales para la próxima vez
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def search_gmail(service, query):
    """Busca mensajes en Gmail y devuelve una lista de detalles."""
    messages = []
    next_page_token = None

    print(f"Buscando con query: {query}")

    while True:
        results = service.users().messages().list(
            userId='me', 
            q=query, 
            maxResults=50, 
            pageToken=next_page_token
        ).execute()
        
        batch = results.get('messages', [])
        messages.extend(batch)
        
        next_page_token = results.get('nextPageToken')
        # Limitamos a un máximo de 500 mensajes para evitar saturación
        if not next_page_token or len(messages) >= 500:
            break

    return messages

def print_message_details(service, messages):
    """Obtiene y muestra los detalles de cada mensaje encontrado."""
    if not messages:
        print('No se encontraron mensajes con esa búsqueda.')
        return

    print(f"\nSe han encontrado {len(messages)} mensaje(s).\n")

    for i, message in enumerate(messages, 1):
        message_id = message['id']
        msg = service.users().messages().get(userId='me', id=message_id).execute()
        snippet = msg.get('snippet', '')
        
        subject = "Sin asunto"
        sender = "Desconocido"
        
        headers = msg.get('payload', {}).get('headers', [])
        for header in headers:
            if header['name'] == 'Subject':
                subject = header['value']
            elif header['name'] == 'From':
                sender = header['value']
        
        print(f"--- CORREO #{i} ---")
        print(f"De: {sender}")
        print(f"Asunto: {subject}")
        print(f"Resumen: {snippet}")
        print("-" * 30 + "\n")

def main():
    parser = argparse.ArgumentParser(description='Buscar mensajes de Gmail.')
    parser.add_argument('--query', type=str, help='Query de búsqueda (ej: "from:promerica").')
    args = parser.parse_args()

    try:
        creds = get_credentials()
        service = build('gmail', 'v1', credentials=creds)

        # Si no hay query, busca mensajes no leídos por defecto
        query = args.query if args.query else "is:unread"
        
        messages = search_gmail(service, query)
        print_message_details(service, messages)

    except HttpError as error:
        print(f'Ocurrió un error de la API de Gmail: {error}')
    except Exception as e:
        print(f'Ocurrió un error inesperado: {e}')

if __name__ == '__main__':
    main()
