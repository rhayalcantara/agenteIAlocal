import requests
import base64

def test_audio_inference(audio_path, endpoint="http://localhost:1234/v1/chat/completions"):
    try:
        # Leer y codificar el audio en base64
        with open(audio_path, "rb") as audio_file:
            audio_base64 = base64.b64encode(audio_file.read()).decode('utf-8')

        payload = {
            "model": "local-model",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analiza este audio (inicio base64): data:audio/mp3;base64,{audio_base64[:100]}..."} 
                    ]
                }
            ],
            "temperature": 0.7
        }

        print(f"Enviando petición a {endpoint}...")
        response = requests.post(endpoint, json=payload)
        
        if response.status_code == 200:
            print("✅ Respuesta exitosa:")
            print(response.json()['choices'][0]['message']['content'])
        else:
            print(f"❌ Error {response.status_code}:")
            print(response.text)

    except Exception as e:
        print(f"❌ Error durante la ejecución: {e}")

if __name__ == "__main__":
    # Usamos el archivo que acabamos de crear
    test_audio_inference("cut_30s.mp3")
