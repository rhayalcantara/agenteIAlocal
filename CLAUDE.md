# CLAUDE.md

Este archivo proporciona orientación a Claude Code (claude.ai/code) cuando trabaja con código en este repositorio.

## Descripción del Proyecto

Este es un proyecto educativo en español que demuestra cómo construir un agente de IA básico usando la API de OpenAI. El proyecto está basado en el artículo de Thorsten Ball en [Ampcode.com](https://ampcode.com/how-to-build-an-agent) y fue creado para el video "Tu primer agente de IA" del canal de YouTube "Ringa Tech".

## Configuración de Desarrollo

### Configuración del Entorno
- Ambiente virtual de Python (opcional pero recomendado)
- Instalar dependencias: `pip install -r requirements.txt`
- Crear archivo `.env` basado en `.env.example`

### Variables de Entorno
El proyecto soporta configuración flexible mediante variables de entorno:

- `API_BASE_URL`: URL del servidor de IA (por defecto: `https://api.openai.com/v1`)
  - OpenAI: `https://api.openai.com/v1`
  - LM Studio local: `http://localhost:1234/v1`
  - LM Studio en red: `http://[IP]:1234/v1`

- `MODEL_NAME`: Nombre del modelo a usar (por defecto: `gpt-4`)
  - Para OpenAI: `gpt-4`, `gpt-3.5-turbo`, etc.
  - Para LM Studio: nombre del modelo cargado en el servidor

- `OPENAI_API_KEY`: Clave de API
  - Obligatorio para OpenAI
  - Opcional para modelos locales (puede ser cualquier valor)

### Ejecución de la Aplicación
- Activar el ambiente virtual (si se está usando uno)
- Ejecutar: `python main.py`
- El programa mostrará la configuración activa (endpoint y modelo)
- Salir del agente escribiendo: `salir`, `exit`, `bye`, o `sayonara`

## Arquitectura

### Componentes Principales

**main.py** - Punto de entrada que implementa el bucle principal de conversación:
- Carga configuración desde variables de entorno (API_BASE_URL, MODEL_NAME, OPENAI_API_KEY)
- Inicializa el cliente de OpenAI con `base_url` y `api_key` configurables
- Muestra información de configuración al iniciar (endpoint y modelo activo)
- Gestiona entrada/salida del usuario vía consola
- Implementa patrón de doble bucle:
  - Bucle externo: acepta entrada del usuario y continúa la conversación
  - Bucle interno: maneja llamadas a herramientas hasta recibir respuesta final
- Usa `client.responses.create()` con el modelo configurado en `MODEL_NAME`

**agent.py** - Clase Agent que implementa arquitectura basada en herramientas:
- La clase `Agent` encapsula toda la lógica del agente
- Lista `messages`: mantiene el historial de conversación con prompt del sistema en español
- Lista `tools`: define las herramientas de función disponibles usando el esquema de llamadas a funciones de OpenAI
- `process_response()`: procesa respuestas de OpenAI, ejecuta herramientas, actualiza historial de mensajes

### Sistema de Herramientas

El agente implementa tres herramientas del sistema de archivos:

1. **list_files_in_dir** - Lista archivos en un directorio (por defecto el actual)
2. **read_file** - Lee el contenido de archivos desde una ruta especificada
3. **edit_file** - Edita archivos reemplazando `prev_text` con `new_text`, crea el archivo si no existe

Flujo de ejecución de herramientas:
- Las herramientas se definen en `setup_tools()` con formato de esquema de funciones de OpenAI
- `process_response()` detecta llamadas a funciones en la salida del modelo
- Los resultados de las herramientas se agregan al historial de mensajes como tipo `function_call_output`
- Retorna `True` si se llamó a una herramienta (desencadenando otra iteración del modelo), `False` para respuesta final

### Patrón de Historial de Mensajes

El agente mantiene el estado de conversación vía `self.messages`:
- Inicia con prompt del sistema que define un asistente conciso que habla español
- Mensajes del usuario se agregan antes de la llamada a la API
- El `response.output` completo se agrega después de cada llamada a la API
- Resultados de herramientas se agregan con `call_id` para correlación

## Notas Importantes de Implementación

### Configuración Flexible de IA
- El proyecto soporta múltiples proveedores de IA mediante configuración de variables de entorno
- Compatible con OpenAI API y modelos locales (LM Studio, Ollama, etc.)
- El cliente se inicializa con `base_url` personalizable (main.py:21-24)
- Valores por defecto apuntan a OpenAI si no se especifica configuración

### Compatibilidad con Modelos Locales
- LM Studio expone una API compatible con OpenAI en `http://[IP]:1234/v1`
- No todos los modelos locales soportan function calling (herramientas)
- Modelos recomendados: Mistral 7B Instruct, Llama 3.1, Qwen 2.5

### Código Existente
- El código actualmente tiene una nota (agent.py:74-75) sobre el envoltorio redundante de diccionario en el valor de retorno de `list_files_in_dir`
- Los resultados de las herramientas están envueltos en un dict `{"files": result}` (agent.py:151), aunque el comentario sugiere que la clave `"result"` sería más apropiada para las tres herramientas
- Las operaciones de archivos usan codificación UTF-8 para soporte de texto en español
- La herramienta `edit_file` crea directorios padre automáticamente si es necesario
