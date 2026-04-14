"""
Telegram Agente — Punto de entrada principal.

Arquitectura productor-consumidor:
  - Main loop (productor): recibe mensajes, pone en cola, confirma recepción inmediata.
  - Worker thread (consumidor): procesa un mensaje a la vez, envía respuesta al terminar.

Soporte de voz:
  - Entrada: mensajes de voz se transcriben con Whisper antes de pasar al LLM.
  - Salida: si TELEGRAM_VOZ_RESPUESTA=true, la respuesta se sintetiza con gTTS y se
    envía como burbuja de voz además del texto.

Comandos especiales:
  /limpiar  — borra el historial del chat
  /memoria  — muestra las memorias guardadas del agente
  /wiki     — muestra estadísticas de la wiki del agente
  /voz      — activa/desactiva respuestas en voz (/voz on | /voz off)
  /ayuda    — lista de comandos disponibles
"""
import os
import sys
import queue
import threading
from dotenv import load_dotenv

load_dotenv()

# Asegurar que agente_core/ esté en el path
_root = os.path.dirname(os.path.abspath(__file__))
_core = os.path.join(_root, "agente_core")
for p in (_core, _root):
    if p not in sys.path:
        sys.path.insert(0, p)

from telegram_listener import TelegramListener
from telegram_notifier import TelegramNotifier
from agente_core.telegram_bridge import obtener_bridge
from agente_core.logger import get_logger
from agente_core.provider_config import obtener_configuracion
from agente_core.voice_handler import transcribir, sintetizar, limpiar_audio_temp

logger = get_logger("telegram_agente")

# ── Configuración del proveedor ────────────────────────────────────────────
_cfg = obtener_configuracion(non_interactive=True)
if _cfg is None:
    print("ERROR: No hay proveedores configurados en .env — abortando.")
    sys.exit(1)

MODEL    = _cfg["model"]
API_KEY  = _cfg["api_key"]
BASE_URL = _cfg["base_url"]
PROVIDER = _cfg["provider"]

ALLOWED_CHAT_IDS_RAW = os.getenv("ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS: set[int] = set()
if ALLOWED_CHAT_IDS_RAW.strip():
    for cid in ALLOWED_CHAT_IDS_RAW.split(","):
        cid = cid.strip()
        if cid.lstrip("-").isdigit():
            ALLOWED_CHAT_IDS.add(int(cid))

# ── Configuración de voz ───────────────────────────────────────────────────
# Puede cambiarse en runtime con /voz on | /voz off por chat_id
_voz_respuesta_global = os.getenv("TELEGRAM_VOZ_RESPUESTA", "false").lower() == "true"
_voz_por_chat: dict[int, bool] = {}   # override por chat

def _voz_activa(chat_id: int) -> bool:
    return _voz_por_chat.get(chat_id, _voz_respuesta_global)

# ── Mensajes de progreso ───────────────────────────────────────────────────
_TOOL_LABELS: dict[str, str] = {
    "execute_bash":           "⚙️ Ejecutando terminal...",
    "execute_command":        "⚙️ Ejecutando comando...",
    "read_file":              "📄 Leyendo archivo...",
    "edit_file":              "✏️ Editando archivo...",
    "list_files_in_dir":      "📁 Listando directorio...",
    "buscar_en_internet":     "🌐 Buscando en internet...",
    "scrape_url":             "🌐 Obteniendo página...",
    "guardar_memoria":        "💾 Guardando memoria...",
    "listar_skills":          "🧩 Listando skills...",
    "activar_skill":          "🧩 Activando skill...",
    "crear_skill":            "🧩 Creando skill...",
    "ejecutar_script_skill":  "🧩 Ejecutando script...",
    "leer_wiki":              "📖 Leyendo wiki...",
    "escribir_wiki":          "📝 Escribiendo wiki...",
    "actualizar_index_wiki":  "📝 Actualizando índice...",
    "buscar_wiki":            "🔍 Buscando en wiki...",
    "listar_wiki":            "📖 Listando wiki...",
    "enviar_archivo_telegram": "📤 Enviando archivo...",
    "enviar_foto_telegram":    "🖼️ Enviando foto...",
}

_AYUDA = """🤖 *Comandos disponibles*

/limpiar — Borra el historial de conversación
/memoria — Muestra las memorias guardadas
/wiki    — Estadísticas de la base de conocimiento
/voz on  — Activa respuestas en voz
/voz off — Desactiva respuestas en voz
/ayuda   — Esta lista de comandos

Puedes enviar mensajes de texto o *mensajes de voz* 🎙️"""


# ── Lógica de comandos ─────────────────────────────────────────────────────

def _manejar_comando(texto: str, chat_id: int, notifier: TelegramNotifier) -> bool:
    """Maneja comandos especiales. Retorna True si fue un comando."""
    partes = texto.strip().lower().split()
    cmd = partes[0]

    if cmd == "/limpiar":
        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER, notifier)
        bridge.limpiar_historial()
        notifier.enviar(chat_id, "🧹 Historial limpiado.")
        return True

    if cmd == "/memoria":
        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER, notifier)
        ctx = bridge.obtener_memoria()
        notifier.enviar(chat_id, f"💾 *Memoria del agente:*\n\n{ctx or '(vacía)'}")
        return True

    if cmd == "/wiki":
        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER, notifier)
        stats = bridge.obtener_wiki_stats()
        msg = (f"📚 *Wiki stats*\n"
               f"Páginas: {stats.get('total_paginas', 0)}\n"
               f"Directorio: `{stats.get('wiki_dir', '?')}`")
        notifier.enviar(chat_id, msg)
        return True

    if cmd == "/voz":
        arg = partes[1] if len(partes) > 1 else ""
        if arg == "on":
            _voz_por_chat[chat_id] = True
            notifier.enviar(chat_id, "🔊 Respuestas en voz *activadas*.")
        elif arg == "off":
            _voz_por_chat[chat_id] = False
            notifier.enviar(chat_id, "🔇 Respuestas en voz *desactivadas*.")
        else:
            estado = "activada" if _voz_activa(chat_id) else "desactivada"
            notifier.enviar(chat_id, f"🎙️ Voz actualmente *{estado}*. Usa `/voz on` o `/voz off`.")
        return True

    if cmd == "/ayuda":
        notifier.enviar(chat_id, _AYUDA)
        return True

    return False


