"""
Agenda Tool — Programación de acciones automáticas.

Tipos de acción:
  diaria             — Todos los días (o días específicos) a una hora fija
  recurrente_ventana — Cada N minutos dentro de un rango horario
  recurrente         — Cada N minutos sin restricción de horario

Operaciones:
  agregar    — Crea una nueva acción en la agenda
  listar     — Muestra todas las acciones (filtradas por estado)
  ver        — Detalle completo de una acción por ID
  activar    — Activa una acción desactivada
  desactivar — Pausa una acción sin eliminarla
  eliminar   — Elimina una acción por ID
  historial  — Muestra las últimas ejecuciones de una acción
"""
import json
import os
import threading
from datetime import datetime

from logger import get_logger

logger = get_logger("agenda")

_lock = threading.Lock()   # compartido entre agente principal y scheduler
_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO = os.path.join(_DATA_DIR, "agenda.json")

MAX_HISTORIAL_POR_ACCION = 20

_DIAS_NOMBRE = {1: "Lun", 2: "Mar", 3: "Mié", 4: "Jue", 5: "Vie", 6: "Sáb", 7: "Dom"}


# ── Helpers privados ──────────────────────────────────────────────────────────

def _cargar() -> dict:
    """Carga el JSON de la agenda. Llamar con _lock adquirido."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    if not os.path.exists(_ARCHIVO):
        return {"acciones": []}
    try:
        with open(_ARCHIVO, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and "acciones" in data:
            return data
    except Exception:
        pass
    return {"acciones": []}


def _guardar(data: dict):
    """Guarda a disco. Llamar con _lock adquirido."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _siguiente_id(acciones: list) -> int:
    return max((a["id"] for a in acciones), default=0) + 1


def _validar_tipo(tipo: str, hora=None, intervalo_minutos=None,
                  hora_inicio=None, hora_fin=None):
    """Retorna mensaje de error o None si es válido."""
    tipos_validos = ("diaria", "recurrente_ventana", "recurrente")
    if tipo not in tipos_validos:
        return f"Tipo inválido '{tipo}'. Válidos: {', '.join(tipos_validos)}"
    if tipo == "diaria":
        if not hora:
            return "Para tipo 'diaria' se requiere 'hora' (formato HH:MM)"
        try:
            datetime.strptime(hora, "%H:%M")
        except ValueError:
            return f"Formato de hora inválido '{hora}'. Use HH:MM (ej: 08:30)"
    if tipo in ("recurrente_ventana", "recurrente"):
        if not intervalo_minutos or int(intervalo_minutos) < 1:
            return "Para este tipo se requiere 'intervalo_minutos' (mínimo 1)"
    if tipo == "recurrente_ventana":
        if not hora_inicio or not hora_fin:
            return "Para 'recurrente_ventana' se requiere 'hora_inicio' y 'hora_fin' (HH:MM)"
        try:
            datetime.strptime(hora_inicio, "%H:%M")
            datetime.strptime(hora_fin, "%H:%M")
        except ValueError:
            return "Formato de hora inválido en hora_inicio o hora_fin. Use HH:MM"
    return None


def _formato_dias(dias_semana):
    if not dias_semana:
        return "todos los días"
    return ", ".join(_DIAS_NOMBRE.get(d, str(d)) for d in sorted(dias_semana))


def _formato_accion_corto(a: dict) -> str:
    tipo = a.get("tipo", "?")
    estado = "✅" if a.get("activa", True) else "⏸️"
    nombre = a.get("nombre", "Sin nombre")
    accion_id = a.get("id", "?")

    if tipo == "diaria":
        detalle = f"diaria a las {a.get('hora', '?')} ({_formato_dias(a.get('dias_semana'))})"
    elif tipo == "recurrente_ventana":
        detalle = (f"cada {a.get('intervalo_minutos', '?')} min "
                   f"({a.get('hora_inicio', '?')}–{a.get('hora_fin', '?')}, "
                   f"{_formato_dias(a.get('dias_semana'))})")
    else:
        detalle = f"cada {a.get('intervalo_minutos', '?')} min"

    ultima = a.get("ultima_ejecucion")
    ult_txt = f" | última: {ultima[:16]}" if ultima else ""
    return f"{estado} #{accion_id} *{nombre}* — {detalle}{ult_txt}"


# ── Operaciones CRUD ──────────────────────────────────────────────────────────

