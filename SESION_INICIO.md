# Guia de Inicio de Sesion — Agente IA Local

Este archivo indica a Claude Code como configurar el entorno al iniciar una nueva sesion.

## 0. Estado al cerrar la sesion del 2026-05-13

### Deploys hechos a GitHub (pendiente `git pull` + restart en servidor del cliente)

| Repo | Rama | Commit | Cambio |
|---|---|---|---|
| `backend-ranger-nomina` | `main` | `dbafccf` | exponer `descripcion` (texto libre) en POST/PUT/GET de `/api/desc_cred_nomina` |
| `rangernomina-frontend` | `master` | `550d773` | input "Detalle (opcional)" + columna "Detalle" en `/desc-cred-nomina` |
| `backend-ranger-nomina` | `main` | `83c7df9` | validar que `id_desc_cred` no sea fijo (rechaza AFP/SFS manual) |
| `rangernomina-frontend` | `master` | `6cd170f` | filtrar items fijos en dropdown `/desc-cred-nomina` + fix flag `excluirFijos` en employee-form (lo reportado por Nicaury) |

### Conversación con Nicaury (grupo SISTEMA RAY, `120363424666838458@g.us`)

- Nicaury reportó el 2026-05-13: "no tiene opción de poner el concepto de descuento en ese módulo"
- Primera interpretación (errónea): le mandé un mensaje sobre el fix técnico de filtrar fijos
- Ella aclaró: "no era ese concepto, es la opción de yo escribir el concepto, no que sea automático" → pidió **campo libre**
- Implementé Opción B (campo libre `descripcion` de la tabla `no_desc_cred_nomina` que ya existía abandonada)
- Le confirmé en el grupo que el cambio estará disponible cuando Rhay actualice el servidor
- **Pendiente de su lado**: probar en producción
- **Pendiente discutir aparte**: su segunda petición "poner descuentos manuales ANTES de generar la nómina, no después" — es cambio mayor del workflow

### Servicios locales que pueden seguir corriendo (o no)

| Proceso | Puerto | Notas |
|---|---|---|
| `whatsapp_monitor.js` | n/a | Persiste en background; el hook SessionStart lo re-arranca si murió |
| backend Ranger (`npm start`) | 3333 | Probablemente apagado al cerrar terminal |
| frontend Angular (`npm start`) | 4200 | Probablemente apagado al cerrar terminal |

## 0.1. Hook automático SessionStart

Al abrir Claude Code en este proyecto, el hook configurado en `.claude/settings.local.json` ejecuta `.claude/scripts/session-start.sh` que:

1. Verifica si `whatsapp_monitor.js` corre (`Get-CimInstance` por nombre `node.exe` + filtro `whatsapp_monitor`)
2. Si no, limpia lockfile huérfano y lo arranca con `nohup node whatsapp_monitor.js > whatsapp_monitor.log 2>&1 &`
3. Emite JSON con `hookSpecificOutput.additionalContext` con los siguientes pasos para Claude:
   - **Armar Monitor** persistente con `tail -F whatsapp_monitor.log` filtrado por `^MSG|` → recibe DMs y grupos de WhatsApp en tiempo real como notifications al chat
   - **Crear cron Telegram** `*/5 * * * *` con CronCreate que ejecute `mcp__telegram__leer_mensajes`; tras recibir mensaje cambiar a 30m; tras ~8 ciclos vacíos en 30m volver a 5m
   - Backend Ranger y frontend Angular NO se arrancan automáticamente — pedírselo al usuario si los necesita

**Claude (la siguiente sesión)**: al recibir el `additionalContext`, ejecutar inmediatamente esos 3 pasos antes de responder al usuario.

## 1. Monitor Hub (Telegram + WhatsApp)

Inicia el Monitor Hub que vigila ambos canales y notifica cuando llegan mensajes:

```bash
cd C:/proyectos/agenteIAlocal && PYTHONIOENCODING=utf-8 python -u -c "import sys; sys.path.insert(0,'agente_core'); from dotenv import load_dotenv; load_dotenv(); from monitor_hub.hub import main; main()"
```

Usar con Monitor tool, filtro: `"MSG|HUB_READY|CONNECTED|FAILED|ERROR"`

