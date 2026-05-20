"""Captura screenshots de OperacionesRanger via Playwright para la demo."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright


OUT_DIR = Path(__file__).parent / "demo_screenshots"
OUT_DIR.mkdir(exist_ok=True)
BASE = "http://localhost:4201"


async def capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        # 1. Login screen
        print("→ login screen")
        await page.goto(f"{BASE}/login", wait_until="networkidle")
        await page.wait_for_timeout(800)
        await page.screenshot(path=str(OUT_DIR / "01_login.png"), full_page=False)

        # 2. Login with credentials
        await page.fill('input[name="username"], input[formcontrolname="username"]', "admin")
        await page.fill('input[name="password"], input[formcontrolname="password"]', "admin123")
        await page.wait_for_timeout(400)
        await page.screenshot(path=str(OUT_DIR / "02_login_filled.png"), full_page=False)

        # Submit login
        print("→ submitting login")
        await page.click('button[type="submit"]')
        await page.wait_for_url("**/dashboard*", timeout=15000)
        await page.wait_for_timeout(2500)  # dejar que carguen cards
        await page.screenshot(path=str(OUT_DIR / "03_dashboard.png"), full_page=False)

        # 3. Turnos
        print("→ turnos")
        await page.goto(f"{BASE}/turnos", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT_DIR / "04_turnos.png"), full_page=False)

        # 4. Feriados
        print("→ feriados")
        await page.goto(f"{BASE}/feriados", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT_DIR / "05_feriados.png"), full_page=False)

        # 5. Puestos
        print("→ puestos")
        await page.goto(f"{BASE}/puestos", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT_DIR / "06_puestos.png"), full_page=False)

        # 6. Incentivos
        print("→ incentivos")
        await page.goto(f"{BASE}/incentivos", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT_DIR / "07_incentivos.png"), full_page=False)

        # 7. Reportes
        print("→ reportes")
        await page.goto(f"{BASE}/reportes", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT_DIR / "08_reportes.png"), full_page=False)

        # 8. Cronogramas
        print("→ cronogramas")
        await page.goto(f"{BASE}/cronogramas", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT_DIR / "09_cronogramas.png"), full_page=False)

        # 9. Clientes
        print("→ clientes")
        await page.goto(f"{BASE}/clientes", wait_until="networkidle")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=str(OUT_DIR / "10_clientes.png"), full_page=False)

        await browser.close()
    print("Done. Output dir:", OUT_DIR)


if __name__ == "__main__":
    asyncio.run(capture())
