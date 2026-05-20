import requests
import json
import re

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
}

print("=" * 80)
print("BUSCANDO PRECIOS DE SUPERMERCADOS NACIONALES EN RD")
print("=" * 80)

# Fuente 1: SupermercadosRD (comparador)
print("\n[1] Accediendo a supermercadosrd.com...")
try:
    r = requests.get('https://supermercadosrd.com', headers=headers, timeout=15)
    print(f"   Status: {r.status_code}")
    print(f"   Longitud: {len(r.text)} chars")
    
    # Buscar precios en el texto
    precios = re.findall(r'\$[\d,.]+', r.text)
    if precios:
        print(f"   Precios encontrados: {precios[:20]}")
except Exception as e:
    print(f"   Error: {e}")

# Fuente 2: PreciosMundi
print("\n[2] Accediendo a preciosmundi.com...")
try:
    r2 = requests.get('https://preciosmundi.com/republica-dominicana/precios-supermercado', headers=headers, timeout=15)
    print(f"   Status: {r2.status_code}")
    print(f"   Longitud: {len(r2.text)} chars")
    
    # Extraer texto visible (no scripts ni styles)
    soup_text = re.sub(r'<script[^>]*>.*?</script>', '', r2.text, flags=re.DOTALL)
    soup_text = re.sub(r'<style[^>]*>.*?</style>', '', soup_text, flags=re.DOTALL)
    soup_text = re.sub(r'<[^>]+>', ' ', soup_text)
    soup_text = re.sub(r'\s+', ' ', soup_text).strip()
    
    # Buscar productos relevantes
    productos = ['carne', 'huevo', 'leche', 'arroz', 'aceite', 'azucar', 'cafe', 'papel', 'jabon']
    for prod in productos:
        indices = [i for i in range(len(soup_text)) if soup_text.lower().find(prod.lower(), i) < len(soup_text)]
        if indices:
            inicio = indices[0]
            contexto = soup_text[max(0, inicio-100):inicio+200]
            if '$' in contexto or 'RD$' in contexto or 'pesos' in contexto.lower():
                print(f"   {prod}: {contexto[:150]}...")
except Exception as e:
    print(f"   Error: {e}")

# Fuente 3: Supermercados Nacional directo
print("\n[3] Accediendo a supermercadosnacional.com...")
try:
    r3 = requests.get('https://supermercadosnacional.com', headers=headers, timeout=15)
    print(f"   Status: {r3.status_code}")
    print(f"   Longitud: {len(r3.text)} chars")
    if r3.status_code == 200 and len(r3.text) > 1000:
        # Buscar ofertas y precios
        ofertas = re.findall(r'[\$]([\d,.]+)\s*[\s\S]{0,100}?(carne|huevo|leche|arroz|aceite|aceite|papel|jabon|sopa|salsa|margarina|mantequilla)', r3.text, re.IGNORECASE)
        if ofertas:
            print(f"   Ofertas encontradas: {ofertas[:10]}")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 80)
print("BÚSQUEDA COMPLETADA")
print("=" * 80)