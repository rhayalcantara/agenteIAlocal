"""
Skill: seguimiento — Tracking universal de notificaciones con cambio de estado.

Rastrear cualquier cosa que cambia en el tiempo:
  - Envíos y paquetes (Amazon, DHL, FedEx, etc.)
  - Transacciones bancarias en proceso
  - Reservas, citas, solicitudes
  - Cualquier notificación con estado progresivo

Operaciones CLI:
  agregar          — Registra un nuevo seguimiento en la BD
  listar           — Lista seguimientos activos (o todos con --todos)
  ver              — Detalle completo + historial de un seguimiento
  actualizar       — Registra nuevo estado; detecta si es final y qué hacer
  vincular-agenda  — Asocia una acción de agenda a un seguimiento
  cerrar           — Cierra manualmente un seguimiento
  resumen          — Vista ejecutiva de todos los seguimientos activos

Base de datos: skills/seguimiento/seguimiento.db (SQLite, creada automáticamente)

# TODO (estadísticas — idea futura):
#   - cmd_estadisticas(): tiempos promedio por tipo, tasa de éxito/cancelación,
#     empresa con más seguimientos, distribución por estado, etc.
#     Agregar operación: run.py estadisticas [--tipo envio] [--mes 2026-04]
"""
import os
import sys
import sqlite3
import argparse
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seguimiento.db")

TIPOS_VALIDOS = ["envio", "transaccion", "reserva", "solicitud", "otro"]

# Palabras clave que indican estado final por tipo (heurística para detección automática)
_ESTADOS_FINALES_KEYWORDS = {
    "envio":       ["entregado", "delivered", "entrega exitosa", "recibido"],
    "transaccion": ["acreditado", "completado", "procesado", "rechazado", "revertido"],
    "reserva":     ["confirmada", "completada", "cancelada", "expirada"],
    "solicitud":   ["aprobada", "rechazada", "completada", "denegada", "finalizada"],
    "otro":        ["completado", "finalizado", "cerrado", "terminado"],
}


# ── Base de datos ─────────────────────────────────────────────────────────────

def _conectar() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # seguro para acceso concurrente
    return conn


