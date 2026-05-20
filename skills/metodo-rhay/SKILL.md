# Metodo Rhay: Arquitectura de Agente IA Modular

Guia para replicar la arquitectura de este agente. El principio central:
**el agente es el frontend**, las herramientas son backends independientes.

## 1. Estructura del Proyecto

```text
mi-agente/
├── agente_core/                # Nucleo del agente
│   ├── agent.py                # Clase Agent: tools, mensajes, loop de ejecucion
│   ├── tools.py                # Herramientas base (archivos, bash)
│   ├── provider_config.py      # Multi-proveedor LLM (OpenAI, LM Studio, etc.)
│   ├── telegram_bridge.py      # Puente Telegram <-> Agent
│   ├── memoria.py              # Memoria persistente del agente
│   ├── wiki_manager.py         # Base de conocimiento estructurada
│   ├── skill_loader.py         # Carga dinamica de skills desde skills/
│   ├── heartbeat.py            # Pulso de vida para el supervisor
│   ├── browser_tool.py         # Automatizacion de navegador
│   ├── excel_tool.py           # Manipulacion de Excel
│   ├── lista_compras_tool.py   # Backend: lista de compras
│   ├── distribucion_casa_tool.py # Backend: mapa de areas del hogar
│   ├── ubicaciones_tool.py     # Backend: objetos y su ubicacion
│   ├── recetas_tool.py         # Backend: recetas con cruce a compras
│   ├── web_scraper.py          # Scraping de paginas web
│   ├── voice_handler.py        # Procesamiento de voz (STT/TTS)
│   ├── logger.py               # Sistema de logging
│   └── data/                   # Datos persistentes (JSON, fotos)
│       ├── lista_compras.json
│       ├── distribucion_casa.json
│       ├── ubicaciones.json
│       ├── recetas.json
│       ├── memoria.json
│       ├── imagenes_compras/
│       ├── imagenes_casa/
│       ├── imagenes_ubicaciones/
│       └── imagenes_recetas/
├── supervisor/                 # Monitoreo y auto-recuperacion
│   ├── supervisor_bot.py       # Bot Telegram separado que vigila al agente
│   ├── health_checker.py       # Verifica heartbeat y estado del proceso
│   ├── process_manager.py      # Inicia, detiene, reinicia el agente
│   ├── decision_engine.py      # LLM decide que hacer ante un problema
│   └── config.py               # Configuracion del supervisor
├── skills/                     # Habilidades modulares (SKILL.md + scripts)
│   ├── claude-auto-resolver/   # Consulta a LLM para resolver errores
│   ├── buscar-noticias/        # Busqueda y envio de noticias
│   ├── youtube-downloader/     # Descarga de videos
│   └── .../                    # Cada skill es una carpeta independiente
├── telegram_agente.py          # Entry point: bot Telegram del agente
├── telegram_listener.py        # Recibe mensajes, fotos, audios, documentos
├── main.py                     # Entry point: agente por consola
└── .env                        # Configuracion (tokens, modelos, URLs)
```

## 2. Patron Core: El Loop del Agente

El agente funciona con un doble bucle:

```
Usuario envia mensaje (Telegram/consola)
    |
    v
telegram_listener.py recibe (texto, foto, audio, documento)
    |
    v
telegram_agente.py encola el mensaje
    |
    v
telegram_bridge.py -> agent.chat(mensaje, image_path=...)
    |
    v
Agent envia mensajes[] al LLM
    |
    v
LLM responde con texto o tool_call
    |
    ├── tool_call -> _ejecutar_tool() -> resultado -> vuelve al LLM
    |                    (bucle interno hasta que no haya mas tools)
    |
    └── texto final -> respuesta al usuario
```

## 3. Patron Backend-Tool (Metodo Rhay)

Cada funcionalidad se implementa como un backend independiente:

### Estructura de un tool:
```python
# agente_core/mi_tool.py

_OPERACIONES = {
    "crear": crear,
    "listar": listar,
    "editar": editar,
    "eliminar": eliminar,
}

def ejecutar(operacion: str, **kwargs) -> str:
    fn = _OPERACIONES.get(operacion)
    return fn(**kwargs)
```

### Registro en agent.py (2 pasos):

**Paso 1 — Schema en setup_tools():**
```python
{"type": "function", "name": "mi_tool",
 "description": "Descripcion + lista de operaciones",
 "parameters": {"type": "object", "properties": {
     "operacion": {"type": "string", "enum": [...]},
     # ... parametros de cada operacion
 }, "required": ["operacion"]}}
```

**Paso 2 — Dispatch en _ejecutar_tool():**
```python
elif fn_name == "mi_tool":
    from mi_tool import ejecutar as mi_ejecutar
    operacion = args.pop("operacion")
    result = mi_ejecutar(operacion, **args)
```

### Soporte de imagenes:
- El usuario envia foto por Telegram -> llega como `image_path` temporal
- El tool copia la imagen a `data/imagenes_X/` (persistente)
- Al consultar, si el resultado contiene `IMAGEN:ruta`, el dispatch
  la envia por Telegram usando `_send_file_callback`

### Cruce entre tools:
Los tools pueden importarse entre si. Ejemplo: `recetas_tool.py` importa
`lista_compras_tool.ejecutar("agregar", ...)` para agregar ingredientes
faltantes automaticamente.

## 4. Sistema de Skills

Skills son modulos de instrucciones (SKILL.md) + scripts opcionales (.py).

```text
skills/mi-skill/
├── SKILL.md    # Instrucciones que el agente lee para saber como usarla
└── run.py      # Script ejecutable (opcional)
```

- `skill_loader.py` escanea `skills/` al iniciar y carga todos los SKILL.md
- El agente tiene herramientas `listar_skills`, `activar_skill`, `crear_skill`
- Las skills son instrucciones para el agente, los tools son codigo ejecutable

**Diferencia clave:**
- **Skill** = instrucciones en lenguaje natural que el agente interpreta
- **Tool** = codigo Python con `ejecutar()` que el agente llama via function calling

## 5. Supervisor

Bot de Telegram separado (token distinto) que vigila al agente:

```
supervisor_bot.py (hilo principal: comandos Telegram)
    |
    ├── _monitor_loop (hilo daemon)
    |       |
    |       ├── health_checker.verificar() -> ok | frozen | crashed
    |       |
    |       ├── Si problema: claude-auto-resolver diagnostica los logs
    |       |
    |       └── decision_engine.decidir() -> auto_restart | alert_user | wait
    |
    └── Comandos: /estado /reiniciar /detener /iniciar /logs /info /llm /modo
```

Modos:
- **manual**: siempre consulta al usuario antes de actuar
- **auto**: el LLM decide y actua (con limite de intentos)

## 6. Multi-Proveedor LLM

`provider_config.py` permite cambiar de proveedor sin tocar codigo:

```env
PROVIDER_DEFAULT=lmstudio          # lmstudio | openrouter | openai | claude | gemini
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=nombre-del-modelo
```

Modelos locales (LM Studio) = datos nunca salen de tu red.

## 7. Como Agregar una Nueva Funcionalidad

1. Crear `agente_core/nueva_tool.py` con patron `ejecutar(operacion, **kwargs)`
2. Datos en `agente_core/data/nueva.json` + imagenes en `data/imagenes_nueva/`
3. En `agent.py`: schema en `setup_tools()` + dispatch en `_ejecutar_tool()`
4. Agregar al perfil `"local"` si debe funcionar con modelos locales
5. Si cruza con otros tools, importar directamente

El agente es la interfaz. Si el usuario necesita reportes visuales,
el agente genera HTML/CSS/JS o PDF y lo envia por Telegram.
