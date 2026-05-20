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
# Probar el bot (el token se toma de la variable de entorno, NO se escribe literal)
python3 -c "
import os, requests
resp = requests.get(f\"https://api.telegram.org/bot{os.environ['RANGER_TELEGRAM_TOKEN']}/getMe\")
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
- El token del bot se toma SIEMPRE de la variable de entorno RANGER_TELEGRAM_TOKEN (definir en .env, nunca hardcodear)
- No necesita puertos abiertos — el bot hace polling saliente
- Claude CLI debe estar instalado y autenticado en el servidor
