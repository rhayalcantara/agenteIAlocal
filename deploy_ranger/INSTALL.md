# Instalacion en el servidor Ranger (macOS)

## 1. Copiar archivos al proyecto en el servidor

Copiar estos archivos al directorio del proyecto Ranger:
- `mcp_telegram_ranger.py` — MCP server de Telegram
- `mcp.json` → renombrar a `.mcp.json` en la raiz del proyecto
- `CLAUDE.md` — instrucciones para Claude

## 2. Instalar dependencias

```bash
pip3 install mcp requests
```

## 3. Verificar que funciona

```bash
# Probar el bot
python3 -c "
import requests
resp = requests.get('https://api.telegram.org/bot8728278032:AAF9C-pPkQJ2ZCqXcF2JUO3lFQn0fxFvZSU/getMe')
print(resp.json())
"
```

## 4. Iniciar Claude Code

```bash
cd /ruta/al/proyecto/ranger
claude
```

Claude detectara el `.mcp.json` y cargara el MCP de Telegram automaticamente.

## 5. Probar comunicacion

Desde Telegram, enviar un mensaje al bot @nombre_del_bot.
En Claude del servidor, ejecutar: leer_mensajes()

## Notas
- El token del bot esta hardcodeado en mcp_telegram_ranger.py (tambien se puede usar variable de entorno RANGER_TELEGRAM_TOKEN)
- No necesita puertos abiertos — el bot hace polling saliente
- Claude CLI debe estar instalado y autenticado en el servidor