def agregar(nombre: str, tipo: str, prompt: str, chat_id: int = 0,
            descripcion: str = None,
            hora: str = None,
            dias_semana: list = None,
            intervalo_minutos: int = None,
            hora_inicio: str = None,
            hora_fin: str = None) -> str:
    """Crea una nueva acción en la agenda."""
    error = _validar_tipo(tipo, hora=hora, intervalo_minutos=intervalo_minutos,
                          hora_inicio=hora_inicio, hora_fin=hora_fin)
    if error:
        return f"❌ {error}"

    if not nombre or not nombre.strip():
        return "❌ Se requiere 'nombre' para la acción."
    if not prompt or not prompt.strip():
        return "❌ Se requiere 'prompt' (instrucción que el agente ejecutará)."

    with _lock:
        data = _cargar()
        nuevo_id = _siguiente_id(data["acciones"])
        accion = {
            "id": nuevo_id,
            "nombre": nombre.strip(),
            "descripcion": descripcion,
            "tipo": tipo,
            "prompt": prompt.strip(),
            "activa": True,
            "chat_id": int(chat_id) if chat_id else 0,
            "creada": datetime.now().isoformat(),
            "ultima_ejecucion": None,
            "ultimo_resultado": None,
            "ultimo_error": None,
            "ejecuciones": [],
        }
        if tipo == "diaria":
            accion["hora"] = hora
            accion["dias_semana"] = [int(d) for d in dias_semana] if dias_semana else None
        elif tipo == "recurrente_ventana":
            accion["intervalo_minutos"] = int(intervalo_minutos)
            accion["hora_inicio"] = hora_inicio
            accion["hora_fin"] = hora_fin
            accion["dias_semana"] = [int(d) for d in dias_semana] if dias_semana else None
        elif tipo == "recurrente":
            accion["intervalo_minutos"] = int(intervalo_minutos)

        data["acciones"].append(accion)
        _guardar(data)

    logger.info(f"Acción #{nuevo_id} creada: {nombre} ({tipo})")
    return f"✅ Acción #{nuevo_id} creada: *{nombre}*\n{_formato_accion_corto(accion)}"


def listar(filtro: str = "todos") -> str:
    """Lista acciones de la agenda. filtro: todos | activas | inactivas"""
    with _lock:
        data = _cargar()

    acciones = data["acciones"]
    if filtro == "activas":
        acciones = [a for a in acciones if a.get("activa", True)]
    elif filtro == "inactivas":
        acciones = [a for a in acciones if not a.get("activa", True)]

    if not acciones:
        msgs = {"todos": "No hay acciones en la agenda.",
                "activas": "No hay acciones activas.",
                "inactivas": "No hay acciones pausadas."}
        return msgs.get(filtro, "No hay acciones.")

    lineas = [f"📅 *Agenda* ({filtro}) — {len(acciones)} acción(es)\n"]
    for a in acciones:
        lineas.append(_formato_accion_corto(a))
    return "\n".join(lineas)


def ver(id: int) -> str:
    """Muestra detalle completo de una acción por ID."""
    with _lock:
        data = _cargar()

    accion = next((a for a in data["acciones"] if a["id"] == int(id)), None)
    if not accion:
        return f"❌ No existe la acción #{id}."

    estado = "✅ Activa" if accion.get("activa", True) else "⏸️ Pausada"
    tipo = accion.get("tipo", "?")
    lineas = [
        f"📋 *Acción #{accion['id']}: {accion['nombre']}*",
        f"Estado: {estado}",
        f"Tipo: {tipo}",
    ]
    if accion.get("descripcion"):
        lineas.append(f"Descripción: {accion['descripcion']}")

    if tipo == "diaria":
        lineas.append(f"Hora: {accion.get('hora', '?')}")
        lineas.append(f"Días: {_formato_dias(accion.get('dias_semana'))}")
    elif tipo == "recurrente_ventana":
        lineas.append(f"Cada: {accion.get('intervalo_minutos', '?')} minutos")
        lineas.append(f"Ventana: {accion.get('hora_inicio', '?')} – {accion.get('hora_fin', '?')}")
        lineas.append(f"Días: {_formato_dias(accion.get('dias_semana'))}")
    elif tipo == "recurrente":
        lineas.append(f"Cada: {accion.get('intervalo_minutos', '?')} minutos")

    lineas.append(f"Prompt: _{accion.get('prompt', ''[:100])}_")
    lineas.append(f"Creada: {accion.get('creada', '?')[:16]}")

    ultima = accion.get("ultima_ejecucion")
    lineas.append(f"Última ejecución: {ultima[:16] if ultima else 'Nunca'}")

    if accion.get("ultimo_error"):
        lineas.append(f"⚠️ Último error: {accion['ultimo_error'][:200]}")
    elif accion.get("ultimo_resultado"):
        lineas.append(f"Último resultado: {accion['ultimo_resultado'][:200]}")

    ejecuciones = accion.get("ejecuciones", [])
    lineas.append(f"Total ejecuciones registradas: {len(ejecuciones)}")

    return "\n".join(lineas)


