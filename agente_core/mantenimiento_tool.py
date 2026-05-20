"""
Mantenimiento Tool — Calendario de mantenimiento de objetos/equipos.

Vinculado a ubicaciones_tool: usa objetos y areas registradas.

Operaciones:
  registrar     — Registra un item de mantenimiento con frecuencia
  listar        — Lista todos los items de mantenimiento
  pendientes    — Muestra que toca revisar ahora o esta atrasado
  completar     — Marca un mantenimiento como realizado hoy
  historial     — Historial de mantenimientos de un item
  eliminar      — Elimina un item del calendario

Estructura del JSON:
  Cada item: {
    "id": int,
    "nombre": str,
    "area": str | null,
    "descripcion": str | null,
    "frecuencia_dias": int,
    "ultimo_mantenimiento": str | null (ISO),
    "proximo_mantenimiento": str | null (ISO),
    "historial": [{"fecha": str, "nota": str | null}],
    "fecha_creado": str (ISO)
  }
"""
import json
import os
from datetime import datetime, timedelta
from logger import get_logger

logger = get_logger("mantenimiento")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "mantenimiento.json")
_ARCHIVO_UBICACIONES = os.path.join(_DATA_DIR, "ubicaciones.json")
_ARCHIVO_CASA = os.path.join(_DATA_DIR, "distribucion_casa.json")


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


