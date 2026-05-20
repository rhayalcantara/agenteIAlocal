"""
Distribucion Casa Tool — Mapa de areas del hogar/oficina.

Registra las areas (sala, cocina, dormitorio, etc.) con foto y descripcion.
Sirve como base para la herramienta de ubicaciones de objetos.

Operaciones:
  agregar_area   — Registra un area nueva con nombre, descripcion y foto
  listar_areas   — Lista todas las areas registradas
  ver_area       — Detalle de un area (descripcion + foto)
  editar_area    — Modifica nombre, descripcion o foto de un area
  eliminar_area  — Elimina un area del mapa

Estructura del JSON:
  Cada area: {
    "id": int,
    "nombre": str,
    "descripcion": str | null,
    "imagen": str | null,
    "fecha_creado": str (ISO),
    "fecha_modificado": str (ISO)
  }
"""
import json
import os
import shutil
from datetime import datetime
from logger import get_logger

logger = get_logger("distribucion_casa")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "distribucion_casa.json")
_IMG_DIR = os.path.join(_DATA_DIR, "imagenes_casa")


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


def _guardar(areas: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(areas, f, ensure_ascii=False, indent=2)


def _siguiente_id(areas: list[dict]) -> int:
    return max((a["id"] for a in areas), default=0) + 1


def _buscar(areas: list[dict], nombre: str) -> dict | None:
    nombre_lower = nombre.lower().strip()
    for a in areas:
        if a["nombre"].lower().strip() == nombre_lower:
            return a
    return None


def _slug(nombre: str) -> str:
    return nombre.lower().strip().replace(" ", "_")


def _guardar_imagen(origen: str, nombre_area: str) -> str | None:
    if not origen or not os.path.exists(origen):
        return None
    os.makedirs(_IMG_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1] or ".jpg"
    destino = os.path.join(_IMG_DIR, f"{_slug(nombre_area)}{ext}")
    try:
        shutil.copy2(origen, destino)
        logger.info(f"Imagen de area guardada: {destino}")
        return destino
    except Exception as e:
        logger.warning(f"No se pudo guardar imagen de area: {e}")
        return None


def _eliminar_imagen(ruta: str | None):
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except Exception:
            pass


# ── Operaciones ──────────────────────────────────────────────────────────────

def agregar_area(nombre: str, descripcion: str = None, imagen: str = None) -> str:
    areas = _cargar()
    existente = _buscar(areas, nombre)
    if existente:
        return (f"El area '{existente['nombre']}' ya existe. "
                f"Usa editar_area para modificarla.")

    img_path = _guardar_imagen(imagen, nombre) if imagen else None
    ahora = datetime.now().isoformat()

    area = {
        "id": _siguiente_id(areas),
        "nombre": nombre.strip(),
        "descripcion": descripcion,
        "imagen": img_path,
        "fecha_creado": ahora,
        "fecha_modificado": ahora,
    }
    areas.append(area)
    _guardar(areas)

    img_txt = " (con foto)" if img_path else ""
    desc_txt = f" — {descripcion}" if descripcion else ""
    return f"Area registrada: '{nombre}'{desc_txt}{img_txt}"


def listar_areas() -> str:
    areas = _cargar()
    if not areas:
        return "No hay areas registradas. Empieza tomando fotos de cada area de tu casa."

    lineas = [f"Mapa de la casa ({len(areas)} areas):"]
    for a in areas:
        img = " [foto]" if a.get("imagen") else ""
        desc = f" — {a['descripcion']}" if a.get("descripcion") else ""
        lineas.append(f"  - {a['nombre']}{desc}{img}")

    return "\n".join(lineas)


def ver_area(nombre: str) -> str:
    areas = _cargar()
    area = _buscar(areas, nombre)
    if not area:
        disponibles = ", ".join(a["nombre"] for a in areas) or "ninguna"
        return f"Area '{nombre}' no encontrada. Areas disponibles: {disponibles}"

    lineas = [f"Area: {area['nombre']}"]
    if area.get("descripcion"):
        lineas.append(f"Descripcion: {area['descripcion']}")
    lineas.append(f"Registrada: {area['fecha_creado'][:10]}")
    if area.get("imagen") and os.path.exists(area["imagen"]):
        lineas.append(f"IMAGEN:{area['imagen']}")
    else:
        lineas.append("Sin foto")

    return "\n".join(lineas)


def editar_area(nombre: str, nuevo_nombre: str = None,
                descripcion: str = None, imagen: str = None) -> str:
    areas = _cargar()
    area = _buscar(areas, nombre)
    if not area:
        return f"Area '{nombre}' no encontrada."

    cambios = []

    if nuevo_nombre and nuevo_nombre.strip().lower() != area["nombre"].lower():
        # Verificar que el nuevo nombre no exista
        if _buscar(areas, nuevo_nombre):
            return f"Ya existe un area llamada '{nuevo_nombre}'."
        # Renombrar imagen si existe
        if area.get("imagen") and os.path.exists(area["imagen"]):
            nueva_img = _guardar_imagen(area["imagen"], nuevo_nombre)
            _eliminar_imagen(area["imagen"])
            area["imagen"] = nueva_img
        area["nombre"] = nuevo_nombre.strip()
        cambios.append(f"nombre → '{nuevo_nombre}'")

    if descripcion is not None:
        area["descripcion"] = descripcion
        cambios.append("descripcion actualizada")

    if imagen:
        img_path = _guardar_imagen(imagen, area["nombre"])
        if img_path:
            _eliminar_imagen(area.get("imagen"))
            area["imagen"] = img_path
            cambios.append("foto actualizada")

    if not cambios:
        return "No se especificaron cambios."

    area["fecha_modificado"] = datetime.now().isoformat()
    _guardar(areas)
    return f"Area '{area['nombre']}' actualizada: {', '.join(cambios)}"


def eliminar_area(nombre: str) -> str:
    areas = _cargar()
    area = _buscar(areas, nombre)
    if not area:
        return f"Area '{nombre}' no encontrada."

    _eliminar_imagen(area.get("imagen"))
    areas.remove(area)
    _guardar(areas)
    return f"Area '{area['nombre']}' eliminada del mapa."


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "agregar_area": agregar_area,
    "listar_areas": listar_areas,
    "ver_area": ver_area,
    "editar_area": editar_area,
    "eliminar_area": eliminar_area,
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
        logger.error(f"distribucion_casa.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
