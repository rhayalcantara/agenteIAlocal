"""
Ejemplo de llamada a un modelo de OpenRouter con carga de API_KEY desde .env
Modelo: openai/gpt-3.5-turbo (público y accesible)
"""

import os
import requests
import json
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Variables configurables
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-3.5-turbo")
MAX_TOKENS = 10000
TEMPERATURE = 0.7

# Cargar la API Key desde el archivo .env
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not OPENROUTER_API_KEY:
    raise ValueError("API_KEY no encontrada en el archivo .env. Asegúrate de tener un archivo .env con OPENROUTER_API_KEY= tu_clave_aqui")

def call_openrouter_model(messages, model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=TEMPERATURE):
    """
    Realiza una llamada al modelo OpenRouter y devuelve la respuesta del modelo.

    Args:
        messages (list): Lista de diccionarios con los mensajes (rol y contenido).
        model (str): Nombre del modelo a usar.
        max_tokens (int): Máximo de tokens en la respuesta.
        temperature (float): Temperatura para controlar la creatividad.

    Returns:
        str: El contenido de la respuesta del modelo.
    """
    # Encabezados de la solicitud
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Payload de la solicitud
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        # Realizar la solicitud POST
        response = requests.post(OPENROUTER_API_URL, headers=headers, data=json.dumps(payload))
        
        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        else:
            print(f"Error en la solicitud: {response.status_code}")
            print(response.text)
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión: {e}")
        return None

# Ejemplo de uso
if __name__ == "__main__":
    # Mensajes como array
    messages = [
        {
            "role": "system",
            "content": "Eres un asistente útil y amable."
        },
        {
            "role": "user",
            "content": "Hola, ¿puedes explicarme qué es Python?"
        }
    ]

    # Llamar al modelo y obtener la respuesta
    response = call_openrouter_model(messages, model=MODEL_NAME, max_tokens=MAX_TOKENS, temperature=TEMPERATURE)
    
    if response:
        print("Respuesta del modelo:")
        print(response)
