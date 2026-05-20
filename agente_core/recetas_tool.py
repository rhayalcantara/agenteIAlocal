"""
Recetas Tool — Registro de recetas con cruce a lista de compras.

Operaciones:
  agregar         — Guarda una receta con nombre, ingredientes, pasos y foto
  ver             — Muestra una receta completa
  listar          — Lista todas las recetas (o filtrar por categoria/ingrediente)
  editar          — Modifica una receta existente
  eliminar        — Elimina una receta
  que_cocinar     — Sugiere recetas segun ingredientes que ya tienes en lista_compras
  preparar        — Marca receta para preparar: revisa ingredientes y agrega faltantes a lista_compras
  favoritas       — Muestra las recetas mas preparadas

Estructura del JSON:
  Cada receta: {
    "id": int,
    "nombre": str,
    "categoria": str | null,       (desayuno, almuerzo, cena, postre, snack, etc.)
    "porciones": int | null,
    "ingredientes": [{"nombre": str, "cantidad": str | null, "unidad": str | null}],
    "pasos": [str],
    "imagen": str | null,
    "fecha_creada": str (ISO),
    "veces_preparada": int,
    "ultima_preparacion": str | null
  }
"""
import json
import os
import shutil
from datetime import datetime
from logger import get_logger

logger = get_logger("recetas")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "recetas.json")
_IMG_DIR = os.path.join(_DATA_DIR, "imagenes_recetas")
_ARCHIVO_COMPRAS = os.path.join(_DATA_DIR, "lista_compras.json")


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


