# SKILL: Claude Auto-Resolver

Esta skill se activa cuando el agente detecta que una tarea o comando está fallando repetidamente, o cuando el usuario solicita ayuda para desbloquear un proceso.

## Objetivo
Utilizar la capacidad de razonamiento de Claude Code CLI mediante el flag `-p` para obtener soluciones rápidas sin interrumpir el flujo interactivo, permitiendo al agente "auto-corregirse".

## Interfaz

### Desde Python
```python
from skills.claude_auto_resolver.run import run_claude_prompt

respuesta = run_claude_prompt("¿Cómo parsear un XML con namespaces en Python?")
respuesta = run_claude_prompt("Error: ModuleNotFoundError: No module named 'bs4'", timeout=90)
```

**Parámetros:**
- `prompt` (str): La pregunta o descripción del error. No puede estar vacío.
- `timeout` (int, opcional): Segundos máximos de espera. Default: 60.

**Retorna:** `str` con la respuesta de Claude, o un mensaje de error descriptivo.

### Desde CLI
```bash
python skills/claude-auto-resolver/run.py "¿Cómo obtener listas de compliance desde internet?"
```

## Cómo usarla (agente)
Cuando encuentres un error persistente en un comando bash o una tarea de edición:
1. Identifica el error exacto.
2. Llama a `run_claude_prompt(error)` para obtener una solución.
3. Aplica la solución sugerida.

## Límites
- Respuesta truncada a 8000 caracteres para evitar saturar el contexto.
- Timeout por defecto de 60 segundos (configurable).