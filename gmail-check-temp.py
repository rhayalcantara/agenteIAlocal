import sys
import os

# Agregar el path del skill
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "skills", "gmail-reader"))
from main import GmailReader

# Leer los últimos 10 correos no leídos
reader = GmailReader()
mensajes = reader.leer(cantidad=10, cuerpo=True)

# Contar cuántos están realmente marcados como leídos/no leídos
print(f"Cantidad de mensajes retornados: {len(mensajes) if mensajes else 0}")

if mensajes:
    print(f"\n--- LISTA DE MENSAJES ---")
    for i, msg in enumerate(mensajes, 1):
        de = msg.get("de", "Desconocido")
        asunto = msg.get("asunto", "Sin asunto")
        fecha = msg.get("fecha", "Sin fecha")
        estado = "NO LEÍDO" if msg.get("unread", False) else "LEÍDO"
        snippet = msg.get("snippet", "Sin snippet")
        print(f"\n[{i}] {estado}")
        print(f"   De: {de}")
        print(f"   Asunto: {asunto}")
        print(f"   Fecha: {fecha}")
        print(f"   Snippet: {snippet[:100] if snippet else 'N/A'}...")
        
        # Buscar adjuntos
        attachments = msg.get("attachments", [])
        if attachments:
            print(f"   ADJUNTOS: {', '.join(attachments)}")
        
        print("---")
else:
    print("\nNo se encontraron correos en el inbox.")
