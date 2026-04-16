"""
Pipeline de doblaje: MP4 (inglés) → MP4 (español)

Pasos:
  1. Extraer audio del MP4 con ffmpeg
  2. Transcribir con Whisper (o reusar audio_output.txt si existe)
  3. Traducir al español con deep_translator (Google Translate gratuito)
  4. Generar voz en español con gTTS
  5. Montar video + audio español con moviepy

Uso:
  python3 translate_video.py "nombre_del_video.mp4"
"""
import sys
import os
import subprocess

# ── Constantes ────────────────────────────────────────────────────────────────
AUDIO_ORIGINAL = "temp_audio_en.mp3"
AUDIO_ESPANOL  = "temp_audio_es.mp3"
TEXTO_EN       = "transcripcion_en.txt"
TEXTO_ES       = "transcripcion_es.txt"


def instalar_si_falta(paquete):
    try:
        __import__(paquete.replace("-", "_"))
    except ImportError:
        print(f"Instalando {paquete}...")
        subprocess.run([sys.executable, "-m", "pip", "install", paquete, "-q"], check=True)


def paso1_extraer_audio(video_path):
    if os.path.exists(AUDIO_ORIGINAL):
        print(f"\n▶ Paso 1: Reusando audio existente ({AUDIO_ORIGINAL})")
        return
    print("\n▶ Paso 1: Extrayendo audio...")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vn",
         "-acodec", "libmp3lame", "-ar", "44100", "-ac", "2", AUDIO_ORIGINAL],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    print(f"   Audio guardado en {AUDIO_ORIGINAL}")


def paso2_transcribir():
    # Reusar transcripción existente si ya fue generada
    if os.path.exists("audio_output.txt"):
        print("\n▶ Paso 2: Reusando transcripción existente (audio_output.txt)")
        with open("audio_output.txt", "r", encoding="utf-8") as f:
            texto = f.read().strip()
        with open(TEXTO_EN, "w", encoding="utf-8") as f:
            f.write(texto)
        return texto

    print("\n▶ Paso 2: Transcribiendo con Whisper (puede tardar)...")
    import whisper
    model = whisper.load_model("base")
    result = model.transcribe(AUDIO_ORIGINAL, language="en")
    texto = result["text"].strip()
    with open(TEXTO_EN, "w", encoding="utf-8") as f:
        f.write(texto)
    print(f"   Transcripción guardada ({len(texto)} chars)")
    return texto


def paso3_traducir(texto_en):
    if os.path.exists(TEXTO_ES):
        print(f"\n▶ Paso 3: Reusando traducción existente ({TEXTO_ES})")
        with open(TEXTO_ES, "r", encoding="utf-8") as f:
            return f.read()
    print("\n▶ Paso 3: Traduciendo al español...")
    instalar_si_falta("deep-translator")
    from deep_translator import GoogleTranslator
    CHUNK = 4500
    chunks = [texto_en[i:i+CHUNK] for i in range(0, len(texto_en), CHUNK)]
    partes = []
    for i, chunk in enumerate(chunks):
        traducido = GoogleTranslator(source="en", target="es").translate(chunk)
        partes.append(traducido)
        print(f"   Chunk {i+1}/{len(chunks)} traducido")
    texto_es = " ".join(partes)
    with open(TEXTO_ES, "w", encoding="utf-8") as f:
        f.write(texto_es)
    print(f"   Traducción guardada ({len(texto_es)} chars)")
    return texto_es


def paso4_tts(texto_es):
    if os.path.exists(AUDIO_ESPANOL):
        print(f"\n▶ Paso 4: Reusando audio español existente ({AUDIO_ESPANOL})")
        return
    print("\n▶ Paso 4: Generando voz en español (gTTS)...")
    from gtts import gTTS
    tts = gTTS(text=texto_es, lang="es", slow=False)
    tts.save(AUDIO_ESPANOL)
    print(f"   Audio español guardado en {AUDIO_ESPANOL}")


def paso5_montar(video_path):
    print("\n▶ Paso 5: Montando video + audio español (ffmpeg)...")
    output_path = video_path.replace(".mp4", "_ES.mp4")
    # ffmpeg: reemplaza el audio del video original con el español
    # -shortest: corta al más corto entre video y audio
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", AUDIO_ESPANOL,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",       # copia el video sin re-encodear (muy rápido)
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print(f"Error ffmpeg: {result.stderr[-500:]}")
        sys.exit(1)
    print(f"\n✅ Video final guardado: {output_path}")
    return output_path


def limpiar():
    for f in [AUDIO_ORIGINAL, AUDIO_ESPANOL]:
        if os.path.exists(f):
            os.remove(f)


def main():
    if len(sys.argv) < 2:
        # Buscar automáticamente el primer mp4 que no sea _ES
        mp4s = [f for f in os.listdir(".") if f.endswith(".mp4") and "_ES" not in f]
        if not mp4s:
            print("ERROR: No se encontró ningún archivo .mp4")
            sys.exit(1)
        video_path = mp4s[0]
        print(f"Video detectado automáticamente: {video_path}")
    else:
        video_path = sys.argv[1]

    if not os.path.exists(video_path):
        print(f"ERROR: Archivo no encontrado: {video_path}")
        sys.exit(1)

    print(f"\n🎬 Iniciando doblaje de: {video_path}\n")

    paso1_extraer_audio(video_path)
    texto_en = paso2_transcribir()
    texto_es = paso3_traducir(texto_en)
    paso4_tts(texto_es)
    output = paso5_montar(video_path)
    limpiar()

    print(f"\n🎉 ¡Listo! Video doblado al español: {output}")
    return output


if __name__ == "__main__":
    main()
