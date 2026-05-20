"""
Documentos Tool — Registro de documentos importantes y su ubicacion fisica.

Vinculado a distribucion_casa: cada documento se asocia a un area.

Operaciones:
  registrar    — Registra un documento con tipo, ubicacion fisica, descripcion y foto
  buscar       — Busca un documento por nombre o tipo (parcial)
  listar       — Lista documentos (todos o filtrar por tipo/area)
  ver          — Detalle completo de un documento con foto
  mover        — Cambia la ubicacion de un documento
  eliminar     — Elimina un documento del registro

Estructura del JSON:
  Cada documento: {
    "id": int,
    "nombre": str,
    "tipo": str,                    (legal, financiero, medico, vehiculo, hogar, personal, etc.)
    "area": str | null,
    "ubicacion_exacta": str | null,  (carpeta azul, gaveta 2, sobre manila, etc.)
    "descripcion": str | null,
    "imagen": str | null,
    "fecha_registrado": str (ISO),
    "fecha_vencimiento": str | null, (para docs con vencimiento)
    "historial_movimientos": [{"area": str, "ubicacion": str, "fecha": str}]
  }
"""
import json
import os
import shutil
from datetime import datetime
from logger import get_logger

logger = get_logger("documentos")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "documentos.json")
_IMG_DIR = os.path.join(_DATA_DIR, "imagenes_documentos")
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


def _guardar(docs: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)


def _siguiente_id(docs: list[dict]) -> int:
    return max((d["id"] for d in docs), default=0) + 1


def _buscar_exacto(docs: list[dict], nombre: str) -> dict | None:
    nombre_lower = nombre.lower().strip()
    for d in docs:
        if d["nombre"].lower().strip() == nombre_lower:
            return d
    return None


def _buscar_parcial(docs: list[dict], texto: str) -> list[dict]:
    texto_lower = texto.lower().strip()
    return [d for d in docs
            if texto_lower in d["nombre"].lower()
            or texto_lower in (d.get("tipo") or "").lower()
            or texto_lower in (d.get("descripcion") or "").lower()]


def _slug(nombre: str) -> str:
    return nombre.lower().strip().replace(" ", "_")


def _guardar_imagen(origen: str, nombre_doc: str) -> str | None:
    if not origen or not os.path.exists(origen):
        return None
    os.makedirs(_IMG_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1] or ".jpg"
    destino = os.path.join(_IMG_DIR, f"{_slug(nombre_doc)}{ext}")
    try:
        shutil.copy2(origen, destino)
        return destino
    except Exception as e:
        logger.warning(f"No se pudo guardar imagen de documento: {e}")
        return None


def _eliminar_imagen(ruta: str | None):
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except Exception:
            pass


