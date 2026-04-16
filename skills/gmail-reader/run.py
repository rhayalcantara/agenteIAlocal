import os
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Si modificas estos SCOPES, elimina el archivo token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    parser = argparse.ArgumentParser(description='Leer correos de Gmail')
    parser.add_argument('--label', type=str, help='Filtrar por etiqueta específica')
    args = parser.parse_args()

    creds = None
    # El archivo token.json almacena los tokens de acceso y actualización del usuario.
    # Se crea automáticamente después del primer inicio de sesión.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Si no hay credenciales válidas, deja que el usuario inicie sesión.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: 'credentials.json' no encontrado. Por favor, coloca tus credenciales en la raíz.")
                return
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Guarda las credenciales para la próxima ejecución.
        with open('token.json', 'wh') as token:
            token.write(creds.to_json())

    try:
        service = build('gmailapi', 'v1', credentials=creds)

        # Construir la query de búsqueda
        query = ''
        if args.label:
            query += f' label:{args.label}'

        print(f"Buscando correos con la query: {query}\n")

        # Llamada a la API para listar mensajes
        results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No se encontraron mensajes nuevos.')
            return

        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = msg_data.get('payload', {})
            headers = payload.get('headers', [])
            
            subject = "Sin asunto"
            sender = "Desconocido"
            
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                if header['name'] == 'From':
                    sender = header['value']
            
            print(f"ID: {msg['id']} | Subject: {subject} | From: {sender}")

    except Exception as error:
        print(f'Ocurrió un error: {error}')

if __name__ == '__main__':
    main()
