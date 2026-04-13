"""
Telegram Agente — Punto de entrada principal.

Arquitectura productor-consumidor:
  - Main loop (productor): recibe mensajes, pone en cola, confirma recepción inmediata.
  - Worker thread (consumidor): procesa un mensaje a la vez, envía respuesta al terminar.

Comandos especiales (manejados antes de llegar al LLM):
  /limpiar  — borra el historial del chat
  /memoria  — muestra las memorias guardadas del agente
  /wiki     — muestra estadísticas de la wiki del agente
  /ayuda    — lista de comandos disponibles
"""
import os
import sys
import queue
import threading
import time
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

logger = get_logger("telegram_agente")

# ── Configuración ─────────────────────────────────────────────────────────
MODEL = os.getenv("MODEL_NAME", "")
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("API_BASE_URL", None)
PROVIDER = os.getenv("PROVIDER", "openai")

ALLOWED_CHAT_IDS_RAW = os.getenv("ALLOWED_CHAT_IDS", "")
ALLOWED_CHAT_IDS: set[int] = set()
if ALLOWED_CHAT_IDS_RAW.strip():
    for cid in ALLOWED_CHAT_IDS_RAW.split(","):
        cid = cid.strip()
        if cid.lstrip("-").isdigit():
            ALLOWED_CHAT_IDS.add(int(cid))

# ── Mensajes de progreso ──────────────────────────────────────────────────
_TOOL_LABELS: dict[str, str] = {
    "execute_bash":        "⚙️ Ejecutando terminal...",
    "execute_command":     "⚙️ Ejecutando comando...",
    "read_file":           "📄 Leyendo archivo...",
    "edit_file":           "✏️ Editando archivo...",
    "list_files_in_dir":   "📁 Listando directorio...",
    "buscar_en_internet":  "🌐 Buscando en internet...",
    "scrape_url":          "🌐 Obteniendo página...",
    "guardar_memoria":     "💾 Guardando memoria...",
    "listar_skills":       "🧩 Listando skills...",
    "activar_skill":       "🧩 Activando skill...",
    "ejecutar_script_skill": "🧩 Ejecutando script...",
    "leer_wiki":           "📖 Leyendo wiki...",
    "escribir_wiki":       "📝 Escribiendo wiki...",
    "actualizar_index_wiki": "📝 Actualizando índice...",
    "buscar_wiki":         "🔍 Buscando en wiki...",
    "listar_wiki":         "📖 Listando wiki...",
}

_AYUDA = """🤖 *Comandos disponibles*

/limpiar — Borra el historial de conversación
/memoria — Muestra las memorias guardadas
/wiki — Estadísticas de la base de conocimiento
/ayuda — Esta lista de comandos

Todo lo demás se procesa con el LLM."""


# ── Lógica de comandos ────────────────────────────────────────────────────

def _manejar_comando(texto: str, chat_id: int, notifier: TelegramNotifier) -> bool:
    """
    Si el texto es un comando especial, lo maneja y retorna True.
    Si no es comando, retorna False.
    """
    cmd = texto.strip().lower().split()[0]

    if cmd == "/limpiar":
        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER)
        bridge.limpiar_historial()
        notifier.enviar(chat_id, "🧹 Historial limpiado.")
        return True

    if cmd == "/memoria":
        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER)
        ctx = bridge.obtener_memoria()
        notifier.enviar(chat_id, f"💾 *Memoria del agente:*\n\n{ctx or '(vacía)'}")
        return True

    if cmd == "/wiki":
        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER)
        stats = bridge.obtener_wiki_stats()
        msg = (
            f"📚 *Wiki stats*\n"
            f"Páginas: {stats.get('total_paginas', 0)}\n"
            f"Directorio: `{stats.get('wiki_dir', '?')}`"
        )
        notifier.enviar(chat_id, msg)
        return True

    if cmd == "/ayuda":
        notifier.enviar(chat_id, _AYUDA)
        return True

    return False


# ── Worker (consumidor) ───────────────────────────────────────────────────

def _worker(cola: queue.Queue, notifier: TelegramNotifier):
    """Procesa mensajes de la cola uno a la vez."""
    logger.info("Worker iniciado.")
    while True:
        item = cola.get()
        if item is None:
            logger.info("Worker finalizado.")
            cola.task_done()
            break

        chat_id = item["chat_id"]
        texto = item["text"]
        logger.info(f"Procesando msg de chat_id={chat_id}: {texto[:80]}")

        # ── Comando especial ──
        if texto.startswith("/"):
            try:
                _manejar_comando(texto, chat_id, notifier)
            except Exception as e:
                logger.error(f"Error manejando comando: {e}", exc_info=True)
                notifier.enviar(chat_id, f"❌ Error: {e}")
            cola.task_done()
            continue

        # ── Mensaje LLM ──
        # Enviamos mensaje de "pensando" y lo editamos con progreso
        progress_msg_id = notifier.enviar(chat_id, "🤔 Procesando...")
        last_label: list[str] = [""]

        def progress_callback(tool_name: str):
            label = _TOOL_LABELS.get(tool_name, f"🔧 {tool_name}...")
            if label != last_label[0]:
                last_label[0] = label
                if progress_msg_id:
                    notifier.editar(chat_id, progress_msg_id, label)

        bridge = obtener_bridge(chat_id, MODEL, API_KEY, BASE_URL, PROVIDER)
        try:
            respuesta = bridge.procesar(texto, progress_callback=progress_callback)
        except Exception as e:
            logger.error(f"Error en bridge.procesar: {e}", exc_info=True)
            respuesta = f"❌ Error inesperado: {e}"

        # Borrar el mensaje de progreso y enviar la respuesta final
        if progress_msg_id:
            notifier.editar(chat_id, progress_msg_id, "✅ Listo.")
        notifier.enviar(chat_id, respuesta)
        cola.task_done()


# ── Main loop (productor) ─────────────────────────────────────────────────

def main():
    if not os.getenv("TELEGRAM_TOKEN"):
        print("ERROR: TELEGRAM_TOKEN no está definido en .env")
        sys.exit(1)
    if not MODEL or not API_KEY:
        print("ERROR: MODEL_NAME / OPENAI_API_KEY no definidos en .env")
        sys.exit(1)

    listener = TelegramListener()
    notifier = TelegramNotifier()

    cola: queue.Queue = queue.Queue()
    worker_thread = threading.Thread(target=_worker, args=(cola, notifier), daemon=True)
    worker_thread.start()

    print(f"[Telegram Agente] Escuchando... modelo={MODEL} proveedor={PROVIDER}")
    logger.info(f"Agente iniciado. modelo={MODEL} proveedor={PROVIDER}")

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
                texto = msg["text"]

                # Filtro de acceso
                if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
                    logger.warning(f"Chat no autorizado: {chat_id}")
                    notifier.enviar(chat_id, "⛔ No tienes acceso a este agente.")
                    continue

                logger.info(f"Recibido de {msg['user']} ({chat_id}): {texto[:80]}")

                # ACK inmediato solo para mensajes LLM (los comandos se procesan directo)
                if not texto.startswith("/"):
                    notifier.enviar(chat_id, "📨 Mensaje recibido, procesando...")

                cola.put(msg)

    except KeyboardInterrupt:
        print("\nDeteniendo agente...")
        cola.put(None)          # señal de fin al worker
        worker_thread.join(timeout=5)
        logger.info("Agente detenido.")


if __name__ == "__main__":
    main()
