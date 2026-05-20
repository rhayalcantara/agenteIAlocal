# Skill: descargavideoytraduce

Descarga o procesa un video, lo transcribe con Whisper, traduce al español y genera audio doblado con edge-tts.

## Modos de uso

| Modo | Argumento | Qué hace |
|------|-----------|----------|
| URL YouTube | `https://youtube.com/watch?v=...` | Descarga + transcribe + traduce + dobla |
| Video local | `ruta/al/video.mp4` | Transcribe + traduce + dobla (sin descargar) |
| Solo audio | `--audio ruta/al/audio.mp3` | Transcribe + traduce + genera TTS |
| Solo texto | `--texto ruta/al/texto.txt` | Traduce + genera TTS |

## ⚠️ ESTA SKILL ES LARGA — USAR `execute_long`, NO `execute_bash` ni `ejecutar_script_skill`

Esta skill descarga + transcribe + traduce + dobla. Tarda **varios minutos** (puede llegar a 30-60min para videos largos). Por eso DEBE encolarse en el job_manager con la herramienta `execute_long`. Si la corres con `execute_bash` el agente queda bloqueado.

### Forma correcta de invocar (con execute_long):

```python
# Video de YouTube
execute_long(
    name="doblaje-<id_video>",
    command='python skills/descargavideoytraduce/run.py "https://www.youtube.com/watch?v=ID"'
)

# Video ya descargado en disco
execute_long(
    name="doblaje-local",
    command='python skills/descargavideoytraduce/run.py "C:/ruta/video.mp4"'
)

# Solo audio
execute_long(
    name="doblaje-audio",
    command='python skills/descargavideoytraduce/run.py --audio "C:/ruta/audio.mp3"'
)
```

### NUNCA uses estos formatos (todos fallan):

```
# ❌ NO existe el módulo "skill"
python -m skill descargavideoytraduce ...

# ❌ NO uses execute_bash para esto, bloquea al agente
execute_bash("python skills/descargavideoytraduce/run.py ...")

# ❌ NO actives la skill — esta se invoca SIEMPRE como un comando shell vía execute_long
ejecutar_script_skill("descargavideoytraduce", ...)   # versión vieja, no apta para procesos largos
```

### Después de encolar, consulta el progreso:

```python
job_status(job_id="...", incluir_output=True, lineas=20)
```

El usuario recibe automáticamente notificaciones `[started]` y `[done]`/`[failed]` por el monitor_hub — no necesitas avisarle tú.

## Pipeline

1. **Descargar** (si es URL) → `downloads/`
2. **Extraer audio** (si es video) → `output/audio_original.mp3`
3. **Transcribir** con Whisper medium → `output/transcripcion.txt`
4. **Traducir** al español via gateway LLM → `output/traduccion_es.txt`
5. **Generar TTS** con edge-tts (es-MX-AlbertoNeural) → `output/audio_espanol.mp3`
6. **Unir** video + audio doblado → `output/<nombre>_doblado.mp4`

## Notas
- Cada etapa guarda su resultado en `output/`, permitiendo retomar si falla
- Si el audio ya está en español, salta la traducción
- Requiere: whisper, edge-tts, yt-dlp (solo para URLs), ffmpeg
