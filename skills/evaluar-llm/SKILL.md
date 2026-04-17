# Skill: Evaluar LLM

Batería de pruebas para evaluar fortalezas y debilidades de cualquier LLM compatible con la API OpenAI en 4 dimensiones clave. Genera un reporte markdown con scores, análisis por criterio y conclusiones.

## Uso
Para usar la skill, pide algo como:
- "evalúa el LLM actual"
- "ejecuta las pruebas de evaluación del modelo"
- "corre la batería de tests al LLM"
- "evalúa gemini" / "evalúa openrouter"

## Dimensiones evaluadas

| # | Dimensión | Qué mide |
|---|-----------|----------|
| 1 | Seguimiento de instrucciones | Si cumple formato, límites y pasos exactos |
| 2 | Entendimiento de conceptos | Si comprende y aplica ideas en contextos nuevos |
| 3 | Proactividad y razonamiento | Si detecta problemas, pide info faltante y anticipa consecuencias |
| 4 | Conclusión de temas | Si pausa, retoma y cierra temas correctamente |

## Pruebas incluidas

### Seguimiento de instrucciones
- **SI-1** Formato estricto — lista numerada exacta de 3 items sin texto extra
- **SI-2** Restricción de longitud — definición en máximo 20 palabras
- **SI-3** Instrucciones múltiples — 3 pasos exactos en orden

### Entendimiento de conceptos
- **EC-1** Analogía creativa — API explicada con analogía de restaurante
- **EC-2** Aplicación en contexto nuevo — principio DRY aplicado fuera del código
- **EC-3** Identificar error conceptual — 99% accuracy no siempre es bueno

### Proactividad y razonamiento
- **PR-1** Detectar información faltante — problema incompleto de cálculo de tiempo
- **PR-2** Razonamiento paso a paso — acertijo del fósforo
- **PR-3** Anticipar consecuencias — borrar rama main en producción

### Conclusión de temas
- **CT-1** Pausar y retomar — esperar confirmación antes de responder
- **CT-2** Resumen y cierre — resumen ejecutivo de 3 temas con recomendación final

## Interfaz

### Desde Python
```python
from skills.evaluar_llm.run import run_evaluar_llm

# Usa el proveedor configurado en .env
ruta = run_evaluar_llm()

# Forzar un proveedor específico
ruta = run_evaluar_llm(provider_override="gemini")
ruta = run_evaluar_llm(provider_override="openrouter")
ruta = run_evaluar_llm(provider_override="lmstudio")
```

### Desde CLI
```bash
# Proveedor por defecto (el configurado en .env)
python skills/evaluar-llm/run.py

# Forzar proveedor
python skills/evaluar-llm/run.py lmstudio
python skills/evaluar-llm/run.py gemini
python skills/evaluar-llm/run.py openrouter
```

## Parámetros
| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| `provider_override` | str | No | Fuerza un proveedor: `lmstudio`, `openai`, `gemini`, `openrouter`, `claude` |
| `output_dir` | str | No | Carpeta donde guardar el reporte (default: raíz del proyecto) |

## Retorna
- Ruta al archivo `.md` generado con el reporte completo
- El reporte incluye: score por dimensión, respuestas completas, criterios aprobados/fallados y conclusiones

## Scoring
- **5.0** = Excelente
- **4.0-4.9** = Fuerte
- **2.5-3.9** = Aceptable
- **< 2.5** = Débil
- **⚠️ manual** = Criterio requiere revisión humana (no automatizable)

## Notas
- La evaluación es semi-automática: algunos criterios se verifican por texto/regex, otros requieren revisión manual
- Funciona con cualquier proveedor compatible con la API OpenAI (LM Studio, OpenAI, OpenRouter, Gemini, Claude via proxy)
- Cada ejecución genera un archivo nuevo con timestamp para comparar modelos en el tiempo