def _guardar(recetas: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(recetas, f, ensure_ascii=False, indent=2)


def _cargar_compras() -> list[dict]:
    if not os.path.exists(_ARCHIVO_COMPRAS):
        return []
    try:
        with open(_ARCHIVO_COMPRAS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, Exception):
        return []


def _siguiente_id(recetas: list[dict]) -> int:
    return max((r["id"] for r in recetas), default=0) + 1


def _buscar(recetas: list[dict], nombre: str) -> dict | None:
    nombre_lower = nombre.lower().strip()
    for r in recetas:
        if r["nombre"].lower().strip() == nombre_lower:
            return r
    return None


def _slug(nombre: str) -> str:
    return nombre.lower().strip().replace(" ", "_")


def _guardar_imagen(origen: str, nombre_receta: str) -> str | None:
    if not origen or not os.path.exists(origen):
        return None
    os.makedirs(_IMG_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1] or ".jpg"
    destino = os.path.join(_IMG_DIR, f"{_slug(nombre_receta)}{ext}")
    try:
        shutil.copy2(origen, destino)
        logger.info(f"Imagen de receta guardada: {destino}")
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


def _agregar_a_compras(nombre_item: str, cantidad: str = None,
                       unidad: str = None, categoria: str = "Recetas") -> str:
    """Agrega un ingrediente a lista_compras usando el tool directamente."""
    try:
        from lista_compras_tool import ejecutar as compras_ejecutar
        kwargs = {"nombre": nombre_item, "categoria": categoria}
        if cantidad and cantidad.isdigit():
            kwargs["cantidad"] = int(cantidad)
        if unidad:
            kwargs["unidad"] = unidad
        return compras_ejecutar("agregar", **kwargs)
    except Exception as e:
        return f"Error agregando '{nombre_item}' a la lista: {e}"


# ── Operaciones ──────────────────────────────────────────────────────────────

def agregar(nombre: str, ingredientes: list = None, pasos: list = None,
            categoria: str = None, porciones: int = None,
            imagen: str = None) -> str:
    recetas = _cargar()
    existente = _buscar(recetas, nombre)
    if existente:
        return f"La receta '{existente['nombre']}' ya existe. Usa editar para modificarla."

    img_path = _guardar_imagen(imagen, nombre) if imagen else None

    receta = {
        "id": _siguiente_id(recetas),
        "nombre": nombre.strip(),
        "categoria": categoria,
        "porciones": porciones,
        "ingredientes": ingredientes or [],
        "pasos": pasos or [],
        "imagen": img_path,
        "fecha_creada": datetime.now().isoformat(),
        "veces_preparada": 0,
        "ultima_preparacion": None,
    }
    recetas.append(receta)
    _guardar(recetas)

    n_ing = len(receta["ingredientes"])
    n_pasos = len(receta["pasos"])
    img_txt = " (con foto)" if img_path else ""
    cat_txt = f" [{categoria}]" if categoria else ""
    return (f"Receta guardada: '{nombre}'{cat_txt}{img_txt}\n"
            f"  {n_ing} ingredientes, {n_pasos} pasos")


def ver(nombre: str) -> str:
    recetas = _cargar()
    receta = _buscar(recetas, nombre)
    if not receta:
        return f"Receta '{nombre}' no encontrada. Usa listar para ver las disponibles."

    lineas = [f"--- {receta['nombre']} ---"]
    if receta.get("categoria"):
        lineas.append(f"Categoria: {receta['categoria']}")
    if receta.get("porciones"):
        lineas.append(f"Porciones: {receta['porciones']}")
    lineas.append(f"Preparada: {receta['veces_preparada']} veces")

    if receta["ingredientes"]:
        lineas.append("\nIngredientes:")
        for ing in receta["ingredientes"]:
            cant = f"{ing.get('cantidad', '')} " if ing.get("cantidad") else ""
            unid = f"{ing.get('unidad', '')} " if ing.get("unidad") else ""
            lineas.append(f"  - {cant}{unid}{ing['nombre']}")

    if receta["pasos"]:
        lineas.append("\nPreparacion:")
        for i, paso in enumerate(receta["pasos"], 1):
            lineas.append(f"  {i}. {paso}")

    if receta.get("imagen") and os.path.exists(receta["imagen"]):
        lineas.append(f"\nIMAGEN:{receta['imagen']}")

    return "\n".join(lineas)


def listar(categoria: str = None, ingrediente: str = None) -> str:
    recetas = _cargar()
    if not recetas:
        return "No hay recetas guardadas."

    if categoria:
        cat_lower = categoria.lower().strip()
        recetas = [r for r in recetas if (r.get("categoria") or "").lower() == cat_lower]
        if not recetas:
            return f"No hay recetas en la categoria '{categoria}'."

    if ingrediente:
        ing_lower = ingrediente.lower().strip()
        recetas = [r for r in recetas
                   if any(ing_lower in i["nombre"].lower() for i in r.get("ingredientes", []))]
        if not recetas:
            return f"No hay recetas con el ingrediente '{ingrediente}'."

    # Agrupar por categoria
    por_cat = {}
    for r in recetas:
        cat = r.get("categoria") or "Sin categoria"
        por_cat.setdefault(cat, []).append(r)

    lineas = [f"Recetas ({len(recetas)}):"]
    for cat, cat_recetas in sorted(por_cat.items()):
        lineas.append(f"\n  [{cat}]")
        for r in cat_recetas:
            n_ing = len(r.get("ingredientes", []))
            img = " [foto]" if r.get("imagen") else ""
            prep = f" (preparada {r['veces_preparada']}x)" if r["veces_preparada"] > 0 else ""
            lineas.append(f"    - {r['nombre']} ({n_ing} ing.){prep}{img}")

    return "\n".join(lineas)


def editar(nombre: str, nuevo_nombre: str = None, ingredientes: list = None,
           pasos: list = None, categoria: str = None, porciones: int = None,
           imagen: str = None) -> str:
    recetas = _cargar()
    receta = _buscar(recetas, nombre)
    if not receta:
        return f"Receta '{nombre}' no encontrada."

    cambios = []

    if nuevo_nombre and nuevo_nombre.strip().lower() != receta["nombre"].lower():
        if _buscar(recetas, nuevo_nombre):
            return f"Ya existe una receta llamada '{nuevo_nombre}'."
        if receta.get("imagen") and os.path.exists(receta["imagen"]):
            nueva_img = _guardar_imagen(receta["imagen"], nuevo_nombre)
            _eliminar_imagen(receta["imagen"])
            receta["imagen"] = nueva_img
        receta["nombre"] = nuevo_nombre.strip()
        cambios.append(f"nombre -> '{nuevo_nombre}'")

    if ingredientes is not None:
        receta["ingredientes"] = ingredientes
        cambios.append(f"{len(ingredientes)} ingredientes")

    if pasos is not None:
        receta["pasos"] = pasos
        cambios.append(f"{len(pasos)} pasos")

    if categoria is not None:
        receta["categoria"] = categoria
        cambios.append(f"categoria -> '{categoria}'")

    if porciones is not None:
        receta["porciones"] = porciones
        cambios.append(f"porciones -> {porciones}")

    if imagen:
        img_path = _guardar_imagen(imagen, receta["nombre"])
        if img_path:
            _eliminar_imagen(receta.get("imagen"))
            receta["imagen"] = img_path
            cambios.append("foto actualizada")

    if not cambios:
        return "No se especificaron cambios."

    _guardar(recetas)
    return f"Receta '{receta['nombre']}' actualizada: {', '.join(cambios)}"


def eliminar(nombre: str) -> str:
    recetas = _cargar()
    receta = _buscar(recetas, nombre)
    if not receta:
        return f"Receta '{nombre}' no encontrada."

    _eliminar_imagen(receta.get("imagen"))
    recetas.remove(receta)
    _guardar(recetas)
    return f"Receta '{receta['nombre']}' eliminada."


def que_cocinar() -> str:
    """Sugiere recetas basandose en los ingredientes disponibles en lista_compras."""
    recetas = _cargar()
    if not recetas:
        return "No hay recetas guardadas."

    compras = _cargar_compras()
    if not compras:
        return "La lista de compras esta vacia. No puedo cruzar ingredientes."

    # Nombres de items en la lista (pendientes y comprados)
    items_compras = {it["nombre"].lower().strip() for it in compras}

    resultados = []
    for r in recetas:
        ings = r.get("ingredientes", [])
        if not ings:
            continue
        nombres_ing = [i["nombre"].lower().strip() for i in ings]
        disponibles = [n for n in nombres_ing if any(n in item or item in n for item in items_compras)]
        faltantes = [n for n in nombres_ing if n not in [d for d in disponibles]]
        pct = len(disponibles) / len(nombres_ing) * 100

        if disponibles:  # al menos un ingrediente coincide
            resultados.append({
                "receta": r["nombre"],
                "total": len(nombres_ing),
                "tienes": len(disponibles),
                "faltan": len(faltantes),
                "pct": pct,
                "faltantes": faltantes,
            })

    if not resultados:
        return "Ninguna receta coincide con los ingredientes de tu lista de compras."

    resultados.sort(key=lambda x: x["pct"], reverse=True)

    lineas = ["Recetas que puedes preparar:\n"]
    for r in resultados[:10]:
        barra = "=" * int(r["pct"] / 10) + "-" * (10 - int(r["pct"] / 10))
        lineas.append(f"  {r['receta']} [{barra}] {r['pct']:.0f}%")
        lineas.append(f"    Tienes {r['tienes']}/{r['total']} ingredientes")
        if r["faltantes"]:
            lineas.append(f"    Faltan: {', '.join(r['faltantes'][:5])}")
        lineas.append("")

    return "\n".join(lineas)


def preparar(nombre: str) -> str:
    """Marca receta para preparar: revisa ingredientes y agrega faltantes a lista_compras."""
    recetas = _cargar()
    receta = _buscar(recetas, nombre)
    if not receta:
        return f"Receta '{nombre}' no encontrada."

    ings = receta.get("ingredientes", [])
    if not ings:
        return f"La receta '{receta['nombre']}' no tiene ingredientes registrados."

    compras = _cargar_compras()
    items_compras = {it["nombre"].lower().strip() for it in compras}

    agregados = []
    ya_tienes = []

    for ing in ings:
        nombre_ing = ing["nombre"].strip()
        # Verificar si ya esta en la lista (match parcial)
        if any(nombre_ing.lower() in item or item in nombre_ing.lower() for item in items_compras):
            ya_tienes.append(nombre_ing)
        else:
            resultado = _agregar_a_compras(
                nombre_ing,
                cantidad=ing.get("cantidad"),
                unidad=ing.get("unidad"),
            )
            agregados.append(nombre_ing)

    # Actualizar contador de preparaciones
    receta["veces_preparada"] += 1
    receta["ultima_preparacion"] = datetime.now().isoformat()
    _guardar(recetas)

    lineas = [f"Preparando: '{receta['nombre']}'"]
    if ya_tienes:
        lineas.append(f"\n  Ya tienes ({len(ya_tienes)}):")
        for item in ya_tienes:
            lineas.append(f"    [v] {item}")
    if agregados:
        lineas.append(f"\n  Agregados a lista de compras ({len(agregados)}):")
        for item in agregados:
            lineas.append(f"    [+] {item}")
    if not agregados:
        lineas.append("\n  Tienes todos los ingredientes!")

    lineas.append(f"\n  Preparacion #{receta['veces_preparada']} de esta receta.")
    return "\n".join(lineas)


def favoritas() -> str:
    recetas = _cargar()
    preparadas = [r for r in recetas if r["veces_preparada"] > 0]
    if not preparadas:
        return "Aun no has marcado ninguna receta como preparada."

    preparadas.sort(key=lambda r: r["veces_preparada"], reverse=True)

    lineas = [f"Recetas favoritas ({len(preparadas)} preparadas):"]
    for r in preparadas[:10]:
        ultima = r.get("ultima_preparacion", "")[:10] if r.get("ultima_preparacion") else "?"
        img = " [foto]" if r.get("imagen") else ""
        lineas.append(f"  {r['veces_preparada']}x  {r['nombre']} (ultima: {ultima}){img}")

    return "\n".join(lineas)


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "agregar": agregar,
    "ver": ver,
    "listar": listar,
    "editar": editar,
    "eliminar": eliminar,
    "que_cocinar": que_cocinar,
    "preparar": preparar,
    "favoritas": favoritas,
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
        logger.error(f"recetas.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
