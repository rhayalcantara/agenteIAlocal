"""
Presencia Tool — Detección de personas por WiFi via RuView.

Usa sensores ESP32-S3 para detectar presencia, signos vitales y actividad
mediante análisis de Channel State Information (CSI) de señales WiFi.
Cruza con distribucion_casa para mapear detecciones a áreas del hogar.

Operaciones:
  estado      — Quién está en casa, en qué áreas
  vitales     — Signos vitales de personas detectadas (respiración, pulso)
  actividad   — Nivel de actividad por zona
  historial   — Registro de presencia por área (últimas horas)
  alertas     — Caídas, inactividad prolongada, zonas vacías
  sensores    — Estado de los sensores ESP32 conectados
  config      — Ver o modificar configuración (URL del servidor, umbrales)

Requiere: RuView corriendo en Docker (puerto 3000 REST, 3001 WebSocket)
"""
import json
import os
import time
from datetime import datetime, timedelta
from logger import get_logger

logger = get_logger("presencia")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO_HISTORIAL = os.path.join(_DATA_DIR, "historial_presencia.json")
_ARCHIVO_CONFIG = os.path.join(_DATA_DIR, "presencia_config.json")
_ARCHIVO_CASA = os.path.join(_DATA_DIR, "distribucion_casa.json")

