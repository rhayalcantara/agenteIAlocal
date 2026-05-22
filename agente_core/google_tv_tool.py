"""
Google TV Tool — Control remoto de Google/Android TVs por ADB over WiFi.

Controla TVs en la red local via ADB. Requiere activar "Depuracion USB"
en Opciones de desarrollador de cada TV.

Operaciones:
  conectar     — Conecta a un TV por IP y lo registra
  estado       — Estado de todos los TVs (encendido, app actual, volumen)
  encender     — Enciende un TV
  apagar       — Apaga un TV
  volumen      — Sube, baja o silencia el volumen
  app          — Abre una app (YouTube, Netflix, Disney+, etc.)
  control      — Envía comando de navegación (arriba, abajo, ok, back, home, etc.)
  escribir     — Escribe texto en el TV (búsquedas, etc.)
  apagar_todos — Apaga todos los TVs registrados
  listar       — Lista TVs registrados y su estado
  escanear     — Busca TVs en la red local
"""
import json
import os
import subprocess
import socket
from logger import get_logger

logger = get_logger("google_tv")

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_ARCHIVO_TVS = os.path.join(_DATA_DIR, "google_tvs.json")
_ADB = os.path.join(os.path.expanduser("~"), "platform-tools", "adb.exe")

# Apps comunes con sus package names
_APPS = {
    "youtube": "com.google.android.youtube.tv",
    "netflix": "com.netflix.ninja",
    "disney": "com.disney.disneyplus",
    "disney+": "com.disney.disneyplus",
    "hbo": "com.hbo.hbomax",
    "hbo max": "com.hbo.hbomax",
    "max": "com.hbo.hbomax",
    "prime": "com.amazon.avod",
    "amazon prime": "com.amazon.avod",
    "spotify": "com.spotify.tv.android",
    "plex": "com.plexapp.android",
    "twitch": "tv.twitch.android.app",
    "chrome": "com.android.chrome",
    "configuracion": "com.android.tv.settings",
    "settings": "com.android.tv.settings",
    "play store": "com.android.vending",
    "kodi": "org.xbmc.kodi",
    "vlc": "org.videolan.vlc",
    "file manager": "com.ape.filemanager",
}

# Deep links para apps que prefieren URL
_APP_URLS = {
    "youtube": "https://www.youtube.com",
}

# Canales de noticias en vivo en YouTube (presets verificados). Las URLs /live
# resuelven al stream en curso del canal.
_CANALES_YT = {
    "dw": "https://www.youtube.com/@dwespanol/live",
    "dw espanol": "https://www.youtube.com/@dwespanol/live",
    "cdn": "https://www.youtube.com/channel/UCpFfLf9o4wJr-yr7dG8gYug/live",
    "cdn37": "https://www.youtube.com/channel/UCpFfLf9o4wJr-yr7dG8gYug/live",
    "noticias sin": "https://www.youtube.com/channel/UCbBIwG4LJfQyM4ZdoiujBxg/live",
    "sin": "https://www.youtube.com/channel/UCbBIwG4LJfQyM4ZdoiujBxg/live",
    "color vision": "https://www.youtube.com/channel/UCiDATmLMS6XfkB7mh8pmeHg/live",
    "listin": "https://www.youtube.com/@nlistindiario/live",
}

