"""Scraping básico de páginas web."""
import urllib.request
import urllib.error
from html.parser import HTMLParser
from logger import get_logger

logger = get_logger("web_scraper")


class _TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link"}

    def __init__(self):
        super().__init__()
        self._skip = 0
        self.text_parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag.lower() in self.SKIP_TAGS and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self.text_parts.append(text)


def scrape_url(url: str, max_chars: int = 5000) -> str:
    """Descarga y extrae el texto de una URL."""
    logger.info(f"Scraping: {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AgenteIA/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        parser = _TextExtractor()
        parser.feed(html)
        texto = " ".join(parser.text_parts)
        # Normalizar espacios
        import re
        texto = re.sub(r"\s+", " ", texto).strip()
        if len(texto) > max_chars:
            texto = texto[:max_chars] + "... [TRUNCADO]"
        logger.debug(f"Scraping OK: {len(texto)} chars de {url}")
        return texto
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return f"Error obteniendo página: {e}"