# Configuración por defecto
_DEFAULT_CONFIG = {
    "ruview_url": os.getenv("RUVIEW_URL", "http://localhost:3000"),
    "ws_url": os.getenv("RUVIEW_WS_URL", "ws://localhost:3001"),
    "umbral_inactividad_min": 60,       # minutos sin movimiento para alerta
    "umbral_caida_confianza": 0.7,      # confianza mínima para alerta de caída
    "max_historial_horas": 24,          # horas de historial a mantener
    "zonas_mapeadas": {},               # zona_ruview -> area_casa
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cargar_config() -> dict:
    os.makedirs(_DATA_DIR, exist_ok=True)
    if not os.path.exists(_ARCHIVO_CONFIG):
        _guardar_config(_DEFAULT_CONFIG)
        return _DEFAULT_CONFIG.copy()
    try:
        with open(_ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        # Merge con defaults para keys nuevas
        for k, v in _DEFAULT_CONFIG.items():
            if k not in cfg:
                cfg[k] = v
        return cfg
    except (json.JSONDecodeError, Exception):
        return _DEFAULT_CONFIG.copy()


def _guardar_config(cfg: dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO_CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _cargar_historial() -> list[dict]:
    if not os.path.exists(_ARCHIVO_HISTORIAL):
        return []
    try:
        with open(_ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, Exception):
        return []


def _guardar_historial(registros: list[dict]):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
        json.dump(registros, f, ensure_ascii=False, indent=2)


def _agregar_historial(entrada: dict):
    """Agrega entrada al historial y limpia registros viejos."""
    cfg = _cargar_config()
    historial = _cargar_historial()
    entrada["timestamp"] = datetime.now().isoformat()
    historial.append(entrada)

    # Limpiar historial viejo
    limite = datetime.now() - timedelta(hours=cfg["max_historial_horas"])
    historial = [h for h in historial if h.get("timestamp", "") >= limite.isoformat()]
    _guardar_historial(historial)


def _areas_casa() -> list[str]:
    """Lee áreas de distribucion_casa.json."""
    if not os.path.exists(_ARCHIVO_CASA):
        return []
    try:
        with open(_ARCHIVO_CASA, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [a["nombre"] for a in data if isinstance(a, dict)]
    except (json.JSONDecodeError, Exception):
        return []


def _mapear_zona(zona_ruview: str, cfg: dict) -> str:
    """Mapea una zona de RuView a un área de distribucion_casa."""
    mapa = cfg.get("zonas_mapeadas", {})
    if zona_ruview in mapa:
        return mapa[zona_ruview]
    # Intento de match por nombre similar
    areas = _areas_casa()
    zona_lower = zona_ruview.lower()
    for area in areas:
        if zona_lower in area.lower() or area.lower() in zona_lower:
            return area
    return zona_ruview


def _api_get(endpoint: str) -> dict | None:
    """Consulta la API REST de RuView."""
    import requests
    cfg = _cargar_config()
    url = f"{cfg['ruview_url']}{endpoint}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"RuView API {endpoint}: status {resp.status_code}")
        return None
    except requests.ConnectionError:
        return None
    except Exception as e:
        logger.warning(f"RuView API error: {e}")
        return None


def _verificar_servidor() -> str | None:
    """Verifica si RuView está corriendo. Retorna error o None."""
    health = _api_get("/health")
    if health is None:
        cfg = _cargar_config()
        return (f"No se puede conectar al servidor RuView en {cfg['ruview_url']}.\n"
                f"Verifica que Docker este corriendo:\n"
                f"  docker-compose -f docker/docker-compose.ruview.yml up -d")
    return None


def _sensing_data() -> dict | None:
    """Obtiene el frame de sensing actual desde la API correcta."""
    return _api_get("/api/v1/sensing/latest")


def _vital_signs_data() -> dict | None:
    """Obtiene signos vitales desde la API."""
    return _api_get("/api/v1/vital-signs")


def _pose_data() -> dict | None:
    """Obtiene datos de pose desde la API."""
    return _api_get("/api/v1/pose/current")


def _info_data() -> dict | None:
    """Obtiene info del servidor."""
    return _api_get("/api/v1/info")


# ── Operaciones ──────────────────────────────────────────────────────────────

def estado() -> str:
    """Estado actual: quién está en casa, en qué áreas."""
    error = _verificar_servidor()
    if error:
        return error

    cfg = _cargar_config()
    data = _sensing_data()
    if not data:
        return "Sin datos de sensing disponibles. Los sensores pueden estar iniciando."

    personas = data.get("persons", [])
    n_personas = data.get("estimated_persons", len(personas))
    timestamp = data.get("timestamp", "?")

    if n_personas == 0:
        _agregar_historial({"tipo": "estado", "personas": 0, "areas": []})
        return "No hay nadie detectado en la casa."

    lineas = [f"Personas detectadas: {n_personas}"]

    areas_detectadas = []
    for p in personas:
        zona_raw = p.get("zone", "desconocida")
        area = _mapear_zona(zona_raw, cfg)
        confianza = p.get("confidence", 0)
        actividad = p.get("activity_level", "?")
        lineas.append(f"  - Persona {p.get('id', '?')}: {area} "
                      f"(confianza: {confianza:.0%}, actividad: {actividad})")
        areas_detectadas.append(area)

    # Areas vacías
    areas_casa = _areas_casa()
    if areas_casa:
        vacias = [a for a in areas_casa if a not in areas_detectadas]
        if vacias:
            lineas.append(f"\nAreas sin presencia: {', '.join(vacias)}")

    _agregar_historial({
        "tipo": "estado",
        "personas": n_personas,
        "areas": areas_detectadas,
    })

    return "\n".join(lineas)


def vitales() -> str:
    """Signos vitales de personas detectadas."""
    error = _verificar_servidor()
    if error:
        return error

    cfg = _cargar_config()
    data = _sensing_data()
    vitals_data = _vital_signs_data()
    if not data and not vitals_data:
        return "Sin datos disponibles."

    personas = data.get("persons", []) if data else []

    # Combinar vitales del frame de sensing y del endpoint dedicado
    vital_signs = {}
    if data:
        vital_signs = data.get("vital_signs", {})
    if vitals_data and vitals_data.get("vital_signs"):
        vital_signs = vitals_data["vital_signs"]

    breathing = vital_signs.get("breathing_rate_bpm") or vital_signs.get("breathing_rate")
    heart_rate = vital_signs.get("heart_rate_bpm") or vital_signs.get("heart_rate")
    br_conf = vital_signs.get("breathing_confidence", 0)
    hr_conf = vital_signs.get("heartbeat_confidence", 0)
    signal_q = vital_signs.get("signal_quality", 0)

    n_personas = len(personas) if personas else (1 if breathing or heart_rate else 0)
    lineas = [f"Signos vitales ({n_personas} persona(s)):"]

    if breathing or heart_rate:
        lineas.append(f"\n  Lectura general:")
        if breathing:
            estado_resp = "normal" if 12 <= breathing <= 20 else "revisar"
            lineas.append(f"    Respiracion: {breathing:.1f} BPM ({estado_resp}) [confianza: {br_conf:.0%}]")
        if heart_rate:
            estado_hr = "normal" if 60 <= heart_rate <= 100 else "revisar"
            lineas.append(f"    Frecuencia cardiaca: {heart_rate:.1f} BPM ({estado_hr}) [confianza: {hr_conf:.0%}]")
        if signal_q:
            lineas.append(f"    Calidad de senal: {signal_q:.0%}")

    # Por persona
    for p in personas:
        area = _mapear_zona(p.get("zone", "?"), cfg)
        lineas.append(f"\n  Persona {p.get('id', '?')} ({area}):")
        p_vitals = p.get("vital_signs", {})
        if p_vitals:
            if p_vitals.get("breathing_rate"):
                lineas.append(f"    Respiracion: {p_vitals['breathing_rate']} BPM")
            if p_vitals.get("heart_rate"):
                lineas.append(f"    Pulso: {p_vitals['heart_rate']} BPM")
        else:
            lineas.append(f"    Actividad: {p.get('activity_level', '?')}")
            lineas.append(f"    Confianza: {p.get('confidence', 0):.0%}")

    return "\n".join(lineas)


def actividad(area: str = None) -> str:
    """Nivel de actividad por zona."""
    error = _verificar_servidor()
    if error:
        return error

    cfg = _cargar_config()
    data = _sensing_data()
    if not data:
        return "Sin datos disponibles."

    personas = data.get("persons", [])

    # Agrupar por area
    por_area = {}
    for p in personas:
        a = _mapear_zona(p.get("zone", "desconocida"), cfg)
        por_area.setdefault(a, []).append(p)

    if area:
        area_lower = area.lower()
        filtrado = {k: v for k, v in por_area.items() if area_lower in k.lower()}
        if not filtrado:
            return f"Sin actividad detectada en '{area}'."
        por_area = filtrado

    if not por_area:
        return "Sin actividad detectada en ninguna area."

    lineas = ["Actividad por area:"]
    for a, personas_area in sorted(por_area.items()):
        n = len(personas_area)
        actividades = [p.get("activity_level", "?") for p in personas_area]
        confianza_prom = sum(p.get("confidence", 0) for p in personas_area) / n
        lineas.append(f"\n  [{a}] {n} persona(s)")
        lineas.append(f"    Actividad: {', '.join(actividades)}")
        lineas.append(f"    Confianza promedio: {confianza_prom:.0%}")

    # Enhanced motion/breathing del frame
    motion = data.get("enhanced_motion", {})
    if motion:
        lineas.append(f"\n  Movimiento general: {motion.get('level', '?')}")

    return "\n".join(lineas)


def historial(area: str = None, horas: int = 4) -> str:
    """Historial de presencia de las últimas N horas."""
    registros = _cargar_historial()
    if not registros:
        return "Sin historial de presencia. El sistema necesita estar activo para acumular datos."

    limite = datetime.now() - timedelta(hours=horas)
    registros = [r for r in registros if r.get("timestamp", "") >= limite.isoformat()]

    if area:
        registros = [r for r in registros
                     if area.lower() in str(r.get("areas", [])).lower()]

    if not registros:
        filtro = f" en '{area}'" if area else ""
        return f"Sin registros de presencia{filtro} en las ultimas {horas} horas."

    lineas = [f"Historial de presencia (ultimas {horas}h):"]

    # Resumir por hora
    por_hora = {}
    for r in registros:
        hora = r["timestamp"][:13]  # YYYY-MM-DDTHH
        por_hora.setdefault(hora, []).append(r)

    for hora, regs in sorted(por_hora.items()):
        hora_fmt = hora.replace("T", " ") + ":00"
        personas_max = max(r.get("personas", 0) for r in regs)
        todas_areas = set()
        for r in regs:
            todas_areas.update(r.get("areas", []))
        areas_txt = ", ".join(sorted(todas_areas)) if todas_areas else "ninguna"
        lineas.append(f"  {hora_fmt} | max {personas_max} personas | areas: {areas_txt}")

    return "\n".join(lineas)


def alertas() -> str:
    """Verifica condiciones de alerta: caídas, inactividad, anomalías."""
    error = _verificar_servidor()
    if error:
        return error

    cfg = _cargar_config()
    data = _sensing_data()
    alertas_list = []

    if data:
        personas = data.get("persons", [])

        # Detectar caídas
        for p in personas:
            if p.get("activity_level", "").lower() in ("fallen", "fall", "caida"):
                area = _mapear_zona(p.get("zone", "?"), cfg)
                confianza = p.get("confidence", 0)
                if confianza >= cfg["umbral_caida_confianza"]:
                    alertas_list.append(
                        f"!! CAIDA detectada: Persona {p.get('id', '?')} en {area} "
                        f"(confianza: {confianza:.0%})")

        # Signos vitales anormales
        vital_signs = data.get("vital_signs", {})
        hr = vital_signs.get("heart_rate")
        br = vital_signs.get("breathing_rate")
        if hr and (hr < 50 or hr > 120):
            alertas_list.append(f"! Frecuencia cardiaca anormal: {hr} BPM")
        if br and (br < 8 or br > 25):
            alertas_list.append(f"! Respiracion anormal: {br} BPM")

    # Verificar inactividad prolongada en el historial
    historial_data = _cargar_historial()
    if historial_data:
        umbral = cfg["umbral_inactividad_min"]
        ultimo_con_personas = None
        for r in reversed(historial_data):
            if r.get("personas", 0) > 0:
                ultimo_con_personas = r.get("timestamp")
                break
        if ultimo_con_personas:
            try:
                dt_ultimo = datetime.fromisoformat(ultimo_con_personas)
                minutos_sin = (datetime.now() - dt_ultimo).total_seconds() / 60
                if minutos_sin > umbral:
                    alertas_list.append(
                        f"! Sin movimiento detectado hace {int(minutos_sin)} minutos "
                        f"(umbral: {umbral} min)")
            except ValueError:
                pass

    if not alertas_list:
        return "Sin alertas. Todo normal."

    return "ALERTAS DE PRESENCIA:\n" + "\n".join(alertas_list)


def sensores() -> str:
    """Estado de los sensores ESP32 conectados."""
    error = _verificar_servidor()
    if error:
        return error

    health = _api_get("/health")
    if not health:
        return "No se pudo obtener estado del servidor."

    data = _sensing_data()

    lineas = [
        "Estado del servidor RuView:",
        f"  Status: {health.get('status', '?')}",
        f"  Fuente CSI: {health.get('source', '?')}",
        f"  Frames procesados: {health.get('tick', 0)}",
        f"  Clientes conectados: {health.get('connected_clients', 0)}",
    ]

    info = _info_data()
    if info:
        lineas.append(f"  Version: {info.get('version', '?')}")
        lineas.append(f"  Backend: {info.get('backend', '?')}")
        features = info.get("features", {})
        if features:
            activas = [k for k, v in features.items() if v]
            lineas.append(f"  Features: {', '.join(activas)}")

    if data:
        nodes = data.get("nodes", [])
        lineas.append(f"\n  Nodos ESP32: {len(nodes)}")
        for node in nodes:
            node_id = node.get("node_id", node.get("id", "?"))
            rssi = node.get("rssi_dbm", "?")
            subs = node.get("subcarrier_count", "?")
            lineas.append(f"    - Nodo {node_id}: RSSI={rssi}dBm, subcarriers={subs}")

        # Clasificacion general
        clasificacion = data.get("classification", {})
        if clasificacion:
            lineas.append(f"\n  Clasificacion:")
            lineas.append(f"    Presencia: {'si' if clasificacion.get('presence') else 'no'}")
            lineas.append(f"    Movimiento: {clasificacion.get('motion_level', '?')}")
            lineas.append(f"    Confianza: {clasificacion.get('confidence', 0):.0%}")

    return "\n".join(lineas)


def config(ruview_url: str = None, ws_url: str = None,
           umbral_inactividad_min: int = None,
           mapear_zona: str = None, a_area: str = None) -> str:
    """Ver o modificar configuración."""
    cfg = _cargar_config()
    cambios = []

    if ruview_url:
        cfg["ruview_url"] = ruview_url.rstrip("/")
        cambios.append(f"ruview_url -> {ruview_url}")
    if ws_url:
        cfg["ws_url"] = ws_url.rstrip("/")
        cambios.append(f"ws_url -> {ws_url}")
    if umbral_inactividad_min is not None:
        cfg["umbral_inactividad_min"] = umbral_inactividad_min
        cambios.append(f"umbral_inactividad -> {umbral_inactividad_min} min")
    if mapear_zona and a_area:
        cfg.setdefault("zonas_mapeadas", {})[mapear_zona] = a_area
        cambios.append(f"zona '{mapear_zona}' -> area '{a_area}'")

    if cambios:
        _guardar_config(cfg)
        return f"Configuracion actualizada:\n  " + "\n  ".join(cambios)

    # Mostrar configuración actual
    lineas = ["Configuracion de presencia:"]
    lineas.append(f"  Servidor REST: {cfg['ruview_url']}")
    lineas.append(f"  WebSocket: {cfg['ws_url']}")
    lineas.append(f"  Umbral inactividad: {cfg['umbral_inactividad_min']} min")
    lineas.append(f"  Max historial: {cfg['max_historial_horas']}h")

    zonas = cfg.get("zonas_mapeadas", {})
    if zonas:
        lineas.append(f"\n  Mapeo de zonas:")
        for z, a in zonas.items():
            lineas.append(f"    {z} -> {a}")

    areas = _areas_casa()
    if areas:
        lineas.append(f"\n  Areas de la casa: {', '.join(areas)}")

    return "\n".join(lineas)


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "estado": estado,
    "vitales": vitales,
    "actividad": actividad,
    "historial": historial,
    "alertas": alertas,
    "sensores": sensores,
    "config": config,
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
        logger.error(f"presencia.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
