"""
mic_recorder.py — Grabación de audio desde el micrófono con detección de silencio.

Uso:
    from mic_recorder import grabar
    ruta_wav = grabar()   # graba hasta detectar silencio y retorna ruta al WAV temporal
"""
import os
import tempfile
from logger import get_logger

logger = get_logger("mic_recorder")

SAMPLE_RATE     = 16000   # Hz — Whisper funciona bien con 16 kHz
CHANNELS        = 1       # mono
CHUNK_SECONDS   = 0.1     # duración de cada chunk en segundos
SILENCE_THRESHOLD = float(os.getenv("VOZ_SILENCIO_UMBRAL", "0.01"))   # RMS mínimo para considerar voz
SILENCE_DURATION  = float(os.getenv("VOZ_SILENCIO_DURACION", "1.5"))  # segundos de silencio para parar
MAX_DURATION      = float(os.getenv("VOZ_DURACION_MAX", "30"))         # límite máximo en segundos


def grabar(segundos: int = None) -> str | None:
    """Graba audio del micrófono y para automáticamente al detectar silencio.

    - Avisa cuando el micrófono está listo.
    - Para cuando hay SILENCE_DURATION segundos continuos de silencio.
    - Usa MAX_DURATION como tiempo máximo de seguridad.

    Retorna la ruta al archivo WAV temporal, o None si falla.
    """
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np
    except ImportError as e:
        logger.error(f"Dependencia de audio faltante: {e}. Ejecuta: pip install sounddevice soundfile")
        return None

    max_dur = float(segundos) if segundos else MAX_DURATION
    chunk_size = int(CHUNK_SECONDS * SAMPLE_RATE)
    silence_chunks_needed = int(SILENCE_DURATION / CHUNK_SECONDS)

    print("\n🎙️  Micrófono listo — habla cuando quieras...", flush=True)

    grabados = []
    silencio_chunks = 0
    hablando = False
    total_chunks = int(max_dur / CHUNK_SECONDS)

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="float32") as stream:
            for _ in range(total_chunks):
                chunk, _ = stream.read(chunk_size)
                grabados.append(chunk.copy())

                rms = float(np.sqrt(np.mean(chunk ** 2)))

                if rms >= SILENCE_THRESHOLD:
                    if not hablando:
                        print("🔴 Grabando...", flush=True)
                        hablando = True
                    silencio_chunks = 0
                else:
                    if hablando:
                        silencio_chunks += 1
                        restante = round((silence_chunks_needed - silencio_chunks) * CHUNK_SECONDS, 1)
                        print(f"\r⏸️  Silencio detectado — parando en {restante}s...   ", end="", flush=True)
                        if silencio_chunks >= silence_chunks_needed:
                            print("\r✅ Grabación finalizada.                            ", flush=True)
                            break

    except Exception as e:
        logger.error(f"Error grabando audio: {e}")
        return None

    if not grabados or not hablando:
        print("⚠️  No se detectó voz.", flush=True)
        return None

    try:
        import numpy as np
        import soundfile as sf
        audio = np.concatenate(grabados, axis=0)
        wav_path = tempfile.mktemp(suffix="_mic.wav", dir="/tmp")
        sf.write(wav_path, audio, SAMPLE_RATE)
        duracion = round(len(audio) / SAMPLE_RATE, 1)
        logger.info(f"Audio grabado: {wav_path} ({duracion}s)")
        return wav_path
    except Exception as e:
        logger.error(f"Error guardando WAV: {e}")
        return None


def limpiar(ruta: str):
    """Elimina un archivo WAV temporal si existe."""
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except Exception:
            pass
