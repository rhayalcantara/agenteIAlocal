import json
import os

def consultar_empleados(archivo='empleados.json'):
    if not os.path.exists(archivo):
        print(f"Error: El archivo {archivo} no existe.")
        return

    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            empleados = json.load(f)
        
        if not empleados:
            print("No hay empleados registrados.")
            return

        print(f"{'ID':<5} | {'Nombre':<20} | {'Puesto':<20} | {'Departamento':<15}")
        print("-" * 65)
        for emp in empleados:
            print(f"{emp['id']:<5} | {emp['nombre']:<20} | {emp['puesto']:<20} | {emp['departamento']:<15}")
            
    except json.JSONDecodeError:
        print("Error: El archivo JSON tiene un formato incorrecto.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    consultar_empleados()
