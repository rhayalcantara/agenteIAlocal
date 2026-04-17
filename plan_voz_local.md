# Plan: Modo Voz en Agente Local (main.py)

## Objetivo
Agregar modo voz al agente local de terminal, usando los mismos módulos
que ya usa Telegram: Whisper (STT) + gTTS (TTS).

## Stack de audio
- **Grabación mic**: sounddevice + soundfile → WAV temporal
- **STT**: agente_core/voice_handler.transcribir() (Whisper)
- **TTS**: agente_core/voice_handler.sintetizar() (gTTS → OGG)
- **Reproducción**: afplay (macOS, ya disponible)

## Archivos a crear/modificar
- `agente_core/mic_recorder.py` (NUEVO) — graba N segundos desde el micrófono
- `main.py` (MODIFICAR) — integrar modo voz + migrar a agent.chat()

## Comportamiento del modo voz
- `/voz` — activa/desactiva modo voz
- En modo voz: presionar ENTER inicia grabación (N segundos configurable),
  luego transcribe → chat → sintetiza → reproduce automáticamente
- En modo texto: comportamiento actual (input() normal)
- El texto transcrito se muestra en pantalla ("Tú [voz]: ...")
- El texto de respuesta también se muestra (además de reproducirse)

## Tareas
1. Instalar sounddevice + soundfile en .venv
2. Crear agente_core/mic_recorder.py
3. Actualizar main.py: migrar a agent.chat() + agregar /voz
4. Verificar requirements.txt
