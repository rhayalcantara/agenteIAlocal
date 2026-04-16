# Skill: Telegram Agent Monitor

Monitorea la salud del agente de Telegram: detecta instancias duplicadas, analiza errores en los logs y aplica correcciones automáticas.

## Cuándo usar esta skill
- El usuario dice que el agente "se frizó", "no responde" o "está lento"
- Hay sospechas de instancias duplicadas
- Se quiere verificar si el agente procesó correctamente un mensaje (texto, voz, foto, archivo)
- Errores de envío en Telegram (entidades, parse_mode, conflictos)

## Diagnóstico rápido

### 1. Verificar instancias activas
```bash
pgrep -f telegram_agente.py
```
Si hay más de un PID → hay conflicto. Mata todos y reinicia uno solo.

### 2. Ver los últimos logs
```bash
tail -n 30 agente_core/logs/agente.log
```

### 3. Errores comunes y solución

| Error en log | Causa | Solución |
|---|---|---|
| `Conflict: terminated by other getUpdates` | Múltiples instancias corriendo | `kill $(pgrep -f telegram_agente.py)` y reiniciar |
| `can't parse entities` | Markdown mal formado en respuesta | El fallback sin parse_mode ya está implementado — verificar si llegó el mensaje igual |
| `No module named 'whisper'` | Whisper no instalado | `pip install openai-whisper` |
| `gTTS no instalado` | gTTS no instalado | `pip install gTTS` |
| `Error transcribiendo` | Falla de Whisper en el audio | Revisar que el archivo .ogg exista y no esté corrupto |
| `502 / 500 Internal Server Error` | LM Studio / Ollama caído o modelo no cargado | Verificar que el servidor local esté corriendo |
| `FP16 is not supported on CPU` | Whisper usando CPU | Warning menor — funciona igual en FP32, se puede ignorar |

### 4. Reinicio limpio
```bash
kill $(pgrep -f telegram_agente.py)
source .venv/bin/activate
python telegram_agente.py &
```

## Verificar que procesó un mensaje

Después de que el usuario envíe un mensaje, busca en el log:

- **Texto**: `Texto de <user> (<chat_id>): ...`
- **Voz**: `Voz de <user>` → luego `Transcripción: ...`
- **Foto**: `Foto recibida de <user>` → `Procesando imagen vision: ...`
- **Documento**: `Documento recibido de <user>: <nombre_archivo>`

Si no aparece nada → el mensaje no llegó al agente (problema de polling o instancia inactiva).

## Ejecutar diagnóstico automatizado

Puedes ejecutar el script de esta skill con:
```
ejecutar_script_skill("telegram-agent-monitor", "run.py")
```

Reporta: instancias activas, últimos errores del log, estado del proceso.

## Portabilidad a otros proyectos

Esta skill funciona en cualquier proyecto que use la misma arquitectura:
- `telegram_agente.py` como punto de entrada
- `agente_core/logs/agente.log` como log principal
- Entorno virtual `.venv`

Para adaptarla a otro proyecto (ej: nómina de Ranger), solo ajusta el nombre del script en el diagnóstico si es diferente a `telegram_agente.py`.
