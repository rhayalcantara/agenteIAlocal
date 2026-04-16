# Skill: descargavideoytraduce

Esta skill automatiza el proceso de descargar un video de YouTube, extraer su audio, transcribirlo al idioma original, traducirlo al español y generar una nueva pista de audio en español mediante TTS para luego montarlo sobre el video original.

## Flujo de trabajo
1. **Descarga**: Utiliza `yt-dlp` para obtener la mejor calidad del video de YouTube.
2. **Extracción de Audio**: Convierte el contenido descargado a un formato compatible (MP3/WAV) usando `ffmpeg`.
3. **Transcripción (Whisper)**: Emplea el modelo Whisper para convertir el audio en texto (idioma original).
4. **Traducción**: Procesa el texto transcrito y lo traduce al español.
5. **Generación de Audio (TTS)**: Utiliza una herramienta de Text-to-Speech para generar la voz en español basada en la traducción.
6. **Montaje Final**: Combina el video original con la nueva pista de audio en español usando `ffmpeg`, asegurando la sincronización básica.

## Requisitos previos
- `yt-dlp` instalado.
- `ffmpeg` instalado.
- Librerías de Python: `openai-whisper`, `googletrans==4.0.0-rc1` (o similar), y una librería de TTS (ej. `gTTS` o `edge-tts`).

## Ejemplo de uso
Para usar esta skill, proporciona la URL del video de YouTube al agente. El agente ejecutará el script con la lógica de procesamiento definida.