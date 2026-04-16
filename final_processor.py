import csv
import xml.etree.ElementTree as ET
import os
import requests

def download_and_process(csv_url=None, xml_url=None):
    results = []

    # Procesar CSV si hay URL o archivo local
    if csv_url:
        try:
            if csv_url.startswith('http'):
                response = requests.get(csv_url)
                response.raise_for_status()
                content = response.text.encode('utf-8')
            else:
                with open(csv_url, 'rb') as f:
                    content = f.read()
            
            import io
            reader = csv.DictReader(io.StringIO(content.decode('utf-8')))
            for row in reader:
                results.append(row)
            print(f"CSV procesado exitosamente.")
        except Exception as e:
            print(f"Error al procesar CSV: {e}")

    # Procesar XML si hay URL o archivo local
    if xml_url:
        try:
            if xml_url.startswith('http'):
                response = requests.get(xml_url)
                response.raise_for_status()
                content = response.content
            else:
                with open(xml_url, 'rb') as f:
                    content = f.read()

            root = ET.fromstring(content)
            for item in root.findall('.//item'):
                data = {child.tag: child.text for child(item)} # Simplificado para ejemplo
                # Si los atributos están en el elemento (como en la muestra)
                item_data = {attr: item.get(attr) for attr in item.attrib}
                results.append(item_data)
            print(f"XML procesado exitosamente.")
        except Exception as e:
            print(f"Error al procesar XML: {e}")

    return results

if __name__ == "__main__":
    # Para la implementación final, esto se adaptará a la fuente real
    # Por ahora, usamos los archivos generados en el paso anterior para verificar lógica
    final_results = download_and_process(csv_url='test_sample.csv', xml_url='test_sample.xml')
    print(f"Total registros finales: {len(final_results)}")
    print("Datos:", final_results)
