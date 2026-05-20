"""
Ubicaciones Tool — Registro de objetos y su ubicacion en la casa/oficina.

Vinculado a distribucion_casa_tool: cada objeto se asocia a un area registrada.

Operaciones:
  registrar     — Registra un objeto con area, lugar exacto, descripcion y foto
  buscar        — Busca un objeto por nombre (parcial)
  listar        — Lista objetos (todos o filtrados por area)
  mover         — Cambia la ubicacion de un objeto a otra area/lugar
  eliminar      — Elimina un objeto del registro
  resumen       — Resumen por areas: cuantos objetos hay en cada una

Estructura del JSON:
  Cada objeto: {
    "id": int,
    "nombre": str,
    "area": str,
    "lugar_exacto": str | null,
    "descripcion": str | null,
    "imagen": str | null,
    "fecha_registrado": str (ISO),
    "fecha_movido": str | null,
    "historial_movimientos": [{"area": str, "lugar": str, "fecha": str}]
  }
"""
import json
import os
import shutil
from datetime import datetime
from logger import get_logger

logger = get_logger("ubicaciones")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "ubicaciones.json")
_IMG_DIR = os.path.join(_DATA_DIR, "imagenes_ubicaciones")
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


def _guardar(objetos: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(objetos, f, ensure_ascii=False, indent=2)


def _areas_registradas() -> list[str]:
    """Lee las areas de distribucion_casa.json."""
    if not os.path.exists(_ARCHIVO_CASA):
        return []
    try:
        with open(_ARCHIVO_CASA, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [a["nombre"] for a in data if isinstance(a, dict)]
    except (json.JSONDecodeError, Exception):
        return []


def _validar_area(area: str) -> str | None:
    """Valida que el area exista. Retorna mensaje de error o None si es valida."""
    areas = _areas_registradas()
    if not areas:
        return None  # Sin mapa registrado, aceptar cualquier area
    area_lower = area.lower().strip()
    for a in areas:
        if a.lower().strip() == area_lower:
            return None
    return (f"Area '{area}' no esta en el mapa. "
            f"Areas registradas: {', '.join(areas)}. "
            f"Usa distribucion_casa para agregar areas nuevas.")


def _siguiente_id(objetos: list[dict]) -> int:
    return max((o["id"] for o in objetos), default=0) + 1


def _buscar_exacto(objetos: list[dict], nombre: str) -> dict | None:
    nombre_lower = nombre.lower().strip()
    for o in objetos:
        if o["nombre"].lower().strip() == nombre_lower:
            return o
    return None


def _buscar_parcial(objetos: list[dict], texto: str) -> list[dict]:
    texto_lower = texto.lower().strip()
    return [o for o in objetos if texto_lower in o["nombre"].lower()]


def _slug(nombre: str) -> str:
    return nombre.lower().strip().replace(" ", "_")


def _guardar_imagen(origen: str, nombre_obj: str) -> str | None:
    if not origen or not os.path.exists(origen):
        return None
    os.makedirs(_IMG_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1] or ".jpg"
    destino = os.path.join(_IMG_DIR, f"{_slug(nombre_obj)}{ext}")
    try:
        shutil.copy2(origen, destino)
        logger.info(f"Imagen de objeto guardada: {destino}")
        return destino
    except Exception as e:
        logger.warning(f"No se pudo guardar imagen: {e}")
        return None


def _eliminar_imagen(ruta: str | None):
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except Exception:
            pass


# ── Operaciones ──────────────────────────────────────────────────────────────

def registrar(nombre: str, area: str, lugar_exacto: str = None,
              descripcion: str = None, imagen: str = None) -> str:
    # Validar area
    error_area = _validar_area(area)
    if error_area:
        return error_area

    objetos = _cargar()
    existente = _buscar_exacto(objetos, nombre)
    if existente:
        return (f"'{existente['nombre']}' ya esta registrado en "
                f"'{existente['area']}'"
                f"{(' (' + existente['lugar_exacto'] + ')') if existente.get('lugar_exacto') else ''}. "
                f"Usa mover para cambiar su ubicacion.")

    img_path = _guardar_imagen(imagen, nombre) if imagen else None
    ahora = datetime.now().isoformat()

    obj = {
        "id": _siguiente_id(objetos),
        "nombre": nombre.strip(),
        "area": area.strip(),
        "lugar_exacto": lugar_exacto,
        "descripcion": descripcion,
        "imagen": img_path,
        "fecha_registrado": ahora,
        "fecha_movido": None,
        "historial_movimientos": [],
    }
    objetos.append(obj)
    _guardar(objetos)

    lugar_txt = f", {lugar_exacto}" if lugar_exacto else ""
    img_txt = " (con foto)" if img_path else ""
    return f"Registrado: '{nombre}' en {area}{lugar_txt}{img_txt}"


def buscar(nombre: str) -> str:
    objetos = _cargar()
    # Primero intentar coincidencia exacta
    exacto = _buscar_exacto(objetos, nombre)
    if exacto:
        lineas = [f"'{exacto['nombre']}':"]
        lineas.append(f"  Area: {exacto['area']}")
        if exacto.get("lugar_exacto"):
            lineas.append(f"  Lugar exacto: {exacto['lugar_exacto']}")
        if exacto.get("descripcion"):
            lineas.append(f"  Descripcion: {exacto['descripcion']}")
        img = " [foto disponible]" if exacto.get("imagen") else ""
        lineas.append(f"  Registrado: {exacto['fecha_registrado'][:10]}{img}")
        if exacto.get("fecha_movido"):
            lineas.append(f"  Ultimo movimiento: {exacto['fecha_movido'][:10]}")
        if exacto.get("imagen") and os.path.exists(exacto["imagen"]):
            lineas.append(f"IMAGEN:{exacto['imagen']}")
        return "\n".join(lineas)

    # Busqueda parcial
    resultados = _buscar_parcial(objetos, nombre)
    if not resultados:
        return f"No se encontro '{nombre}'. Usa listar para ver todos los objetos registrados."

    lineas = [f"Encontrados {len(resultados)} objetos con '{nombre}':"]
    for o in resultados:
        lugar = f" ({o['lugar_exacto']})" if o.get("lugar_exacto") else ""
        img = " [foto]" if o.get("imagen") else ""
        lineas.append(f"  - {o['nombre']} -> {o['area']}{lugar}{img}")
    return "\n".join(lineas)


def listar(area: str = None) -> str:
    objetos = _cargar()
    if not objetos:
        return "No hay objetos registrados."

    if area:
        area_lower = area.lower().strip()
        objetos = [o for o in objetos if o["area"].lower().strip() == area_lower]
        if not objetos:
            return f"No hay objetos registrados en '{area}'."
        titulo = f"Objetos en {area}"
    else:
        titulo = "Todos los objetos registrados"

    # Agrupar por area
    por_area = {}
    for o in objetos:
        por_area.setdefault(o["area"], []).append(o)

    lineas = [f"{titulo} ({len(objetos)} objetos):"]
    for area_nombre, area_objetos in sorted(por_area.items()):
        lineas.append(f"\n  [{area_nombre}]")
        for o in area_objetos:
            lugar = f" ({o['lugar_exacto']})" if o.get("lugar_exacto") else ""
            img = " [foto]" if o.get("imagen") else ""
            lineas.append(f"    - {o['nombre']}{lugar}{img}")

    return "\n".join(lineas)


def mover(nombre: str, area: str, lugar_exacto: str = None,
          imagen: str = None) -> str:
    # Validar area destino
    error_area = _validar_area(area)
    if error_area:
        return error_area

    objetos = _cargar()
    obj = _buscar_exacto(objetos, nombre)
    if not obj:
        return f"'{nombre}' no esta registrado. Usa registrar para agregarlo."

    area_anterior = obj["area"]
    lugar_anterior = obj.get("lugar_exacto", "")

    # Registrar movimiento en historial
    obj["historial_movimientos"].append({
        "area": area_anterior,
        "lugar": lugar_anterior,
        "fecha": datetime.now().isoformat(),
    })

    obj["area"] = area.strip()
    obj["lugar_exacto"] = lugar_exacto
    obj["fecha_movido"] = datetime.now().isoformat()

    # Actualizar imagen si se proporciona
    if imagen:
        img_path = _guardar_imagen(imagen, nombre)
        if img_path:
            _eliminar_imagen(obj.get("imagen"))
            obj["imagen"] = img_path

    _guardar(objetos)

    lugar_txt = f", {lugar_exacto}" if lugar_exacto else ""
    return (f"'{obj['nombre']}' movido: {area_anterior} -> {area}{lugar_txt}")


def eliminar(nombre: str) -> str:
    objetos = _cargar()
    obj = _buscar_exacto(objetos, nombre)
    if not obj:
        return f"'{nombre}' no esta registrado."

    _eliminar_imagen(obj.get("imagen"))
    objetos.remove(obj)
    _guardar(objetos)
    return f"'{obj['nombre']}' eliminado del registro."


def resumen() -> str:
    objetos = _cargar()
    if not objetos:
        return "No hay objetos registrados."

    por_area = {}
    for o in objetos:
        por_area.setdefault(o["area"], []).append(o)

    con_foto = sum(1 for o in objetos if o.get("imagen"))
    con_historial = sum(1 for o in objetos if o.get("historial_movimientos"))

    lineas = [
        f"Resumen de ubicaciones ({len(objetos)} objetos en {len(por_area)} areas):",
        f"  Con foto: {con_foto} | Con movimientos previos: {con_historial}",
        "",
    ]
    for area_nombre, area_objetos in sorted(por_area.items(), key=lambda x: -len(x[1])):
        lineas.append(f"  {area_nombre}: {len(area_objetos)} objetos")

    # Objetos mas movidos
    movidos = sorted(objetos, key=lambda o: len(o.get("historial_movimientos", [])), reverse=True)
    top_movidos = [o for o in movidos[:5] if o.get("historial_movimientos")]
    if top_movidos:
        lineas.append("\n  Objetos mas reubicados:")
        for o in top_movidos:
            n_mov = len(o["historial_movimientos"])
            lineas.append(f"    {o['nombre']}: {n_mov} movimiento(s), ahora en {o['area']}")

    return "\n".join(lineas)


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "registrar": registrar,
    "buscar": buscar,
    "listar": listar,
    "mover": mover,
    "eliminar": eliminar,
    "resumen": resumen,
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
        logger.error(f"ubicaciones.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
