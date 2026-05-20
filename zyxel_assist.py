"""Asistido v2: navegador headed, usuario hace login, script extrae info.

Heurística de detección de login:
  El title del dashboard cambia de '.::Welcome to the Web-Based Configurator::.'
  a otro (Connection Status, etc). Eso es lo único confiable en este firmware.
"""
import re
import sys
import time
from playwright.sync_api import sync_playwright

ROUTER_URL = "http://10.0.0.1/"
LOGIN_TITLE = ".::Welcome to the Web-Based Configurator::."

PRIVATE_PREFIXES = ("10.", "192.168.", "172.16.", "172.17.", "172.18.",
                     "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
                     "172.24.", "172.25.", "172.26.", "172.27.", "172.28.",
                     "172.29.", "172.30.", "172.31.",
                     "127.", "255.", "0.0.0.0", "169.254.")


def collect_ips(html: str) -> list[str]:
    found = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", html)
    out = []
    for ip in found:
        if any(ip.startswith(p) for p in PRIVATE_PREFIXES):
            continue
        if ip in out:
            continue
        out.append(ip)
    return out


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = browser.new_context(viewport=None, ignore_https_errors=True)
        page = ctx.new_page()

        print(f"[1] Abriendo {ROUTER_URL}", flush=True)
        try:
            page.goto(ROUTER_URL, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"  goto warning (ignorado): {e}", flush=True)
        time.sleep(3)

        deadline = time.time() + 300
        print("[2] Esperando que el usuario ingrese clave y entre... (5 min máx)",
              flush=True)
        last_title = ""
        while time.time() < deadline:
            try:
                t = page.title()
                if t != last_title:
                    print(f"  title: {t!r}", flush=True)
                    last_title = t
                if t and LOGIN_TITLE not in t and "Welcome" not in t:
                    print(f"[3] Login detectado por título: {t!r}", flush=True)
                    break
                # Backup: si el HTML ya no contiene #userpassword, también
                if not page.locator("#userpassword").count():
                    html = page.content()
                    if "userpassword" not in html and "loginPage" not in html:
                        print("[3] Login detectado por DOM", flush=True)
                        break
            except Exception:
                pass
            time.sleep(2)
        else:
            print("[!] timeout sin detectar login", flush=True)
            browser.close()
            return 1

        time.sleep(3)
        page.screenshot(path="zyxel_dash.png", full_page=True)
        with open("zyxel_dash.html", "w", encoding="utf-8") as f:
            f.write(page.content())
        ips = collect_ips(page.content())
        print(f"[4] IPs públicas en dashboard: {ips}", flush=True)
        print(f"   URL actual: {page.url}", flush=True)
        print(f"   Title: {page.title()!r}", flush=True)

        # Probar URLs comunes de status en Zyxel firmware viejo
        common_paths = [
            "/cgi-bin/DAL?oid=cardpage_status",
            "/cgi-bin/DAL?oid=device_info",
            "/cgi-bin/DAL?oid=ip_interface",
            "/index.html",
            "/cardpage_status.html",
            "/StatusInfo.html",
            "/Connection_Status.html",
        ]
        for path in common_paths:
            try:
                url = f"http://10.0.0.1{path}"
                resp = ctx.request.get(url, timeout=8000)
                body = resp.text() if resp.ok else ""
                if body:
                    found = collect_ips(body)
                    print(f"[5] {path} ({resp.status}) ips={found}", flush=True)
                    if found:
                        with open(f"zyxel_data_{path.replace('/', '_').replace('?', '_').replace('=','-')}.txt",
                                  "w", encoding="utf-8") as f:
                            f.write(body)
            except Exception as e:
                print(f"   {path}: ERR {e}", flush=True)

        # Click en menús del dashboard
        for name in ["Connection Status", "System Information", "WAN Status",
                      "Broadband", "WAN", "Status"]:
            try:
                el = page.get_by_text(name, exact=True).first
                if el.count():
                    el.click(timeout=3000)
                    time.sleep(3)
                    safe = name.replace(" ", "_")
                    page.screenshot(path=f"zyxel_{safe}.png", full_page=True)
                    txt = page.content()
                    found = collect_ips(txt)
                    print(f"[6] click '{name}' -> ips={found}", flush=True)
                    if found:
                        with open(f"zyxel_{safe}.html", "w", encoding="utf-8") as f:
                            f.write(txt)
            except Exception as e:
                print(f"   '{name}': {e}", flush=True)

        print("[7] Listo. El navegador queda abierto 90s para que veas.",
              flush=True)
        time.sleep(90)
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
