"""Graba video MP4 del demo HTML — auto-start sin veil, 41s exactos."""
import asyncio, sys, shutil
from pathlib import Path
from playwright.async_api import async_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).parent
DEMO_FILE = HERE / "DEMO_OPERACIONES_RANGER_v3.html"
OUT_DIR = HERE / "demo_video_tmp"
# limpiar prev
if OUT_DIR.exists():
    shutil.rmtree(OUT_DIR)
OUT_DIR.mkdir()


async def record():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--autoplay-policy=no-user-gesture-required", "--mute-audio=false"],
        )
        ctx = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(OUT_DIR),
            record_video_size={"width": 1440, "height": 900},
        )
        page = await ctx.new_page()

        # Inyectar script ANTES de cargar: arranca el demo automaticamente
        await page.add_init_script("""
            window.__autoStart = true;
            document.addEventListener('DOMContentLoaded', () => {
                // Hide veil, set startMs, add playing class
                const veil = document.getElementById('playVeil');
                if (veil) veil.classList.add('hidden');
                const stage = document.getElementById('stage');
                if (stage) stage.classList.add('playing');
                window.__demoStartMs = Date.now();
            });
        """)

        url = DEMO_FILE.as_uri()
        print(f"Goto {url}")
        await page.goto(url, wait_until="load")
        # Pequena espera para que CSS animations arranquen
        await page.wait_for_timeout(200)
        # Reset timing in JS y arrancar audio
        await page.evaluate("""
            (async () => {
                const audio = document.getElementById('narration');
                const stage = document.getElementById('stage');
                stage.classList.remove('playing');
                // force reflow
                void stage.offsetWidth;
                stage.classList.add('playing');
                window.startMs = Date.now();
                try { await audio.play(); } catch(e) { console.warn(e); }
            })();
        """)
        # Grabar exacto 41 segundos
        await page.wait_for_timeout(41000)
        print("Done")

        await ctx.close()
        await browser.close()

    videos = list(OUT_DIR.glob("*.webm"))
    if not videos:
        print("ERROR: no video")
        return
    src = videos[0]
    dest = HERE / "DEMO_OPERACIONES_RANGER_v3.webm"
    if dest.exists():
        dest.unlink()
    shutil.move(str(src), str(dest))
    print(f"Saved: {dest} -> {dest.stat().st_size // 1024} KB")


if __name__ == "__main__":
    asyncio.run(record())
