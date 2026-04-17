# Plan: Streaming de salida + tracking de procesos bash activos

## Objetivo
Ver en tiempo real la salida de comandos bash mientras el agente los ejecuta,
y saber en todo momento si hay un proceso bash corriendo.

## Cambios

### 1. bash_terminal.py — BashTerminal
- Agregar `self.proceso_activo: dict | None = None`
  Estructura: `{"comando": str, "inicio": datetime, "pid": int}`
- En `ejecutar()`:
  - Setear `proceso_activo` al inicio del comando
  - Imprimir cada línea al vuelo con prefijo `│ ` (streaming real)
  - Limpiar `proceso_activo = None` al terminar (en finally)

### 2. agent.py — propiedad bash_proceso_activo
- Agregar `@property bash_proceso_activo` que retorna
  `iatools.terminal.proceso_activo` (o None si no hay nada corriendo)

## Archivos a modificar
- `agente_core/bash_terminal.py`
- `agente_core/agent.py`

## Tareas
1. Agregar proceso_activo y streaming en bash_terminal.py
2. Exponer propiedad bash_proceso_activo en agent.py