# Comandos en español a keycodes Android
_CONTROLES = {
    "arriba": "KEYCODE_DPAD_UP",
    "abajo": "KEYCODE_DPAD_DOWN",
    "izquierda": "KEYCODE_DPAD_LEFT",
    "derecha": "KEYCODE_DPAD_RIGHT",
    "ok": "KEYCODE_DPAD_CENTER",
    "enter": "KEYCODE_ENTER",
    "seleccionar": "KEYCODE_DPAD_CENTER",
    "atras": "KEYCODE_BACK",
    "back": "KEYCODE_BACK",
    "home": "KEYCODE_HOME",
    "inicio": "KEYCODE_HOME",
    "menu": "KEYCODE_MENU",
    "play": "KEYCODE_MEDIA_PLAY_PAUSE",
    "pausa": "KEYCODE_MEDIA_PAUSE",
    "pause": "KEYCODE_MEDIA_PAUSE",
    "stop": "KEYCODE_MEDIA_STOP",
    "siguiente": "KEYCODE_MEDIA_NEXT",
    "anterior": "KEYCODE_MEDIA_PREVIOUS",
    "adelantar": "KEYCODE_MEDIA_FAST_FORWARD",
    "retroceder": "KEYCODE_MEDIA_REWIND",
    "mute": "KEYCODE_VOLUME_MUTE",
    "silencio": "KEYCODE_VOLUME_MUTE",
    "buscar": "KEYCODE_SEARCH",
    "info": "KEYCODE_INFO",
    "guia": "KEYCODE_GUIDE",
    "apagar": "KEYCODE_POWER",
    "encender": "KEYCODE_POWER",
    "volumen_subir": "KEYCODE_VOLUME_UP",
    "volumen_bajar": "KEYCODE_VOLUME_DOWN",
}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _cargar_tvs() -> dict:
    os.makedirs(_DATA_DIR, exist_ok=True)
    if not os.path.exists(_ARCHIVO_TVS):
        return {}
    try:
        with open(_ARCHIVO_TVS, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return {}


def _guardar_tvs(tvs: dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_ARCHIVO_TVS, "w", encoding="utf-8") as f:
        json.dump(tvs, f, ensure_ascii=False, indent=2)


def _adb(args: str, ip: str = None, timeout: int = 10) -> str:
    """Ejecuta un comando ADB. Retorna stdout."""
    cmd = [_ADB]
    if ip:
        cmd.extend(["-s", f"{ip}:5555"])
    cmd.extend(args.split())
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error: {e}]"


def _adb_shell(command: str, ip: str, timeout: int = 10) -> str:
    """Ejecuta un comando shell en el TV via ADB."""
    cmd = [_ADB, "-s", f"{ip}:5555", "shell"] + command.split()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "[timeout]"
    except Exception as e:
        return f"[error: {e}]"


def _buscar_tv(nombre: str) -> tuple[str, dict] | None:
    tvs = _cargar_tvs()
    nombre_lower = nombre.lower().strip()
    for n, data in tvs.items():
        if n.lower() == nombre_lower or nombre_lower in n.lower():
            return n, data
    return None


def _estado_adb(ip: str) -> str:
    """Devuelve el estado real del device en `adb devices` (device/unauthorized/offline/'')."""
    for line in _adb("devices").splitlines():
        line = line.strip()
        if line.startswith(f"{ip}:5555"):
            parts = line.split()
            return parts[-1] if parts else ""
    return ""


def _asegurar_conexion(ip: str) -> bool:
    """Verifica/reestablece conexión ADB. Solo True si el device está autorizado ('device').

    Nota: NO basta con que aparezca el ip en la salida — el header 'List of devices'
    contiene la palabra 'device'. Hay que validar el estado real de la línea del device.
    """
    if _estado_adb(ip) == "device":
        return True
    _adb(f"connect {ip}:5555")
    return _estado_adb(ip) == "device"


# ── Operaciones ──────────────────────────────────────────────────────────────

def conectar(nombre: str, ip: str, area: str = None) -> str:
    """Conecta a un TV por IP y lo registra."""
    result = _adb(f"connect {ip}:5555")

    if "cannot" in result.lower() or "refused" in result.lower():
        return (f"No se pudo conectar a {ip}. Verifica que:\n"
                f"  1. El TV este encendido\n"
                f"  2. Depuracion USB este activada\n"
                f"  3. Este en la misma red WiFi\n"
                f"Error: {result}")

    if "unauthorized" in result.lower() or "authenticate" in result.lower():
        return (f"Conexion a {ip} requiere autorizacion.\n"
                f"Revisa el TV — debe aparecer un mensaje para permitir la depuracion.\n"
                f"Acepta y marca 'Siempre permitir'. Luego intenta de nuevo.")

    # Obtener info del TV
    modelo = _adb_shell("getprop ro.product.model", ip)
    marca = _adb_shell("getprop ro.product.brand", ip)
    android = _adb_shell("getprop ro.build.version.release", ip)

    tvs = _cargar_tvs()
    tvs[nombre] = {
        "ip": ip,
        "modelo": modelo,
        "marca": marca,
        "android": android,
        "area": area,
    }
    _guardar_tvs(tvs)

    area_txt = f" [{area}]" if area else ""
    return (f"TV conectado: '{nombre}'{area_txt}\n"
            f"  IP: {ip}\n"
            f"  Marca: {marca}\n"
            f"  Modelo: {modelo}\n"
            f"  Android: {android}")


