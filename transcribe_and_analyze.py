import whisper
import requests
import os

def transcribe_audio(file_path):
    print(f"⏳ Cargando modelo Whisper...")
    model = whisper.load_model("base")
    print(f"⏳ Transcribiendo {file_path}...")
    result = model.transcribe(file_path)
    return result['text']

def ask_lmstudio(prompt):
    url = "http://localhost:1234/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "messages": [
            {"role": "system", "content": "Eres un asistente que analiza transcripciones de audio."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
    }
    response = requests.post(url, headers=headers, json=data)
    return response.json()['choices'][0]['message']['content']

if __name__ == "__main__":
    audio_file = "cut_30s.mp3" # Asegúrate de que este archivo existe
    
    if not os.path.exists(audio_file):
        print(f"❌ Error: No se encuentra el archivo {audio_file}")
    else:
        try:
            text = transcribe_audio(audio_file)
            print(f"\n✅ Transcripción completada:\n'{text}'\n")
            
            prompt_analisis = f"Analiza la siguiente transcripción de audio y dime qué dice principalmente:\n\n{text}"
            print("🚀 Enviando a LM Studio...")
            respuesta = ask_lmstudio(prompt_analisis)
            print(f"\n🤖 Respuesta de LM Studio:\n{respuesta}")
        except Exception as e:
            print(f"❌ Error durante el proceso: {e}")
