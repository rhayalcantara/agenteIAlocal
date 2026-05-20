"""Skill: buscar-noticias — Scraper de Diario Libre."""
import requests
from bs4 import BeautifulSoup
import os
import sys

def scrape_diariolibre():
    url = "https://www.diariolibre.com/ultima-hora"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        articles = []
        for item in soup.find_all('article'):
            # Buscar titulo en h2 o h3
            title_tag = item.find(['h2', 'h3'])
            link_tag = item.find('a', href=True)
            img_tag = item.find('img', src=True)

            if title_tag and link_tag:
                title = title_tag.get_text(strip=True)
                if not title:
                    continue
                href = link_tag['href']
                # Construir URL completa si es relativa
                if href.startswith('/'):
                    href = "https://www.diariolibre.com" + href
                img_url = img_tag['src'] if img_tag else ""

                articles.append({
                    "title": title,
                    "link": href,
                    "image": img_url
                })

        if not articles:
            print("No se encontraron noticias.")
            return

        # Generar reporte Markdown
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        reporte_path = os.path.join(root, 'reporte_diariolibre.md')
        with open(reporte_path, 'w', encoding='utf-8') as f:
            f.write("# Noticias Recientes de Diario Libre\n\n")
            for article in articles[:10]:
                if article['image']:
                    f.write(f"![{article['title']}]({article['image']})\n")
                f.write(f"[{article['title']}]({article['link']})\n\n")

        # Output para el agente
        print(f"Reporte generado: {reporte_path}")
        print(f"Total: {len(articles[:10])} noticias")
        print()
        for i, a in enumerate(articles[:10], 1):
            print(f"{i}. {a['title']}")

    except Exception as e:
        print(f"Error al scrapear Diario Libre: {e}")

if __name__ == "__main__":
    scrape_diariolibre()
