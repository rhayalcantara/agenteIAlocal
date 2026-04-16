# Skill: Buscar Noticias (Diario Libre)

Esta skill permite extraer automáticamente los titulares más recientes y sus imágenes del sitio web Diario Libre, generando un reporte en formato Markdown.

## Uso
Para usar la skill, simplemente pide algo como:
- "Busca noticias de Diario Libre"
- "Ejecuta el scraper de noticias"

## Lo que hace
1. Ejecuta el script `diariolibre_scraper.py`.
2. Realiza un scraping profesional usando BeautifulSoup4 y Requests.
3. Identifica los contenedores de noticias, extrayendo títulos (`h2`, `h3`), enlaces y la imagen asociada.
4. Genera un archivo llamado `reporte_diariolibre.md` con formato Markdown compatible.
5. El resultado final es un reporte visual listo para ser compartido o leído.

## Formato de salida
El archivo generado contiene:
![Imagen](url)
[Título](url_noticia)
