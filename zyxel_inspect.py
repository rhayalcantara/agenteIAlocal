"""Login al Zyxel VMG1312-T20B y extracción de la WAN IP.

Uso:
    python zyxel_inspect.py [--user USER] [--password PASS] [--headed]
"""
import argparse
import re
import sys
from playwright.sync_api import sync_playwright

ROUTER_URL = "http://10.0.0.1/"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", default="r00t")
    ap.add_argument("--password", default="99907549")
    ap.add_argument("--headed", action="store_true", help="ver el navegador")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()

        page.on("request", lambda r: print(f"  >> {r.method} {r.url}", flush=True))
        page.on("response", lambda r: print(f"  << {r.status} {r.url}", flush=True))
        page.on("console", lambda m: print(f"  [console.{m.type}] {m.text}", flush=True))
        page.on("pageerror", lambda e: print(f"  [pageerror] {e}", flush=True))

        print(f"[1] GET {ROUTER_URL}", flush=True)
        page.goto(ROUTER_URL, wait_until="networkidle", timeout=30000)
        page.screenshot(path="zyxel_01_login.png")

        # El login JS detecta inputs con id típicos: Username, Password.
        # Intentamos varios selectores comunes en firmware Zyxel.
        candidates_user = ["#username", "input[name='zy-name']", "#Username",
                           "input[name=Username]", "input[name=username]"]
        candidates_pass = ["#userpassword", "input[name='zy-password']", "#Password",
                           "input[name=Password]", "input[name=password]",
                           "input[type=password]"]
        candidates_btn = ["#loginBtn", "input[type=submit][value=Login]",
                          "button[type=submit]", "input[type=submit]"]

        def first_visible(sels):
            for s in sels:
                try:
                    el = page.query_selector(s)
                    if el and el.is_visible():
                        return s
                except Exception:
                    pass
            return None

        u_sel = first_visible(candidates_user)
        p_sel = first_visible(candidates_pass)
        b_sel = first_visible(candidates_btn)
        print(f"[2] selectores: user={u_sel} pass={p_sel} btn={b_sel}", flush=True)

        if not (u_sel and p_sel):
            print("[!] no encontré los inputs de login. HTML guardado.", flush=True)
            with open("zyxel_login_dump.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            browser.close()
            return 2

        page.fill(u_sel, args.user)
        page.fill(p_sel, args.password)
        page.screenshot(path="zyxel_02_filled.png")

        print("[2.5] disparando submit...", flush=True)
        if b_sel:
            page.click(b_sel)
        else:
            page.press(p_sel, "Enter")

        try:
            page.wait_for_load_state("networkidle", timeout=25000)
        except Exception as e:
            print(f"  wait_for_load_state timeout: {e}", flush=True)
        page.wait_for_timeout(3000)  # extra para JS
        print(f"[2.6] URL actual: {page.url}", flush=True)
        page.screenshot(path="zyxel_03_post_login.png")

        # Buscar links/menús que mencionen WAN
        body_text = page.content()
        with open("zyxel_post_login.html", "w", encoding="utf-8") as f:
            f.write(body_text)

        # Heurística: extraer todas las IPs visibles en el dashboard
        ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", body_text)
        ips = [ip for ip in ips if ip not in ("10.0.0.1", "10.0.0.240",
                                                "192.168.1.1", "0.0.0.0",
                                                "255.255.255.0", "127.0.0.1")]
        print(f"[3] IPs encontradas en página post-login: {sorted(set(ips))[:15]}", flush=True)

        # Intentar navegar a Status / WAN
        for link_text in ["Status", "WAN", "System Information", "Network Setting", "Broadband"]:
            try:
                link = page.get_by_text(link_text, exact=False).first
                if link:
                    link.click(timeout=3000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                    print(f"[4] click en '{link_text}' OK", flush=True)
                    page.screenshot(path=f"zyxel_04_{link_text.replace(' ','_')}.png")
                    txt = page.content()
                    ips2 = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", txt)
                    ips2 = [ip for ip in ips2 if ip not in ("10.0.0.1", "10.0.0.240",
                                                              "192.168.1.1", "0.0.0.0",
                                                              "255.255.255.0", "127.0.0.1")]
                    print(f"    IPs en '{link_text}': {sorted(set(ips2))[:15]}", flush=True)
                    break
            except Exception as e:
                pass

        browser.close()
        return 0


if __name__ == "__main__":
    sys.exit(main())
