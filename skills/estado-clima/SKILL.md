# Skill: estado-clima

Esta skill permite obtener un resumen actualizado del pronóstico meteorológico en la República Dominicana, extrayendo información directamente de los boletines oficiales de la ONAMET.

## Uso

Para usar esta skill, simplemente solicita el estado del clima o el pronóstico meteorológico actual.

**Ejemplos:**
- "dime cómo estará el clima hoy"
- "ejecuta estado-clima para saber si va a llover"
- "¿qué dice la ONAMET sobre el tiempo en Santo Domingo?"

## Funcionamiento Interno

1. **Búsqueda:** La skill realiza una búsqueda en internet (vía DuckDuckGo) enfocada en el sitio oficial de la ONAMET o noticias meteorológicas recientes de la República Dominicana.
2. **Extracción:** Analiza el contenido del boletín más reciente para identificar:
    - Estado general del tiempo (vaguadas, tormentas, etc.).
    - Pronóstico detallado por regiones o provincias.
    - Temperaturas máximas y mínimas esperadas.
3. **Síntesis:** Estructura la información en un formato legible y organizado (usando tablas y emojis) para que el usuario reciba una respuesta clara y rápida.

## Notas
Esta skill es ideal para planificación de actividades al aire libre, viajes o precaución ante fenómenos naturales como tormentas o granizadas.