def estado(nombre: str = None) -> str:
    """Estado de un TV o todos los TVs."""
    tvs = _cargar_tvs()
    if not tvs:
        return "No hay TVs registrados. Usa conectar(nombre, ip) para agregar uno."

    if nombre:
        result = _buscar_tv(nombre)
        if not result:
            return f"TV '{nombre}' no encontrado."
        tvs = {result[0]: result[1]}

    lineas = [f"TVs ({len(tvs)}):"]

    for n, data in tvs.items():
        ip = data["ip"]
        area_txt = f" [{data.get('area', '')}]" if data.get("area") else ""

        if not _asegurar_conexion(ip):
            lineas.append(f"\n  {n}{area_txt} ({ip}) — sin conexion")
            continue

        # Estado de pantalla
        power = _adb_shell("dumpsys power | grep 'Display Power'", ip)
        is_on = "ON" in power

        # App actual
        focus = _adb_shell("dumpsys window | grep mCurrentFocus", ip)
        app_raw = ""
        if "/" in focus:
            app_raw = focus.split("/")[0].split()[-1] if focus else "?"

        # Volumen
        vol = _adb_shell("dumpsys audio | grep 'STREAM_MUSIC' -A 3 | grep 'Muted\\|volume'", ip)

        estado_txt = "Encendido" if is_on else "Apagado/Standby"
        modelo = data.get("modelo", "?")

        lineas.append(f"\n  {n}{area_txt} ({ip}) — {modelo}")
        lineas.append(f"    Estado: {estado_txt}")
        lineas.append(f"    App: {app_raw or '?'}")

    return "\n".join(lineas)


def encender(nombre: str) -> str:
    """Enciende un TV."""
    result = _buscar_tv(nombre)
    if not result:
        return f"TV '{nombre}' no encontrado."
    nombre, data = result
    ip = data["ip"]

    if not _asegurar_conexion(ip):
        return f"No se pudo conectar a '{nombre}' ({ip})."

    power = _adb_shell("dumpsys power | grep 'Display Power'", ip)
    if "ON" in power:
        return f"'{nombre}' ya esta encendido."

    _adb_shell("input keyevent KEYCODE_WAKEUP", ip)
    return f"'{nombre}' encendido."


def apagar(nombre: str) -> str:
    """Apaga un TV."""
    result = _buscar_tv(nombre)
    if not result:
        return f"TV '{nombre}' no encontrado."
    nombre, data = result
    ip = data["ip"]

    if not _asegurar_conexion(ip):
        return f"No se pudo conectar a '{nombre}' ({ip})."

    power = _adb_shell("dumpsys power | grep 'Display Power'", ip)
    if "OFF" in power:
        return f"'{nombre}' ya esta apagado."

    _adb_shell("input keyevent KEYCODE_SLEEP", ip)
    return f"'{nombre}' apagado."


