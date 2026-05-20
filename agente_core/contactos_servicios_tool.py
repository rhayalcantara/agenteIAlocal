"""
Contactos Servicios Tool — Directorio de proveedores de servicios.

Operaciones:
  agregar      — Registra un contacto (nombre, oficio, telefono, notas)
  buscar       — Busca por nombre u oficio (parcial)
  listar       — Lista todos los contactos (o filtrar por oficio)
  editar       — Modifica datos de un contacto
  registrar_visita — Registra que vino a hacer un trabajo (fecha + nota)
  historial    — Historial de visitas de un contacto
  eliminar     — Elimina un contacto

Estructura del JSON:
  Cada contacto: {
    "id": int,
    "nombre": str,
    "oficio": str,
    "telefono": str | null,
    "email": str | null,
    "notas": str | null,
    "calificacion": int | null,    (1-5 estrellas)
    "fecha_agregado": str (ISO),
    "visitas": [{"fecha": str, "trabajo": str, "costo": float | null, "nota": str | null}]
  }
"""
import json
import os
from datetime import datetime
from logger import get_logger

logger = get_logger("contactos_servicios")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "contactos_servicios.json")


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cargar() -> list[dict]:
    os.makedirs(_DATA_DIR, exist_ok=True)
    if not os.path.exists(_ARCHIVO):
        return []
    try:
        with open(_ARCHIVO, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, Exception):
        return []