# ── Worker (consumidor) ────────────────────────────────────────────────────

def _worker(cola: queue.Queue, notifier: TelegramNotifier):
    """Procesa mensajes de la cola uno a la vez."""
    logger.info("Worker iniciado.")
    while True:
        item = cola.get()
        if item is None:
            logger.info("Worker finalizado.")
            cola.task_done()
            break

        chat_id    = item["chat_id"]
        texto      = item["text"]
        audio_path = item.get("audio_path")
        es_voz     = item.get("es_voz", False)

        # ── STT: transcribir audio si viene de voz ─────────────────────
        if es_voz and audio_path:
            notifier.enviar(chat_id, "🎙️ Transcribiendo audio...")
            texto = transcribir(audio_path)
            limpiar_audio_temp(audio_path)
            if not texto:
                notifier.enviar(chat_id, "❌ No pude entender el audio. Intenta de nuevo.")
                cola.task_done()
                continue
            logger.info(f"Transcripción: {texto[:100]}")
            # Confirmar al usuario lo que se entendió
            notifier.enviar(chat_id, f"🗣️ Entendí: _{texto}_")

        if not texto:
            cola.task_done()
            continue

        # ── Comando especial ───────────────────────────────────────────
        if texto.startswith("/"):
            try:
                _manejar_comando(texto, chat_id, notifier)
            except Exception as e:
                logger.error(f"Error manejando comando: {e}", exc_info=True)
                notifier.enviar(chat_id, f"❌ Error: {e}")
            cola.task_done()
            continue

        # ── Mensaje al LLM ─────────────────────────────────────────────
        progress_msg_id = notifier.enviar(chat_id, "🤔 Procesando...")
        last_label: list[str] = [""]

        def progress_callback(tool_name: str):
            label = _TOOL_LABELS.get(tool_name, f"🔧 {tool_name}...")
            if label != last_label[0]:
                last_label[0] = label
                if progress_msg_id:
                    notifier.editar(chat_id, progress_msg_id, label)

        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER, notifier)
        try:
            respuesta = bridge.procesar(texto, progress_callback=progress_callback)
        except Exception as e:
            logger.error(f"Error en bridge.procesar: {e}", exc_info=True)
            respuesta = f"❌ Error inesperado: {e}"

        if progress_msg_id:
            notifier.editar(chat_id, progress_msg_id, "✅ Listo.")

        # ── Enviar respuesta en texto ──────────────────────────────────
        notifier.enviar(chat_id, respuesta)

        # ── TTS: responder con voz si está activado ────────────────────
        if _voz_activa(chat_id) and respuesta:
            speed = float(os.getenv("TTS_SPEED", "1.0"))
            audio_resp = sintetizar(respuesta, lang="es", speed=speed)
            if audio_resp:
                notifier.enviar_voz(chat_id, audio_resp)
                limpiar_audio_temp(audio_resp)

        cola.task_done()


# ── Main loop (productor) ──────────────────────────────────────────────────

def main():
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("ERROR: TELEGRAM_BOT_TOKEN no está definido en .env")
        sys.exit(1)

    listener = TelegramListener()
    notifier = TelegramNotifier()

    cola: queue.Queue = queue.Queue()
    worker_thread = threading.Thread(target=_worker, args=(cola, notifier), daemon=True)
    worker_thread.start()

    voz_str = "🔊 ON" if _voz_respuesta_global else "🔇 OFF"
    print(f"[Telegram Agente] Escuchando... modelo={MODEL} proveedor={PROVIDER} | voz={voz_str}")
    logger.info(f"Agente iniciado. modelo={MODEL} proveedor={PROVIDER} voz={_voz_respuesta_global}")

    if ALLOWED_CHAT_IDS:
        logger.info(f"Lista de acceso: {ALLOWED_CHAT_IDS}")
    else:
        logger.warning("ALLOWED_CHAT_IDS vacío — cualquier chat puede usar el agente.")

    try:
        while True:
            updates = listener.get_updates()
            mensajes = listener.extraer_mensajes(updates)

            for msg in mensajes:
                chat_id = msg["chat_id"]
                texto   = msg["text"]
                es_voz  = msg.get("es_voz", False)

                # Filtro de acceso
                if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
                    logger.warning(f"Chat no autorizado: {chat_id}")
                    notifier.enviar(chat_id, "⛔ No tienes acceso a este agente.")
                    continue

                if es_voz:
                    logger.info(f"Voz de {msg['user']} ({chat_id})")
                else:
                    logger.info(f"Texto de {msg['user']} ({chat_id}): {texto[:80]}")

                cola.put(msg)

    except KeyboardInterrupt:
        print("\nDeteniendo agente...")
        cola.put(None)
        worker_thread.join(timeout=5)
        logger.info("Agente detenido.")


if __name__ == "__main__":
    main()