def volumen(nombre: str, accion: str, nivel: int = None) -> str:
    """Controla volumen: subir, bajar, mute."""
    result = _buscar_tv(nombre)
    if not result:
        return f"TV '{nombre}' no encontrado."
    nombre, data = result
    ip = data["ip"]

    if not _asegurar_conexion(ip):
        return f"No se pudo conectar a '{nombre}'."

    accion_lower = accion.lower()
    if accion_lower in ("mute", "silencio", "silenciar"):
        _adb_shell("input keyevent KEYCODE_VOLUME_MUTE", ip)
        return f"'{nombre}': Silenciado"
    elif accion_lower in ("subir", "up", "+"):
        pasos = nivel or 1
        for _ in range(pasos):
            _adb_shell("input keyevent KEYCODE_VOLUME_UP", ip)
        return f"'{nombre}': Volumen +{pasos}"
    elif accion_lower in ("bajar", "down", "-"):
        pasos = nivel or 1
        for _ in range(pasos):
            _adb_shell("input keyevent KEYCODE_VOLUME_DOWN", ip)
        return f"'{nombre}': Volumen -{pasos}"
    else:
        return f"Accion '{accion}' no reconocida. Usa: subir, bajar, mute"


def app(nombre: str, aplicacion: str) -> str:
    """Abre una app en el TV."""
    result = _buscar_tv(nombre)
    if not result:
        return f"TV '{nombre}' no encontrado."
    nombre, data = result
    ip = data["ip"]

    if not _asegurar_conexion(ip):
        return f"No se pudo conectar a '{nombre}'."

    app_lower = aplicacion.lower().strip()

    # Intentar deep link primero
    if app_lower in _APP_URLS:
        url = _APP_URLS[app_lower]
        _adb_shell(f"am start -a android.intent.action.VIEW -d {url}", ip)
        return f"'{nombre}': Abriendo {aplicacion}"

    # Intentar por package name
    package = _APPS.get(app_lower, aplicacion)
    result_launch = _adb_shell(f"monkey -p {package} -c android.intent.category.LAUNCHER 1", ip)

    if "No activities" in result_launch:
        # Listar apps instaladas que coincidan
        apps = _adb_shell("pm list packages", ip)
        matches = [l.replace("package:", "") for l in apps.splitlines()
                   if app_lower in l.lower()]
        if matches:
            return (f"App '{aplicacion}' no encontrada como '{package}'.\n"
                    f"Apps similares: {', '.join(matches[:5])}")
        return f"App '{aplicacion}' no instalada en '{nombre}'."

    return f"'{nombre}': Abriendo {aplicacion}"


def youtube(nombre: str, canal: str = None, url: str = None,
            buscar: str = None, video: str = None) -> str:
    """Reproduce contenido de YouTube en el TV.

    Opciones (en orden de prioridad):
      canal  — preset de noticias en vivo (dw, cdn, noticias sin, color vision, listin)
      url    — cualquier URL de YouTube (canal/live, watch?v=, etc.)
      video  — ID de video de YouTube
      buscar — texto de búsqueda (abre resultados)
    Si no se pasa nada, abre YouTube en home.
    """
    result = _buscar_tv(nombre)
    if not result:
        return f"TV '{nombre}' no encontrado."
    nombre, data = result
    ip = data["ip"]

    if not _asegurar_conexion(ip):
        return (f"No se pudo conectar a '{nombre}' (estado ADB: {_estado_adb(ip) or 'sin device'}). "
                f"Si dice 'unauthorized', acepta la depuración USB en la TV.")

    if canal:
        destino = _CANALES_YT.get(canal.lower().strip())
        if not destino:
            disp = ", ".join(sorted(set(_CANALES_YT.keys())))
            return f"Canal '{canal}' no está en presets. Disponibles: {disp}. O usa url=/buscar=/video=."
        etiqueta = f"canal '{canal}' en vivo"
    elif url:
        destino = url
        etiqueta = url
    elif video:
        destino = f"https://www.youtube.com/watch?v={video}"
        etiqueta = f"video {video}"
    elif buscar:
        from urllib.parse import quote_plus
        destino = f"https://www.youtube.com/results?search_query={quote_plus(buscar)}"
        etiqueta = f"búsqueda '{buscar}'"
    else:
        destino = "https://www.youtube.com"
        etiqueta = "YouTube (home)"

    _adb_shell("input keyevent KEYCODE_WAKEUP", ip)  # asegurar pantalla encendida
    _adb_shell(f"am start -a android.intent.action.VIEW -d {destino}", ip)
    return f"'{nombre}': reproduciendo {etiqueta} en YouTube"


