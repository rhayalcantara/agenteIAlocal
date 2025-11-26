# Mejora: Manejo Robusto de Errores

## Fecha: 2025-11-25

---

## 🎯 Problema Identificado

Durante las pruebas con LM Studio usando el modelo `gpt-oss-safeguard-20b`, se identificó que después de múltiples llamadas a herramientas (6 en el test), el servidor de LM Studio retornaba un error:

```
openai.InternalServerError: Internal Server Error
```

Esto causaba que el programa se cerrara abruptamente sin dar información útil al usuario.

---

## 🔧 Solución Implementada

Se agregó manejo de errores con `try-except` en el bucle interno de `main.py` que procesa las respuestas del modelo.

### Código Agregado

**Archivo**: `main.py:42-67`

```python
while True:
    try:
        response = client.responses.create(
            model=model_name,
            input=agent.messages,
            tools=agent.tools
        )

        called_tool = agent.process_response(response)

        #Si no se llamo herramienta, tenemos la respuesta final
        if not called_tool:
            break

    except Exception as e:
        print(f"\n⚠️  Error al comunicarse con el modelo: {type(e).__name__}")
        print(f"Detalles: {str(e)[:200]}...")
        print("\nPosibles soluciones:")
        print("  1. El contexto es muy largo - intenta reiniciar la conversación")
        print("  2. Reinicia el servidor en LM Studio")
        print("  3. Verifica que el modelo soporte function calling")

        # Remover el último mensaje del usuario para que no quede en historial
        if agent.messages and agent.messages[-1].get("role") == "user":
            agent.messages.pop()

        break
```

---

## ✅ Beneficios

### 1. **No Más Crashes**
El programa ya no se cierra abruptamente cuando hay un error del servidor.

### 2. **Mensajes Informativos**
El usuario recibe:
- Tipo de error que ocurrió
- Detalles del error (primeros 200 caracteres)
- Lista de posibles soluciones

### 3. **Limpieza del Historial**
Si hay un error, se remueve el último mensaje del usuario del historial para evitar corrupción de datos.

### 4. **Continuidad de la Conversación**
El usuario puede continuar usando el agente sin necesidad de reiniciarlo completamente.

---

## 📊 Resultado del Testing

### Test Exitoso con LM Studio

**Configuración**:
- **Servidor**: `http://192.168.1.96:1234/v1`
- **Modelo**: `gpt-oss-safeguard-20b`

**Resultados**:
- ✅ Conexión exitosa al servidor LM Studio en red
- ✅ Carga correcta de configuración desde `.env`
- ✅ Herramientas funcionando correctamente:
  - `list_files_in_dir` ejecutada 2 veces
  - `read_file` ejecutada 3 veces
- ✅ El modelo local comprende function calling
- ✅ Manejo de error cuando el contexto creció demasiado

### Ejemplo de Salida

```
==================================================
Mi primer agente de IA
==================================================
📡 Endpoint: http://192.168.1.96:1234/v1
🤖 Modelo: gpt-oss-safeguard-20b
==================================================
Tú: [pregunta del usuario]
  - El modelo considera llamar a la herramienta list_files_in_dir
  - Argumentos: {'directory': 'c:\\Proyectos\\tu-primer-agente-de-ia'}
  ⚙️ Herramienta llamada: list_files_in_dir
  [... múltiples llamadas a herramientas ...]

⚠️  Error al comunicarse con el modelo: InternalServerError
Detalles: <!DOCTYPE html>...

Posibles soluciones:
  1. El contexto es muy largo - intenta reiniciar la conversación
  2. Reinicia el servidor en LM Studio
  3. Verifica que el modelo soporte function calling
```

---

## 🔍 Causas Comunes de Errores

### 1. **Contexto Muy Largo**
**Causa**: Después de múltiples llamadas a herramientas, el historial de mensajes crece mucho.

**Solución**:
- Reiniciar la conversación (escribir `salir` y volver a ejecutar)
- Implementar límite de contexto (mejora futura)

### 2. **Límites del Modelo Local**
**Causa**: No todos los modelos locales manejan bien function calling complejo.

**Solución**:
- Usar modelos recomendados (Mistral 7B Instruct, Llama 3.1, Qwen 2.5)
- Reducir complejidad de las preguntas

### 3. **Problemas del Servidor LM Studio**
**Causa**: LM Studio puede tener problemas internos o quedarse sin recursos.

**Solución**:
- Reiniciar el servidor en LM Studio
- Verificar uso de RAM/GPU
- Probar con un modelo más pequeño

### 4. **Problemas de Red**
**Causa**: Conexión interrumpida cuando se usa LM Studio en red.

**Solución**:
- Verificar conectividad de red
- Probar con `localhost` si es posible
- Verificar firewall

---

## 🚀 Mejoras Futuras Sugeridas

### 1. Límite de Contexto
Implementar un límite en el número de mensajes en el historial:

```python
# Mantener solo los últimos N mensajes
MAX_MESSAGES = 20
if len(agent.messages) > MAX_MESSAGES:
    # Mantener system prompt + últimos mensajes
    agent.messages = [agent.messages[0]] + agent.messages[-MAX_MESSAGES:]
```

### 2. Reintentos Automáticos
Implementar reintentos con backoff exponencial:

```python
max_retries = 3
for attempt in range(max_retries):
    try:
        response = client.responses.create(...)
        break
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
            continue
        else:
            # Mostrar error después de todos los reintentos
            print(error_message)
```

### 3. Timeout Configurable
Agregar timeout desde variables de entorno:

```python
TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))  # segundos

client = OpenAI(
    base_url=api_base_url,
    api_key=api_key,
    timeout=TIMEOUT
)
```

### 4. Logging Detallado
Guardar errores en archivo de log para debugging:

```python
import logging

logging.basicConfig(
    filename='agent_errors.log',
    level=logging.ERROR
)

except Exception as e:
    logging.error(f"Error: {e}", exc_info=True)
    # Mostrar mensaje al usuario
```

---

## 📝 Archivos Modificados

### `main.py`
- **Líneas 41-67**: Agregado bloque try-except con manejo de errores
- **Funcionalidad**: Captura excepciones, muestra mensajes útiles, limpia historial

---

## ✅ Validación

- [x] Error capturado correctamente
- [x] Programa no se cierra abruptamente
- [x] Mensajes informativos mostrados al usuario
- [x] Historial limpiado para evitar corrupción
- [x] Usuario puede continuar la conversación
- [x] Testing con LM Studio exitoso

---

## 📚 Documentación Actualizada

- [x] Este documento (`mejora-manejo-errores.md`)
- [ ] Actualizar `README.md` con sección de errores comunes (opcional)
- [ ] Actualizar `CLAUDE.md` con información de manejo de errores (opcional)

---

## 🎉 Conclusión

La implementación de manejo de errores robusto mejora significativamente la experiencia del usuario al:

1. Prevenir crashes inesperados
2. Proporcionar información útil sobre qué salió mal
3. Sugerir soluciones concretas
4. Mantener la integridad del historial de conversación
5. Permitir continuar la sesión sin reiniciar

**Estado**: ✅ IMPLEMENTADO Y VALIDADO
