"""
main.py — Agente IA Local (terminal)

Modos de entrada:
  - Texto  : escribe tu mensaje y presiona ENTER
  - Voz    : activa con /voz y presiona ENTER para grabar

Comandos disponibles:
  /limpiar   — borra el historial de conversación
  /memoria   — muestra las memorias guardadas
  /voz       — activa/desactiva modo voz (toggle)
  /voz on    — activa modo voz
  /voz off   — desactiva modo voz
  /salir     — sale del agente
"""
import os
import sys
import subprocess
from dotenv import load_dotenv

load_dotenv()

# Asegurar que agente_core/ esté en el path
_root = os.path.dirname(os.path.abspath(__file__))
_core = os.path.join(_root, "agente_core")
for p in (_core, _root):
    if p not in sys.path:
        sys.path.insert(0, p)

from agente_core.provider_config import obtener_configuracion
from agente_core.agent import Agent
from agente_core.voice_handler import transcribir, sintetizar, limpiar_audio_temp
from agente_core.mic_recorder import grabar, limpiar

# ── Configuración de proveedor ─────────────────────────────────────────────
_cfg = obtener_configuracion(non_interactive=False)
if _cfg is None:
    print("ERROR: No hay proveedores configurados en .env — abortando.")
    sys.exit(1)

MODEL    = _cfg["model"]
API_KEY  = _cfg["api_key"]
BASE_URL = _cfg["base_url"]
PROVIDER = _cfg["provider"]

# ── Configuración de voz ───────────────────────────────────────────────────
_voz_activa = os.getenv("VOZ_HABILITADO", "false").lower() == "true"
_VOZ_DURACION = int(os.getenv("VOZ_DURACION_MAX", "12"))

# ── Streaming ──────────────────────────────────────────────────────────────
_STREAM_HABILITADO = os.getenv("STREAM_HABILITADO", "true").lower() == "true"

print("=" * 52)
print("  Agente IA Local")
print("=" * 52)
print(f"  Proveedor : {_cfg['nombre']}")
print(f"  Modelo    : {MODEL}")
print(f"  Endpoint  : {BASE_URL}")
voz_str    = "ON" if _voz_activa else "OFF"
stream_str = "ON" if _STREAM_HABILITADO else "OFF"
print(f"  Modo voz  : {voz_str}  (cambia con /voz)")
print(f"  Streaming : {stream_str}  (STREAM_HABILITADO en .env)")
print("=" * 52)

# ── Inicializar agente ─────────────────────────────────────────────────────
agent = Agent(
    model=MODEL,
    api_key=API_KEY,
    base_url=BASE_URL,
    provider=PROVIDER,
)


# ── Reproducción de audio (macOS afplay / fallback ffplay) ─────────────────
def _reproducir(ruta: str):
    """Reproduce un archivo de audio en segundo plano."""
    if not ruta or not os.path.exists(ruta):
        return
    try:
        if os.path.exists("/usr/bin/afplay"):
            subprocess.Popen(["afplay", ruta],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(["ffplay", "-nodisp", "-autoexit", ruta],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"⚠️  No se pudo reproducir audio: {e}")


# ── Comandos ───────────────────────────────────────────────────────────────
def cmd_limpiar():
    agent.limpiar_historial()
    print("🧹 Historial limpiado.")
    return True


def cmd_memoria():
    hechos = agent.memoria.listar_hechos()
    if hechos:
        print("\n📝 Memorias guardadas:")
        for h in hechos:
            print(f"  [{h.get('categoria','?')}] {h.get('contenido','')}")
    else:
        print("📝 Sin memorias guardadas aún.")
    return True


def cmd_salir():
    print("Hasta luego!")
    return False


def cmd_voz(arg: str = ""):
    global _voz_activa
    arg = arg.strip().lower()
    if arg == "on":
        _voz_activa = True
    elif arg == "off":
        _voz_activa = False
    else:
        _voz_activa = not _voz_activa   # toggle
    estado = "activado" if _voz_activa else "desactivado"
    print(f"🎙️  Modo voz {estado}.")
    return True


# ── Loop principal ─────────────────────────────────────────────────────────
while True:
    try:
        modo = "🎙️  [ENTER=grabar] " if _voz_activa else "Tú: "
        user_input = input(modo).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nHasta luego!")
        break

    if not user_input and not _voz_activa:
        continue

    # ── Comandos de texto ──────────────────────────────────────────────────
    partes    = user_input.split(maxsplit=1)
    cmd       = partes[0].lower() if partes else ""
    cmd_arg   = partes[1] if len(partes) > 1 else ""

    if cmd == "/limpiar":
        cmd_limpiar(); continue
    if cmd == "/memoria":
        cmd_memoria(); continue
    if cmd in ("/salir", "/exit", "/bye", "/sayonara"):
        cmd_salir(); break
    if cmd == "/voz":
        cmd_voz(cmd_arg); continue
    if cmd == "/ayuda":
        print(__doc__); continue

    # ── Modo voz: grabar desde micrófono ──────────────────────────────────
    if _voz_activa and not user_input:
        audio_path = grabar(segundos=_VOZ_DURACION)
        if not audio_path:
            print("❌ No se pudo grabar audio.")
            continue
        texto = transcribir(audio_path)
        limpiar(audio_path)
        if not texto:
            print("❌ No se pudo transcribir el audio.")
            continue
        print(f"Tú [voz]: {texto}")
        user_input = texto

    elif _voz_activa and user_input:
        # Si el usuario escribió algo en modo voz, se trata como texto
        pass

    # ── Llamada al agente ──────────────────────────────────────────────────
    def _stream_cb(chunk):
        """Imprime tokens del LLM en tiempo real. None = primer token (prefijo)."""
        if chunk is None:
            print("Asistente: ", end="", flush=True)
        else:
            print(chunk, end="", flush=True)

    _usar_stream = _STREAM_HABILITADO and not _voz_activa

    try:
        respuesta = agent.chat(
            user_input,
            stream_callback=_stream_cb if _usar_stream else None,
            contexto={"fuente": "local", "modo": "voz" if _voz_activa else "texto"},
        )

        # Mostrar metadata de la ejecución
        meta = agent._ultima_ejecucion
        if meta.get("herramientas_usadas"):
            print(f"  🔧 Tools: {', '.join(meta['herramientas_usadas'])} "
                  f"| iter: {meta.get('iteraciones',1)} "
                  f"| ~{meta.get('tokens_aprox',0)} tokens")

        # ── TTS: sintetizar y reproducir si modo voz está activo ──────────
        if _voz_activa and respuesta:
            audio_resp = sintetizar(respuesta, lang="es")
            if audio_resp:
                _reproducir(audio_resp)
                # Limpieza diferida (5s para que afplay termine)
                import threading
                threading.Timer(8, limpiar_audio_temp, args=[audio_resp]).start()

    except KeyboardInterrupt:
        print("\n⚠️  Interrumpido.")
    except Exception as e:
        print(f"\n⚠️  Error: {type(e).__name__}: {str(e)[:200]}")