def _inicializar_db():
    """Crea las tablas si no existen. Seguro llamarlo siempre."""
    with _conectar() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS seguimientos (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo          TEXT    NOT NULL,
                titulo        TEXT    NOT NULL,
                empresa       TEXT    DEFAULT '',
                referencia    TEXT    DEFAULT '',
                url           TEXT    DEFAULT '',
                estado_actual TEXT    DEFAULT 'Pendiente',
                estado_final  TEXT    DEFAULT '',
                activo        INTEGER DEFAULT 1,
                chat_id       INTEGER DEFAULT 0,
                agenda_id     INTEGER,
                creado        TEXT,
                actualizado   TEXT,
                notas         TEXT    DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS historial (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                seguimiento_id   INTEGER NOT NULL REFERENCES seguimientos(id),
                estado           TEXT    NOT NULL,
                descripcion      TEXT    DEFAULT '',
                timestamp        TEXT    NOT NULL,
                fuente           TEXT    DEFAULT 'auto'
            );

            CREATE INDEX IF NOT EXISTS idx_seguimientos_activo
                ON seguimientos(activo);
            CREATE INDEX IF NOT EXISTS idx_historial_seguimiento
                ON historial(seguimiento_id);
        """)


def _es_estado_final(tipo: str, estado: str, estado_final_config: str) -> bool:
    """
    Determina si un estado indica que el seguimiento llegó a su fin.
    Usa el estado_final configurado Y palabras clave por tipo como fallback.
    """
    estado_lower = estado.lower()

    # Comparar contra el estado final configurado explícitamente
    if estado_final_config:
        if estado_final_config.lower() in estado_lower:
            return True
        if estado_lower in estado_final_config.lower():
            return True

    # Fallback: palabras clave por tipo
    keywords = _ESTADOS_FINALES_KEYWORDS.get(tipo, _ESTADOS_FINALES_KEYWORDS["otro"])
    return any(kw in estado_lower for kw in keywords)


# ── Operaciones ───────────────────────────────────────────────────────────────

def cmd_agregar(args) -> str:
    _inicializar_db()
    now = datetime.now().isoformat()
    estado_inicial = args.estado_inicial or "Pendiente"

    with _conectar() as conn:
        cur = conn.execute("""
            INSERT INTO seguimientos
                (tipo, titulo, empresa, referencia, url,
                 estado_actual, estado_final,
                 activo, chat_id, creado, actualizado, notas)
            VALUES (?,?,?,?,?,?,?,1,?,?,?,?)
        """, (
            args.tipo,
            args.titulo,
            args.empresa or "",
            args.referencia or "",
            args.url or "",
            estado_inicial,
            args.estado_final or "",
            args.chat_id or 0,
            now,
            now,
            args.notas or "",
        ))
        sid = cur.lastrowid

        conn.execute("""
            INSERT INTO historial (seguimiento_id, estado, descripcion, timestamp, fuente)
            VALUES (?,?,?,?,?)
        """, (sid, estado_inicial, "Seguimiento creado", now, "manual"))

    prompt_monitoreo = (
        f'Monitorea el seguimiento #{sid} ({args.titulo}). '
        f'Empresa: {args.empresa or "?"}, Referencia: {args.referencia or "?"}, '
        f'URL: {args.url or "sin URL"}. '
        f'Ejecuta: ejecutar_script_skill seguimiento run.py "ver --id {sid}" para ver estado actual. '
        f'Luego visita la URL o busca correos de {args.empresa or "la empresa"} sobre la referencia. '
        f'Actualiza con: ejecutar_script_skill seguimiento run.py '
        f'"actualizar --id {sid} --estado [NUEVO_ESTADO] --descripcion [DETALLE] --fuente web". '
        f'Si el resultado indica estado final: notifica al usuario, cierra el seguimiento y desactiva esta agenda.'
    )

    return (
        f"✅ Seguimiento #{sid} registrado: {args.titulo}\n"
        f"Tipo: {args.tipo} | Empresa: {args.empresa or 'N/A'} | "
        f"Ref: {args.referencia or 'N/A'}\n"
        f"Estado inicial: {estado_inicial}\n"
        f"Estado final esperado: {args.estado_final or 'No definido'}\n"
        f"URL de tracking: {args.url or 'No definida'}\n"
        f"\n"
        f"PRÓXIMO PASO — Crea una agenda recurrente con este prompt:\n"
        f"{prompt_monitoreo}\n"
        f"\n"
        f"Luego vincula la agenda: ejecutar_script_skill seguimiento run.py "
        f'"vincular-agenda --id {sid} --agenda-id [ID_AGENDA]"'
    )


def cmd_listar(args) -> str:
    _inicializar_db()
    with _conectar() as conn:
        if args.todos:
            rows = conn.execute(
                "SELECT * FROM seguimientos ORDER BY actualizado DESC"
            ).fetchall()
        elif args.tipo:
            rows = conn.execute(
                "SELECT * FROM seguimientos WHERE tipo=? AND activo=1 ORDER BY actualizado DESC",
                (args.tipo,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM seguimientos WHERE activo=1 ORDER BY actualizado DESC"
            ).fetchall()

    if not rows:
        return "No hay seguimientos activos." if not args.todos else "No hay seguimientos registrados."

    lineas = [f"📋 Seguimientos — {len(rows)} encontrado(s)\n"]
    for r in rows:
        icono = "🟢" if r["activo"] else "⏹️"
        agenda_txt = f" | agenda #{r['agenda_id']}" if r["agenda_id"] else ""
        lineas.append(
            f"{icono} #{r['id']} [{r['tipo']}] {r['titulo']}\n"
            f"   {r['empresa']} | ref: {r['referencia']}\n"
            f"   Estado: {r['estado_actual']} | {r['actualizado'][:16]}{agenda_txt}"
        )
    return "\n".join(lineas)


def cmd_ver(args) -> str:
    _inicializar_db()
    with _conectar() as conn:
        r = conn.execute(
            "SELECT * FROM seguimientos WHERE id=?", (args.id,)
        ).fetchone()
        if not r:
            return f"❌ No existe el seguimiento #{args.id}."

        hist = conn.execute(
            "SELECT * FROM historial WHERE seguimiento_id=? ORDER BY timestamp DESC LIMIT 15",
            (args.id,)
        ).fetchall()

    icono = "🟢 Activo" if r["activo"] else "⏹️ Cerrado"
    lineas = [
        f"📦 Seguimiento #{r['id']}: {r['titulo']}",
        f"Estado: {icono}",
        f"Tipo: {r['tipo']} | Empresa: {r['empresa']}",
        f"Referencia: {r['referencia']}",
        f"URL: {r['url'] or 'No definida'}",
        f"Estado actual: {r['estado_actual']}",
        f"Estado final esperado: {r['estado_final'] or 'No definido'}",
        f"Agenda vinculada: #{r['agenda_id']}" if r["agenda_id"] else "Agenda vinculada: No",
        f"Creado: {r['creado'][:16]} | Actualizado: {r['actualizado'][:16]}",
    ]
    if r["notas"]:
        lineas.append(f"Notas: {r['notas']}")

    lineas.append(f"\nHistorial ({len(hist)} registros, más recientes primero):")
    for h in hist:
        lineas.append(
            f"  [{h['timestamp'][:16]}] {h['estado']}"
            + (f": {h['descripcion']}" if h["descripcion"] else "")
            + f" ({h['fuente']})"
        )

    return "\n".join(lineas)


def cmd_actualizar(args) -> str:
    _inicializar_db()
    now = datetime.now().isoformat()

    with _conectar() as conn:
        r = conn.execute(
            "SELECT * FROM seguimientos WHERE id=?", (args.id,)
        ).fetchone()
        if not r:
            return f"❌ No existe el seguimiento #{args.id}."
        if not r["activo"]:
            return f"⚠️ El seguimiento #{args.id} ya está cerrado."

        estado_anterior = r["estado_actual"]
        nuevo_estado = args.estado
        hubo_cambio = estado_anterior.lower() != nuevo_estado.lower()

        if hubo_cambio:
            conn.execute(
                "UPDATE seguimientos SET estado_actual=?, actualizado=? WHERE id=?",
                (nuevo_estado, now, args.id)
            )
            conn.execute("""
                INSERT INTO historial (seguimiento_id, estado, descripcion, timestamp, fuente)
                VALUES (?,?,?,?,?)
            """, (args.id, nuevo_estado, args.descripcion or "", now, args.fuente or "auto"))

    if not hubo_cambio:
        return (
            f"[SILENCIOSO] Sin cambio en seguimiento #{args.id} ({r['titulo']}). "
            f"Estado actual: {estado_anterior}"
        )

    es_final = _es_estado_final(r["tipo"], nuevo_estado, r["estado_final"] or "")

    lineas = [
        f"🔄 Seguimiento #{args.id}: {r['titulo']}",
        f"Estado: {estado_anterior} → {nuevo_estado}",
    ]

    if es_final:
        lineas += [
            "",
            "🏁 ESTADO FINAL ALCANZADO",
            "ACCIONES REQUERIDAS:",
            f"  1. Notifica al usuario: el seguimiento '{r['titulo']}' llegó a su estado final: {nuevo_estado}",
            f"  2. Cierra: ejecutar_script_skill seguimiento run.py \"cerrar --id {args.id} --razon '{nuevo_estado}'\"",
        ]
        if r["agenda_id"]:
            lineas.append(f"  3. Desactiva agenda: agenda desactivar id={r['agenda_id']}")

    return "\n".join(lineas)


def cmd_vincular_agenda(args) -> str:
    _inicializar_db()
    with _conectar() as conn:
        r = conn.execute(
            "SELECT titulo FROM seguimientos WHERE id=?", (args.id,)
        ).fetchone()
        if not r:
            return f"❌ No existe el seguimiento #{args.id}."
        conn.execute(
            "UPDATE seguimientos SET agenda_id=? WHERE id=?",
            (args.agenda_id, args.id)
        )
    return f"✅ Seguimiento #{args.id} vinculado a agenda #{args.agenda_id}."


def cmd_cerrar(args) -> str:
    _inicializar_db()
    now = datetime.now().isoformat()
    with _conectar() as conn:
        r = conn.execute(
            "SELECT titulo FROM seguimientos WHERE id=?", (args.id,)
        ).fetchone()
        if not r:
            return f"❌ No existe el seguimiento #{args.id}."
        conn.execute(
            "UPDATE seguimientos SET activo=0, actualizado=? WHERE id=?",
            (now, args.id)
        )
        if args.razon:
            conn.execute("""
                INSERT INTO historial (seguimiento_id, estado, descripcion, timestamp, fuente)
                VALUES (?,?,?,?,?)
            """, (args.id, "Cerrado", args.razon, now, "manual"))
    return f"⏹️ Seguimiento #{args.id} '{r['titulo']}' cerrado."


def cmd_resumen(args) -> str:
    _inicializar_db()
    with _conectar() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM seguimientos WHERE activo=1"
        ).fetchone()[0]

        if not total:
            return "No hay seguimientos activos."

        por_tipo = conn.execute(
            "SELECT tipo, COUNT(*) as n FROM seguimientos WHERE activo=1 GROUP BY tipo"
        ).fetchall()

        recientes = conn.execute("""
            SELECT id, titulo, tipo, empresa, estado_actual, actualizado
            FROM seguimientos WHERE activo=1
            ORDER BY actualizado DESC LIMIT 5
        """).fetchall()

    lineas = [f"📊 Resumen de seguimientos — {total} activo(s)"]
    for pt in por_tipo:
        lineas.append(f"  {pt['tipo']}: {pt['n']}")
    lineas.append("\nMás recientemente actualizados:")
    for r in recientes:
        lineas.append(
            f"  #{r['id']} [{r['tipo']}] {r['titulo']} ({r['empresa']})\n"
            f"    Estado: {r['estado_actual']} | {r['actualizado'][:16]}"
        )
    return "\n".join(lineas)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Seguimiento universal de estados",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="operacion", required=True)

    # agregar
    p = sub.add_parser("agregar", help="Registra un nuevo seguimiento")
    p.add_argument("--tipo", required=True, choices=TIPOS_VALIDOS,
                   help="Tipo: envio | transaccion | reserva | solicitud | otro")
    p.add_argument("--titulo", required=True, help="Nombre descriptivo del seguimiento")
    p.add_argument("--empresa", default="", help="Empresa o remitente (Amazon, DHL, Banco...)")
    p.add_argument("--referencia", default="", help="Número de tracking, orden, transacción...")
    p.add_argument("--url", default="", help="URL de seguimiento en el sitio del carrier/banco")
    p.add_argument("--estado-inicial", dest="estado_inicial", default="",
                   help="Estado inicial (default: Pendiente)")
    p.add_argument("--estado-final", dest="estado_final", default="",
                   help="Palabra clave del estado final (ej: Entregado, Acreditado)")
    p.add_argument("--chat-id", dest="chat_id", type=int, default=0,
                   help="chat_id de Telegram donde notificar")
    p.add_argument("--notas", default="", help="Notas adicionales")

    # listar
    p = sub.add_parser("listar", help="Lista seguimientos")
    p.add_argument("--tipo", default="", help="Filtrar por tipo")
    p.add_argument("--todos", action="store_true", help="Incluir cerrados")

    # ver
    p = sub.add_parser("ver", help="Detalle de un seguimiento")
    p.add_argument("--id", type=int, required=True)

    # actualizar
    p = sub.add_parser("actualizar", help="Registra nuevo estado")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--estado", required=True, help="Nuevo estado (texto libre)")
    p.add_argument("--descripcion", default="", help="Detalle del cambio")
    p.add_argument("--fuente", default="auto",
                   choices=["auto", "email", "web", "manual"],
                   help="Fuente del update")

    # vincular-agenda
    p = sub.add_parser("vincular-agenda", help="Asocia ID de agenda a un seguimiento")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--agenda-id", dest="agenda_id", type=int, required=True)

    # cerrar
    p = sub.add_parser("cerrar", help="Cierra manualmente un seguimiento")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--razon", default="", help="Motivo del cierre")

    # resumen
    sub.add_parser("resumen", help="Vista ejecutiva de todos los activos")

    args = parser.parse_args()

    _ops = {
        "agregar":         cmd_agregar,
        "listar":          cmd_listar,
        "ver":             cmd_ver,
        "actualizar":      cmd_actualizar,
        "vincular-agenda": cmd_vincular_agenda,
        "cerrar":          cmd_cerrar,
        "resumen":         cmd_resumen,
    }

    try:
        print(_ops[args.operacion](args))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
