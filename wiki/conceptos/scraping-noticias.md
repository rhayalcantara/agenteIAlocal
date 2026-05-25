# Concepto: scraping de noticias

Cómo está implementado el scraping en [buscar-noticias](../proyectos/buscar-noticias.md), por qué se decidió así, y dónde tocar cuando Diario Libre cambie su HTML.

## Stack

- **`requests`** — GET único, `timeout=15s`, sin sesión persistente.
- **`beautifulsoup4`** — parser `html.parser` (stdlib, no necesita lxml).
- **stdlib `os` / `sys`** — paths y exit codes.

## User-Agent obligatorio

Diario Libre responde **403** sin User-Agent reconocible. Se usa uno de Chrome estable:

```python
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
"(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
```

Si en el futuro 403 vuelve a aparecer aunque el header esté: probablemente bloquearon esa versión específica — actualizar el número de Chrome basta.

## Estructura que asume del HTML

El parser asume que cada noticia es un `<article>` con:
- Un `<h2>` o `<h3>` con el título dentro.
- Un `<a href>` con el enlace (el primero del article).
- Opcionalmente un `<img src>` con la imagen.

```python
for item in soup.find_all('article'):
    title_tag = item.find(['h2', 'h3'])
    link_tag  = item.find('a', href=True)
    img_tag   = item.find('img', src=True)
```

URLs relativas se prefijan con `https://www.diariolibre.com`. Si el `<h2>/<h3>` viene vacío, ese artículo se descarta sin contar (no rompe la corrida).

## Top 10

Después del parseo se hace `articles[:10]` — orden = el orden del sitio (más reciente arriba). El agente luego elige los 3 principales al armar el resumen de Telegram, así que tomar 10 sirve también como "colchón" por si los primeros no dan información suficiente.

## Output

**Markdown plano** en `reporte_diariolibre.md`. Cada noticia es 2 líneas:
```markdown
![titulo](url-imagen)
[titulo](url-articulo)
```

Más una línea en blanco entre noticias. Esto es deliberadamente simple: el agente vuelve a leer el archivo y arma su propio mensaje — el reporte es un **buffer intermedio**, no el producto final.

A stdout se imprime el conteo + los 10 títulos numerados para que el agente los pueda referenciar sin tener que volver a leer el archivo.

## Si el sitio cambia el HTML

Síntomas: `"No se encontraron noticias."` en stdout, o `reporte_diariolibre.md` se queda vacío / con menos de 10.

Pasos para reparar:
1. `curl -A "Mozilla/5.0 ..." https://www.diariolibre.com/ultima-hora > tmp.html` y abrir.
2. Buscar qué etiqueta envuelve cada noticia (puede que ya no sea `<article>` — los sitios a veces migran a `<div class="...">` con data-attrs).
3. Ajustar el `soup.find_all(...)` y los selectores internos.

Cambio mínimo: si solo cambió el nombre del tag (p.ej. `<article>` → `<div class="card-noticia">`), una sola línea basta.

## Por qué no Selenium / Playwright

- El sitio renderiza el HTML server-side; no hace falta JS.
- `requests` arranca en ~50ms vs ~3-5s de un browser headless.
- El cron corre 2 veces al día — overhead acumulado importa.

Si en algún momento Diario Libre migra a SPA (Next.js cliente puro), tocará reabrir esta decisión.

## Extender a otra fuente

Patrón sugerido (NO implementado aún):
- Carpeta `skills/buscar-noticias-listin/` con su propio `run.py`.
- O bien generalizar a `skills/buscar-noticias/` con un argumento `--fuente {diariolibre,listin,...}` y un diccionario de selectores por fuente.

Decisión actual: **una skill por fuente**. Cuando aparezca la segunda fuente se evalúa si vale generalizar.

## Relacionado

- [buscar-noticias (skill)](../proyectos/buscar-noticias.md)
- [Diario Libre (fuente)](../noticias/diariolibre.md)