Config en `monitor_config.json`:
- Telegram: habilitado, poll 5s, chat_id 5483766132
- WhatsApp: habilitado, poll 10s, todos los grupos + DMs (sin status broadcast)

### Comportamiento con mensajes
- **Telegram**: leer con `mcp__telegram__leer_mensajes` y responder con `mcp__telegram__enviar_mensaje` (chat_id: 5483766132)
- **WhatsApp**: SOLO monitorear y reportar al usuario por Telegram. NUNCA responder por WhatsApp sin permiso explicito

## 2. MCP Telegram

Verificar que el MCP de Telegram este conectado (`/mcp`). Si no, reconectar.

Permisos auto-aprobados en `.claude/settings.local.json`:
- `mcp__telegram__enviar_mensaje`
- `mcp__telegram__leer_mensajes`
- `mcp__telegram__enviar_archivo`
- `mcp__telegram__enviar_voz`
- `mcp__telegram__info_bot`

Bot: `@bobito_rhay_bot` (TELEGRAM_TOKEN en .env)

## 3. WhatsApp

- Sesion guardada en `.wwebjs_auth/` (no necesita QR)
- Script monitor: `whatsapp_monitor.js` (Node.js persistente)
- Script lectura: `whatsapp_leer.js "NOMBRE GRUPO" N`
- Grupo prioritario: **SISTEMA RAY** (ID: `120363424666838458@g.us`)
- Skill: `skills/whatsapp-listener/`

## 4. Agente Local (Telegram)

Inicio manual (no lo arranca Claude Code, lo sube el usuario):
```bash
PYTHONIOENCODING=utf-8 python telegram_agente.py
```

- Modelo principal: configurable en .env (lfm2:latest, qwen3.6:latest, etc.)
- Gateway: `https://rhayalcantara-002-site2.ntempurl.com/api/v1`
- Tool Router activo (TOOL_ROUTER_ENABLED=true) — filtra herramientas por mensaje
- Tool Router LLM opcional (TOOL_ROUTER_LLM=true, modelo lfm2:latest)

## 5. Configuracion del Gateway

- URL: `https://rhayalcantara-002-site2.ntempurl.com/api/v1`
- Key: GATEWAY_API_KEY en .env
- Modelos disponibles: lfm2:latest, qwen3.6:latest, qwen3-next-80b, gemma-4-26b, etc.
- Vision: soportado con qwen3.6 (max 512px, quality 60, max_tokens 4096)

## 6. Datos importantes

- Chat ID Telegram de Rhay: `5483766132`
- WhatsApp chat ID de Rhay: `38427156299926@lid`
- Grupo SISTEMA RAY (WhatsApp): `120363424666838458@g.us`
- Modelos Qwen3.x necesitan min 2048 max_tokens (4096 para vision)
- ffmpeg instalado via winget en: `/c/Users/rhay_/AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1-full_build/bin`

## 7. Archivos clave

| Archivo | Proposito |
|---------|-----------|
| `monitor_config.json` | Config del Monitor Hub (canales, filtros) |
| `monitor_hub_server.py` | Hub + Dashboard web (puerto 8080) |
| `telegram_monitor_mcp.py` | Monitor ligero standalone (deprecado, usar hub) |
| `whatsapp_monitor.js` | Proceso Node.js persistente para WhatsApp |
| `whatsapp_leer.js` | Lee historial de un chat/grupo |
| `whatsapp_test.js` | Listener basico con QR |
| `mcp_telegram.py` | MCP server de Telegram |
| `telegram_agente.py` | Agente local principal |
| `pendientes_desarrollo.md` | Lista de pendientes |
| `whatsapp_sistema_ray.md` | Historial de mensajes SISTEMA RAY |
| `design_monitor_hub.md` | Arquitectura del Monitor Hub |

## 8. Memorias guardadas

Ver `~/.claude/projects/C--proyectos-agenteIAlocal/memory/MEMORY.md`:
- Qwen3.6 necesita min 2048 tokens (4096 vision)
- WhatsApp grupo SISTEMA RAY del cliente Ranger
- Workflow: agente local guarda en MD, Claude analiza
- NUNCA responder por WhatsApp sin permiso

## 9. Secuencia rapida de inicio
      
1. Verificar MCP Telegram conectado
2. Iniciar Monitor Hub (Telegram + WhatsApp)
3. Listo — los mensajes llegan automaticamente
