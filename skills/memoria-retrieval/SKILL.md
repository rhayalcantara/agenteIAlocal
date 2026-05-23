# Skill: Memoria con Recuperación

Búsqueda semántica en el historial COMPLETO de la conversación, más allá de la ventana visible y de los mensajes que el compactador ya comprimió. Cada turno user/assistant queda indexado con un embedding multilingüe en una SQLite aparte (`agente_core/data/memoria_retrieval.db`); el LLM consulta vía la tool `buscar_memoria` cuando lo necesita.

## Cuándo usar

Usa `buscar_memoria` SIEMPRE que:

- El usuario referencia algo de hace tiempo: *"¿qué te dije sobre…?"*, *"¿recuerdas cuando hablamos de…?"*, *"el modelo de mi nevera"*, *"lo del médico"*.
- Necesitas un dato específico que probablemente ya fue compactado (el compactador resume tramos viejos cuando el historial supera 16 mensajes / 80k tokens).
- El usuario pregunta por una fecha, número, nombre propio, modelo, o decisión que no aparece en los últimos 6–10 turnos visibles.

NO la uses si:

- El dato está claramente en los últimos mensajes visibles (lectura directa).
- Es una pregunta general sin referencia al pasado ("¿cómo está el clima hoy?").
- Acabas de leer el mismo dato en este turno.

## Cómo se llama

```
buscar_memoria(query="modelo de mi nevera", k=5)
buscar_memoria(query="qué dije sobre el médico", k=8, dias_max=30)
buscar_memoria(query="cuándo decidimos lo de Ranger", rol="user", k=10)
```

**Parámetros:**

| nombre | tipo | descripción |
|---|---|---|
| `query` | string (requerido) | Pregunta o tema en lenguaje natural |
| `k` | number | Cuántos resultados (default 5, máx 20) |
| `rol` | "user" \| "assistant" | Filtrar por quién lo dijo (opcional) |
| `dias_max` | number | Limitar a últimos N días (opcional) |

**Retorna:** JSON con lista `[{id, rol, ts, texto, score}, ...]` ordenada por relevancia descendente. Un `score` >0.75 es alta confianza; 0.55-0.75 medio; <0.5 ya empieza a ser ruido.

## Comportamiento esperado

1. El LLM recibe la pregunta del usuario, ve que referencia algo viejo, llama `buscar_memoria`.
2. La tool devuelve los K fragmentos más similares semánticamente.
3. El LLM lee los textos, valida si responden la pregunta, y responde al usuario citándolos.
4. Si los scores son bajos (todos <0.5) o los textos no son relevantes, el LLM debería **decirlo honestamente** ("no encuentro nada de eso en lo que hemos hablado") en lugar de inventar.

## Convivencia con la memoria existente

El agente tiene **dos sistemas de memoria, complementarios**:

- **`memoria.py` / `memoria.json`** (existente, NO TOCAR): hechos estructurados con categorías (preferencia/proyecto/hecho/instrucción) + resúmenes. Se inyecta en el system prompt en cada turno. Para **datos curados** que vale la pena tener siempre presentes.
- **`memoria_retrieval_tool.py` (esto)**: índice semántico de TODOS los turnos en bruto. NO va en el system prompt. Se consulta **solo cuando hace falta**, vía la tool. Para **recuperar conversación literal** vieja.

No reemplazan, conviven.

## Operaciones de mantenimiento (CLI o desde Python)

```bash
# Stats del índice
python agente_core/memoria_retrieval_tool.py estado

# Limpiar todo
python agente_core/memoria_retrieval_tool.py limpiar

# Limpiar de antes de cierta fecha
python agente_core/memoria_retrieval_tool.py limpiar antes_de_ts=2026-01-01T00:00:00Z

# Probar una búsqueda manualmente
python agente_core/memoria_retrieval_tool.py buscar query="mi nevera" k=3
```

## Notas técnicas

- **Modelo:** `intfloat/multilingual-e5-small` (384 dim, ~120 MB, descarga única en `~/.cache/huggingface/hub/`). Multilingüe — todo el repo está en español. Configurable vía variable de entorno `MEMORIA_RETRIEVAL_MODEL`.
- **Prefijos del modelo:** `query:` / `passage:` aplicados internamente (críticos para calidad con e5).
- **Similitud:** cosine en numpy in-memory; basta hasta ~50k mensajes. Más allá, migrar a `sqlite-vec` o FAISS (Fase 1.5).
- **Ingestión:** después de cada turno user y assistant, el agente llama `ingestar` en un thread daemon — si falla, solo loggea, NO rompe el turno.
- **Persistencia:** `agente_core/data/memoria_retrieval.db` (SQLite + WAL). Ignorado por git (`*.db`).
- **Privacidad:** mensajes en plano, igual que `agente_core/logs/messages.json` actual. Borrar con `limpiar()` si hace falta.

## Fuera de alcance Fase 1

- Grafo de relaciones entre entidades.
- Refiner que reescriba skills/memoria viendo trayectorias (estilo Continual Harness, Karten et al. 2026).
- Tabla `bloques` para resúmenes rodantes (los resúmenes siguen en `memoria.json`).
- BM25 híbrido, reranking, GPU, multi-tenant estricto.
