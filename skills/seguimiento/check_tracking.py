import sqlite3
import sys
import os

# Agregar al path el directorio del script
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, script_dir)

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seguimiento.db')
print(f"DB path: {db_path}")
print(f"DB exists: {os.path.exists(db_path)}")

if not os.path.exists(db_path):
    print("No existe la base de datos")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Listar todas las tablas
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print(f"Tables: {tables}")

# Buscar seguimiento con id=6
try:
    cursor.execute("SELECT * FROM seguimientos WHERE id=6")
    row = cursor.fetchone()
    if row:
        print(f"Found tracking #6: {row}")
    else:
        print("No tracking #6 found")
except Exception as e:
    print(f"Error: {e}")

conn.close()
