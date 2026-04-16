import requests
from bs4 import BeautifulSoup
import re

def investigar_ofac():
    url = "https://sanctionslist.ofac.treas.gov/Home/ConsolidatedList"
    print(f"Investigando en: {url}")
    try:
        response = requests
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Buscamos patrones comunes de descarga (xml, zip, csv)
            if any(ext in href.lower() for ext in ['.xml', '.zip', '.csv']):
                links.append(href if href.startswith('http') else f"https://sanctionslist.ofac.treas.gov{href}")
        
        print(f"Se encontraron {len(links)} enlaces potenciales de descarga:")
        for link in links:
            print(f"- {link}")
            
    except Exception as e:
        print(f"Error durante la investigación: {e}")

if __name__ == "__main__":
    investigar_ofac()
