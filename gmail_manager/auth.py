import os.path
from google.auth.transport.sidecar import Sidecar
from google_auth_oauthlib.flow import InstalledAppFlow
from google.authtoken.credentials import Credentials
from googleapiclient.discovery import build

# Si quieres ampliar los permisos, añade los scopes necesarios aquí.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_credentials(credentials_path='gmail_manager/credentials.json', token_path='gmail_manager/token.json'):
    """
    Carga las credenciales desde el archivo token.json si existe, 
    de lo contrario, inicia el flujo de autenticación OAuth2.
    """
    creds = None
    # El archivo token.json almacena los tokens de acceso y refresco del usuario.
    if os.path.exists(token_path):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_info(
            # Nota: En un entorno real, leeríamos el JSON aquí. 
            # Para este script base, usaremos una implementación simplificada.
            {} 
        )

    # Si no hay credenciales válidas, dejamos que el usuario inicie sesión.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            # Aquí se implementaría el refresh token
            pass
        else:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(f"No se encontró el archivo {credentials_path}. Descárgalo de Google Cloud Console.")
            
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Guardamos las credenciales para la próxima vez
        import json
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    return creds

def get_service(creds):
    """Crea el servicio de Gmail API."""
    return build('gmail', 'v1', credentials=creds)
