import requests
from bs4 import BeautifulSoup

url = "https://indomet.gob.do/pronostico/informes-marino/informe-del-tiempo/"

def scrape_indomet(target_url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(target_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Intentar extraer contenido relevante (títulos, párrafos, tablas)
        content = []
        
        # Buscamos elementos comunes de informes
        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'td']):
            text = tag.get_text().strip()
            if text:
                content.append(f"[{tag.name}] {text}")
        
        return "\n".join(content)

    except Exception as e:
        return f"Error al acceder a la URL: {str(e)}"

if __name__ == "__main__":
    result = scrape_indomet(url)
    print(result)
