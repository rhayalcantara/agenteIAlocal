"""TTS local con piper-tts.

Carga el modelo una vez (singleton) y sintetiza párrafos a OGG/Opus
(o WAV si no hay ffmpeg). Diseñado para streaming: el caller llama
por chunk de texto y obtiene una ruta a un .ogg listo para servir.
"""
from __future__ import annotations

import io
import logging
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

logger = logging.getLogger("claude_server.tts")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
VOICE_MODEL = PROJECT_ROOT / "claude_server" / "piper_voices" / "es_ES-davefx-medium.onnx"
UPLOADS_DIR = PROJECT_ROOT / "claude_server" / "data" / "uploads"

_voice = None
_have_ffmpeg = bool(shutil.which("ffmpeg"))


def _get_voice():
    global _voice
    if _voice is None:
        from piper import PiperVoice  # import lazy — onnxruntime es pesado
        logger.info(f"Cargando voz piper: {VOICE_MODEL.name}")
        _voice = PiperVoice.load(str(VOICE_MODEL))
    return _voice


def is_available() -> bool:
    return VOICE_MODEL.exists()


def synthesize_to_file(text: str, prefix: str = "tts") -> Path | None:
    """Sintetiza texto y guarda en data/uploads/. Retorna la ruta (.ogg o .wav)."""
    text = (text or "").strip()
    if not text:
        return None
    if not is_available():
        logger.warning(f"piper voice no encontrada en {VOICE_MODEL}")
        return None
    voice = _get_voice()

    # 1. WAV en memoria
    wav_buf = io.BytesIO()
    try:
        with wave.open(wav_buf, "wb") as wf:
            voice.synthesize_wav(text, wf)
    except Exception as e:
        logger.error(f"piper synth falló: {e}")
        return None

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    if not _have_ffmpeg:
        # Fallback: dejar WAV directo.
        wav_path = UPLOADS_DIR / f"{prefix}_{_short_id()}.wav"
        wav_path.write_bytes(wav_buf.getvalue())
        return wav_path

    # 2. Convertir a OGG/Opus con ffmpeg (~10x menor, plays en browser).
    ogg_path = UPLOADS_DIR / f"{prefix}_{_short_id()}.ogg"
    try:
        proc = subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "wav", "-i", "pipe:0",
                "-c:a", "libopus", "-b:a", "32k",
                "-f", "ogg", str(ogg_path),
            ],
            input=wav_buf.getvalue(),
            capture_output=True,
            timeout=20,
        )
        if proc.returncode != 0:
            logger.warning(f"ffmpeg fallo {proc.returncode}: {proc.stderr.decode(errors='replace')[:200]}")
            # Devolver WAV como fallback.
            wav_path = UPLOADS_DIR / f"{prefix}_{_short_id()}.wav"
            wav_path.write_bytes(wav_buf.getvalue())
            return wav_path
        return ogg_path
    except Exception as e:
        logger.warning(f"ffmpeg no se pudo invocar: {e} — devolviendo WAV")
        wav_path = UPLOADS_DIR / f"{prefix}_{_short_id()}.wav"
        wav_path.write_bytes(wav_buf.getvalue())
        return wav_path


def _short_id() -> str:
    import secrets, datetime
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + secrets.token_hex(4)


def public_url(path: Path) -> str:
    """Convierte una ruta dentro de data/uploads/ en URL pública."""
    return f"/uploads/{path.name}"
