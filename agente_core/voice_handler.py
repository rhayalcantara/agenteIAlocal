"""
Voice Handler — STT (Whisper) + TTS (gTTS → OGG/Opus)

STT: transcribir(audio_path) → str
TTS: sintetizar(texto, lang) → ruta_ogg o None

El modelo Whisper se carga una vez y se cachea para no relentizar
cada mensaje de voz.
"""
import os
import re
import subprocess
import tempfile
from logger import get_logger

logger = get_logger("voice_handler")

# Cache del modelo Whisper (se carga al primer uso)
_whisper_model = None
_WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        logger.info(f"Cargando modelo Whisper '{_WHISPER_MODEL_SIZE}'...")
        _whisper_model = whisper.load_model(_WHISPER_MODEL_SIZE)
        logger.info("Modelo Whisper listo.")
    return _whisper_model


def transcribir(audio_path: str, language: str = None) -> str:
    """Transcribe un archivo de audio a texto usando Whisper.

    Args:
        audio_path: ruta al archivo de audio (.ogg, .mp3, .wav, .m4a, etc.)
        language: código de idioma opcional (None = auto-detect)

    Returns:
        Texto transcrito, o cadena vacía si falla.
    """
    if not os.path.exists(audio_path):
        logger.warning(f"Archivo de audio no encontrado: {audio_path}")
        return ""
    try:
        model = _get_whisper()
        opts = {}
        if language:
            opts["language"] = language
        result = model.transcribe(audio_path, **opts)
        texto = result["text"].strip()
        logger.info(f"Transcripción ({len(texto)} chars): {texto[:100]}")
        return texto
    except Exception as e:
        logger.error(f"Error transcribiendo {audio_path}: {e}")
        return ""


def _limpiar_texto_tts(texto: str) -> str:
    """Elimina caracteres especiales, Markdown y símbolos que el TTS leería en voz alta."""
    # 1. Bloques de código — eliminar completamente
    texto = re.sub(r"```[\s\S]*?```", "", texto)
    texto = re.sub(r"`[^`]*`", "", texto)

    # 2. URLs completas — eliminar (se leerían letra por letra)
    texto = re.sub(r"https?://\S+", "", texto)

    # 3. Imágenes Markdown y links — conservar solo el texto visible
    texto = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", texto)
    texto = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r"\1", texto)

    # 4. Encabezados al inicio de línea (# ## ### …)
    texto = re.sub(r"^#{1,6}\s*", "", texto, flags=re.MULTILINE)

    # 5. Tachado
    texto = re.sub(r"~~([^~]*)~~", r"\1", texto)
    texto = re.sub(r"~~", "", texto)

    # 6. Negrita/cursiva — extraer el contenido, luego barrer restos
    texto = re.sub(r"\*{1,3}([^\*\n]*)\*{1,3}", r"\1", texto)
    texto = re.sub(r"_{2}([^_\n]*)_{2}", r"\1", texto)
    texto = re.sub(r"_([^_\n]*)_", r"\1", texto)
    # Asteriscos y underscores sueltos que hayan quedado
    texto = re.sub(r"[\*_]+", "", texto)

    # 7. Citas
    texto = re.sub(r"^>\s*", "", texto, flags=re.MULTILINE)

    # 8. Listas (guion, punto, bala unicode •)
    texto = re.sub(r"^\s*[-+•·]\s+", "", texto, flags=re.MULTILINE)
    texto = re.sub(r"^\s*\d+[.)]\s+", "", texto, flags=re.MULTILINE)

    # 9. Líneas horizontales
    texto = re.sub(r"^[\s]*[-_*]{3,}[\s]*$", "", texto, flags=re.MULTILINE)

    # 10. Pipes de tablas
    texto = re.sub(r"\|", " ", texto)

    # 11. Hashtags (#palabra) en cualquier posición del texto
    texto = re.sub(r"#\w+", "", texto)

    # 12. Caracteres sueltos que no aportan al habla
    texto = re.sub(r"[#\\<>\[\]{}~^@=+]", "", texto)

    # 13. Emojis y símbolos Unicode (bloques U+1F000–U+1FFFF y similares)
    texto = re.sub(
        r"[\U0001F000-\U0001FFFF"   # Emoticons, símbolos varios
        r"\U00002600-\U000027BF"     # Símbolos misceláneos, flechas, etc.
        r"\U0000FE00-\U0000FE0F"     # Selectores de variación
        r"\U00002300-\U000023FF"     # Símbolos técnicos
        r"\U00002B00-\U00002BFF]+",  # Flechas suplementarias
        " ", texto
    )

    # 14. Espacios y saltos redundantes
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    texto = re.sub(r" {2,}", " ", texto)
    return texto.strip()


