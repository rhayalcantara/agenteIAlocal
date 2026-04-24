"""
Skill seguimiento: tracking universal de procesos con cambio de estado.
Soporta: envios, transacciones, reservas, solicitudes, otros.

Uso:
    python run.py agregar --tipo envio --titulo "Pedido X" [--empresa X] [--referencia X] ...
    python run.py listar [--tipo envio] [--todos]
    python run.py ver --id 1
    python run.py actualizar --id 1 --estado "En tránsito" --fuente web [--descripcion "detalle"]
    python run.py vincular-agenda --id 1 --agenda-id 5
    python run.py cerrar --id 1 [--razon "motivo"]
    python run.py resumen
"""
import sqlite3
import os
import sys
from datetime import datetime

# DB siempre junto al script, independientemente del cwd
_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_DIR, "seguimiento.db")


def _conectar():
    """Conecta y crea tablas si no existen."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS seguimientos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo        TEXT NOT NULL,
            titulo      TEXT NOT NULL,
            empresa     TEXT,
            referencia  TEXT,
            url         TEXT,
            estado_actual  TEXT DEFAULT 'Pendiente',
            estado_final   TEXT,
            agenda_id         INTEGER,
            chat_id           TEXT,
            email_notificar   TEXT,
            notas             TEXT,
            activo            INTEGER DEFAULT 1,
            creado            TEXT DEFAULT (datetime('now','localtime')),
            actualizado       TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    # Migración: agregar columna si la DB ya existe sin ella
    try:
        conn.execute("ALTER TABLE seguimientos ADD COLUMN email_notificar TEXT")
        conn.commit()
    except Exception:
        pass  # Ya existe, ignorar
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            seguimiento_id   INTEGER NOT NULL,
            estado           TEXT NOT NULL,
            descripcion      TEXT,
            fuente           TEXT DEFAULT 'manual',
            timestamp        TEXT DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (seguimiento_id) REFERENCES seguimientos(id)
        )
    """)
    conn.commit()
    return conn


# ── Operaciones ───────────────────────────────────────────────────────────────

