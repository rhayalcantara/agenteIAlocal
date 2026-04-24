"""
Visor de la base de datos de seguimientos.

Uso:
    python skills/seguimiento/ver_db.py              # muestra todo en terminal
    python skills/seguimiento/ver_db.py --html       # abre visor en el navegador
    python skills/seguimiento/ver_db.py --id 3       # solo un seguimiento
    python skills/seguimiento/ver_db.py --todos      # incluye cerrados
"""
import os
import sys
import sqlite3
import argparse
import webbrowser
import tempfile
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seguimiento.db")


def _conectar():
    if not os.path.exists(_DB_PATH):
        print(f"No existe la base de datos en:\n  {_DB_PATH}")
        print("Aún no se ha registrado ningún seguimiento.")
        sys.exit(0)
    con = sqlite3.connect(_DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _icono_tipo(tipo):
    return {"envio": "📦", "transaccion": "💳", "reserva": "🗓️",
            "solicitud": "📋", "otro": "🔹"}.get(tipo, "🔹")


def _icono_estado(activo):
    return "🟢" if activo else "⏹️"


# ── Visor terminal ────────────────────────────────────────────────────────────

def mostrar_terminal(solo_id=None, todos=False):
    con = _conectar()

    if solo_id:
        rows = con.execute("SELECT * FROM seguimientos WHERE id=?", (solo_id,)).fetchall()
    elif todos:
        rows = con.execute("SELECT * FROM seguimientos ORDER BY id").fetchall()
    else:
        rows = con.execute("SELECT * FROM seguimientos WHERE activo=1 ORDER BY id").fetchall()

    if not rows:
        print("No hay seguimientos" + (" activos." if not todos else "."))
        return

    sep = "─" * 72

    for r in rows:
        hist = con.execute(
            "SELECT * FROM historial WHERE seguimiento_id=? ORDER BY timestamp DESC",
            (r["id"],)
        ).fetchall()

        tipo_icon = _icono_tipo(r["tipo"])
        estado_icon = _icono_estado(r["activo"])

        print(f"\n{sep}")
        print(f" {estado_icon} #{r['id']}  {tipo_icon}  {r['titulo']}")
        print(sep)
        print(f"  Empresa    : {r['empresa'] or '—'}")
        print(f"  Referencia : {r['referencia'] or '—'}")
        print(f"  URL        : {r['url'] or '—'}")
        print(f"  Estado     : {r['estado_actual']}")
        print(f"  Esperado   : {r['estado_final'] or '—'}")
        print(f"  Agenda ID  : {r['agenda_id'] or '—'}")
        print(f"  Chat ID    : {r['chat_id'] or '—'}")
        print(f"  Creado     : {r['creado'][:16]}")
        print(f"  Actualizado: {r['actualizado'][:16]}")
        if r["notas"]:
            print(f"  Notas      : {r['notas']}")

        if hist:
            print(f"\n  Historial ({len(hist)} entradas):")
            for h in hist:
                marca = h["timestamp"][:16]
                print(f"    [{marca}] {h['estado']}"
                      + (f" — {h['descripcion']}" if h["descripcion"] else "")
                      + f"  ({h['fuente']})")
        else:
            print("\n  Sin historial.")

    print(f"\n{sep}")
    total = len(rows)
    print(f"  Total mostrados: {total}")
    print(sep)


# ── Visor HTML ────────────────────────────────────────────────────────────────

def generar_html(solo_id=None, todos=False) -> str:
    con = _conectar()

    if solo_id:
        rows = con.execute("SELECT * FROM seguimientos WHERE id=?", (solo_id,)).fetchall()
    elif todos:
        rows = con.execute("SELECT * FROM seguimientos ORDER BY id").fetchall()
    else:
        rows = con.execute("SELECT * FROM seguimientos WHERE activo=1 ORDER BY id").fetchall()

    ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cards = ""
    for r in rows:
        hist = con.execute(
            "SELECT * FROM historial WHERE seguimiento_id=? ORDER BY timestamp DESC",
            (r["id"],)
        ).fetchall()

        color = "#2ecc71" if r["activo"] else "#95a5a6"
        tipo_icon = _icono_tipo(r["tipo"])
        badge = "ACTIVO" if r["activo"] else "CERRADO"

        hist_rows = ""
        for h in hist:
            desc = h["description"] if "description" in h.keys() else h["descripcion"] if "descripcion" in h.keys() else ""
            # compatibilidad con ambas columnas
            try:
                desc = h["descripcion"]
            except Exception:
                desc = ""
            hist_rows += f"""
            <tr>
              <td>{h['timestamp'][:16]}</td>
              <td><b>{h['estado']}</b></td>
              <td>{desc}</td>
              <td><span class="badge-fuente">{h['fuente']}</span></td>
            </tr>"""

        hist_tabla = f"""
        <table class="hist">
          <thead><tr><th>Fecha</th><th>Estado</th><th>Detalle</th><th>Fuente</th></tr></thead>
          <tbody>{hist_rows or '<tr><td colspan="4">Sin historial</td></tr>'}</tbody>
        </table>""" if hist else "<p class='sin-hist'>Sin historial registrado.</p>"

        cards += f"""
      <div class="card">
        <div class="card-header" style="border-left:5px solid {color}">
          <span class="tipo-icon">{tipo_icon}</span>
          <span class="titulo">#{r['id']} — {r['titulo']}</span>
          <span class="badge" style="background:{color}">{badge}</span>
        </div>
        <div class="card-body">
          <div class="meta">
            <div><label>Empresa</label><span>{r['empresa'] or '—'}</span></div>
            <div><label>Referencia</label><span>{r['referencia'] or '—'}</span></div>
            <div><label>Estado actual</label><span class="estado">{r['estado_actual']}</span></div>
            <div><label>Estado final esperado</label><span>{r['estado_final'] or '—'}</span></div>
            <div><label>URL</label><span>{f'<a href="{r["url"]}" target="_blank">{r["url"][:60]}...</a>' if r["url"] else '—'}</span></div>
            <div><label>Agenda ID</label><span>{r['agenda_id'] or '—'}</span></div>
            <div><label>Creado</label><span>{r['creado'][:16]}</span></div>
            <div><label>Actualizado</label><span>{r['actualizado'][:16]}</span></div>
          </div>
          <h4>Historial de estados</h4>
          {hist_tabla}
        </div>
      </div>"""

    titulo_seccion = "Activos" if not todos else "Todos"
    if solo_id:
        titulo_seccion = f"Seguimiento #{solo_id}"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Seguimientos — Agente IA</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0f1117; color: #e0e0e0; padding: 20px; }}
    h1 {{ font-size: 1.4rem; color: #fff; margin-bottom: 4px; }}
    .subtitle {{ color: #666; font-size: 0.85rem; margin-bottom: 24px; }}
    .card {{ background: #1a1d27; border-radius: 10px; margin-bottom: 20px;
             overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.4); }}
    .card-header {{ display: flex; align-items: center; gap: 12px;
                    padding: 14px 18px; background: #13151f; }}
    .tipo-icon {{ font-size: 1.4rem; }}
    .titulo {{ flex: 1; font-weight: 600; font-size: 1rem; color: #fff; }}
    .badge {{ padding: 3px 10px; border-radius: 20px; font-size: 0.72rem;
              font-weight: 700; color: #fff; letter-spacing: .5px; }}
    .badge-fuente {{ background: #2c3e50; padding: 2px 7px; border-radius: 4px;
                     font-size: 0.72rem; color: #aaa; }}
    .card-body {{ padding: 16px 18px; }}
    .meta {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px;
             margin-bottom: 18px; }}
    .meta div {{ display: flex; gap: 8px; align-items: baseline; font-size: 0.88rem; }}
    .meta label {{ color: #666; min-width: 130px; flex-shrink: 0; }}
    .meta span {{ color: #ccc; }}
    .estado {{ color: #3498db; font-weight: 600; }}
    h4 {{ color: #888; font-size: 0.8rem; text-transform: uppercase;
          letter-spacing: 1px; margin-bottom: 10px; }}
    .hist {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    .hist th {{ background: #0f1117; color: #666; text-align: left;
                padding: 7px 10px; font-weight: 500; }}
    .hist td {{ padding: 7px 10px; border-top: 1px solid #1e2130; color: #bbb; }}
    .hist tr:hover td {{ background: #1e2130; }}
    .hist b {{ color: #e0e0e0; }}
    .sin-hist {{ color: #555; font-size: 0.85rem; padding: 8px 0; }}
    .empty {{ text-align: center; color: #555; padding: 60px 20px; }}
    a {{ color: #3498db; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    @media (max-width: 600px) {{
      .meta {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <h1>📋 Seguimientos — {titulo_seccion}</h1>
  <p class="subtitle">Base de datos: {_DB_PATH} &nbsp;|&nbsp; Generado: {ahora}</p>
  {''.join([cards]) if rows else '<div class="empty">No hay seguimientos para mostrar.</div>'}
</body>
</html>"""


def abrir_html(solo_id=None, todos=False):
    html = generar_html(solo_id=solo_id, todos=todos)
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8",
        prefix="seguimientos_"
    )
    tmp.write(html)
    tmp.close()
    print(f"Abriendo visor en el navegador...")
    print(f"Archivo: {tmp.name}")
    webbrowser.open(f"file:///{tmp.name.replace(os.sep, '/')}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Visor de seguimientos")
    parser.add_argument("--html", action="store_true", help="Abrir visor en el navegador")
    parser.add_argument("--id", type=int, default=None, help="Ver solo un seguimiento por ID")
    parser.add_argument("--todos", action="store_true", help="Incluir seguimientos cerrados")
    args = parser.parse_args()

    if args.html:
        abrir_html(solo_id=args.id, todos=args.todos)
    else:
        mostrar_terminal(solo_id=args.id, todos=args.todos)


if __name__ == "__main__":
    main()
