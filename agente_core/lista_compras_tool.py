"""
Lista de Compras Tool — Backend para gestión de compras del supermercado.

Operaciones disponibles:
  agregar       — Agrega un item a la lista de compras (con imagen opcional)
  listar        — Lista items (todos, pendientes o comprados)
  comprado      — Marca un item como comprado
  eliminar      — Elimina un item de la lista
  estadisticas  — Resumen de compras: frecuencia, tasa de compra, etc.
  limpiar       — Elimina todos los items comprados (archivar ciclo)

Estructura del JSON:
  Cada item: {
    "id": int,
    "nombre": str,
    "categoria": str | null,
    "cantidad": int,
    "unidad": str | null,
    "estado": "pendiente" | "comprado",
    "imagen": str | null,        (ruta persistente de la foto del producto)
    "fecha_agregado": str (ISO),
    "fecha_comprado": str | null,
    "veces_agregado": int,
    "veces_comprado": int
  }
"""
import json
import os
import shutil
from datetime import datetime
from logger import get_logger

logger = get_logger("lista_compras")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "lista_compras.json")
_HISTORIAL = os.path.join(_DATA_DIR, "historial_compras.json")
_IMG_DIR = os.path.join(_DATA_DIR, "imagenes_compras")


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


def _cargar_historial() -> list[dict]:
    if not os.path.exists(_HISTORIAL):
        return []
    try:
        with open(_HISTORIAL, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, Exception):
        return []


