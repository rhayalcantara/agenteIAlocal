# Plan: Variable de Contexto para el Agente Local

## Objetivo
Agregar soporte de contexto de entrada y metadata de salida al método `chat()` del agente,
sin romper compatibilidad con callers existentes (Telegram, CLI).

## Cambios en `agente_core/agent.py`

### 1. Parámetro `contexto: dict = None` en `chat()`
- Si viene con datos, se serializa como prefijo en el mensaje del usuario:
  ```
  [Contexto: fuente=telegram | usuario=rhay | chat_id=123]
  <mensaje original>
  ```
- El mensaje original no se modifica; se arma un mensaje compuesto solo para el LLM.

### 2. Tracking interno durante el loop
- Lista `_herramientas_usadas` que acumula los nombres de tools llamadas en cada iteración.
- Contador `_iteraciones` que incrementa en cada vuelta del while.
- Al final, calcular `tokens_aprox` con `_contar_tokens()`.

### 3. Atributo `self._ultima_ejecucion` al terminar `chat()`
```python
self._ultima_ejecucion = {
    "herramientas_usadas": ["buscar_en_internet"],
    "iteraciones": 2,
    "tokens_aprox": 1240,
}
```
- Se sobreescribe en cada llamada a `chat()`.
- Retorno de `chat()` sigue siendo `str` (sin cambios en la firma de salida).

## Archivos a modificar
- `agente_core/agent.py` — único archivo afectado

## Tareas
1. Agregar parámetro `contexto` a `chat()` e inyectarlo en el mensaje
2. Agregar tracking de herramientas e iteraciones dentro del loop de `chat()`
3. Asignar `self._ultima_ejecucion` al finalizar el loop
4. Verificar que callers existentes no se rompen (sin cambios en Telegram/CLI)