def _areas_registradas() -> list[str]:
    if not os.path.exists(_ARCHIVO_CASA):
        return []
    try:
        with open(_ARCHIVO_CASA, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [a["nombre"] for a in data if isinstance(a, dict)]
    except (json.JSONDecodeError, Exception):
        return []


def _dias_para_vencer(fecha_venc: str) -> int | None:
    if not fecha_venc:
        return None
    try:
        venc = datetime.fromisoformat(fecha_venc)
        return (venc - datetime.now()).days
    except ValueError:
        return None


# ── Operaciones ──────────────────────────────────────────────────────────────

def registrar(nombre: str, tipo: str, area: str = None,
              ubicacion_exacta: str = None, descripcion: str = None,
              fecha_vencimiento: str = None, imagen: str = None) -> str:
    docs = _cargar()
    existente = _buscar_exacto(docs, nombre)
    if existente:
        return (f"'{existente['nombre']}' ya esta registrado en "
                f"'{existente.get('area', '?')}'. Usa mover para cambiar ubicacion.")

    img_path = _guardar_imagen(imagen, nombre) if imagen else None

    doc = {
        "id": _siguiente_id(docs),
        "nombre": nombre.strip(),
        "tipo": tipo.strip(),
        "area": area,
        "ubicacion_exacta": ubicacion_exacta,
        "descripcion": descripcion,
        "imagen": img_path,
        "fecha_registrado": datetime.now().isoformat(),
        "fecha_vencimiento": fecha_vencimiento,
        "historial_movimientos": [],
    }
    docs.append(doc)
    _guardar(docs)

    ubic = f" en {area}" if area else ""
    ubic += f" ({ubicacion_exacta})" if ubicacion_exacta else ""
    img_txt = " (con foto)" if img_path else ""
    venc_txt = ""
    if fecha_vencimiento:
        dias = _dias_para_vencer(fecha_vencimiento)
        if dias is not None and dias < 30:
            venc_txt = f"\n  ATENCION: Vence en {dias} dias ({fecha_vencimiento})"
        else:
            venc_txt = f"\n  Vencimiento: {fecha_vencimiento}"
    return f"Documento registrado: '{nombre}' [{tipo}]{ubic}{img_txt}{venc_txt}"


def buscar(texto: str) -> str:
    docs = _cargar()

    exacto = _buscar_exacto(docs, texto)
    if exacto:
        return _formato_detalle(exacto)

    resultados = _buscar_parcial(docs, texto)
    if not resultados:
        return f"No se encontro '{texto}'. Usa listar para ver todos los documentos."

    lineas = [f"Encontrados {len(resultados)} documentos con '{texto}':"]
    for d in resultados:
        ubic = f" -> {d['area']}" if d.get("area") else ""
        ubic += f" ({d['ubicacion_exacta']})" if d.get("ubicacion_exacta") else ""
        img = " [foto]" if d.get("imagen") else ""
        lineas.append(f"  - {d['nombre']} [{d['tipo']}]{ubic}{img}")
    return "\n".join(lineas)


def _formato_detalle(doc: dict) -> str:
    lineas = [f"'{doc['nombre']}' [{doc['tipo']}]"]
    if doc.get("area"):
        lineas.append(f"  Area: {doc['area']}")
    if doc.get("ubicacion_exacta"):
        lineas.append(f"  Ubicacion: {doc['ubicacion_exacta']}")
    if doc.get("descripcion"):
        lineas.append(f"  Descripcion: {doc['descripcion']}")
    lineas.append(f"  Registrado: {doc['fecha_registrado'][:10]}")
    if doc.get("fecha_vencimiento"):
        dias = _dias_para_vencer(doc["fecha_vencimiento"])
        estado = ""
        if dias is not None:
            if dias < 0:
                estado = " VENCIDO"
            elif dias < 30:
                estado = f" (vence en {dias} dias)"
        lineas.append(f"  Vencimiento: {doc['fecha_vencimiento']}{estado}")
    img = " [foto disponible]" if doc.get("imagen") else ""
    if img:
        lineas.append(f"  {img}")
    if doc.get("imagen") and os.path.exists(doc["imagen"]):
        lineas.append(f"IMAGEN:{doc['imagen']}")
    return "\n".join(lineas)


def ver(nombre: str) -> str:
    docs = _cargar()
    doc = _buscar_exacto(docs, nombre)
    if not doc:
        return f"Documento '{nombre}' no encontrado."
    return _formato_detalle(doc)


def listar(tipo: str = None, area: str = None) -> str:
    docs = _cargar()
    if not docs:
        return "No hay documentos registrados."

    if tipo:
        tipo_lower = tipo.lower().strip()
        docs = [d for d in docs if (d.get("tipo") or "").lower() == tipo_lower]
        if not docs:
            return f"No hay documentos de tipo '{tipo}'."
    if area:
        area_lower = area.lower().strip()
        docs = [d for d in docs if (d.get("area") or "").lower() == area_lower]
        if not docs:
            return f"No hay documentos en '{area}'."

    # Agrupar por tipo
    por_tipo = {}
    for d in docs:
        t = d.get("tipo") or "Sin tipo"
        por_tipo.setdefault(t, []).append(d)

    lineas = [f"Documentos ({len(docs)}):"]

    # Alertas de vencimiento primero
    por_vencer = []
    for d in docs:
        dias = _dias_para_vencer(d.get("fecha_vencimiento"))
        if dias is not None and dias <= 30:
            por_vencer.append((d, dias))

    if por_vencer:
        por_vencer.sort(key=lambda x: x[1])
        lineas.append("\n  ALERTAS DE VENCIMIENTO:")
        for d, dias in por_vencer:
            if dias < 0:
                lineas.append(f"    !! {d['nombre']} — VENCIDO hace {abs(dias)} dias")
            else:
                lineas.append(f"    ! {d['nombre']} — vence en {dias} dias ({d['fecha_vencimiento']})")

    for t, t_docs in sorted(por_tipo.items()):
        lineas.append(f"\n  [{t}]")
        for d in t_docs:
            ubic = ""
            if d.get("area"):
                ubic = f" -> {d['area']}"
                if d.get("ubicacion_exacta"):
                    ubic += f" ({d['ubicacion_exacta']})"
            img = " [foto]" if d.get("imagen") else ""
            lineas.append(f"    - {d['nombre']}{ubic}{img}")

    return "\n".join(lineas)


def mover(nombre: str, area: str, ubicacion_exacta: str = None,
          imagen: str = None) -> str:
    docs = _cargar()
    doc = _buscar_exacto(docs, nombre)
    if not doc:
        return f"Documento '{nombre}' no encontrado."

    area_anterior = doc.get("area") or "?"
    ubic_anterior = doc.get("ubicacion_exacta") or ""

    doc["historial_movimientos"].append({
        "area": area_anterior,
        "ubicacion": ubic_anterior,
        "fecha": datetime.now().isoformat(),
    })

    doc["area"] = area.strip()
    doc["ubicacion_exacta"] = ubicacion_exacta

    if imagen:
        img_path = _guardar_imagen(imagen, nombre)
        if img_path:
            _eliminar_imagen(doc.get("imagen"))
            doc["imagen"] = img_path

    _guardar(docs)

    ubic_txt = f", {ubicacion_exacta}" if ubicacion_exacta else ""
    return f"'{doc['nombre']}' movido: {area_anterior} -> {area}{ubic_txt}"


def eliminar(nombre: str) -> str:
    docs = _cargar()
    doc = _buscar_exacto(docs, nombre)
    if not doc:
        return f"Documento '{nombre}' no encontrado."

    _eliminar_imagen(doc.get("imagen"))
    docs.remove(doc)
    _guardar(docs)
    return f"Documento '{doc['nombre']}' [{doc['tipo']}] eliminado."


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "registrar": registrar,
    "buscar": buscar,
    "ver": ver,
    "listar": listar,
    "mover": mover,
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
        logger.error(f"documentos.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
