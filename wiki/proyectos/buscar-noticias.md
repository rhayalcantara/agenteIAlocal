# Skill: buscar-noticias

Skill de scraping que extrae los titulares más recientes de **Diario Libre** y genera un reporte en Markdown que el agente luego empaqueta y manda por Telegram.

## Ubicación

- **Código:** `skills/buscar-noticias/run.py`
- **Descriptor:** `skills/buscar-noticias/SKILL.md`
- **Salida:** `reporte_diariolibre.md` en la raíz del proyecto (se sobreescribe cada corrida).

## Qué hace, exactamente

1. GET a `https://www.diariolibre.com/ultima-hora` con un `User-Agent` de Chrome (sin él, el sitio responde 403).
2. Parsea el HTML con BeautifulSoup, busca todos los `<article>` y extrae de cada uno:
   - Título (`<h2>` o `<h3>`)
   - Enlace (`<a href>`, prefijando dominio si es ruta relativa)
   - Imagen (`<img src>`, si existe)
3. Toma los **10 primeros artículos** (cualquier extra se descarta) y los vuelca a `reporte_diariolibre.md` con formato:
   ```markdown
   ![titulo](url-imagen)
   [titulo](url-articulo)
   ```
4. Imprime a stdout el conteo + los 10 títulos para que el agente los lea.

## Cómo se invoca

**Manualmente (debug):**
```powershell
venv\Scripts\python.exe skills\buscar-noticias\run.py
```

**Desde el agente (lenguaje natural):**
- "Busca noticias"
- "Qué hay de nuevo"
- "Noticias de hoy"

El agente ejecuta el skill vía `ejecutar_script_skill('buscar-noticias', 'run.py', '')` y después lee `reporte_diariolibre.md` para generar el resumen final que envía por Telegram (con los 3 titulares principales + imágenes adjuntas).

## Cuándo se ejecuta sola

Hay **dos acciones de agenda diarias** que la disparan sin que Rhay pida nada — ver [Agenda de noticias](../configuracion/agenda-noticias.md):
- **08:00** — Resumen matutino.
- **20:00** — Resumen nocturno.

## Decisiones / lo que NO hace

- **No usa Gmail/SMTP.** El reparto es Telegram puro (lo decide la acción de agenda, no la skill).
- **No persiste histórico.** `reporte_diariolibre.md` es de un solo uso: se sobreescribe cada corrida. Si hace falta histórico, se mete a [[memoria-retrieval]] cuando el LLM lo decida.
- **No filtra por sección/categoría.** Toma los 10 que aparezcan en `ultima-hora`, en el orden del sitio.
- **No reintenta.** Si Diario Libre devuelve error o el HTML cambia, la skill imprime `"Error al scrapear..."` y el agente lo ve como output.

## Relacionado

- [Scraping de noticias](../conceptos/scraping-noticias.md) — detalle técnico del parser.
- [Agenda de noticias](../configuracion/agenda-noticias.md) — cómo y cuándo corre sola.
- [Diario Libre (fuente)](../noticias/diariolibre.md) — notas sobre la fuente.
