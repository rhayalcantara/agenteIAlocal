import requests
from bs4 import BeautifulSoup

def scrape_diariolibre():
    url = "https://www.diariolibre.com/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        report_content = "# Reporte de Noticias - Diario Libre\n\n"
        news_found = 0

        # Buscamos contenedores comunes de noticias. 
        # En sitios de noticias, las noticias suelen estar en artículos o divs con clases específicas.
        # Intentaremos buscar h2 y h3 que contengan enlaces e imágenes asociadas.
        
        for tag in soup.find_all(['h2', 'h3']):
            link_tag = tag.find('a')
            if not link_tag or not link_tag.get('href'):
                continue
                
            link_url = link_tag['href']
            # Asegurar que la URL sea absoluta
            if link_url.startswith('/'):
                link_url = "https://www.diariolibre.com" + link_url
            
            title = link_tag.get_text(strip=True)
            
            # Buscar imagen en el mismo contenedor o niveles superiores cercanos
            image_url = None
            # Subimos al padre para buscar la imagen que suele estar en el mismo bloque
            parent = tag.find_parent(['div', 'article'])
            if parent:
                img_tag = parent.find('img')
                if img_tag and img_tag.get('src'):
                    image_url = img_tag['src']
                    if image_url.startswith('/'):
                        image_url = "https://www.diariolibre.com" + image_url

            if title and title != "":
                if image_url:
                    report_content += f"![{title}]({image_url})\n"
                report_content += f"[{title}]({link_url})\n\n"
                news_found += 1
            
            # Limitar a las primeras 20 noticias para el reporte
            if news_found >= 20:
                break

        if news_found == 0:
            report_content += "No se pudieron extraer noticias con el formato esperado."
            
        with open("reporte_diariolibre.md", "w", encoding="utf-8") as f:
            f.write(report_content)
            
        print(f"Éxito: Se encontraron {news_found} noticias.")
        return True

    except Exception as e:
        print(f"Error durante el scraping: {e}")
        return False

if __name__ == "__main__":
    scrape_diariolibre()
