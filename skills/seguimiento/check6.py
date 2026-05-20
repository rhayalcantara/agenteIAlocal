import sqlite3, sys
DB = r'C:\proyectos\agenteIAlocal\skills\seguimiento\seguimiento.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
row = conn.execute("SELECT * FROM seguimientos WHERE id=6").fetchone()
if row:
    for k in ['id','titulo','estado_actual','actualizado','estado_final','empresa','referencia']:
        print(f"{k}: {row[k]}")
    hist = conn.execute("SELECT estado, descripcion, fuente, timestamp FROM historial WHERE seguimiento_id=6 ORDER BY timestamp DESC").fetchall()
    if hist:
        print(f"HISTORIAL ({len(hist)} entradas):")
        for h in hist:
            desc = f" - {h['descripcion']}" if h.get('descripcion') else ""
            print(f"  [{h['timestamp']}] {h['estado']}{desc} ({h['fuente']})")
    else:
        print("Sin historial.")
else:
    print("No encontrado.")
conn.close()