def _guardar(items: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _siguiente_id(items: list[dict]) -> int:
    return max((it["id"] for it in items), default=0) + 1


def _buscar(items: list[dict], nombre: str) -> dict | None:
    nombre_lower = nombre.lower().strip()
    for it in items:
        if it["nombre"].lower().strip() == nombre_lower:
            return it
    return None


def _calcular_proximo(ultimo: str, frecuencia_dias: int) -> str:
    fecha = datetime.fromisoformat(ultimo)
    proximo = fecha + timedelta(days=frecuencia_dias)
    return proximo.isoformat()


def _dias_restantes(proximo: str) -> int:
    """Dias hasta el proximo mantenimiento. Negativo = atrasado."""
    fecha = datetime.fromisoformat(proximo)
    delta = fecha - datetime.now()
    return delta.days


def _frecuencia_legible(dias: int) -> str:
    if dias == 1:
        return "diario"
    if dias == 7:
        return "semanal"
    if dias == 14:
        return "quincenal"
    if dias == 30:
        return "mensual"
    if dias == 60:
        return "bimestral"
    if dias == 90:
        return "trimestral"
    if dias == 180:
        return "semestral"
    if dias == 365:
        return "anual"
    return f"cada {dias} dias"


def _areas_registradas() -> list[str]:
    if not os.path.exists(_ARCHIVO_CASA):
        return []
    try:
        with open(_ARCHIVO_CASA, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [a["nombre"] for a in data if isinstance(a, dict)]
    except (json.JSONDecodeError, Exception):
        return []


# ── Operaciones ──────────────────────────────────────────────────────────────

def registrar(nombre: str, frecuencia_dias: int, area: str = None,
              descripcion: str = None, ultimo_mantenimiento: str = None) -> str:
    items = _cargar()
    existente = _buscar(items, nombre)
    if existente:
        return (f"'{existente['nombre']}' ya esta registrado "
                f"({_frecuencia_legible(existente['frecuencia_dias'])}).")

    ahora = datetime.now().isoformat()

    # Si no se indica ultimo mantenimiento, asumir que se hizo hoy
    ultimo = ultimo_mantenimiento or ahora
    proximo = _calcular_proximo(ultimo, frecuencia_dias)

    item = {
        "id": _siguiente_id(items),
        "nombre": nombre.strip(),
        "area": area,
        "descripcion": descripcion,
        "frecuencia_dias": frecuencia_dias,
        "ultimo_mantenimiento": ultimo,
        "proximo_mantenimiento": proximo,
        "historial": [{"fecha": ultimo, "nota": "Registro inicial"}],
        "fecha_creado": ahora,
    }
    items.append(item)
    _guardar(items)

    freq = _frecuencia_legible(frecuencia_dias)
    area_txt = f" ({area})" if area else ""
    proximo_fecha = proximo[:10]
    return (f"Mantenimiento registrado: '{nombre}'{area_txt}\n"
            f"  Frecuencia: {freq}\n"
            f"  Proximo: {proximo_fecha}")


def listar() -> str:
    items = _cargar()
    if not items:
        return "No hay items de mantenimiento registrados."

    # Agrupar por area
    por_area = {}
    for it in items:
        area = it.get("area") or "Sin area"
        por_area.setdefault(area, []).append(it)

    lineas = [f"Calendario de mantenimiento ({len(items)} items):"]
    for area, area_items in sorted(por_area.items()):
        lineas.append(f"\n  [{area}]")
        for it in sorted(area_items, key=lambda x: x.get("proximo_mantenimiento") or ""):
            freq = _frecuencia_legible(it["frecuencia_dias"])
            proximo = it.get("proximo_mantenimiento", "")[:10]
            dias = _dias_restantes(it["proximo_mantenimiento"]) if it.get("proximo_mantenimiento") else 0
            if dias < 0:
                estado = f"ATRASADO {abs(dias)}d"
            elif dias == 0:
                estado = "HOY"
            elif dias <= 7:
                estado = f"en {dias}d"
            else:
                estado = proximo
            n_hist = len(it.get("historial", []))
            lineas.append(f"    - {it['nombre']} ({freq}) -> {estado} [{n_hist} realizados]")

    return "\n".join(lineas)


def pendientes() -> str:
    items = _cargar()
    if not items:
        return "No hay items de mantenimiento registrados."

    ahora = datetime.now()
    atrasados = []
    proximos = []

    for it in items:
        if not it.get("proximo_mantenimiento"):
            continue
        dias = _dias_restantes(it["proximo_mantenimiento"])
        entry = {**it, "_dias": dias}
        if dias < 0:
            atrasados.append(entry)
        elif dias <= 7:
            proximos.append(entry)

    if not atrasados and not proximos:
        return "Todo al dia. No hay mantenimientos pendientes esta semana."

    lineas = []

    if atrasados:
        atrasados.sort(key=lambda x: x["_dias"])
        lineas.append(f"ATRASADOS ({len(atrasados)}):")
        for it in atrasados:
            area_txt = f" ({it['area']})" if it.get("area") else ""
            lineas.append(f"  ! {it['nombre']}{area_txt} — atrasado {abs(it['_dias'])} dias")

    if proximos:
        proximos.sort(key=lambda x: x["_dias"])
        lineas.append(f"\nPROXIMOS 7 DIAS ({len(proximos)}):")
        for it in proximos:
            area_txt = f" ({it['area']})" if it.get("area") else ""
            if it["_dias"] == 0:
                cuando = "HOY"
            elif it["_dias"] == 1:
                cuando = "manana"
            else:
                cuando = f"en {it['_dias']} dias"
            lineas.append(f"  - {it['nombre']}{area_txt} — {cuando}")

    return "\n".join(lineas)


def completar(nombre: str, nota: str = None) -> str:
    items = _cargar()
    item = _buscar(items, nombre)
    if not item:
        return f"'{nombre}' no esta en el calendario de mantenimiento."

    ahora = datetime.now().isoformat()
    item["ultimo_mantenimiento"] = ahora
    item["proximo_mantenimiento"] = _calcular_proximo(ahora, item["frecuencia_dias"])
    item["historial"].append({
        "fecha": ahora,
        "nota": nota,
    })
    _guardar(items)

    proximo = item["proximo_mantenimiento"][:10]
    freq = _frecuencia_legible(item["frecuencia_dias"])
    n_total = len(item["historial"])
    nota_txt = f"\n  Nota: {nota}" if nota else ""
    return (f"Mantenimiento completado: '{item['nombre']}'\n"
            f"  Realizado: {ahora[:10]}\n"
            f"  Proximo: {proximo} ({freq})\n"
            f"  Total realizados: {n_total}{nota_txt}")


def historial(nombre: str) -> str:
    items = _cargar()
    item = _buscar(items, nombre)
    if not item:
        return f"'{nombre}' no esta en el calendario de mantenimiento."

    hist = item.get("historial", [])
    if not hist:
        return f"'{item['nombre']}' no tiene historial de mantenimientos."

    lineas = [
        f"Historial de '{item['nombre']}' ({len(hist)} mantenimientos):",
        f"  Frecuencia: {_frecuencia_legible(item['frecuencia_dias'])}",
    ]
    if item.get("area"):
        lineas.append(f"  Area: {item['area']}")
    lineas.append("")

    for h in reversed(hist):
        fecha = h["fecha"][:10]
        nota = f" — {h['nota']}" if h.get("nota") else ""
        lineas.append(f"  {fecha}{nota}")

    return "\n".join(lineas)


def eliminar(nombre: str) -> str:
    items = _cargar()
    item = _buscar(items, nombre)
    if not item:
        return f"'{nombre}' no esta en el calendario de mantenimiento."

    items.remove(item)
    _guardar(items)
    return f"'{item['nombre']}' eliminado del calendario de mantenimiento."


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "registrar": registrar,
    "listar": listar,
    "pendientes": pendientes,
    "completar": completar,
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
        logger.error(f"mantenimiento.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
