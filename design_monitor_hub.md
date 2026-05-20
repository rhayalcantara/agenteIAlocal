# Monitor Hub — Arquitectura

Sistema centralizado de monitoreo multi-canal para el agente IA local.

## Vision
Un solo proceso que vigila multiples canales de comunicacion (Telegram, WhatsApp, Gmail, etc.) y notifica a Claude Code o al agente local cuando hay actividad relevante.

## Arquitectura

```
┌─────────────────────────────────────────────┐
│              Monitor Hub (Python)            │
│                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ Telegram  │ │ WhatsApp │ │  Gmail   │    │
│  │  Plugin   │ │  Plugin  │ │  Plugin  │    │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘    │
│       │             │            │           │
│       ▼             ▼            ▼           │
│  ┌─────────────────────────────────────┐    │
│  │         Event Bus (interno)         │    │
│  └────────────┬────────────────────────┘    │
│               │                             │
│  ┌────────────▼────────────────────────┐    │
│  │      Dispatcher / Router           │    │
│  │  - Filtros por canal/grupo/palabra  │    │
│  │  - Prioridad (urgente/normal)       │    │
│  │  - Deduplicacion                    │    │
│  └────┬───────────┬───────────┬────────┘    │
│       │           │           │             │
│       ▼           ▼           ▼             │
│   stdout      webhook     archivo           │
│  (Claude)    (futuro)      (.md)            │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │     Dashboard Web (FastAPI)         │    │
│  │  - Estado de cada canal             │    │
│  │  - Ultimos mensajes                 │    │
│  │  - Config on/off por canal          │    │
│  │  - Logs en tiempo real              │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

## Plugins (canales)

Cada canal es un plugin con interfaz estandar:

```python
class ChannelPlugin:
    name: str           # "telegram", "whatsapp", "gmail"
    enabled: bool
    poll_interval: int  # segundos entre checks

    def connect(self) -> bool
    def poll(self) -> list[Message]
    def send(self, chat_id, text) -> bool
    def disconnect(self)
```

### Plugin: Telegram
- Usa requests directo a la API de Telegram
- Token: TELEGRAM_TOKEN de .env
- Poll interval: 5s

### Plugin: WhatsApp
- Usa subprocess para correr whatsapp_leer.js
- O un server Node.js persistente con comunicacion via stdin/stdout
- Sesion guardada en .wwebjs_auth/
- Poll interval: 30s (mas pesado que Telegram)

### Plugin: Gmail
- Usa la API de Gmail (ya existe gmail-reader skill)
- Poll interval: 60s
- Filtra por labels o queries

## Mensaje estandar

```python
@dataclass
class Message:
    channel: str        # "telegram", "whatsapp", "gmail"
    chat_id: str        # ID del chat/grupo/thread
    chat_name: str      # "SISTEMA RAY", "DM con Rhay"
    user: str           # nombre del remitente
    text: str           # contenido
    timestamp: datetime
    type: str           # "text", "voice", "image", "document"
    priority: str       # "normal", "urgent"
    raw: dict           # datos originales del canal
```

## Configuracion (config.json)

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "poll_interval": 5,
      "token_env": "TELEGRAM_TOKEN",
      "filters": {
        "allowed_chats": [5483766132]
      }
    },
    "whatsapp": {
      "enabled": true,
      "poll_interval": 30,
      "filters": {
        "watch_groups": ["SISTEMA RAY"],
        "ignore_groups": ["Familia"]
      }
    },
    "gmail": {
      "enabled": false,
      "poll_interval": 60,
      "filters": {
        "query": "is:unread label:important"
      }
    }
  },
  "dispatcher": {
    "output": "stdout",
    "dedup_window": 60,
    "urgent_keywords": ["urgente", "error", "caido", "no funciona"]
  },
  "dashboard": {
    "enabled": true,
    "port": 8080
  }
}
```

## Dashboard Web

FastAPI + HTML simple (sin framework frontend pesado):

- **GET /** — Dashboard principal: estado de canales, ultimos 20 mensajes
- **GET /channels** — Lista de canales con estado on/off
- **POST /channels/{name}/toggle** — Activar/desactivar canal
- **GET /messages** — Ultimos mensajes (filtrable por canal)
- **GET /logs** — Logs en tiempo real (SSE)
- **GET /config** — Ver configuracion
- **POST /config** — Actualizar configuracion

## Fases de implementacion

### Fase 1: Core + Telegram (ya tenemos)
- [ ] Refactorizar telegram_monitor_mcp.py como plugin
- [ ] Crear monitor_hub.py con event bus basico
- [ ] Config desde JSON
- [ ] Output a stdout (para Claude Code)

### Fase 2: WhatsApp
- [ ] Plugin WhatsApp usando whatsapp_leer.js
- [ ] Filtro por grupo (SISTEMA RAY)
- [ ] Guardar mensajes en .md automaticamente

### Fase 3: Dashboard
- [ ] FastAPI con endpoints basicos
- [ ] Pagina HTML con estado de canales
- [ ] Toggle on/off desde el browser
- [ ] Ultimos mensajes en tiempo real

### Fase 4: Gmail + extensibilidad
- [ ] Plugin Gmail
- [ ] Sistema de prioridades (urgent keywords)
- [ ] Notificaciones cruzadas (WhatsApp urgente → notifica por Telegram)

## Archivos

```
agente_core/
  monitor_hub/
    __init__.py
    hub.py              # Main loop, event bus
    config.py           # Carga config.json
    message.py          # Dataclass Message
    plugins/
      __init__.py
      base.py           # ChannelPlugin base class
      telegram.py       # Plugin Telegram
      whatsapp.py       # Plugin WhatsApp
      gmail.py          # Plugin Gmail
    dashboard/
      app.py            # FastAPI
      templates/
        index.html      # Dashboard UI
monitor_config.json     # Configuracion
```