def _guardar(contactos: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(contactos, f, ensure_ascii=False, indent=2)


def _siguiente_id(contactos: list[dict]) -> int:
    return max((c["id"] for c in contactos), default=0) + 1


def _buscar_exacto(contactos: list[dict], nombre: str) -> dict | None:
    nombre_lower = nombre.lower().strip()
    for c in contactos:
        if c["nombre"].lower().strip() == nombre_lower:
            return c
    return None


def _buscar_parcial(contactos: list[dict], texto: str) -> list[dict]:
    texto_lower = texto.lower().strip()
    return [c for c in contactos
            if texto_lower in c["nombre"].lower()
            or texto_lower in (c.get("oficio") or "").lower()]


def _estrellas(n: int | None) -> str:
    if n is None:
        return ""
    return "*" * n + "-" * (5 - n)


# ── Operaciones ──────────────────────────────────────────────────────────────

def agregar(nombre: str, oficio: str, telefono: str = None,
            email: str = None, notas: str = None,
            calificacion: int = None) -> str:
    contactos = _cargar()
    existente = _buscar_exacto(contactos, nombre)
    if existente:
        return (f"'{existente['nombre']}' ya existe como {existente['oficio']}. "
                f"Usa editar para modificarlo.")

    contacto = {
        "id": _siguiente_id(contactos),
        "nombre": nombre.strip(),
        "oficio": oficio.strip(),
        "telefono": telefono,
        "email": email,
        "notas": notas,
        "calificacion": calificacion,
        "fecha_agregado": datetime.now().isoformat(),
        "visitas": [],
    }
    contactos.append(contacto)
    _guardar(contactos)

    tel_txt = f" | Tel: {telefono}" if telefono else ""
    return f"Contacto agregado: {nombre} ({oficio}){tel_txt}"


def buscar(texto: str) -> str:
    contactos = _cargar()

    # Exacto primero
    exacto = _buscar_exacto(contactos, texto)
    if exacto:
        lineas = [f"{exacto['nombre']} — {exacto['oficio']}"]
        if exacto.get("telefono"):
            lineas.append(f"  Tel: {exacto['telefono']}")
        if exacto.get("email"):
            lineas.append(f"  Email: {exacto['email']}")
        if exacto.get("calificacion"):
            lineas.append(f"  Calificacion: [{_estrellas(exacto['calificacion'])}]")
        if exacto.get("notas"):
            lineas.append(f"  Notas: {exacto['notas']}")
        n_visitas = len(exacto.get("visitas", []))
        if n_visitas > 0:
            ultima = exacto["visitas"][-1]
            lineas.append(f"  Visitas: {n_visitas} | Ultima: {ultima['fecha'][:10]} — {ultima.get('trabajo', '')}")
        return "\n".join(lineas)

    # Parcial
    resultados = _buscar_parcial(contactos, texto)
    if not resultados:
        return f"No se encontro '{texto}'. Usa listar para ver todos los contactos."

    lineas = [f"Encontrados {len(resultados)} contactos:"]
    for c in resultados:
        tel = f" | {c['telefono']}" if c.get("telefono") else ""
        cal = f" [{_estrellas(c.get('calificacion'))}]" if c.get("calificacion") else ""
        lineas.append(f"  - {c['nombre']} ({c['oficio']}){tel}{cal}")
    return "\n".join(lineas)


def listar(oficio: str = None) -> str:
    contactos = _cargar()
    if not contactos:
        return "No hay contactos registrados."

    if oficio:
        oficio_lower = oficio.lower().strip()
        contactos = [c for c in contactos if oficio_lower in (c.get("oficio") or "").lower()]
        if not contactos:
            return f"No hay contactos con oficio '{oficio}'."

    # Agrupar por oficio
    por_oficio = {}
    for c in contactos:
        of = c.get("oficio") or "Sin oficio"
        por_oficio.setdefault(of, []).append(c)

    lineas = [f"Directorio de servicios ({len(contactos)} contactos):"]
    for of, of_contactos in sorted(por_oficio.items()):
        lineas.append(f"\n  [{of}]")
        for c in of_contactos:
            tel = f" | {c['telefono']}" if c.get("telefono") else ""
            cal = f" [{_estrellas(c.get('calificacion'))}]" if c.get("calificacion") else ""
            n_vis = len(c.get("visitas", []))
            vis = f" ({n_vis} visitas)" if n_vis > 0 else ""
            lineas.append(f"    - {c['nombre']}{tel}{cal}{vis}")

    return "\n".join(lineas)


def editar(nombre: str, nuevo_nombre: str = None, oficio: str = None,
           telefono: str = None, email: str = None, notas: str = None,
           calificacion: int = None) -> str:
    contactos = _cargar()
    contacto = _buscar_exacto(contactos, nombre)
    if not contacto:
        return f"Contacto '{nombre}' no encontrado."

    cambios = []

    if nuevo_nombre and nuevo_nombre.strip().lower() != contacto["nombre"].lower():
        if _buscar_exacto(contactos, nuevo_nombre):
            return f"Ya existe un contacto llamado '{nuevo_nombre}'."
        contacto["nombre"] = nuevo_nombre.strip()
        cambios.append(f"nombre -> '{nuevo_nombre}'")

    if oficio is not None:
        contacto["oficio"] = oficio.strip()
        cambios.append(f"oficio -> '{oficio}'")
    if telefono is not None:
        contacto["telefono"] = telefono
        cambios.append("telefono actualizado")
    if email is not None:
        contacto["email"] = email
        cambios.append("email actualizado")
    if notas is not None:
        contacto["notas"] = notas
        cambios.append("notas actualizadas")
    if calificacion is not None:
        contacto["calificacion"] = calificacion
        cambios.append(f"calificacion -> [{_estrellas(calificacion)}]")

    if not cambios:
        return "No se especificaron cambios."

    _guardar(contactos)
    return f"Contacto '{contacto['nombre']}' actualizado: {', '.join(cambios)}"


def registrar_visita(nombre: str, trabajo: str, costo: float = None,
                     nota: str = None) -> str:
    contactos = _cargar()
    contacto = _buscar_exacto(contactos, nombre)
    if not contacto:
        return f"Contacto '{nombre}' no encontrado."

    visita = {
        "fecha": datetime.now().isoformat(),
        "trabajo": trabajo,
        "costo": round(costo, 2) if costo else None,
        "nota": nota,
    }
    contacto["visitas"].append(visita)
    _guardar(contactos)

    costo_txt = f" | Costo: ${costo:,.2f}" if costo else ""
    n_total = len(contacto["visitas"])
    return (f"Visita registrada para {contacto['nombre']} ({contacto['oficio']})\n"
            f"  Trabajo: {trabajo}{costo_txt}\n"
            f"  Total de visitas: {n_total}")


def historial(nombre: str) -> str:
    contactos = _cargar()
    contacto = _buscar_exacto(contactos, nombre)
    if not contacto:
        return f"Contacto '{nombre}' no encontrado."

    visitas = contacto.get("visitas", [])
    if not visitas:
        return f"'{contacto['nombre']}' no tiene visitas registradas."

    total_costo = sum(v.get("costo") or 0 for v in visitas)

    lineas = [
        f"Historial de {contacto['nombre']} ({contacto['oficio']}) — {len(visitas)} visitas:",
    ]
    if total_costo > 0:
        lineas.append(f"  Gasto total: ${total_costo:,.2f}")
    lineas.append("")

    for v in reversed(visitas):
        fecha = v["fecha"][:10]
        costo = f" | ${v['costo']:,.2f}" if v.get("costo") else ""
        nota = f" — {v['nota']}" if v.get("nota") else ""
        lineas.append(f"  {fecha} | {v['trabajo']}{costo}{nota}")

    return "\n".join(lineas)


def eliminar(nombre: str) -> str:
    contactos = _cargar()
    contacto = _buscar_exacto(contactos, nombre)
    if not contacto:
        return f"Contacto '{nombre}' no encontrado."

    contactos.remove(contacto)
    _guardar(contactos)
    return f"Contacto '{contacto['nombre']}' ({contacto['oficio']}) eliminado."


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "agregar": agregar,
    "buscar": buscar,
    "listar": listar,
    "editar": editar,
    "registrar_visita": registrar_visita,
    "historial": historial,
    "eliminar": eliminar,
}


def ejecutar(operacion: str, **kwargs) -> str:
    fn = _OPERACIONES.get(operacion)
    if fn is None:
        disponibles = ", ".join(sorted(_OPERACIONES.keys()))
        return f"Operacion '{operacion}' no existe. Disponibles: {disponibles}"
    try:
        return fn(**kwargs)
    except TypeError as e:
        return f"Parametros incorrectos para '{operacion}': {e}"
    except Exception as e:
        logger.error(f"contactos_servicios.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
