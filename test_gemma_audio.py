import requests
import base64
import os

# Configuración de la URL de tu LM Studio
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

def encode_audio_to_base64(audio_path):
    """Convierte un archivo de audio a base64."""
    with open(audio_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode('utf-8')

def test_audio_inference(audio_path, prompt):
    if not os.path.exists(audio_path):
        print(f"❌ Error: El archivo '{audio_path}' no existe. Por favor, coloca un archivo de audio con ese nombre en la carpeta.")
        return

    try:
        # Codificamos el audio
        audio_base64 = encode_audio_to_base64(audio_path)
        
        # Estructura de mensaje (formato multimodal estándar para APIs tipo OpenAI)
        payload = {
            "model": "gemma-4-e4b-it",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_base64,
                                "format": "wav"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.7
        }

        print(f"🚀 Enviando petición a {LM_STUDIO_URL}...")
        response = requests.post(LM_STUDIO_URL, json=payload)
        
        if response.status_code == 200:
            print("✅ Respuesta recibida:")
            print(response.json()['choices'][0]['message']['content'])
        else:
            print(f"❌ Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    # Nombre del archivo de audio que debe existir en la carpeta
    PATH_AL_AUDIO = "test_audio.wav" 
    PROMPT_USUARIO = "¿Puedes decirme qué escuchas en este audio?"
    
    test_audio_inference(PATH_AL_AUDIO, PROMPT_USUARIO)
