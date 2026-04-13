"""Bridge entre Telegram y el Agente IA.

Responsabilidades:
- Mantener una instancia de Agent por chat_id
- Protección anti-loop: límite de iteraciones + detección de tool calls repetidos
- Soporte de progress_callback para notificaciones en tiempo real
"""
import os
import sys

_core = os.path.dirname(os.path.abspath(__file__))
if _core not in sys.path:
    sys.path.insert(0, _core)

from agent import Agent
from logger import get_logger

logger = get_logger("telegram_bridge")

# ── Configuración anti-loop ────────────────────────────────────────────────
MAX_ITERACIONES = int(os.getenv("TELEGRAM_MAX_ITER", "20"))
MAX_REPETICIONES_TOOL = 3   # cuántas veces puede llamar la MISMA tool sin parar


class TelegramBridge:
    """Una instancia por sesión de chat."""

    def __init__(self, chat_id: int, model: str, api_key: str,
                 base_url: str = None, provider: str = "openai"):
        self.chat_id = chat_id
        self._agente = Agent(
            model=model,
            api_key=api_key,
            base_url=base_url,
            provider=provider,
        )
        self._reset_loop_counters()

    # ── Anti-loop helpers ──────────────────────────────────────────────────

    def _reset_loop_counters(self):
        self._iteraciones = 0
        self._ultima_tool: str | None = None
        self._rep_tool = 0

    def _registrar_tool(self, tool_name: str) -> bool:
        """Registra un uso de tool. Retorna False si hay loop detectado."""
        if tool_name == self._ultima_tool:
            self._rep_tool += 1
            if self._rep_tool >= MAX_REPETICIONES_TOOL:
                logger.warning(
                    f"[anti-loop] Tool '{tool_name}' repetida "
                    f"{self._rep_tool} veces — abortando."
                )
                return False
        else:
            self._ultima_tool = tool_name
            self._rep_tool = 1
        return True

    # ── API pública ────────────────────────────────────────────────────────

    def procesar(self, mensaje: str, progress_callback=None) -> str:
        """
        Procesa un mensaje del usuario. Retorna la respuesta final del agente.

        progress_callback(tool_name: str) — llamado antes de ejecutar cada tool,
        útil para enviar actualizaciones de progreso a Telegram.
        """
        self._reset_loop_counters()

        # Wrapper del progress_callback que también aplica anti-loop
        def _cb(tool_name: str):
            self._iteraciones += 1
            if self._iteraciones > MAX_ITERACIONES:
                raise _LoopLimitError(
                    f"Límite de {MAX_ITERACIONES} iteraciones alcanzado."
                )
            if not self._registrar_tool(tool_name):
                raise _LoopLimitError(
                    f"Tool '{tool_name}' en loop — detenido."
                )
            if progress_callback:
                progress_callback(tool_name)

        try:
            return self._agente.chat(mensaje, progress_callback=_cb)
        except _LoopLimitError as e:
            logger.warning(f"[bridge] Loop detectado: {e}")
            return (
                "⚠️ El agente entró en un loop y fue detenido automáticamente.\n"
                f"Detalle: {e}\n\n"
                "Puedes usar /limpiar para reiniciar el historial."
            )
        except Exception as e:
            logger.error(f"[bridge] Error inesperado: {e}", exc_info=True)
            return f"❌ Error interno del agente: {e}"

    def limpiar_historial(self):
        self._agente.limpiar_historial()
        self._reset_loop_counters()

    def obtener_memoria(self) -> str:
        return self._agente.memoria.obtener_contexto()

    def obtener_wiki_stats(self) -> dict:
        return self._agente.wiki.estadisticas()


class _LoopLimitError(Exception):
    pass


# ── Registry global de bridges por chat ───────────────────────────────────

_bridges: dict[int, TelegramBridge] = {}


def obtener_bridge(chat_id: int, model: str, api_key: str,
                   base_url: str = None, provider: str = "openai") -> TelegramBridge:
    """Retorna (o crea) el bridge para un chat_id."""
    if chat_id not in _bridges:
        logger.info(f"Creando bridge para chat_id={chat_id}")
        _bridges[chat_id] = TelegramBridge(
            chat_id=chat_id,
            model=model,
            api_key=api_key,
            base_url=base_url,
            provider=provider,
        )
    return _bridges[chat_id]
