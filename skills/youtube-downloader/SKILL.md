# Skill: youtube-downloader

Descarga, transcribe y traduce videos de YouTube al español usando yt-dlp, Whisper y gTTS.

## Herramientas necesarias
- `yt-dlp` — descarga de video
- `ffmpeg` — extracción de audio
- `openai-whisper` — transcripción STT
- `gTTS` — síntesis de voz TTS (español)

## Cómo usar esta skill

### 1. Solo descargar el video
```
execute_bash: yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" <URL>
```

### 2. Descargar + extraer audio
```
execute_bash: yt-dlp -x --audio-format mp3 -o "audio.mp3" <URL>
```

### 3. Transcribir audio existente con Whisper
```
execute_bash: whisper audio_output.mp3 --model base --language English --output_format txt
```

### 4. Pipeline completo (descarga → transcripción → traducción → TTS → montaje)
Ejecutar el script `pipeline.py` con la URL como argumento:
```
ejecutar_script_skill: {skill: "youtube-downloader", script: "pipeline.py", args: "<URL>"}
```

## Notas
- El modelo Whisper `base` es suficiente para velocidad. Usar `small` o `medium` para más precisión.
- La voz gTTS es funcional pero robótica. Para mejor calidad usar ElevenLabs o Qwen3-TTS.
- Los archivos se guardan en el directorio de trabajo actual.