def _guardar_historial(registros: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


def _siguiente_id(items: list[dict]) -> int:
    return max((it["id"] for it in items), default=0) + 1


def _buscar(items: list[dict], nombre: str) -> dict | None:
    nombre_lower = nombre.lower().strip()
    for it in items:
        if it["nombre"].lower().strip() == nombre_lower:
            return it
    return None


def _guardar_imagen(origen: str, nombre_item: str) -> str | None:
    """Copia una imagen temporal a almacenamiento permanente. Retorna la ruta destino."""
    if not origen or not os.path.exists(origen):
        return None
    os.makedirs(_IMG_DIR, exist_ok=True)
    # Nombre seguro: lowercase, sin espacios
    slug = nombre_item.lower().strip().replace(" ", "_")
    ext = os.path.splitext(origen)[1] or ".jpg"
    destino = os.path.join(_IMG_DIR, f"{slug}{ext}")
    try:
        shutil.copy2(origen, destino)
        logger.info(f"Imagen guardada: {destino}")
        return destino
    except Exception as e:
        logger.warning(f"No se pudo guardar imagen: {e}")
        return None


def _eliminar_imagen(ruta: str | None):
    """Elimina la imagen del disco si existe."""
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except Exception:
            pass


# ── Operaciones ──────────────────────────────────────────────────────────────

def agregar(nombre: str, cantidad: int = 1, unidad: str = None,
            categoria: str = None, imagen: str = None) -> str:
    items = _cargar()
    existente = _buscar(items, nombre)

    # Guardar imagen si viene una
    img_path = _guardar_imagen(imagen, nombre) if imagen else None

    if existente:
        # Actualizar imagen si se proporciona una nueva
        if img_path:
            _eliminar_imagen(existente.get("imagen"))
            existente["imagen"] = img_path

        # Si ya existe y está pendiente, solo actualizar cantidad
        if existente["estado"] == "pendiente":
            existente["cantidad"] += cantidad
            existente["veces_agregado"] += 1
            _guardar(items)
            img_txt = " (imagen actualizada)" if img_path else ""
            return (f"'{existente['nombre']}' ya estaba en la lista. "
                    f"Cantidad actualizada a {existente['cantidad']}.{img_txt}")
        # Si existe pero ya fue comprado, re-activarlo como pendiente
        existente["estado"] = "pendiente"
        existente["cantidad"] = cantidad
        existente["fecha_comprado"] = None
        existente["veces_agregado"] += 1
        if categoria:
            existente["categoria"] = categoria
        _guardar(items)
        return f"'{existente['nombre']}' reactivado como pendiente (cantidad: {cantidad})."

    nuevo = {
        "id": _siguiente_id(items),
        "nombre": nombre.strip(),
        "categoria": categoria,
        "cantidad": cantidad,
        "unidad": unidad,
        "estado": "pendiente",
        "imagen": img_path,
        "fecha_agregado": datetime.now().isoformat(),
        "fecha_comprado": None,
        "veces_agregado": 1,
        "veces_comprado": 0,
    }
    items.append(nuevo)
    _guardar(items)
    cant_txt = f" ({cantidad} {unidad})" if unidad else (f" (x{cantidad})" if cantidad > 1 else "")
    cat_txt = f" [{categoria}]" if categoria else ""
    img_txt = " (con foto)" if img_path else ""
    return f"Agregado: '{nombre}'{cant_txt}{cat_txt}{img_txt}"


def listar(filtro: str = "todos") -> str:
    items = _cargar()
    if not items:
        return "La lista de compras esta vacia."

    if filtro == "pendientes":
        items = [it for it in items if it["estado"] == "pendiente"]
        titulo = "Items pendientes"
    elif filtro == "comprados":
        items = [it for it in items if it["estado"] == "comprado"]
        titulo = "Items comprados"
    else:
        titulo = "Lista de compras"

    if not items:
        return f"No hay items {filtro}."

    # Agrupar por categoria
    por_categoria = {}
    for it in items:
        cat = it.get("categoria") or "Sin categoria"
        por_categoria.setdefault(cat, []).append(it)

    lineas = [f"{titulo} ({len(items)} items):"]
    for cat, cat_items in sorted(por_categoria.items()):
        lineas.append(f"\n  [{cat}]")
        for it in cat_items:
            estado = "v" if it["estado"] == "comprado" else " "
            cant = ""
            if it.get("unidad"):
                cant = f" ({it['cantidad']} {it['unidad']})"
            elif it["cantidad"] > 1:
                cant = f" (x{it['cantidad']})"
            img = " [foto]" if it.get("imagen") else ""
            lineas.append(f"    [{estado}] {it['nombre']}{cant}{img}")

    return "\n".join(lineas)


def comprado(nombre: str) -> str:
    items = _cargar()
    item = _buscar(items, nombre)
    if not item:
        return f"'{nombre}' no esta en la lista. Usa listar para ver los items disponibles."
    if item["estado"] == "comprado":
        return f"'{item['nombre']}' ya estaba marcado como comprado."

    item["estado"] = "comprado"
    item["fecha_comprado"] = datetime.now().isoformat()
    item["veces_comprado"] += 1
    _guardar(items)

    # Registrar en historial
    historial = _cargar_historial()
    historial.append({
        "nombre": item["nombre"],
        "categoria": item.get("categoria"),
        "cantidad": item["cantidad"],
        "unidad": item.get("unidad"),
        "fecha": datetime.now().isoformat(),
    })
    _guardar_historial(historial)

    pendientes = sum(1 for it in items if it["estado"] == "pendiente")
    return f"'{item['nombre']}' marcado como comprado. Quedan {pendientes} items pendientes."


def ver_imagen(nombre: str) -> str:
    items = _cargar()
    item = _buscar(items, nombre)
    if not item:
        return f"'{nombre}' no esta en la lista."
    img = item.get("imagen")
    if not img or not os.path.exists(img):
        return f"'{item['nombre']}' no tiene imagen guardada."
    return f"IMAGEN:{img}"


def eliminar(nombre: str) -> str:
    items = _cargar()
    item = _buscar(items, nombre)
    if not item:
        return f"'{nombre}' no esta en la lista."

    _eliminar_imagen(item.get("imagen"))
    items.remove(item)
    _guardar(items)
    return f"'{item['nombre']}' eliminado de la lista."


def estadisticas() -> str:
    items = _cargar()
    historial = _cargar_historial()

    total = len(items)
    pendientes = sum(1 for it in items if it["estado"] == "pendiente")
    comprados = sum(1 for it in items if it["estado"] == "comprado")

    lineas = [
        "Estadisticas de compras:",
        f"  Lista actual: {total} items ({pendientes} pendientes, {comprados} comprados)",
    ]

    if historial:
        lineas.append(f"  Compras historicas: {len(historial)} items comprados en total")

        # Productos mas frecuentes
        frecuencia = {}
        for reg in historial:
            n = reg["nombre"]
            frecuencia[n] = frecuencia.get(n, 0) + 1
        top = sorted(frecuencia.items(), key=lambda x: x[1], reverse=True)[:5]
        lineas.append("\n  Top 5 productos mas comprados:")
        for nombre, veces in top:
            lineas.append(f"    {nombre}: {veces} veces")

        # Categorias mas frecuentes
        cat_freq = {}
        for reg in historial:
            cat = reg.get("categoria") or "Sin categoria"
            cat_freq[cat] = cat_freq.get(cat, 0) + 1
        top_cat = sorted(cat_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        lineas.append("\n  Top categorias:")
        for cat, veces in top_cat:
            lineas.append(f"    {cat}: {veces} items")

    # Items que se agregan pero no se compran (tasa de abandono)
    nunca_comprados = [it for it in items if it["veces_comprado"] == 0 and it["veces_agregado"] >= 2]
    if nunca_comprados:
        lineas.append("\n  Items que agregas pero nunca compras:")
        for it in nunca_comprados[:5]:
            lineas.append(f"    {it['nombre']} (agregado {it['veces_agregado']} veces, comprado 0)")

    return "\n".join(lineas)


def limpiar() -> str:
    items = _cargar()
    antes = len(items)
    items = [it for it in items if it["estado"] != "comprado"]
    eliminados = antes - len(items)
    _guardar(items)
    if eliminados == 0:
        return "No habia items comprados para limpiar."
    return f"Limpieza completada: {eliminados} items comprados eliminados. Quedan {len(items)} pendientes."


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "agregar": agregar,
    "listar": listar,
    "comprado": comprado,
    "ver_imagen": ver_imagen,
    "eliminar": eliminar,
    "estadisticas": estadisticas,
    "limpiar": limpiar,
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
        logger.error(f"lista_compras.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
