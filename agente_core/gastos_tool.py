"""
Gastos Tool — Tracking de gastos personales.

Operaciones:
  registrar    — Registra un gasto con monto, categoria, descripcion y foto (recibo)
  listar       — Lista gastos (filtrar por periodo, categoria)
  resumen      — Resumen por periodo: totales, por categoria, promedios
  eliminar     — Elimina un gasto por ID
  presupuesto  — Define o consulta presupuesto mensual por categoria
  comparar     — Compara gastos entre dos meses

Estructura del JSON:
  Cada gasto: {
    "id": int,
    "monto": float,
    "categoria": str,
    "descripcion": str | null,
    "imagen": str | null,         (foto del recibo)
    "fecha": str (ISO),
    "mes": str (YYYY-MM)
  }
"""
import json
import os
import shutil
from datetime import datetime, timedelta
from logger import get_logger

logger = get_logger("gastos")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "gastos.json")
_ARCHIVO_PRESUPUESTOS = os.path.join(_DATA_DIR, "presupuestos.json")
_IMG_DIR = os.path.join(_DATA_DIR, "imagenes_gastos")


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


def _guardar(gastos: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(gastos, f, ensure_ascii=False, indent=2)


def _cargar_presupuestos() -> dict:
    if not os.path.exists(_ARCHIVO_PRESUPUESTOS):
        return {}
    try:
        with open(_ARCHIVO_PRESUPUESTOS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, Exception):
        return {}


def _guardar_presupuestos(pres: dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO_PRESUPUESTOS, "w", encoding="utf-8") as f:
        json.dump(pres, f, ensure_ascii=False, indent=2)


def _siguiente_id(gastos: list[dict]) -> int:
    return max((g["id"] for g in gastos), default=0) + 1


def _mes_actual() -> str:
    return datetime.now().strftime("%Y-%m")


def _filtrar_mes(gastos: list[dict], mes: str) -> list[dict]:
    return [g for g in gastos if g.get("mes") == mes]


def _filtrar_categoria(gastos: list[dict], categoria: str) -> list[dict]:
    cat_lower = categoria.lower().strip()
    return [g for g in gastos if (g.get("categoria") or "").lower() == cat_lower]


def _guardar_imagen(origen: str, gasto_id: int) -> str | None:
    if not origen or not os.path.exists(origen):
        return None
    os.makedirs(_IMG_DIR, exist_ok=True)
    ext = os.path.splitext(origen)[1] or ".jpg"
    destino = os.path.join(_IMG_DIR, f"recibo_{gasto_id}{ext}")
    try:
        shutil.copy2(origen, destino)
        return destino
    except Exception as e:
        logger.warning(f"No se pudo guardar recibo: {e}")
        return None


def _eliminar_imagen(ruta: str | None):
    if ruta and os.path.exists(ruta):
        try:
            os.remove(ruta)
        except Exception:
            pass


def _formato_monto(monto: float) -> str:
    return f"${monto:,.2f}"


# ── Operaciones ──────────────────────────────────────────────────────────────

def registrar(monto: float, categoria: str, descripcion: str = None,
              imagen: str = None, fecha: str = None) -> str:
    gastos = _cargar()
    ahora = datetime.now()

    if fecha:
        try:
            fecha_dt = datetime.fromisoformat(fecha)
            mes = fecha_dt.strftime("%Y-%m")
            fecha_iso = fecha_dt.isoformat()
        except ValueError:
            mes = _mes_actual()
            fecha_iso = ahora.isoformat()
    else:
        mes = _mes_actual()
        fecha_iso = ahora.isoformat()

    nuevo_id = _siguiente_id(gastos)
    img_path = _guardar_imagen(imagen, nuevo_id) if imagen else None

    gasto = {
        "id": nuevo_id,
        "monto": round(monto, 2),
        "categoria": categoria.strip(),
        "descripcion": descripcion,
        "imagen": img_path,
        "fecha": fecha_iso,
        "mes": mes,
    }
    gastos.append(gasto)
    _guardar(gastos)

    img_txt = " (con recibo)" if img_path else ""
    desc_txt = f" — {descripcion}" if descripcion else ""
    # Verificar presupuesto
    alerta = ""
    presupuestos = _cargar_presupuestos()
    cat_lower = categoria.lower().strip()
    if cat_lower in presupuestos:
        total_cat = sum(g["monto"] for g in _filtrar_mes(gastos, mes)
                        if (g.get("categoria") or "").lower() == cat_lower)
        limite = presupuestos[cat_lower]
        if total_cat > limite:
            exceso = total_cat - limite
            alerta = f"\n  ALERTA: Excediste el presupuesto de {categoria} por {_formato_monto(exceso)}"
        elif total_cat > limite * 0.8:
            restante = limite - total_cat
            alerta = f"\n  Atencion: Solo te quedan {_formato_monto(restante)} de presupuesto en {categoria}"

    return (f"Gasto registrado: {_formato_monto(monto)} en {categoria}{desc_txt}{img_txt}"
            f"{alerta}")


def listar(mes: str = None, categoria: str = None, ultimos: int = None) -> str:
    gastos = _cargar()
    if not gastos:
        return "No hay gastos registrados."

    titulo_parts = []

    if mes:
        gastos = _filtrar_mes(gastos, mes)
        titulo_parts.append(f"mes {mes}")
    if categoria:
        gastos = _filtrar_categoria(gastos, categoria)
        titulo_parts.append(f"categoria {categoria}")

    if not gastos:
        filtro = " y ".join(titulo_parts) if titulo_parts else ""
        return f"No hay gastos{' para ' + filtro if filtro else ''}."

    # Ordenar por fecha descendente
    gastos.sort(key=lambda g: g["fecha"], reverse=True)

    if ultimos:
        gastos = gastos[:ultimos]

    titulo = "Gastos"
    if titulo_parts:
        titulo += f" ({', '.join(titulo_parts)})"

    total = sum(g["monto"] for g in gastos)
    lineas = [f"{titulo} — {len(gastos)} registros, total: {_formato_monto(total)}"]

    for g in gastos:
        fecha_corta = g["fecha"][:10]
        desc = f" — {g['descripcion']}" if g.get("descripcion") else ""
        img = " [recibo]" if g.get("imagen") else ""
        lineas.append(f"  #{g['id']} {fecha_corta} | {_formato_monto(g['monto'])} | {g['categoria']}{desc}{img}")

    return "\n".join(lineas)


def resumen(mes: str = None) -> str:
    gastos = _cargar()
    if not gastos:
        return "No hay gastos registrados."

    mes = mes or _mes_actual()
    gastos_mes = _filtrar_mes(gastos, mes)

    if not gastos_mes:
        return f"No hay gastos en {mes}."

    total = sum(g["monto"] for g in gastos_mes)
    promedio_diario = total / 30

    # Por categoria
    por_cat = {}
    for g in gastos_mes:
        cat = g.get("categoria") or "Sin categoria"
        por_cat[cat] = por_cat.get(cat, 0) + g["monto"]

    presupuestos = _cargar_presupuestos()

    lineas = [
        f"Resumen de gastos — {mes}",
        f"  Total: {_formato_monto(total)}",
        f"  Promedio diario: {_formato_monto(promedio_diario)}",
        f"  Transacciones: {len(gastos_mes)}",
        "",
        "  Por categoria:",
    ]

    for cat, monto in sorted(por_cat.items(), key=lambda x: -x[1]):
        pct = monto / total * 100
        barra = "=" * int(pct / 5) + "-" * (20 - int(pct / 5))
        linea = f"    {cat}: {_formato_monto(monto)} ({pct:.0f}%) [{barra}]"
        # Verificar presupuesto
        cat_lower = cat.lower().strip()
        if cat_lower in presupuestos:
            limite = presupuestos[cat_lower]
            if monto > limite:
                linea += f" EXCEDIDO ({_formato_monto(monto - limite)} sobre {_formato_monto(limite)})"
            else:
                linea += f" (quedan {_formato_monto(limite - monto)} de {_formato_monto(limite)})"
        lineas.append(linea)

    # Top 3 gastos mas grandes del mes
    top = sorted(gastos_mes, key=lambda g: g["monto"], reverse=True)[:3]
    lineas.append("\n  Top 3 gastos:")
    for g in top:
        desc = g.get("descripcion") or g["categoria"]
        lineas.append(f"    {_formato_monto(g['monto'])} — {desc} ({g['fecha'][:10]})")

    return "\n".join(lineas)


def eliminar(id: int) -> str:
    gastos = _cargar()
    gasto = next((g for g in gastos if g["id"] == id), None)
    if not gasto:
        return f"Gasto #{id} no encontrado."

    _eliminar_imagen(gasto.get("imagen"))
    gastos.remove(gasto)
    _guardar(gastos)
    return f"Gasto #{id} eliminado ({_formato_monto(gasto['monto'])} en {gasto['categoria']})."


def presupuesto(categoria: str = None, monto: float = None) -> str:
    presupuestos = _cargar_presupuestos()

    # Sin argumentos: mostrar todos los presupuestos
    if not categoria:
        if not presupuestos:
            return "No hay presupuestos definidos. Usa presupuesto(categoria, monto) para crear uno."
        gastos = _cargar()
        mes = _mes_actual()
        gastos_mes = _filtrar_mes(gastos, mes)
        lineas = [f"Presupuestos mensuales ({mes}):"]
        for cat, limite in sorted(presupuestos.items()):
            gastado = sum(g["monto"] for g in gastos_mes
                         if (g.get("categoria") or "").lower() == cat)
            restante = limite - gastado
            estado = "OK" if restante >= 0 else "EXCEDIDO"
            lineas.append(f"  {cat}: {_formato_monto(gastado)} / {_formato_monto(limite)} [{estado}]")
        return "\n".join(lineas)

    cat_lower = categoria.lower().strip()

    # Solo categoria: mostrar ese presupuesto
    if monto is None:
        if cat_lower not in presupuestos:
            return f"No hay presupuesto para '{categoria}'."
        gastos = _cargar()
        mes = _mes_actual()
        gastado = sum(g["monto"] for g in _filtrar_mes(gastos, mes)
                      if (g.get("categoria") or "").lower() == cat_lower)
        limite = presupuestos[cat_lower]
        restante = limite - gastado
        return (f"Presupuesto de {categoria}: {_formato_monto(limite)}\n"
                f"  Gastado este mes: {_formato_monto(gastado)}\n"
                f"  Restante: {_formato_monto(restante)}")

    # Categoria + monto: definir/actualizar presupuesto
    presupuestos[cat_lower] = round(monto, 2)
    _guardar_presupuestos(presupuestos)
    return f"Presupuesto de '{categoria}' definido: {_formato_monto(monto)} mensual."


def comparar(mes1: str, mes2: str) -> str:
    gastos = _cargar()
    g1 = _filtrar_mes(gastos, mes1)
    g2 = _filtrar_mes(gastos, mes2)

    if not g1 and not g2:
        return f"No hay gastos en {mes1} ni en {mes2}."

    total1 = sum(g["monto"] for g in g1)
    total2 = sum(g["monto"] for g in g2)
    diff = total2 - total1
    pct = (diff / total1 * 100) if total1 > 0 else 0

    # Por categoria
    cats = set()
    cat1 = {}
    cat2 = {}
    for g in g1:
        cat = g.get("categoria") or "Sin categoria"
        cats.add(cat)
        cat1[cat] = cat1.get(cat, 0) + g["monto"]
    for g in g2:
        cat = g.get("categoria") or "Sin categoria"
        cats.add(cat)
        cat2[cat] = cat2.get(cat, 0) + g["monto"]

    signo = "+" if diff >= 0 else ""
    tendencia = "subieron" if diff > 0 else "bajaron" if diff < 0 else "se mantuvieron"

    lineas = [
        f"Comparacion: {mes1} vs {mes2}",
        f"  {mes1}: {_formato_monto(total1)} ({len(g1)} gastos)",
        f"  {mes2}: {_formato_monto(total2)} ({len(g2)} gastos)",
        f"  Diferencia: {signo}{_formato_monto(diff)} ({signo}{pct:.1f}%) — {tendencia}",
        "",
        "  Por categoria:",
    ]
    for cat in sorted(cats):
        m1 = cat1.get(cat, 0)
        m2 = cat2.get(cat, 0)
        d = m2 - m1
        s = "+" if d >= 0 else ""
        lineas.append(f"    {cat}: {_formato_monto(m1)} -> {_formato_monto(m2)} ({s}{_formato_monto(d)})")

    return "\n".join(lineas)


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "registrar": registrar,
    "listar": listar,
    "resumen": resumen,
    "eliminar": eliminar,
    "presupuesto": presupuesto,
    "comparar": comparar,
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
        logger.error(f"gastos.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
