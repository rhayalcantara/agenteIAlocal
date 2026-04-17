"""
doblador_local.py — Dobla un video local al español.

Pasos:
  1. Extrae audio WAV con ffmpeg (rápido)
  2. Transcribe con Whisper (modelo configurable con WHISPER_MODEL, default: tiny)
  3. Traduce al español con deep_translator
  4. Genera voz en español con Edge-TTS
  5. Mezcla audio doblado con el video original usando ffmpeg

Uso:
  python doblador_local.py <ruta_video>

Variables de entorno opcionales:
  WHISPER_MODEL  — tamaño del modelo Whisper (tiny, base, small, medium). Default: tiny
  TTS_VOICE      — voz de Edge-TTS. Default: es-ES-AlvaroNeural
"""
import os
import sys
import asyncio
import subprocess
import tempfile
import whisper
import edge_tts
from deep_translator import GoogleTranslator


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
TTS_VOICE     = os.getenv("TTS_VOICE", "es-ES-AlvaroNeural")


def _extraer_audio_wav(input_video: str, wav_path: str):
    """Extrae el audio del video como WAV 16kHz mono (formato óptimo para Whisper)."""
    print("[1/4] Extrayendo audio con ffmpeg...")
    cmd = [
        "ffmpeg", "-y", "-i", input_video,
        "-vn",                  # sin video
        "-ar", "16000",         # 16 kHz — lo que Whisper espera
        "-ac", "1",             # mono
        "-acodec", "pcm_s16le", # WAV sin compresión
        wav_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg falló:\n{result.stderr.decode()[-500:]}")
    print(f"    Audio extraído: {wav_path}")


def _transcribir(wav_path: str) -> list[dict]:
    """Transcribe el WAV con Whisper. Retorna lista de segmentos."""
    print(f"[2/4] Transcribiendo con Whisper (modelo={WHISPER_MODEL})...")
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(wav_path, fp16=False)
    segments = result.get("segments", [])
    print(f"    {len(segments)} segmentos transcritos.")
    return segments


def _traducir(segments: list[dict]) -> str:
    """Traduce los segmentos al español y retorna el texto completo."""
    print("[3/4] Traduciendo al español...")
    translator = GoogleTranslator(source="auto", target="es")
    partes = []
    for seg in segments:
        texto = seg.get("text", "").strip()
        if not texto:
            continue
        try:
            traducido = translator.translate(texto)
            partes.append(traducido)
        except Exception as e:
            print(f"    ⚠️  Error traduciendo segmento: {e} — usando original")
            partes.append(texto)

    if not partes:
        raise RuntimeError("No se pudo extraer texto para traducir.")

    texto_completo = " ".join(partes)
    print(f"    Traducción lista ({len(texto_completo)} chars).")
    return texto_completo


async def _generar_tts(texto: str, output_audio: str):
    """Genera audio en español con Edge-TTS."""
    print(f"[4/4] Generando voz con Edge-TTS (voz={TTS_VOICE})...")
    communicate = edge_tts.Communicate(texto, TTS_VOICE)
    await communicate.save(output_audio)
    print(f"    Audio TTS guardado: {output_audio}")


def _mezclar(input_video: str, dubbed_audio: str, output_video: str):
    """Reemplaza la pista de audio del video con el audio doblado."""
    print("[5/4] Mezclando video + audio doblado con ffmpeg...")
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-i", dubbed_audio,
        "-c:v", "copy",         # copia el video sin recodificar (rápido)
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-shortest",            # corta al más corto (video o audio)
        output_video,
    ]
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mezcla falló:\n{result.stderr.decode()[-500:]}")
    print(f"    ✅ Video final: {output_video}")


async def _dub_video(input_video: str):
    if not os.path.exists(input_video):
        raise FileNotFoundError(f"Archivo no encontrado: {input_video}")

    base       = os.path.splitext(input_video)[0]
    wav_tmp    = tempfile.mktemp(suffix="_audio.wav", dir="/tmp")
    dubbed_mp3 = base + "_dubbed.mp3"
    output_mp4 = base + "_doblado_es.mp4"

    try:
        _extraer_audio_wav(input_video, wav_tmp)
        segments  = _transcribir(wav_tmp)
        texto_es  = _traducir(segments)
        await _generar_tts(texto_es, dubbed_mp3)
        _mezclar(input_video, dubbed_mp3, output_mp4)
        print(f"\n🎬 ¡Doblaje completado! → {output_mp4}")
    finally:
        # Limpiar WAV temporal
        if os.path.exists(wav_tmp):
            os.remove(wav_tmp)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python doblador_local.py <ruta_video>")
        sys.exit(1)
    asyncio.run(_dub_video(sys.argv[1]))
