# Fuente: Diario Libre

Notas sobre Diario Libre como fuente de la skill [buscar-noticias](../proyectos/buscar-noticias.md).

## Por qué Diario Libre

Es el medio dominicano con mayor cobertura general y HTML estable (los redactores publican con CMS, no SPA cliente). De los que se probaron en 2026-04, fue el único donde un scraper de 30 líneas con BeautifulSoup funcionó al primer intento.

## URL fuente

`https://www.diariolibre.com/ultima-hora` — feed cronológico inverso, sin paginar. Los 10–15 artículos más recientes están todos en la primera carga.

## Cobertura observada

El feed mezcla:
- **Política** y sucesos nacionales (peso fuerte).
- **Actualidad / reportajes** (suelen ser los titulares "blandos" — fundaciones, sociedad).
- **Salud** (cuando hay brotes, p.ej. leptospirosis).
- **Economía / empleo**.
- **Deportes** (sobre todo baloncesto NBA cuando es temporada, béisbol cuando aplica).

No hay sección de tecnología fuerte — para tecnología/IA, esta fuente no aporta. Si en el futuro hace falta, agregar otra skill (`buscar-noticias-tecno` o similar).

## Calidad de titulares

- **Buenos** para resumen: claros, autocontenidos, sin clickbait extremo.
- **Algunos** son títulos de sección genéricos (`/economia/empleo`) en lugar de URL del artículo — el agente cuando arma el resumen suele detectar esto y aclarar que es "sección de economía/empleo" en lugar de citar como noticia puntual.

## Imagen

Casi todos los artículos traen imagen en CDN propio:
```
https://resources.diariolibre.com/images/<año>/<mes>/<día>/<slug>.jpg
```
Algunas con `-focus-0-0-598-352` en el nombre = crops automáticos. Funcionan bien embebidas en Markdown y como attachment de Telegram.

## Frecuencia de actualización

Empíricamente: el feed rota ~5-8 titulares nuevos entre las 8 AM y las 8 PM. Eso justifica los [dos resúmenes diarios](../configuracion/agenda-noticias.md) — no se repite el contenido.

Fines de semana publican menos; el resumen del domingo nocturno suele tener overlap con el del sábado.

## Cuando algo se rompe

- **403 sistemático:** revisar el User-Agent (ver [Scraping de noticias](../conceptos/scraping-noticias.md)).
- **HTML cambió:** mismo doc, sección "Si el sitio cambia el HTML".
- **No carga el sitio:** ver si es caída del medio (visitar en navegador) o problema de red local antes de tocar la skill.

## Si Rhay quiere otra fuente

Opciones evaluadas mentalmente, no implementadas:
- **Listín Diario** (`listindiario.com`) — alternativa principal, HTML similar.
- **El Día** — menos cobertura digital.
- **CDN** (Cadena de Noticias) — tiene canal de YouTube, mejor para video que para texto.

Hoy NO hay urgencia de diversificar — Diario Libre cubre lo que Rhay quiere recibir en el resumen. Si esa necesidad cambia, se evalúa.

## Relacionado

- [buscar-noticias (skill)](../proyectos/buscar-noticias.md)
- [Scraping de noticias](../conceptos/scraping-noticias.md)
- [Agenda de noticias](../configuracion/agenda-noticias.md)
