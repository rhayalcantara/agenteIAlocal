import requests
import json

# --- CONFIGURACIÓN ---
# Asegúrate de que LM Studio esté corriendo y sirviendo el modelo.
# El puerto predeterminado suele ser 1234 o el que hayas configurado.
API_URL = "http://localhost:1234/v1/chat/completions"

# Nombre del modelo cargado en LM Studio (esto es solo informativo para la llamada)
MODEL_NAME = "gemma-4-e4b-it" 

def generar_respuesta_con_gemma(prompt_usuario: str, temperatura: float = 0.7):
    """
    Envía un prompt de texto a un servidor local (LM Studio) que aloja Gemma 4.
    """
    print("🤖 Enviando solicitud al modelo...")
    
    headers = {
        "Content-Type": "application/json",
    }
    
    # Estructura del payload siguiendo el formato de la API de OpenAI (común en LM Studio)
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "Eres un asistente útil y conciso basado en Gemma 4."},
            {"role": "user", "content": prompt_usuario}
        ],
        "temperature": temperatura,
        "max_tokens": 500
    }

    try:
        # Realiza la petición POST al endpoint de chat completions
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Lanza una excepción para códigos de error HTTP (4xx o 5xx)
        
        data = response.json()
        
        # Extraer la respuesta del formato JSON devuelto por el servidor
        respuesta_texto = data['choices'][0]['message']['content'].strip()
        return respuesta_texto

    except requests.exceptions.ConnectionError:
        print("\n" + "="*60)
        print("❌ ERROR DE CONEXIÓN:")
        print("Asegúrate de que LM Studio esté corriendo y sirviendo el modelo.")
        print(f"Verifica que el endpoint '{API_URL}' sea correcto.")
        print("="*60)
        return None
    except requests.exceptions.RequestException as e:
        print(f"\n❌ Ocurrió un error al conectar con la API: {e}")
        return None

# ==============================================================
# --- EJECUCIÓN DEL EJEMPLO ---
# ==============================================================

if __name__ == "__main__":
    # 1. Define tu pregunta (el prompt)
    mi_pregunta = "¿Cuáles son los tres beneficios principales de usar modelos LLM en desarrollo de software?"
    
    # 2. Llama a la función para obtener la respuesta
    respuesta = generar_respuesta_con_gemma(mi_pregunta)

    # 3. Muestra el resultado
    if respuesta:
        print("\n" + "="*60)
        print("✅ RESPUESTA DE GEMMA 4:")
        print(respuesta)
        print("="*60)
