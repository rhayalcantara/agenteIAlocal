"""
Skill: descargavideoytraduce
Descarga (o usa) un video, extrae audio, transcribe con Whisper,
traduce al español y genera audio doblado con edge-tts.

Uso:
  python run.py <youtube_url>           # descarga + pipeline completo
  python run.py <ruta_local.mp4>        # video ya descargado
  python run.py --audio <ruta.mp3>      # solo audio, saltar descarga+extracción
  python run.py --texto <ruta.txt>      # solo texto, saltar transcripción
"""
import subprocess
import tempfile
import os
import sys
import json
import glob
import asyncio

# ── Rutas de trabajo ─────────────────────────────────────────────────────────
_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.join(_DIR, "..", "..")
_DOWNLOADS = os.path.join(_ROOT, "downloads")
_OUTPUT = os.path.join(_ROOT, "output")

# ffmpeg en PATH o ruta conocida de winget
_FFMPEG_DIRS = [
    os.path.join(os.path.expanduser("~"),
                 "AppData", "Local", "Microsoft", "WinGet", "Packages",
                 "Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe",
                 "ffmpeg-8.1-full_build", "bin"),
]


def _find_ffmpeg():
    """Busca ffmpeg en PATH o rutas conocidas."""
    import shutil
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    for d in _FFMPEG_DIRS:
        candidate = os.path.join(d, "ffmpeg.exe")
        if os.path.exists(candidate):
            return candidate
    return "ffmpeg"  # fallback


FFMPEG = _find_ffmpeg()


# ── Paso 1: Descargar video ─────────────────────────────────────────────────

def descargar_video(url, output_dir=None):
    """Descarga el video con yt-dlp."""
    import yt_dlp
    out = output_dir or _DOWNLOADS
    os.makedirs(out, exist_ok=True)

    ydl_opts = {
        'outtmpl': os.path.join(out, '%(id)s.%(ext)s'),
        'format': 'mp4/best',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_path = ydl.prepare_filename(info)
        return video_path, info.get('title', 'video')


# ── Paso 2: Extraer audio ───────────────────────────────────────────────────

def extraer_audio(video_path, audio_path=None):
    """Extrae audio del video con ffmpeg."""
    if audio_path is None:
        audio_path = os.path.join(_OUTPUT, "audio_original.mp3")
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)

    cmd = [
        FFMPEG, '-y',
        '-i', video_path,
        '-vn',
        '-acodec', 'libmp3lame',
        '-q:a', '2',
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr[:500]}")
    return audio_path


# ── Paso 3: Transcribir ─────────────────────────────────────────────────────

def transcribir(audio_path):
    """Transcribe audio con Whisper."""
    import whisper
    print("Transcribiendo con Whisper...")
    model = whisper.load_model("medium")
    result = model.transcribe(audio_path, language=None)
    idioma = result.get("language", "en")
    texto = result['text']
    print(f"  Idioma detectado: {idioma}")
    print(f"  Longitud: {len(texto)} chars")
    return texto, idioma


# ── Paso 4: Traducir ────────────────────────────────────────────────────────

def traducir(texto, idioma_origen="en"):
    """Traduce al español usando el gateway LLM."""
    print("Traduciendo al español...")

    # Intentar con el gateway (más confiable que googletrans)
    try:
        from openai import OpenAI
        sys.path.insert(0, _ROOT)
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_ROOT, ".env"))

        client = OpenAI(
            base_url=os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            api_key=os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
        )
        model = os.getenv("LMSTUDIO_MODEL", "qwen3.6:latest")

        # Dividir en chunks si es muy largo
        chunks = _split_text(texto, max_length=2000)
        traducido = []

        for i, chunk in enumerate(chunks):
            print(f"  Traduciendo chunk {i+1}/{len(chunks)}...")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Traduce el siguiente texto al español. "
                     "Devuelve SOLO la traducción, sin explicaciones ni notas."},
                    {"role": "user", "content": chunk},
                ],
                max_tokens=4096,
                temperature=0.3,
            )
            traducido.append(resp.choices[0].message.content.strip())

        return " ".join(traducido)

    except Exception as e:
        print(f"  Error con gateway LLM: {e}")
        # Fallback: googletrans
        try:
            from googletrans import Translator
            translator = Translator()
            result = translator.translate(texto, src=idioma_origen, dest='es')
            return result.text
        except Exception as e2:
            raise RuntimeError(f"No se pudo traducir. Gateway: {e} | Googletrans: {e2}")


# ── Paso 5: Generar audio TTS ───────────────────────────────────────────────

async def generar_audio_espanol(texto, audio_output):
    """Genera audio en español. Intenta edge-tts; si falla (p.ej. el bug
    NoAudioReceived por el token Sec-MS-GEC de Microsoft) cae a gTTS."""
    chunks = _split_text(texto, max_length=300)

    try:
        import edge_tts
        partes = []
        for i, chunk in enumerate(chunks):
            output_chunk = f"{audio_output.replace('.mp3', '')}_part{i}.mp3"
            comm = edge_tts.Communicate(chunk, 'es-MX-AlbertoNeural', rate='-10%')
            await comm.save(output_chunk)
            partes.append(output_chunk)
            print(f"  TTS parte {i+1}/{len(chunks)} generada (edge-tts)")
    except Exception as e:
        print(f"  edge-tts falló ({e}); usando gTTS como fallback...")
        partes = _gtts_chunks(chunks, audio_output)

    # Concatenar partes si hay más de una
    if len(partes) == 1:
        os.rename(partes[0], audio_output)
    else:
        _concatenar_audios(partes, audio_output)
        for p in partes:
            os.remove(p)

    return audio_output


