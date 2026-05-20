"""Configurar port forwarding 8081 -> 10.0.0.240:8081 en Zyxel VMG1312-T20B."""
import sys
import time
from playwright.sync_api import sync_playwright

ROUTER_URL = "http://10.0.0.1/"
LOGIN_TITLE = ".::Welcome to the Web-Based Configurator::."

EXT_PORT = 8081
INT_PORT = 8081
LAN_IP = "10.0.0.240"
RULE_NAME = "Test8081"


def wait_for_login(page, max_seconds=300):
    deadline = time.time() + max_seconds
    while time.time() < deadline:
        try:
            t = page.title()
            if t and LOGIN_TITLE not in t and "Welcome" not in t:
                return True
            if not page.locator("#userpassword").count():
                html = page.content()
                if "userpassword" not in html and "loginPage" not in html:
                    return True
        except Exception:
            pass
        time.sleep(2)
    return False


def close_quickstart(page):
    """Cerrar el wizard 'Quick Start' si aparece."""
    for sel in [
        "input[type=button][value=Close]",
        "button:has-text('Close')",
        "img.modal_close",
        "div.x_close",
        "[onclick*='QuickStart']",
    ]:
        try:
            el = page.locator(sel).first
            if el.count() and el.is_visible(timeout=300):
                el.click(timeout=2000)
                time.sleep(1)
                print(f"  Cerrado quickstart con {sel}", flush=True)
                return True
        except Exception:
            pass
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        ctx = browser.new_context(viewport=None, ignore_https_errors=True)
        page = ctx.new_page()

        page.goto(ROUTER_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        print("[1] Haz login en la ventana...", flush=True)
        if not wait_for_login(page):
            print("[!] timeout login", flush=True)
            browser.close()
            return 1

        print("[2] Logged in", flush=True)
        time.sleep(3)
        close_quickstart(page)
        time.sleep(1)
        page.screenshot(path="pf_01_dashboard.png", full_page=True)

        # Navegar a Network Setting -> NAT -> Port Forwarding
        # En Zyxel VMG1312, la URL típica es /cgi-bin/index.html#... pero es JS-driven
        print("[3] Buscando menú Network Setting", flush=True)
        try:
            page.get_by_text("Network Setting", exact=True).first.hover(timeout=5000)
            time.sleep(1)
            page.screenshot(path="pf_02_menu_hover.png", full_page=True)
        except Exception as e:
            print(f"   Network Setting hover: {e}", flush=True)

        # Probamos URLs directas comunes en este firmware
        candidate_paths = [
            "/cgi-bin/Itf_Group_Mng?oid=PortForwarding",
            "/cgi-bin/index.html?oid=PortForwarding",
            "/?oid=PortForwarding",
            "/PortForwarding.html",
        ]
        for path in candidate_paths:
            try:
                resp = ctx.request.get(f"http://10.0.0.1{path}", timeout=8000)
                print(f"   {path} -> {resp.status} len={len(resp.text())}", flush=True)
            except Exception as e:
                print(f"   {path} -> ERR {e}", flush=True)

        # Click en NAT submenu
        for label in ["NAT", "Port Forwarding", "Forwarding"]:
            try:
                el = page.get_by_text(label, exact=True).first
                if el.count():
                    el.scroll_into_view_if_needed(timeout=2000)
                    el.click(timeout=3000)
                    time.sleep(2)
                    print(f"   click '{label}' OK", flush=True)
                    page.screenshot(path=f"pf_03_{label.replace(' ','_')}.png",
                                    full_page=True)
            except Exception as e:
                print(f"   '{label}': {e}", flush=True)

        time.sleep(3)
        page.screenshot(path="pf_99_final.png", full_page=True)
        with open("pf_final.html", "w", encoding="utf-8") as f:
            f.write(page.content())

        print("[4] Navegador queda abierto 240s — termina manualmente",
              flush=True)
        time.sleep(240)
        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