def control(nombre: str, comando: str) -> str:
    """Envía un comando de navegación al TV."""
    result = _buscar_tv(nombre)
    if not result:
        return f"TV '{nombre}' no encontrado."
    nombre, data = result
    ip = data["ip"]

    if not _asegurar_conexion(ip):
        return f"No se pudo conectar a '{nombre}'."

    key = _CONTROLES.get(comando.lower().strip())
    if not key:
        if comando.upper().startswith("KEYCODE_"):
            key = comando.upper()
        else:
            comandos_disp = ", ".join(sorted(_CONTROLES.keys()))
            return f"Comando '{comando}' no reconocido. Disponibles: {comandos_disp}"

    _adb_shell(f"input keyevent {key}", ip)
    return f"'{nombre}': {comando}"


def escribir(nombre: str, texto: str) -> str:
    """Escribe texto en el TV."""
    result = _buscar_tv(nombre)
    if not result:
        return f"TV '{nombre}' no encontrado."
    nombre, data = result
    ip = data["ip"]

    if not _asegurar_conexion(ip):
        return f"No se pudo conectar a '{nombre}'."

    # Escapar espacios para ADB
    texto_escaped = texto.replace(" ", "%s").replace("'", "\\'")
    _adb_shell(f"input text '{texto_escaped}'", ip)
    return f"'{nombre}': Texto enviado: '{texto}'"


def apagar_todos() -> str:
    """Apaga todos los TVs registrados."""
    tvs = _cargar_tvs()
    if not tvs:
        return "No hay TVs registrados."

    resultados = []
    for nombre in tvs:
        resultados.append(apagar(nombre))
    return "\n".join(resultados)


def listar() -> str:
    """Lista todos los TVs registrados."""
    tvs = _cargar_tvs()
    if not tvs:
        return ("No hay TVs registrados.\n"
                "Para agregar uno usa: conectar(nombre='TV Sala', ip='192.168.1.XX')\n"
                "Requiere Depuracion USB activada en el TV.")

    lineas = [f"TVs registrados ({len(tvs)}):"]
    for n, data in tvs.items():
        area = f" [{data.get('area')}]" if data.get("area") else ""
        modelo = data.get("modelo", "?")
        marca = data.get("marca", "?")
        lineas.append(f"  - {n}{area}: {data['ip']} ({marca} {modelo})")

    lineas.append(f"\nApps: {', '.join(sorted(_APPS.keys()))}")
    lineas.append(f"Controles: {', '.join(sorted(_CONTROLES.keys()))}")
    return "\n".join(lineas)


def escanear() -> str:
    """Busca Android TVs en la red local."""
    import subprocess
    result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
    import re
    ips = set(re.findall(r"(\d+\.\d+\.\d+\.\d+)", result.stdout))

    found = []
    for ip in sorted(ips):
        if not ip.startswith("192.168.") or ip.endswith(".255") or ip.endswith(".1"):
            continue
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            r = s.connect_ex((ip, 5555))
            s.close()
            if r == 0:
                found.append(ip)
        except Exception:
            pass

    if not found:
        return "No se encontraron Android TVs con ADB activo en la red."

    lineas = [f"TVs encontrados ({len(found)}):"]
    for ip in found:
        lineas.append(f"  - {ip}:5555")
    lineas.append("\nUsa conectar(nombre='TV Sala', ip='X.X.X.X') para registrar uno.")
    return "\n".join(lineas)


# ── Dispatcher ───────────────────────────────────────────────────────────────

_OPERACIONES = {
    "conectar": conectar,
    "estado": estado,
    "encender": encender,
    "apagar": apagar,
    "volumen": volumen,
    "app": app,
    "youtube": youtube,
    "control": control,
    "escribir": escribir,
    "apagar_todos": apagar_todos,
    "listar": listar,
    "escanear": escanear,
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
        logger.error(f"google_tv.ejecutar({operacion}): {e}", exc_info=True)
        return f"Error en '{operacion}': {e}"
