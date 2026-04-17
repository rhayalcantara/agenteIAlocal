"""
Punto de entrada para el agente en modo consola.

Comandos disponibles:
  /limpiar   — borra el historial de conversación
  /memoria   — muestra las memorias guardadas
  /voz       — activa/desactiva modo voz (toggle)
  /voz on    — activa modo voz
  /voz off   — desactiva modo voz
  /ayuda     — muestra esta ayuda
  salir      — sale del agente
"""
import sys
import os
import subprocess
import threading
import queue
import re

# Asegurar que agente_core/ esté en el path
_dir = os.path.dirname(os.path.abspath(__file__))
if _dir not in sys.path:
    sys.path.insert(0, _dir)

# Cargar .env desde la raíz del proyecto
from dotenv import load_dotenv
load_dotenv(os.path.join(_dir, "..", ".env"))

from provider_config import obtener_configuracion
from agent import Agent
from voice_handler import transcribir, sintetizar, limpiar_audio_temp
from mic_recorder import grabar, limpiar as limpiar_audio
from logger import get_logger

logger = get_logger("main")

# ── Configuración de voz ───────────────────────────────────────────────────
_voz_activa = os.getenv("VOZ_HABILITADO", "false").lower() == "true"


# ── Reproducción de audio (macOS afplay / fallback ffplay) ─────────────────
def _reproducir(ruta: str):
    """Reproduce audio y espera a que termine antes de continuar.

    afplay (macOS) no soporta OGG/Opus — usa ffplay para ese formato.
    """
    if not ruta or not os.path.exists(ruta):
        return
    try:
        usar_ffplay = ruta.endswith(".ogg") or not os.path.exists("/usr/bin/afplay")
        if usar_ffplay:
            subprocess.run(["ffplay", "-nodisp", "-autoexit", ruta],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["afplay", ruta],
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"⚠️  No se pudo reproducir audio: {e}")


def _dividir_en_chunks(texto: str, max_chars: int = 400) -> list[str]:
    """Divide texto en trozos naturales respetando oraciones."""
    partes = re.split(r'(?<=[.!?])\s+', texto.strip())
    chunks, actual = [], ""
    for parte in partes:
        if not parte:
            continue
        if len(actual) + len(parte) + 1 <= max_chars:
            actual = (actual + " " + parte).strip()
        else:
            if actual:
                chunks.append(actual)
            # Si la parte sola es mayor que max_chars, córtala por comas
            if len(parte) > max_chars:
                subpartes = re.split(r'(?<=,)\s+', parte)
                sub_actual = ""
                for sub in subpartes:
                    if len(sub_actual) + len(sub) + 1 <= max_chars:
                        sub_actual = (sub_actual + " " + sub).strip()
                    else:
                        if sub_actual:
                            chunks.append(sub_actual)
                        sub_actual = sub
                if sub_actual:
                    chunks.append(sub_actual)
                actual = ""
            else:
                actual = parte
    if actual:
        chunks.append(actual)
    return chunks


def _reproducir_tts_pipeline(texto: str, lang: str = "es"):
    """Convierte texto en chunks y los reproduce en pipeline.

    El productor convierte el siguiente chunk mientras el consumidor
    reproduce el actual — reduce la espera total significativamente.
    """
    from voice_handler import _limpiar_texto_tts
    texto_limpio = _limpiar_texto_tts(texto)
    if not texto_limpio:
        return

    chunks = _dividir_en_chunks(texto_limpio)
    if not chunks:
        return

    q = queue.Queue(maxsize=2)

    def _productor():
        for chunk in chunks:
            try:
                audio = sintetizar(chunk, lang=lang)
            except Exception:
                audio = None
            q.put(audio)
        q.put(None)  # señal de fin

    t = threading.Thread(target=_productor, daemon=True)
    t.start()

    while True:
        audio = q.get()
        if audio is None:
            break
        if audio:
            _reproducir(audio)
            limpiar_audio_temp(audio)


def _turno_voz(agente) -> str | None:
    """Graba voz directamente sin esperar ENTER. Retorna el texto transcrito o None."""
    print("\n🎙️  Puedes hablar ahora  (Ctrl+C para escribir un comando)", flush=True)
    try:
        audio_path = grabar()
    except KeyboardInterrupt:
        try:
            user_input = input("\nComando: ").strip()
            return user_input if user_input else None
        except (KeyboardInterrupt, EOFError):
            raise
    if not audio_path:
        return None
    texto = transcribir(audio_path)
    limpiar_audio(audio_path)
    if not texto:
        print("❌ No se pudo transcribir el audio.")
        return None
    print(f"Tú [voz]: {texto}")
    return texto


def cmd_voz(arg: str = ""):
    global _voz_activa
    arg = arg.strip().lower()
    if arg == "on":
        _voz_activa = True
    elif arg == "off":
        _voz_activa = False
    else:
        _voz_activa = not _voz_activa
    estado = "activado" if _voz_activa else "desactivado"
    print(f"🎙️  Modo voz {estado}.")


def main():
    global _voz_activa

    print("=" * 60)
    print("  Agente IA — Modo Consola")
    print("=" * 60)

    try:
        config = obtener_configuracion()
    except KeyboardInterrupt:
        print("\nCancelado.")
        return

    if config is None:
        return

    agente = Agent(
        model=config["model"],
        api_key=config["api_key"],
        base_url=config.get("base_url"),
        provider=config.get("provider", "openai"),
    )

    voz_str = "ON" if _voz_activa else "OFF"
    print(f"  Modelo    : {config['model']} | Proveedor: {config.get('provider')}")
    print(f"  Modo voz  : {voz_str}  (cambia con /voz)")
    print("  Escribe /ayuda para ver comandos disponibles.\n")

    while True:
        try:
            if _voz_activa:
                user_input = _turno_voz(agente)
                if user_input is None:
                    continue
            else:
                user_input = input("Tú: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nHasta luego.")
            break

        if not user_input:
            continue

        # ── Comandos ───────────────────────────────────────────────────────
        partes  = user_input.split(maxsplit=1)
        cmd     = partes[0].lower() if partes else ""
        cmd_arg = partes[1] if len(partes) > 1 else ""

        if cmd in ("salir", "exit", "quit"):
            print("Hasta luego.")
            break

        if cmd in ("limpiar", "/limpiar"):
            agente.limpiar_historial()
            print("[Historial limpiado]\n")
            continue

        if cmd == "/memoria":
            hechos = agente.memoria.listar_hechos()
            if hechos:
                print("\n📝 Memorias guardadas:")
                for h in hechos:
                    print(f"  [{h.get('categoria','?')}] {h.get('contenido','')}")
            else:
                print("📝 Sin memorias guardadas aún.")
            continue

        if cmd == "/voz":
            cmd_voz(cmd_arg)
            continue

        if cmd == "/ayuda":
            print(__doc__)
            continue

        # ── Llamada al agente ──────────────────────────────────────────────
        try:
            respuesta = agente.chat(user_input)
            print(f"\nAgente: {respuesta}\n")

            if _voz_activa and respuesta:
                _reproducir_tts_pipeline(respuesta, lang="es")

        except KeyboardInterrupt:
            print("\n⚠️  Interrumpido.")
        except Exception as e:
            logger.error(f"Error en chat: {e}", exc_info=True)
            print(f"[Error]: {e}\n")


if __name__ == "__main__":
    main()