def activar(id: int) -> str:
    """Activa una acción desactivada."""
    with _lock:
        data = _cargar()
        accion = next((a for a in data["acciones"] if a["id"] == int(id)), None)
        if not accion:
            return f"❌ No existe la acción #{id}."
        if accion.get("activa", True):
            return f"ℹ️ La acción #{id} '{accion['nombre']}' ya está activa."
        accion["activa"] = True
        _guardar(data)

    logger.info(f"Acción #{id} activada.")
    return f"✅ Acción #{id} *{accion['nombre']}* activada."


def desactivar(id: int) -> str:
    """Pausa una acción sin eliminarla."""
    with _lock:
        data = _cargar()
        accion = next((a for a in data["acciones"] if a["id"] == int(id)), None)
        if not accion:
            return f"❌ No existe la acción #{id}."
        if not accion.get("activa", True):
            return f"ℹ️ La acción #{id} '{accion['nombre']}' ya está pausada."
        accion["activa"] = False
        _guardar(data)

    logger.info(f"Acción #{id} desactivada.")
    return f"⏸️ Acción #{id} *{accion['nombre']}* pausada."


def eliminar(id: int) -> str:
    """Elimina una acción de la agenda."""
    with _lock:
        data = _cargar()
        antes = len(data["acciones"])
        data["acciones"] = [a for a in data["acciones"] if a["id"] != int(id)]
        if len(data["acciones"]) == antes:
            return f"❌ No existe la acción #{id}."
        _guardar(data)

    logger.info(f"Acción #{id} eliminada.")
    return f"🗑️ Acción #{id} eliminada."


def historial(id: int, ultimas: int = 5) -> str:
    """Muestra las últimas N ejecuciones de una acción."""
    with _lock:
        data = _cargar()

    accion = next((a for a in data["acciones"] if a["id"] == int(id)), None)
    if not accion:
        return f"❌ No existe la acción #{id}."

    ejecuciones = accion.get("ejecuciones", [])
    if not ejecuciones:
        return f"📭 La acción #{id} '{accion['nombre']}' no tiene ejecuciones registradas."

    recientes = ejecuciones[-int(ultimas):]
    lineas = [f"📜 *Historial — #{id} {accion['nombre']}* (últimas {len(recientes)})\n"]
    for e in reversed(recientes):
        icono = "✅" if e.get("exito") else "❌"
        ts = e.get("timestamp", "")[:16]
        resumen = e.get("resumen", "")[:150]
        lineas.append(f"{icono} {ts}: {resumen}")

    return "\n".join(lineas)


# ── API interna para el scheduler (no expuesta al LLM) ───────────────────────

def obtener_acciones_activas() -> list[dict]:
    """Retorna todas las acciones activas. Thread-safe."""
    with _lock:
        data = _cargar()
    return [a for a in data["acciones"] if a.get("activa", True)]


def registrar_ejecucion(id: int, resultado: str, exito: bool):
    """
    Persiste el resultado de una ejecución en el historial de la acción.
    Actualiza ultima_ejecucion, ultimo_resultado/ultimo_error.
    Limita historial a MAX_HISTORIAL_POR_ACCION entradas.
    Thread-safe.
    """
    with _lock:
        data = _cargar()
        accion = next((a for a in data["acciones"] if a["id"] == int(id)), None)
        if not accion:
            return
        ts = datetime.now().isoformat()
        accion["ultima_ejecucion"] = ts
        if exito:
            accion["ultimo_resultado"] = resultado[:500]
            accion["ultimo_error"] = None
        else:
            accion["ultimo_error"] = resultado[:500]
        if "ejecuciones" not in accion:
            accion["ejecuciones"] = []
        accion["ejecuciones"].append({
            "timestamp": ts,
            "exito": exito,
            "resumen": resultado[:200],
        })
        accion["ejecuciones"] = accion["ejecuciones"][-MAX_HISTORIAL_POR_ACCION:]
        _guardar(data)


# ── Dispatcher ────────────────────────────────────────────────────────────────

_OPERACIONES = {
    "agregar":    agregar,
    "listar":     listar,
    "ver":        ver,
    "activar":    activar,
    "desactivar": desactivar,
    "eliminar":   eliminar,
    "historial":  historial,
}


def ejecutar(operacion: str, **kwargs) -> str:
    fn = _OPERACIONES.get(operacion)
    if fn is None:
        return (f"❌ Operación '{operacion}' no existe. "
                f"Disponibles: {', '.join(sorted(_OPERACIONES))}")
    try:
        return fn(**kwargs)
    except TypeError as e:
        return f"❌ Parámetros incorrectos para '{operacion}': {e}"
    except Exception as e:
        logger.error(f"agenda.ejecutar({operacion}): {e}", exc_info=True)
        return f"❌ Error en '{operacion}': {e}"
