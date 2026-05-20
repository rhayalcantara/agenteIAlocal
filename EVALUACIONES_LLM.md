# Evaluaciones LLM — Ranking de Modelos Locales

Evaluaciones realizadas el 2026-04-24 con la skill `evaluar-llm`.
5 dimensiones: Seguimiento de instrucciones, Entendimiento de conceptos,
Proactividad y razonamiento, Conclusion de temas, Compatibilidad con agente.

## Ranking Final

| # | Modelo | Score | Tiempo prom. | Compat. Agente | Mejor para |
|---|--------|-------|-------------|----------------|------------|
| **1** | **lfm2:latest** | **4.92/5** | **4.7s** | 4.67/5 | **Velocidad + calidad** |
| 2 | qwen3.6:latest | 4.75/5 | 22.6s | 4.0/5 | Thinking profundo |
| 3 | qwen/qwen3-next-80b | 4.58/5 | 7.3s | **5.0/5** | **Mejor para el agente** |
| 3 | google/gemma-4-26b-a4b | 4.58/5 | 16.1s | **5.0/5** | **Mejor para el agente** |
| 5 | qwen/qwen3-30b-a3b-2507 | 4.50/5 | 6.0s | 4.67/5 | Balance velocidad/calidad |
| 6 | google/gemma-4-31b | 4.44/5 | 121.0s | pendiente | Lento para uso practico |
| 7 | qwen3.5:122b | 3.89/5 | sin datos | sin datos | Muy grande, lento |
| 7 | qwen/qwen3.5-35b-a3b | 3.89/5 | sin datos | sin datos | Aceptable |

## Hallazgos Clave

### Problema del thinking mode (Qwen 3.5/3.6)
Los modelos con thinking mode (`<think>`) consumian todos los tokens en
razonamiento interno y retornaban respuestas vacias. Fix: subir max_tokens
de 512 a 2048. Con el fix, todos los modelos pasaron de ~1.0/5 a ~4.0+/5.

### Compatibilidad con agente (Dimension 5)
Pruebas extraidas del log real del agente. Evalua si el LLM:
- Usa nombres correctos de herramientas (no inventa `buscar-noticias`, `leer_archivo`)
- Pasa argumentos completos (no omite `path` en `edit_file`)
- Planifica secuencias multi-step correctamente (buscar -> crear HTML -> enviar)
- Genera queries de Gmail correctas (from:banco after:2026/04)
- No inventa herramientas que no existen

### Velocidad
- **lfm2**: 4.7s promedio — el mas rapido por lejos
- **qwen3-30b**: 6.0s — segundo mas rapido
- **qwen3-next-80b**: 7.3s — rapido para 80B
- **gemma-4-26b**: 16.1s — aceptable
- **qwen3.6**: 22.6s — lento por thinking
- **gemma-4-31b**: 121.0s — inutilizable para Telegram

## Recomendaciones

### Para el agente de Telegram (uso diario)
1. **lfm2:latest** — Mejor score, mas rapido, buena compatibilidad
2. **qwen/qwen3-30b-a3b-2507** — Buen balance, muy rapido
3. **qwen/qwen3-next-80b** — Compatibilidad perfecta con tools, rapido

### Para tareas complejas (analisis, razonamiento)
1. **qwen3.6:latest** — Thinking profundo, mejor razonamiento
2. **qwen3.5:122b** — Modelo grande con buena calidad

### NO recomendados
- **google/gemma-4-31b** — Calidad buena pero 2 minutos por respuesta
- Cualquier modelo con max_tokens < 2048 en modelos thinking

## Historial de Evaluaciones

| Fecha | Modelo | Score (antes fix) | Score (despues fix) |
|-------|--------|-------------------|---------------------|
| 2026-04-23 | qwen/qwen3.6-27b | 1.11/5 | no re-evaluado |
| 2026-04-23 | qwen/qwen3.6-35b-a3b | 1.11/5 | no re-evaluado |
| 2026-04-23 | qwen/qwen3.5-35b-a3b | 1.11/5 | 3.89/5 |
| 2026-04-23 | qwen3.6:latest | 1.67/5 | 4.75/5 |
| 2026-04-23 | qwen3.5:122b | 0.56/5 | 3.89/5 |
| 2026-04-23 | qwen/qwen3-30b-a3b-2507 | 4.44/5 | 4.50/5 |
| 2026-04-23 | qwen/qwen3-next-80b | 3.89/5 | 4.58/5 |
| 2026-04-24 | lfm2:latest | 5.0/5 | 4.92/5 (con dim 5) |
| 2026-04-24 | google/gemma-4-26b-a4b | 4.44/5 | 4.58/5 (con dim 5) |
| 2026-04-24 | google/gemma-4-31b | invalida | 4.44/5 |

## Archivos de Reportes Detallados

Los reportes completos con respuestas, criterios y tiempos por prueba
estan en la raiz del proyecto: `evaluacion_llm_lmstudio_YYYYMMDD_HHMM.md`
