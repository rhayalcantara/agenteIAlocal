# Comunicación Claude Local ↔ Claude Ranger

Reporte preparado mientras Rhay caminaba (2026-05-13 17:00–18:00).

## TL;DR

Ya diseñaste todo el `deploy_ranger/` el 2026-04-28 (hace 2 semanas). Nunca se desplegó. Solo falta:
1. Re-crear el bot `@claudy_*_bot` (su token está muerto)
2. Subir `deploy_ranger/` al servidor de Ranger
3. Agregar un segundo MCP local que escuche al bot Claudy

Tiempo estimado: 30-45 min de trabajo manual cuando estés disponible.

## Hallazgos

### Lo que ya existe (carpeta `deploy_ranger/`)

| Archivo | Qué hace |
|---|---|
| `mcp_telegram_ranger.py` | MCP server para que Claude del servidor lea/envíe Telegram |
| `telegram_loop_ranger.py` | Loop persistente: cuando llega mensaje al bot Ranger, ejecuta `claude -p <prompt>` y responde por AMBOS bots |
| `auto_deploy.sh` | Watcher que detecta commits y dispara `git pull` |
| `mcp.json` | Config MCP del lado Ranger (renombrar a `.mcp.json` en su raíz) |
| `CLAUDE.md` | Instrucciones para el Claude del servidor |
| `INSTALL.md` | Pasos de instalación en macOS |

### Estado de los bots

| Bot | Token | Estado | Uso |
|---|---|---|---|
| `@bobito_rhay_bot` | en `.env` (`TELEGRAM_TOKEN`) | ✅ vivo | Bot actual local (lo usa esta sesión) |
| `@rhayranger_claude_bot` | hardcoded en `deploy_ranger/*.py` (`8728278032:...`) | ✅ vivo | Para Claude del servidor |
| `@claudy_*_bot` | hardcoded `8761021691:...` | ❌ **token inválido** | Diseñado como puente para que Local "vea" respuestas de Ranger |

El bot Claudy está roto — alguien lo eliminó/revocó. Hay que decidir si re-crearlo o cambiar el patrón.

### Diseño original (de `telegram_loop_ranger.py`)

```
Rhay (DM) ──(orden)──> @rhayranger_claude_bot ──> Claude Ranger ejecuta
                                                       │
                       ┌───────────────────────────────┤
                       │ respuesta dual                │
                       ▼                               ▼
              @rhayranger_claude_bot          @claudy_*_bot
                       │                               │
                       ▼                               ▼
              Rhay la ve                  Claude Local la lee (vía MCP)
```

El problema con este diseño aun resuelto: **Claude Local no tiene forma de ORIGINAR mensajes a Ranger**. Solo recibe. Si quieres bidireccional real, falta el camino inverso.

### Opciones para activar (de menos a más cambio)

**Opción A — Restaurar el diseño original (1 vía: Local recibe, Rhay origina)**
1. Re-crear bot Claudy en `@BotFather`, obtener token nuevo
2. Subir `deploy_ranger/` al servidor + instalar deps + `claude login` + correr `telegram_loop_ranger.py`
3. Agregar MCP local nuevo `telegram-claudy` que polle el bot Claudy
4. Resultado: Rhay manda órdenes a Ranger, ambos Claudes ven las respuestas

**Opción B — Bridge bidireccional con dos bots dedicados (recomendada)**
1. Re-crear bot Claudy
2. En `telegram_loop_ranger.py`, en vez de filtrar `is_bot`, aceptar mensajes que vienen del **chat_id del bot Claudy** (Local manda a Ranger usando Claudy → un mensaje en el grupo, Ranger lo lee con Bot R, ignora todos los `is_bot` excepto cuando `from.id == claudy_bot_id`)
3. Resultado: ambos Claudes pueden hablar entre sí en un grupo común con Rhay como espectador

**Opción C — HTTP cola en gateway propio (más limpia, más trabajo)**
1. Añadir endpoints `POST /bridge/send` y `GET /bridge/poll?for=local|ranger` al backend del gateway `ntempurl.com`
2. Cada Claude usa Bash/WebFetch
3. Pros: payloads grandes, sin límites Telegram, encaja con tu Job Manager
4. Contras: ~1h de código en el gateway, sin push (solo polling)

**Opción D — Anthropic Routines API (descartar por ahora)**
- Routines tienen trigger HTTP pero crean sesión nueva en cloud, no inyectan a la sesión local viva del otro lado. No sirve para tiempo real.

## Recomendación

**Empieza con Opción A** (mínimo viable, restaura tu diseño). Si va bien, gradúa a B agregando el filtro inverso en `telegram_loop_ranger.py`. C lo dejas para cuando necesites payloads grandes (archivos, imágenes).

## Punch list para Opción A

Cuando estés disponible:

**En tu PC local (cambios de código)**:
- [ ] Re-crear bot Claudy en BotFather, guardar token nuevo
- [ ] Actualizar token hardcoded en `deploy_ranger/telegram_loop_ranger.py:21` y `deploy_ranger/mcp_telegram_ranger.py:10` (o usar env var)
- [ ] Crear `mcp_telegram_claudy.py` clon del `mcp_telegram.py` actual pero con el token Claudy
- [ ] Agregar entrada en `.mcp.json` local: `"telegram-claudy": { ... }`
- [ ] Commit y push a GitHub

**En el servidor de Ranger** (necesito te lo hagas tú, no tengo acceso):
- [ ] `git pull` en el proyecto Ranger para traer `deploy_ranger/`
- [ ] `pip3 install mcp requests`
- [ ] Verificar `claude` CLI instalado y autenticado (`claude login`)
- [ ] Copiar `deploy_ranger/mcp.json` a `.mcp.json` en la raíz del proyecto
- [ ] Copiar `deploy_ranger/CLAUDE.md` a la raíz
- [ ] Levantar `python3 telegram_loop_ranger.py` como servicio persistente (systemd, launchd o `nohup`)

**Verificación end-to-end**:
- [ ] Desde tu Telegram, mandar al bot Ranger: "leer status del repo"
- [ ] Ver respuesta llegar por Bot Ranger Y por Bot Claudy
- [ ] Yo (local) confirmo que mi MCP claudy la ve

## Costos/riesgos

- **Token en código fuente**: los 2 tokens están hardcoded en `deploy_ranger/*.py` (ya commiteados al repo). Idealmente moverlos a env vars antes de push final. Mientras tanto NO compartir el repo con terceros.
- **Bot Ranger ejecuta Claude CLI sin sandbox**: cualquiera con acceso al bot puede ejecutar arbitrariamente. Solo Rhay (chat_id `5483766132`) debe poder mandarle. Filtrar `if chat_id != 5483766132: continue` en el loop.
- **Costo Claude**: cada mensaje al bot Ranger lanza una sesión nueva. Si quedan loops, gasta tu cuota.

## Lo que NO hice (por seguridad)

- No commit ni push de cambios al repo
- No tocar el servidor de Ranger (no tengo acceso)
- No mandar mensajes de prueba a ningún bot que no fuera el actual
