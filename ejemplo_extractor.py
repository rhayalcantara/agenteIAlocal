import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def extraer_lista_regulatoria(url):
    """
    Simula la extracción de una tabla de normativas desde un sitio web regulador.
    """
    print(f"[*] Iniciando extracción en: {url}")
    
    try:
        # En un escenario real, se usaría requests.get(url)
        # Aquí simulamos el contenido HTML que encontraríamos
        html_simulado = """
        <table>
            <tr><th>ID</th><th>Normativa</th><th>Fecha de Vigencia</th><th>Estado</th></tr>
            <tr><td>REG-001</td><td>Ley de Protección de Datos</td><td>2024-01-15</td><td>Activa</td></tr>
            <tr><td>REG-002</td><td>Protocolo Anti-Lavado (AML)</td><td>2023-11-20</td><td>Activa</td></tr>
            <tr><td>REG-003</td><td>Regulación de Capitales</td><td>2024-03-10</td><td>En Revisión</td></tr>
        </table>
        """
        
        soup = BeautifulSoup(html_simulado, 'html.parser')
        tabla = soup.find('table')
        
        datos = []
        filas = tabla.find_all('tr')[1:]  # Saltar cabecera
        
        for fila in filas:
            columnas = fila.find_all('td')
            datos.append({
                'ID': columnas[0].text,
                'Normativa': columnas[1].text,
                'Fecha': columnas[2].text,
                'Estado': columnas[3].text
            })
        
        return pd.DataFrame(datos)

    except Exception as e:
        print(f"[!] Error durante la extracción: {e}")
        return None

def guardar_reporte(df, nombre_archivo):
    fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
    nombre_final = f"{nombre_archivo}_{fecha_str}.csv"
    df.to_csv(nombre_final, index=
False)
    print(f"[✓] Reporte guardado como: {nombre_final}")

if __name__ == "__main__":
    URL_EJEMPLO = "https://ejemplo-regulador.gov/listas"
    
    df_regulatorio = extraer_lista_regulatoria(URL_EJEMPLO)
    
    if df_regulatorio is not None:
        print("\n--- Datos Extraídos ---")
        print(df_regulatorio)
        guardar_reporte(df_regulatorio, "cumplimiento_bancario")
