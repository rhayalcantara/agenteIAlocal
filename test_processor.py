import csv
import xml.etree.ElementTree as ET
import os

# Muestra de datos para prueba
csv_content = """id,nombre,valor
1,Producto A,100
2,Producto B,200
"""

xml_content = """<root>
    <item id="3" nombre="Producto C" valor="300" />
    <item id="4" nombre="Producto D" valor="400" />
</root>
"""

def test_process():
    # Crear archivos de prueba
    with open('test_sample.csv', 'w') as f:
        f.write(csv_content)
    
    with open('test_sample.xml', 'w') as f:
        f.write(xml_content)
    
    print("Archivos de prueba creados.")

    # Procesar CSV
    results = []
    with open('test_sample.csv', mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    print(f"CSV procesado: {len(results)} filas.")

    # Procesar XML
    tree = ET.parse('test_sample.xml')
    root = tree.getroot()
    for item in root.findall('item'):
        results.append({
            'id': item.get('id'),
            'nombre': item.get('nombre'),
            'valor': item.get('valor')
        })
    print(f"XML procesado: {len(results) - 2} elementos adicionales.")
    
    print("Total registros en memoria:", len(results))

if __name__ == "__main__":
    test_process()