def _gtts_chunks(chunks, audio_output):
    """Genera cada chunk con gTTS (Google). No requiere token de Microsoft."""
    from gtts import gTTS
    partes = []
    for i, chunk in enumerate(chunks):
        output_chunk = f"{audio_output.replace('.mp3', '')}_part{i}.mp3"
        gTTS(chunk, lang='es').save(output_chunk)
        partes.append(output_chunk)
        print(f"  TTS parte {i+1}/{len(chunks)} generada (gTTS)")
    return partes


def _concatenar_audios(partes, output):
    """Concatena múltiples archivos de audio con ffmpeg."""
    list_file = output + ".list.txt"
    with open(list_file, "w") as f:
        for p in partes:
            f.write(f"file '{os.path.abspath(p)}'\n")

    cmd = [FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', list_file,
           '-c', 'copy', output]
    subprocess.run(cmd, capture_output=True, check=True)
    os.remove(list_file)


# ── Paso 6: Unir video + audio ──────────────────────────────────────────────

def unir_video_audio(video_path, audio_espanol, output_path=None):
    """Une video original con audio traducido."""
    if output_path is None:
        base = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(_OUTPUT, f"{base}_doblado.mp4")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        FFMPEG, '-y',
        '-i', video_path,
        '-i', audio_espanol,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-shortest',
        output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg error: {result.stderr[:500]}")
    return output_path


# ── Utilidades ───────────────────────────────────────────────────────────────

def _split_text(texto, max_length=300):
    """Divide texto en chunks por oraciones."""
    if len(texto) <= max_length:
        return [texto]

    sentences = texto.replace('. ', '.|').split('|')
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_length:
            if current:
                chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}" if current else sentence

    if current:
        chunks.append(current.strip())

    return chunks


# ── Main: pipeline flexible ──────────────────────────────────────────────────

def main():
    os.makedirs(_OUTPUT, exist_ok=True)

    if len(sys.argv) < 2:
        print("Uso:")
        print("  python run.py <youtube_url>        # descarga + pipeline")
        print("  python run.py <ruta_video.mp4>     # video local")
        print("  python run.py --audio <ruta.mp3>   # desde audio")
        print("  python run.py --texto <ruta.txt>   # desde texto")
        sys.exit(1)

    arg1 = sys.argv[1]
    video_path = None
    audio_path = None
    texto = None
    idioma = "en"
    title = "video"

    # ── Detectar modo ────────────────────────────────────────────────────
    if arg1 == "--audio":
        # Modo: solo audio → transcribir + traducir + TTS
        audio_path = sys.argv[2] if len(sys.argv) > 2 else None
        if not audio_path or not os.path.exists(audio_path):
            print(f"Error: archivo de audio no encontrado: {audio_path}")
            sys.exit(1)
        print(f"Modo: desde audio ({audio_path})")

    elif arg1 == "--texto":
        # Modo: solo texto → traducir + TTS
        texto_path = sys.argv[2] if len(sys.argv) > 2 else None
        if not texto_path or not os.path.exists(texto_path):
            print(f"Error: archivo de texto no encontrado: {texto_path}")
            sys.exit(1)
        with open(texto_path, "r", encoding="utf-8") as f:
            texto = f.read()
        print(f"Modo: desde texto ({len(texto)} chars)")

    elif os.path.exists(arg1):
        # Modo: video local
        video_path = os.path.abspath(arg1)
        title = os.path.splitext(os.path.basename(video_path))[0]
        print(f"Modo: video local ({video_path})")

    elif arg1.startswith("http"):
        # Modo: URL de YouTube
        print(f"Descargando: {arg1}")
        video_path, title = descargar_video(arg1)
        print(f"Video descargado: {video_path}")

    else:
        print(f"Error: '{arg1}' no es una URL válida ni un archivo existente")
        sys.exit(1)

    try:
        # ── Extraer audio si tenemos video ───────────────────────────────
        if video_path and not audio_path:
            audio_path = os.path.join(_OUTPUT, "audio_original.mp3")
            print("Extrayendo audio...")
            extraer_audio(video_path, audio_path)
            print(f"Audio extraído: {audio_path}")

        # ── Transcribir si tenemos audio ─────────────────────────────────
        if audio_path and not texto:
            texto, idioma = transcribir(audio_path)
            # Guardar transcripción
            trans_path = os.path.join(_OUTPUT, "transcripcion.txt")
            with open(trans_path, "w", encoding="utf-8") as f:
                f.write(texto)
            print(f"Transcripción guardada: {trans_path}")
            print(f"  Preview: {texto[:150]}...")

        # ── Traducir ─────────────────────────────────────────────────────
        if idioma != "es":
            texto_es = traducir(texto, idioma)
        else:
            texto_es = texto
            print("Audio ya está en español, saltando traducción")

        # Guardar traducción
        trad_path = os.path.join(_OUTPUT, "traduccion_es.txt")
        with open(trad_path, "w", encoding="utf-8") as f:
            f.write(texto_es)
        print(f"Traducción guardada: {trad_path}")

        # ── Generar audio TTS ────────────────────────────────────────────
        audio_es = os.path.join(_OUTPUT, "audio_espanol.mp3")
        print("Generando audio en español...")
        asyncio.run(generar_audio_espanol(texto_es, audio_es))
        print(f"Audio en español: {audio_es}")

        # ── Unir video + audio si tenemos video ─────────────────────────
        if video_path:
            output = unir_video_audio(video_path, audio_es)
            print(f"Video doblado: {output}")
        else:
            print(f"Solo audio generado (sin video para unir): {audio_es}")

        print("\n✅ Pipeline completado")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