def sintetizar(texto: str, lang: str = "es", speed: float = 1.0) -> str | None:
    """Convierte texto a voz y retorna la ruta al archivo de audio.

    Genera MP3 con gTTS y lo convierte a OGG/Opus con ffmpeg
    (formato requerido por sendVoice de Telegram).
    Si la conversión falla, retorna el MP3 directamente.

    Args:
        texto: texto a sintetizar
        lang: código de idioma ('es', 'en', etc.)
        speed: velocidad (1.0 = normal; gTTS solo soporta normal/slow)

    Returns:
        Ruta al archivo .ogg (o .mp3 como fallback), o None si falla.
    """
    if not texto or not texto.strip():
        return None
    try:
        from gtts import gTTS
    except ImportError:
        logger.error("gTTS no instalado. Ejecuta: pip install gTTS")
        return None

    try:
        # Limpiar caracteres especiales antes de sintetizar
        texto = _limpiar_texto_tts(texto)
        if not texto:
            return None

        # Generar MP3 con gTTS (máx 4096 chars por chunk)
        mp3_path = tempfile.mktemp(suffix="_tts.mp3", dir="/tmp")
        slow = speed < 0.8
        chunks = [texto[i:i+4096] for i in range(0, len(texto), 4096)]
        tts = gTTS(text=chunks[0], lang=lang, slow=slow)
        tts.save(mp3_path)
        # Si hay más chunks, concatenar al mismo MP3
        if len(chunks) > 1:
            for chunk in chunks[1:]:
                chunk_path = tempfile.mktemp(suffix="_tts_chunk.mp3", dir="/tmp")
                gTTS(text=chunk, lang=lang, slow=slow).save(chunk_path)
                subprocess.run(
                    ["ffmpeg", "-y",
                     "-i", f"concat:{mp3_path}|{chunk_path}",
                     "-acodec", "copy", mp3_path + "_merged.mp3"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                os.replace(mp3_path + "_merged.mp3", mp3_path)
                os.remove(chunk_path)

        # Convertir a OGG/Opus para sendVoice (mejor calidad en Telegram)
        ogg_path = mp3_path.replace("_tts.mp3", "_tts.ogg")
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path,
             "-c:a", "libopus", "-b:a", "64k", ogg_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        os.remove(mp3_path)

        if result.returncode == 0 and os.path.exists(ogg_path):
            logger.info(f"TTS generado: {ogg_path}")
            return ogg_path

        # Fallback: guardar como MP3 si ffmpeg/opus falla
        logger.warning(f"Conversión OGG falló, usando MP3: {result.stderr.decode()[-200:]}")
        mp3_fallback = mp3_path.replace("_tts.mp3", "_tts_fb.mp3")
        tts2 = gTTS(text=texto[:4096], lang=lang, slow=slow)
        tts2.save(mp3_fallback)
        return mp3_fallback

    except Exception as e:
        logger.error(f"Error TTS: {e}")
        return None


def limpiar_audio_temp(ruta: str):
    """Elimina un archivo de audio temporal si existe."""
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except Exception:
            pass