def agregar(**kwargs):
    """Registra un nuevo seguimiento."""
    tipo  = kwargs.get('tipo')
    titulo = kwargs.get('titulo')
    if not tipo or not titulo:
        return "❌ Error: --tipo y --titulo son obligatorios."

    conn = _conectar()
    try:
        estado_inicial = kwargs.get('estado_inicial') or kwargs.get('estado-inicial', 'Iniciado')
        c = conn.execute("""
            INSERT INTO seguimientos
                (tipo, titulo, empresa, referencia, url, estado_actual, estado_final,
                 chat_id, email_notificar, notas)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            tipo, titulo,
            kwargs.get('empresa'),
            kwargs.get('referencia'),
            kwargs.get('url'),
            estado_inicial,
            kwargs.get('estado_final'),
            kwargs.get('chat_id'),
            kwargs.get('email_notificar'),
            kwargs.get('notas'),
        ))
        seg_id = c.lastrowid
        # Registrar estado inicial en historial
        conn.execute("""
            INSERT INTO historial (seguimiento_id, estado, fuente)
            VALUES (?, ?, 'manual')
        """, (seg_id, estado_inicial))
        conn.commit()

        ref = kwargs.get('referencia', '—')
        empresa = kwargs.get('empresa', '—')
        prompt = (
            f"Monitorear seguimiento #{seg_id} — {titulo} ({empresa}, ref: {ref}). "
            f"Usa: ejecutar_script_skill('seguimiento', 'run.py', 'ver --id {seg_id}') "
            f"para ver estado actual. Luego actualiza con: "
            f"ejecutar_script_skill('seguimiento', 'run.py', 'actualizar --id {seg_id} "
            f"--estado \"[nuevo estado]\" --fuente web')"
        )
        email_line = ""
        if kwargs.get('email_notificar'):
            email_line = f"\n   Notificar por email a: {kwargs['email_notificar']}"

        return (
            f"✅ Seguimiento #{seg_id} creado: {titulo}\n"
            f"   Empresa: {empresa} | Ref: {ref}\n"
            f"   Estado inicial: {estado_inicial}\n"
            f"   Estado final esperado: {kwargs.get('estado_final', '—')}"
            f"{email_line}\n\n"
            f"PROMPT PARA AGENDA DE MONITOREO:\n{prompt}"
        )
    except Exception as e:
        return f"❌ Error al crear seguimiento: {e}"
    finally:
        conn.close()


def listar(**kwargs):
    """Lista seguimientos activos (o todos con --todos)."""
    conn = _conectar()
    query = "SELECT id, tipo, titulo, empresa, referencia, estado_actual FROM seguimientos"
    params = []
    conditions = []

    if not kwargs.get('todos'):
        conditions.append("activo = 1")

    tipo = kwargs.get('tipo')
    if tipo:
        conditions.append("tipo = ?")
        params.append(tipo)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()

    if not rows:
        return "📭 No hay seguimientos" + (" activos." if not kwargs.get('todos') else ".")

    lines = ["📋 Seguimientos:\n"]
    for r in rows:
        lines.append(f"  #{r['id']} [{r['tipo']}] {r['titulo']}")
        lines.append(f"       Empresa: {r['empresa'] or '—'} | Ref: {r['referencia'] or '—'}")
        lines.append(f"       Estado: {r['estado_actual']}\n")
    return "\n".join(lines)


def ver(**kwargs):
    """Muestra detalle completo de un seguimiento con historial."""
    seg_id = kwargs.get('id')
    if not seg_id:
        return "❌ Error: --id es obligatorio."

    conn = _conectar()
    row = conn.execute("SELECT * FROM seguimientos WHERE id = ?", (seg_id,)).fetchone()
    if not row:
        conn.close()
        return f"❌ Seguimiento #{seg_id} no encontrado."

    historial = conn.execute(
        "SELECT estado, descripcion, fuente, timestamp FROM historial "
        "WHERE seguimiento_id = ? ORDER BY timestamp DESC LIMIT 15",
        (seg_id,)
    ).fetchall()
    conn.close()

    result = [
        f"🔍 Seguimiento #{row['id']}: {row['titulo']}",
        f"   Tipo: {row['tipo']} | Activo: {'Sí' if row['activo'] else 'No'}",
        f"   Empresa: {row['empresa'] or '—'}",
        f"   Referencia: {row['referencia'] or '—'}",
        f"   URL: {row['url'] or '—'}",
        f"   Estado actual: {row['estado_actual']}",
        f"   Estado final esperado: {row['estado_final'] or '—'}",
        f"   Agenda ID: {row['agenda_id'] or '—'}",
        f"   Chat ID: {row['chat_id'] or '—'}",
        f"   Email notificar: {row['email_notificar'] or '—'}",
        f"   Creado: {row['creado']}",
        "",
        f"   Historial ({len(historial)} entradas):",
    ]
    for h in historial:
        desc = f" — {h['descripcion']}" if h['descripcion'] else ""
        result.append(f"     [{h['timestamp']}] {h['estado']}{desc} ({h['fuente']})")
    return "\n".join(result)


def actualizar(**kwargs):
    """Registra un nuevo estado en el historial."""
    seg_id = kwargs.get('id')
    estado = kwargs.get('estado')
    fuente = kwargs.get('fuente', 'manual')

    if not seg_id or not estado:
        return "❌ Error: --id y --estado son obligatorios."

    conn = _conectar()
    row = conn.execute(
        "SELECT titulo, estado_actual, estado_final, agenda_id, email_notificar FROM seguimientos WHERE id = ?",
        (seg_id,)
    ).fetchone()

    if not row:
        conn.close()
        return f"❌ Seguimiento #{seg_id} no encontrado."

    estado_anterior = row['estado_actual']
    hubo_cambio = estado.strip().lower() != estado_anterior.strip().lower()

    if not hubo_cambio:
        conn.close()
        return (
            f"[SILENCIOSO] Sin cambio en seguimiento #{seg_id} ({row['titulo']}). "
            f"Estado actual: {estado_anterior}"
        )

    conn.execute("""
        INSERT INTO historial (seguimiento_id, estado, descripcion, fuente)
        VALUES (?, ?, ?, ?)
    """, (seg_id, estado, kwargs.get('descripcion', ''), fuente))
    conn.execute(
        "UPDATE seguimientos SET estado_actual = ?, actualizado = datetime('now','localtime') WHERE id = ?",
        (estado, seg_id)
    )
    conn.commit()
    conn.close()

    # Detectar estado final
    estado_final = row['estado_final'] or ''
    es_final = estado_final and estado_final.lower() in estado.lower()

    if es_final:
        agenda_instruccion = ""
        if row['agenda_id']:
            agenda_instruccion = f"\n3. Desactiva la agenda: agenda desactivar id={row['agenda_id']}"

        email_instruccion = ""
        if row['email_notificar']:
            em = row['email_notificar']
            tit = row['titulo']
            email_instruccion = (
                f"\n4. Envia correo de confirmacion: ejecutar_script_skill('gmail-reader', 'run.py', "
                f"'enviar --para \"{em}\" "
                f"--asunto \"Tu pedido {tit} ha llegado\" "
                f"--cuerpo \"Buenas noticias! Tu pedido ha sido entregado. Estado: {estado}\"')"
            )

        return (
            f"ESTADO FINAL ALCANZADO en seguimiento #{seg_id}: {row['titulo']}\n"
            f"   Estado: {estado}\n\n"
            f"Acciones requeridas:\n"
            f"1. Notifica al usuario sobre el estado final\n"
            f"2. Cierra el seguimiento: ejecutar_script_skill('seguimiento', 'run.py', "
            f"'cerrar --id {seg_id}')"
            f"{agenda_instruccion}"
            f"{email_instruccion}"
        )

    email_instruccion = ""
    if row['email_notificar']:
        em = row['email_notificar']
        tit = row['titulo']
        email_instruccion = (
            f"\nNOTIFICAR POR EMAIL: ejecutar_script_skill('gmail-reader', 'run.py', "
            f"'enviar --para \"{em}\" "
            f"--asunto \"Actualizacion de tu pedido: {tit}\" "
            f"--cuerpo \"Estado actualizado: {estado}\"')"
        )

    return f"Seguimiento #{seg_id} actualizado: {estado_anterior} -> {estado}{email_instruccion}"


def vincular_agenda(**kwargs):
    """Vincula una agenda al seguimiento."""
    seg_id = kwargs.get('id')
    agenda_id = kwargs.get('agenda_id') or kwargs.get('agenda-id')
    if not seg_id or not agenda_id:
        return "❌ Error: --id y --agenda-id son obligatorios."

    conn = _conectar()
    conn.execute(
        "UPDATE seguimientos SET agenda_id = ? WHERE id = ?",
        (agenda_id, seg_id)
    )
    conn.commit()
    conn.close()
    return f"🔗 Seguimiento #{seg_id} vinculado a agenda #{agenda_id}"


def cerrar(**kwargs):
    """Cierra (desactiva) un seguimiento."""
    seg_id = kwargs.get('id')
    if not seg_id:
        return "❌ Error: --id es obligatorio."

    razon = kwargs.get('razon', 'Cerrado manualmente')
    conn = _conectar()
    conn.execute(
        "UPDATE seguimientos SET activo = 0, actualizado = datetime('now','localtime') WHERE id = ?",
        (seg_id,)
    )
    conn.execute("""
        INSERT INTO historial (seguimiento_id, estado, descripcion, fuente)
        VALUES (?, 'CERRADO', ?, 'sistema')
    """, (seg_id, razon))
    conn.commit()
    conn.close()
    return f"✅ Seguimiento #{seg_id} cerrado. Razón: {razon}"


def resumen():
    """Vista ejecutiva de seguimientos."""
    conn = _conectar()
    por_tipo = conn.execute(
        "SELECT tipo, COUNT(*) as total, SUM(activo) as activos "
        "FROM seguimientos GROUP BY tipo"
    ).fetchall()
    recientes = conn.execute(
        "SELECT id, titulo, estado_actual, actualizado FROM seguimientos "
        "WHERE activo = 1 ORDER BY actualizado DESC LIMIT 5"
    ).fetchall()
    conn.close()

    lines = ["📊 Resumen de seguimientos:\n"]
    for r in por_tipo:
        lines.append(f"   {r['tipo']}: {r['total']} total ({r['activos']} activos)")
    if recientes:
        lines.append("\n   Más recientes:")
        for r in recientes:
            lines.append(f"     #{r['id']} {r['titulo']} — {r['estado_actual']} ({r['actualizado']})")
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # UTF-8 en stdout para Windows (evita UnicodeEncodeError con emojis)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    # Parsear args: --key value → {'key': value}  (hyphens → underscores)
    args = {}
    i = 2
    while i < len(sys.argv):
        token = sys.argv[i]
        if token.startswith("--"):
            key = token[2:].replace("-", "_")   # --estado-final → estado_final
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                args[key] = sys.argv[i + 1]
                i += 2
            else:
                args[key] = True   # flags booleanos: --todos
                i += 1
        else:
            i += 1

    dispatch = {
        "agregar":         agregar,
        "listar":          listar,
        "ver":             ver,
        "actualizar":      actualizar,
        "vincular-agenda": vincular_agenda,
        "cerrar":          cerrar,
        "resumen":         lambda **_: resumen(),
    }

    fn = dispatch.get(cmd)
    if fn is None:
        print(f"Comando desconocido: '{cmd}'. Opciones: {', '.join(dispatch)}")
        sys.exit(1)

    print(fn(**args))
