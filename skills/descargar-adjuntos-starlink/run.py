"""
Skill: descargar-adjuntos-starlink
Descarga los 3 adjuntos (factura, comprobante, acuse_electronico) de correos de Starlink
desde avdmail@avdinternacional.com y los guarda en la carpeta de descargas del usuario.
"""
import os
import sys
import json
import base64
import re
from pathlib import Path

# Credenciales de gmail
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CREDENTIALS_FILE = os.path.join(_ROOT, "gmail_manager", "credentials.json")
TOKEN_FILE = os.path.join(_ROOT, "gmail_manager", "token.json")

# Carpeta de descargas del usuario
def get_download_folder():
    """Obtiene la carpeta de descargas del sistema"""
    download_home = os.path.expanduser("~") + "/Downloads"
    # En Windows, las descargas están en Downloads
    if sys.platform == 'win32':
        download_home = os.environ.get('USERPROFILE', os.path.expanduser('~')) + r"\Downloads"
    return Path(download_home)

def get_service():
    """Obtiene el servicio de Gmail autenticado."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        print("ERROR: Instala google-api-python-client")
        sys.exit(1)

    if not os.path.exists(TOKEN_FILE):
        print(f"ERROR: No existe token de autenticación en {TOKEN_FILE}")
        print("Ejecuta primero: python gmail_manager/main.py")
        sys.exit(1)

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, [
        "https://www.googleapis.com/auth/gmail.readonly",
    ])
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        else:
            print("ERROR: Token expirado. Ejecuta: python gmail_manager/main.py")
            sys.exit(1)

    return build("gmail", "v1", credentials=creds)

def get_attachment_type(filename):
    """Determina el tipo de archivo basado en el nombre."""
    if not filename:
        return "otro"
    
    nombre = filename.lower()
    if 'factura' in nombre:
        return 'factura'
    elif 'comprobante' in nombre:
        return 'comprobante'
    elif 'acuse' in nombre:
        return 'acuse_electronico'
    elif 'pdf' in nombre:
        return 'pdf_desconocido'
    else:
        return 'otro'

def parse_email_date(date_str):
    """Parsea la fecha del correo comparándola con fechas actuales."""
    return date_str

def descargar_adjuntos(correo_id, service):
    """Descarga los 3 adjuntos de un correo de Starlink."""
    msg = service.users().messages().get(
        userId="me", 
        id=correo_id, 
        format="full"
    ).execute()
    
    headers = msg["payload"]["headers"]
    fecha = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Sin fecha')
    
    # Obtener nombre limpio del asunto
    asunto = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Sin asunto')
    # Extraer el número de documento del asunto
    match = re.search(r'E(\d+)', asunto)
    doc_num = match.group(1) if match else 'unknown'
    
    print(f"\nProcesando correo: {asunto}")
    print(f"Fecha: {fecha}")
    
    # Obtener los adjuntos
    adjuntos = []
    
    def procesar_partes(parts):
        """Procesa recursivamente las partes del mensaje."""
        for part in parts:
            if part.get('filename') and part.get('body', {}).get('attachmentId'):
                attach = service.users().messages().attachments().get(
                    userId='me',
                    messageId=correo_id,
                    id=part['body']['attachmentId']
                ).execute()
                
                data = attach.get('data', '')
                data = base64.urlsafe_b64decode(data)
                
                filename = part['filename']
                tipo = get_attachment_type(filename)
                
                adjuntos.append({
                    'filename': filename,
                    'tipo': tipo,
                    'data': data
                })
            elif part.get('parts'):
                procesar_partes(part['parts'])
    
    procesar_partes(msg['payload'].get('parts', []))
    
    if not adjuntos:
        print("  ❌ No se encontraron adjuntos en este correo")
        return []
    
    # Guardar los adjuntos
    download_folder = get_download_folder()
    starlink_folder = download_folder / "starlink" / doc_num
    starlink_folder.mkdir(parents=True, exist_ok=True)
    
    print(f"  Guardando en: {starlink_folder}")
    
    saved_files = []
    for adj in adjuntos:
        filename = adj['filename']
        tipo = adj['tipo']
        
        # Para nombrar los archivos
        if tipo == 'factura':
            nombre_guardar = f'factura.pdf'
        elif tipo == 'comprobante':
            nombre_guardar = f'comprobante.pdf'
        elif tipo == 'acuse_electronico':
            nombre_guardar = f'acuse_electronico.pdf'
        else:
            nombre_guardar = filename
        
        filepath = starlink_folder / nombre_guardar
        filepath.write_bytes(adj['data'])
        saved_files.append(filepath)
        print(f"  ✓ Guardado: {nombre_guardar}")
    
    return saved_files

def main():
    print("📥 Descargando adjuntos de Starlink...")
    
    service = get_service()
    
    # Busca correos recientes de Starlink sin procesar
    # Query: desde avdmail@avdinternacional.com con adjuntos y en la carpeta de entrada
    query = "from:avdmail@avdinternacional.com has:attachment"
    
    print(f"🔍 Buscando correos de Starlink...")
    messages = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=10,
        pageToken=None
    ).execute()
    
    messages_list = messages.get('messages', [])
    
    if not messages_list:
        print("✅ No se encontraron correos de Starlink con adjuntos para descargar")
        return
    
    print(f"📧 Encontrados {len(messages_list)} correos de Starlink con adjuntos:")
    
    total_descargados = 0
    
    for msg in messages_list:
        msg_id = msg['id']
        msg_full = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()
        
        headers = msg_full["payload"]["headers"]
        asunto = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'Sin asunto')
        from_addr = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'unknown')
        fecha = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Sin fecha')
        
        print(f"\n  📬 {asunto[:50]}...")
        print(f"     De: {from_addr}")
        print(f"     Fecha: {fecha}")
        
        # Verificar si ya tiene los 3 archivos guardados
        download_folder = get_download_folder()
        match_doc = re.search(r'E(\d+)', asunto)
        doc_num = match_doc.group(1) if match_doc else 'unknown'
        starlink_folder = download_folder / "starlink" / doc_num
        
        # Contar cuántos archivos ya tienen
        if starlink_folder.exists():
            archivos = list(starlink_folder.glob("*.pdf"))
            if len(archivos) >= 3:
                print(f"     ⏭️  Archivos ya guardados ({len(archivos)} encontrados), saltando")
                continue
        
        # Descargar los adjuntos
        desc_arg = descargar_adjuntos(msg_id, service)
        total_descargados += len(desc_arg)
        
        print(f"     Resultado: {len(desc_arg)} archivos descargados")
    
    print(f"\n🏁 Total descargados: {total_descargados} archivos")
    print("📁 Ubicación base: Downloads/starlink/NUMERO_DOCUMENTO/")

if __name__ == "__main__":
    main()