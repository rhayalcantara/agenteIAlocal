#!/usr/bin/env python3
"""YOUTUBE DOWNLOAD + TRANSLATE
Descarga videos de YouTube y genera subtítulos en español.

Requiere: yt-dlp, whisper, deep-translator, gtts
"""

import yt_dlp
import os
import sys
import subprocess
import json

def download_video(youtube_url, fmt='best'):
    """Descarga el video de YouTube y devuelve el nombre del archivo."""
    output_options = {
        'format': fmt,
        'outtmpl': 'video_orig.%(ext)s',
        'noplaylist': True,
    }
    with yt_dlp.YoutubeDL(output_options) as ydl:
        info = ydl.extract_info(youtube_url, download=True)
        title = info.get('title', 'video')
        print(f"[+] Video descargado: {title}")
    return 'video_orig.mp4'

def extract_audio(video_path):
    """Extrae el audio del video como MP3."""
    subprocess.run(
        ['ffmpeg', '-y', '-i', video_path, '-vn', '-acodec', 'libmp3lame', 'audio.mp3'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
    )
    print(f"[+] Audio extraído: audio.mp3")
    return 'audio.mp3'

def transcribe_audio():
    """Transcribe el audio con Whisper y devuelve texto."""
    import whisper
    model = whisper.load_model('base')
    result = model.transcribe('audio.mp3', language='en')
    print(f"[+] Transcripción: {len(result['segments'])} segmentos")
    text = result['text'].strip()
    return text

def translate_text(text):
    """Traduce texto del inglés al español."""
    from deep_translator import GoogleTranslator
    translator = GoogleTranslator(source='en', target='es')
    translated = translator.translate(text)
    print(f"[+] Traducción completada ({len(text)} -> {len(translated)} chars)")
    return translated

def process_full(youtube_url):
    """Proceso completo: descarga, transcribe y traduce."""
    print("*" * 60)
    print("🎬 DESCARGA Y TRADUCCIÓN DE VIDEO DE YOUTUBE")
    print("*" * 60)
    
    # Paso 1: Descargar video
    print("\n[1/6] Descargando video...")
    video_path = download_video(youtube_url)
    
    # Paso 2: Extraer audio
    print("[2/6] Extrayendo audio...")
    audio_path = extract_audio(video_path)
    
    # Paso 3: Transcribir
    print("[3/6] Transcribiendo con Whisper...")
    original_text = transcribe_audio()
    
    # Guardar texto original
    with open('original_text.txt', 'w', encoding='utf-8') as f:
        f.write(original_text)
    print(f"[+] Texto original guardado: original_text.txt")
    
    # Paso 4: Traducir
    print("[4/6] Traduciendo al español...")
    translated_text = translate_text(original_text)
    
    # Guardar texto traducido
    with open('translated_text_es.txt', 'w', encoding='utf-8') as f:
        f.write(translated_text)
    print(f"[+] Texto traducido guardado: translated_text_es.txt")
    
    print("\n" + "=" * 60)
    print("✅ PROCESO COMPLETADO!")
    print("=" * 60)
    print(f"📁 Video: {video_path}")
    print(f"📁 Audio: audio.mp3")
    print(f"📁 Texto original: original_text.txt")
    print(f"📁 Traducción ES: translated_text_es.txt")
    print("=" * 60)

if __name__ == '__main__':
    url = 'https://www.youtube.com/watch?v=nIxiVAuXn4o'
    if len(sys.argv) > 1:
        url = sys.argv[1]
    process_full(url)