# scraper-general

Usa selenium o playwright para acceder a páginas web que requieren JavaScript y extraer precios.

## Instrucciones
1. Identifica la URL de la página web a hacer scraping
2. Usa selenium o playwright para renderizar el JavaScript
3. Navega a la página y espera a que cargue
4. Usa las herramientas de browser para interactuar con la página:
   - browser_navegar para navegar a URLs
   - browser_screenshot para tomar screenshots
   - browser_click para hacer clic en elementos
   - browser_escribir para escribir en inputs
   - browser_obtener_texto para extraer el texto del DOM
   - browser_ejecutar_js para ejecutar JavaScript
5. Identifica los productos y precios en el DOM
6. Presenta los resultados de forma estructurada