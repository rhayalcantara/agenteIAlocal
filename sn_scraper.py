import requests
import re
import json
from html.parser import HTMLParser

print("🔍 Analizando supermercado nacional...")

url = 'https://supermercadosnacional.com/ofertas'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

r = requests.get(url, headers=headers, timeout=15)
html = r.text
print(f"✅ Status: {r.status_code}, Tamaño: {len(html)} chars, URL final: {r.url}")

# 1. Buscar window.__INITIAL_STATE__ o window.__NUXT__ o window.__DATA__
print("\n📊 Buscando datos embebidos (window.__STATE__, window.__DATA__, etc)...")
state_patterns = [
    r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});',
    r'window\.__NUXT__\s*=\s*(\{.+?\});',
    r'window\.__DATA__\s*=\s*(\{.+?\});',
    r'window\.state\s*=\s*(\{.+?\});',
]
for i, pattern in enumerate(state_patterns):
    matches = re.findall(pattern, html, re.IGNORECASE | re.DOTALL)
    if matches:
        print(f"   ✅ Encontrado con patrón {i}: {len(matches[0])} chars")
        print(f"   Preview: {matches[0][:200]}...")
        # Try to parse
        try:
            parsed = json.loads(matches[0])
            print(f"   ✅ JSON válido! Keys: {list(parsed.keys())}")
        except:
            print(f"   ❌ No es JSON válido")

# 2. Buscar script tags con type="application/json"
print("\n📊 Buscando scripts JSON embebidos...")
json_scripts = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
for i, js in enumerate(json_scripts):
    try:
        data = json.loads(js)
        print(f"   ✅ Script JSON #{i}: keys = {list(data.keys()) if isinstance(data, dict) else type(data)}")
        if isinstance(data, dict):
            print(f"   Preview: {json.dumps({k: str(v)[:100]} for k, v in list(data.items())[:5]), indent=2}")
    except:
        print(f"   ⚠️ Script JSON #{i}: {len(js)} chars, no parseable")

# 3. Buscar URLs de API en el HTML (fetched/loaded)
print("\n📊 Buscando URLs de API en el código...")
api_patterns = [
    r'["\'](/api/[^"\']+)["\']',
    r'["\']http(?:s)?://[^"\']+/api/[^"\']+["\']',
    r'fetch\(["\']([^"\']+)["\']',
    r'axios\.\w+\(["\']([^"\']+)["\']',
    r'\.get\(["\']([^"\']+)["\']',
]
all_api_urls = set()
for pattern in api_patterns:
    urls = re.findall(pattern, html, re.IGNORECASE)
    all_api_urls.update(urls)

print(f"   Encontradas {len(all_api_urls)} URLs potenciales de API:")
for u in sorted(all_api_urls)[:20]:
    print(f"      - {u}")

# 4. Buscar data-* attributes que contengan JSON
print("\n📊 Buscando attributes data-* con JSON...")
data_attrs = re.findall(r'data-[^=]+=["\'](\{[^"\']*})\s*["\']', html)
for i, da in enumerate(data_attrs[:5]):
    try:
        parsed = json.loads(da)
        print(f"   ✅ data-#{i}: {str(parsed)[:100]}...")
    except:
        pass

# 5. Buscar strings que parezcan productos (JSON arrays)
print("\n📊 Buscando arrays JSON con productos/padres/precios...")
product_patterns = [
    r'\{"id":\d+,"name":\s*"[^"]+","price":\d+[^}]*\}',
    r'\[{"name":"[^"]+","price":\d+[^}]*}\]',
    r'"products":\[(\{[^\]]+\})\]',
    r'"offers":\[(\{[^\]]+\})\]',
]
for i, pp in enumerate(product_patterns):
    matches = re.findall(pp, html, re.IGNORECASE | re.DOTALL)
    if matches and len(matches) > 0:
        print(f"   ✅ Patrón {i}: {len(matches)} matchs")
        print(f"      Example: {matches[0][:300]}...")

print("\n✅ Análisis completo. El sitio es una SPA con JS bundles ofuscados.")
print("💡 Para extraer datos reales necesitaré: scraping con Selenium/Playwright o interceptar llamadas API")
