# Plan: Soporte para APIs de IA Locales (LM Studio)

## Objetivo
Modificar el agente para soportar el uso de modelos de IA locales a través de LM Studio, permitiendo especificar una IP de red personalizada en lugar de usar exclusivamente la API de OpenAI.

## Análisis Actual

### Estado Actual del Código
- El proyecto usa directamente `OpenAI()` client con API key desde `.env`
- El modelo está hardcodeado como "gpt-5-nano" en `main.py:28`
- No hay configuración para cambiar el endpoint base de la API
- No hay flexibilidad para seleccionar diferentes proveedores de IA

### Requerimientos
- Permitir configuración de endpoint personalizado (LM Studio en red local)
- Mantener compatibilidad con OpenAI API
- Configuración a través de variables de entorno
- Selección flexible de modelo

## Plan de Implementación

### 1. Actualizar Configuración de Entorno
**Archivo**: `.env`
- Agregar `API_BASE_URL` para el endpoint de LM Studio
- Agregar `MODEL_NAME` para especificar el modelo a usar
- Mantener `OPENAI_API_KEY` (opcional si se usa modelo local)

**Ejemplo de configuración**:
```
# Para LM Studio local
API_BASE_URL=http://192.168.1.100:1234/v1
MODEL_NAME=local-model-name
OPENAI_API_KEY=not-needed-for-local

# Para OpenAI (comentar las de arriba)
# API_BASE_URL=https://api.openai.com/v1
# MODEL_NAME=gpt-5-nano
# OPENAI_API_KEY=sk-...
```

### 2. Modificar Inicialización del Cliente
**Archivo**: `main.py`

Cambios necesarios:
- Cargar `API_BASE_URL` y `MODEL_NAME` desde `.env`
- Inicializar cliente OpenAI con `base_url` personalizado
- Usar variable `MODEL_NAME` en lugar de hardcodear "gpt-5-nano"

**Código propuesto**:
```python
import os
from openai import OpenAI
from dotenv import load_dotenv
from agent import Agent

load_dotenv()

# Configuración flexible
api_base_url = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
model_name = os.getenv("MODEL_NAME", "gpt-5-nano")
api_key = os.getenv("OPENAI_API_KEY", "not-needed")

print("Mi primer agente de IA")
print(f"Usando modelo: {model_name}")
print(f"Endpoint: {api_base_url}")

# Inicializar cliente con configuración personalizada
client = OpenAI(
    base_url=api_base_url,
    api_key=api_key
)

agent = Agent()
# ... resto del código usando 'model_name' en lugar de "gpt-5-nano"
```

### 3. Actualizar Llamadas al Modelo
**Archivo**: `main.py`

Cambiar:
```python
response = client.responses.create(
    model="gpt-5-nano",  # <-- hardcodeado
    input=agent.messages,
    tools=agent.tools
)
```

Por:
```python
response = client.responses.create(
    model=model_name,  # <-- desde variable de entorno
    input=agent.messages,
    tools=agent.tools
)
```

### 4. Documentación
**Archivo**: `README.md`

Agregar sección explicando:
- Cómo configurar LM Studio como servidor
- Cómo obtener la IP de red local
- Ejemplos de configuración para diferentes escenarios
- Troubleshooting común

**Archivo**: `CLAUDE.md`

Actualizar con:
- Nueva arquitectura de configuración
- Soporte para múltiples proveedores
- Variables de entorno disponibles

### 5. Validación y Manejo de Errores (Opcional pero Recomendado)
**Archivo**: `main.py`

Agregar validaciones:
- Verificar conectividad con el endpoint antes de iniciar
- Mensajes de error claros si no se puede conectar
- Timeout configurable para requests

## Consideraciones Técnicas

### Compatibilidad con LM Studio
- LM Studio expone una API compatible con OpenAI
- El endpoint típicamente es `http://[IP]:1234/v1`
- Requiere que LM Studio esté ejecutándose con un modelo cargado
- Soporta function calling (herramientas) si el modelo lo permite

### Limitaciones Potenciales
- No todos los modelos locales soportan function calling
- El rendimiento depende del hardware donde corra LM Studio
- Latencia de red si se usa desde otra máquina

### Testing
- Probar con LM Studio en red local
- Probar que OpenAI sigue funcionando
- Verificar que las herramientas funcionen con modelos locales

## Archivos a Modificar
1. `main.py` - Cliente y llamadas al modelo
2. `.env` - Nuevas variables de configuración
3. `README.md` - Documentación de uso
4. `CLAUDE.md` - Documentación técnica

## Próximos Pasos
1. Revisar y discutir el plan
2. Implementar cambios según prioridad
3. Crear archivo `.env.example` con plantillas
4. Probar con LM Studio real
5. Actualizar documentación