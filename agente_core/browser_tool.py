"""
Herramientas de browser para el agente IA usando Playwright.

Funciones disponibles:
- browser_navegar       → abre una URL y devuelve el texto de la página
- browser_screenshot    → toma screenshot y devuelve la ruta del archivo
- browser_click         → hace clic en un elemento por texto o selector
- browser_escribir      → escribe texto en un campo
- browser_obtener_texto → devuelve el texto visible de la página actual
- browser_ejecutar_js   → ejecuta JavaScript en la página
"""
import os
import tempfile
from logger import get_logger

logger = get_logger("browser_tool")

# Instancia global para reutilizar el browser entre llamadas
_playwright = None
_browser = None
_page = None


def _obtener_pagina():
    """Devuelve la página activa, iniciando el browser si es necesario."""
    global _playwright, _browser, _page
    try:
        from playwright.sync_api import sync_playwright
        if _playwright is None:
            _playwright = sync_playwright().start()
            _browser = _playwright.chromium.launch(headless=True)
            _page = _browser.new_page()
            logger.info("Browser Playwright iniciado (headless Chromium)")
        elif _page is None or _page.is_closed():
            _page = _browser.new_page()
        return _page
    except Exception as e:
        logger.error(f"Error iniciando browser: {e}")
        raise


def browser_navegar(url: str, esperar: str = "domcontentloaded", timeout: int = 15000, **kwargs) -> str:
    """Navega a una URL y devuelve el texto visible de la página."""
    try:
        page = _obtener_pagina()
        logger.info(f"Navegando a: {url}")
        page.goto(url, wait_until=esperar, timeout=timeout)
        titulo = page.title()
        texto = page.inner_text("body")
        texto = " ".join(texto.split())  # normalizar espacios
        if len(texto) > 6000:
            texto = texto[:6000] + "\n... [TRUNCADO]"
        return f"[{titulo}]\nURL: {url}\n\n{texto}"
    except Exception as e:
        logger.error(f"browser_navegar error: {e}")
        return f"Error navegando a {url}: {e}"


def browser_screenshot(nombre: str = None, **kwargs) -> str:
    """Toma un screenshot de la página actual. Devuelve la ruta del archivo."""
    try:
        page = _obtener_pagina()
        if nombre:
            ruta = os.path.join(tempfile.gettempdir(), f"{nombre}.png")
        else:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            ruta = tmp.name
            tmp.close()
        page.screenshot(path=ruta, full_page=True)
        logger.info(f"Screenshot guardado: {ruta}")
        return ruta
    except Exception as e:
        logger.error(f"browser_screenshot error: {e}")
        return f"Error tomando screenshot: {e}"


def browser_click(selector: str, **kwargs) -> str:
    """Hace clic en un elemento. Acepta selector CSS, texto visible o aria-label."""
    try:
        page = _obtener_pagina()
        # Intentar por texto primero, luego por selector CSS
        try:
            page.get_by_text(selector, exact=False).first.click(timeout=5000)
        except Exception:
            page.click(selector, timeout=5000)
        logger.info(f"Click en: {selector}")
        page.wait_for_load_state("domcontentloaded", timeout=5000)
        return f"Click realizado en '{selector}'. URL actual: {page.url}"
    except Exception as e:
        logger.error(f"browser_click error: {e}")
        return f"Error haciendo click en '{selector}': {e}"


def browser_escribir(selector: str, texto: str, **kwargs) -> str:
    """Escribe texto en un campo de formulario."""
    try:
        page = _obtener_pagina()
        page.fill(selector, texto, timeout=5000)
        logger.info(f"Texto escrito en '{selector}': {texto[:40]}")
        return f"Texto '{texto[:40]}' escrito en '{selector}'"
    except Exception as e:
        logger.error(f"browser_escribir error: {e}")
        return f"Error escribiendo en '{selector}': {e}"


def browser_obtener_texto(selector: str = "body", **kwargs) -> str:
    """Devuelve el texto visible del elemento indicado (por defecto toda la página)."""
    try:
        page = _obtener_pagina()
        texto = page.inner_text(selector)
        texto = " ".join(texto.split())
        if len(texto) > 6000:
            texto = texto[:6000] + "\n... [TRUNCADO]"
        return texto
    except Exception as e:
        return f"Error obteniendo texto de '{selector}': {e}"


def browser_ejecutar_js(script: str, **kwargs) -> str:
    """Ejecuta JavaScript en la página actual y devuelve el resultado."""
    try:
        page = _obtener_pagina()
        resultado = page.evaluate(script)
        logger.info(f"JS ejecutado: {script[:60]}")
        return str(resultado)[:3000]
    except Exception as e:
        return f"Error ejecutando JS: {e}"


def browser_cerrar():
    """Cierra el browser y libera recursos."""
    global _playwright, _browser, _page
    try:
        if _page and not _page.is_closed():
            _page.close()
        if _browser:
            _browser.close()
        if _playwright:
            _playwright.stop()
        _playwright = _browser = _page = None
        logger.info("Browser cerrado.")
    except Exception as e:
        logger.warning(f"Error cerrando browser: {e}")
