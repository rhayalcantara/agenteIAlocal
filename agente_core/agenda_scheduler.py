"""
Agenda Scheduler — Daemon thread que ejecuta acciones automáticas.

Ciclo de vida:
  1. Revisa la agenda cada INTERVALO_REVISION segundos
  2. Para cada acción activa evalúa si debe dispararse (según tipo y horario)
  3. Lanza un thread independiente por acción con un sub-agente temporal
  4. El sub-agente ejecuta el prompt y envía el resultado por Telegram
  5. El resultado (éxito o error) queda registrado en el historial de la acción

El sub-agente es una instancia separada de Agent — no comparte historial
ni estado con el agente principal que atiende al usuario en Telegram.
"""
import os
import sys
import threading
from datetime import datetime

# Asegurar que agente_core/ esté en el path (cuando se importa desde telegram_agente.py)
_core = os.path.dirname(os.path.abspath(__file__))
if _core not in sys.path:
    sys.path.insert(0, _core)

from logger import get_logger
from agenda_tool import obtener_acciones_activas, registrar_ejecucion

logger = get_logger("agenda_scheduler")

INTERVALO_REVISION = 60       # segundos entre revisiones del scheduler
TIMEOUT_EJECUCION = 300       # 5 minutos máximo por acción


def _debe_ejecutar(accion: dict, ahora: datetime,
                   ejecutadas_este_minuto: set) -> bool:
    """
    Determina si una acción debe dispararse en este ciclo.

    Garantías:
    - Anti-spam: nunca la misma acción dos veces en el mismo minuto
    - Verifica día de semana si está configurado
    - Evalúa el timing según el tipo de acción
    """
    accion_id = accion["id"]

    # Anti-spam: ya se ejecutó en este minuto
    if accion_id in ejecutadas_este_minuto:
        return False

    # Verificar día de semana (si la acción tiene restricción)
    dias = accion.get("dias_semana")  # None = todos los días
    if dias:
        if ahora.isoweekday() not in dias:
            return False

    tipo = accion.get("tipo")
    ultima_iso = accion.get("ultima_ejecucion")
    ultima_dt = None
    if ultima_iso:
        try:
            ultima_dt = datetime.fromisoformat(ultima_iso)
        except (ValueError, TypeError):
            pass

    if tipo == "diaria":
        hora_conf = accion.get("hora", "")
        hora_ahora = ahora.strftime("%H:%M")
        if hora_ahora != hora_conf:
            return False
        # Anti-spam adicional: no ejecutar si ya se ejecutó en este mismo minuto del día
        if ultima_dt:
            misma_fecha = ultima_dt.strftime("%Y-%m-%d")
            mismo_minuto = ultima_dt.strftime("%H:%M")
            if misma_fecha == ahora.strftime("%Y-%m-%d") and mismo_minuto == hora_ahora:
                return False
        return True

    elif tipo == "recurrente_ventana":
        hora_inicio = accion.get("hora_inicio", "00:00")
        hora_fin = accion.get("hora_fin", "23:59")
        hora_actual_str = ahora.strftime("%H:%M")
        # Verificar que estamos dentro de la ventana horaria
        if not (hora_inicio <= hora_actual_str <= hora_fin):
            return False
        # Primera vez: ejecutar de inmediato si estamos en ventana
        if ultima_dt is None:
            return True
        intervalo = accion.get("intervalo_minutos", 15)
        minutos_transcurridos = (ahora - ultima_dt).total_seconds() / 60
        return minutos_transcurridos >= intervalo

    elif tipo == "recurrente":
        if ultima_dt is None:
            return True  # Primera vez: ejecutar de inmediato
        intervalo = accion.get("intervalo_minutos", 60)
        minutos_transcurridos = (ahora - ultima_dt).total_seconds() / 60
        return minutos_transcurridos >= intervalo

    return False


class AgendaScheduler(threading.Thread):
    """
    Hilo daemon que revisa la agenda y dispara acciones automáticas.

    - Es completamente independiente del agente principal
    - Cada acción se ejecuta en su propio thread con timeout
    - Los resultados se envían al usuario vía TelegramNotifier
    """

    def __init__(self, notifier, chat_id_default: int,
                 model: str, api_key: str,
                 base_url: str = None, provider: str = "openai",
                 agenda_model: str = None, agenda_api_key: str = None,
                 agenda_base_url: str = None, agenda_provider: str = None):
        super().__init__(daemon=True, name="agenda-scheduler")
        self._notifier = notifier
        self._chat_id_default = chat_id_default
        # Modelo principal (fallback si no hay modelo específico para la agenda)
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._provider = provider
        # Modelo del sub-agente (puede ser uno más rápido/barato)
        self._agenda_model = agenda_model or model
        self._agenda_api_key = agenda_api_key or api_key
        self._agenda_base_url = agenda_base_url or base_url
        self._agenda_provider = agenda_provider or provider
        if agenda_model:
            logger.info(f"Sub-agente usará modelo propio: {agenda_provider}/{agenda_model}")
        self._stop_event = threading.Event()
        # Rastrear threads activos por acción (para no lanzar duplicados)
        self._ejecutando: dict[int, threading.Thread] = {}
        self._lock_ejecutando = threading.Lock()
        # Control anti-spam por minuto
        self._minuto_actual: str = ""
        self._ejecutadas_este_minuto: set = set()

    def run(self):
        logger.info(f"AgendaScheduler iniciado (revisión cada {INTERVALO_REVISION}s).")
        # Esperar un ciclo inicial para que el agente termine de inicializarse
        self._stop_event.wait(INTERVALO_REVISION)
        while not self._stop_event.is_set():
            try:
                self._ciclo()
            except Exception as e:
                logger.error(f"Error en ciclo del scheduler: {e}", exc_info=True)
            self._stop_event.wait(INTERVALO_REVISION)
        logger.info("AgendaScheduler detenido.")

    def _ciclo(self):
        """Un ciclo de revisión de la agenda."""
        ahora = datetime.now()
        minuto_str = ahora.strftime("%Y-%m-%d %H:%M")

        # Resetear anti-spam al cambiar de minuto
        if minuto_str != self._minuto_actual:
            self._minuto_actual = minuto_str
            self._ejecutadas_este_minuto = set()

        acciones = obtener_acciones_activas()
        if not acciones:
            return

        for accion in acciones:
            accion_id = accion["id"]

            # No lanzar si ya hay un thread activo para esta acción
            with self._lock_ejecutando:
                hilo_existente = self._ejecutando.get(accion_id)
                if hilo_existente and hilo_existente.is_alive():
                    logger.debug(f"Acción #{accion_id} ya en ejecución, omitiendo.")
                    continue
                elif hilo_existente:
                    del self._ejecutando[accion_id]

            if not _debe_ejecutar(accion, ahora, self._ejecutadas_este_minuto):
                continue

            # Marcar como disparada en este minuto (anti-spam)
            self._ejecutadas_este_minuto.add(accion_id)

            hilo = threading.Thread(
                target=self._ejecutar_accion,
                args=(accion,),
                name=f"agenda-accion-{accion_id}",
                daemon=True,
            )
            with self._lock_ejecutando:
                self._ejecutando[accion_id] = hilo
            hilo.start()
            logger.info(f"Acción #{accion_id} '{accion.get('nombre', '?')}' disparada.")

    def _ejecutar_accion(self, accion: dict):
        """
        Ejecuta una acción en un thread separado.

        Crea un sub-agente temporal (instancia independiente de Agent)
        que no comparte historial con el agente principal del usuario.
        """
        accion_id = accion["id"]
        nombre = accion.get("nombre", f"Acción #{accion_id}")
        chat_id = accion.get("chat_id") or self._chat_id_default

        logger.info(f"Ejecutando acción #{accion_id}: {nombre} → chat_id={chat_id}")
        resultado = None
        exito = False

        try:
            from agent import Agent

            # Sub-agente temporal: instancia independiente con historial limpio.
            # Usa el modelo configurado para la agenda (puede ser uno más rápido).
            agente = Agent(
                model=self._agenda_model,
                api_key=self._agenda_api_key,
                base_url=self._agenda_base_url,
                provider=self._agenda_provider,
            )
            # Limpiar historial para garantizar contexto limpio
            agente.limpiar_historial()

            # Callbacks para que el sub-agente pueda enviar archivos/fotos
            def _send_file_cb(ruta: str, caption: str = "") -> bool:
                if self._notifier and chat_id:
                    return self._notifier.enviar_archivo(chat_id, ruta, caption)
                return False

            def _send_photo_url_cb(url: str, caption: str = "") -> bool:
                if self._notifier and chat_id:
                    return self._notifier.enviar_foto_url(chat_id, url, caption)
                return False

            # Contexto inyectado en el prompt para que el agente sepa que es automático
            prompt_con_contexto = (
                f"[Ejecución automática de agenda — acción: {nombre}]\n\n"
                f"{accion['prompt']}\n\n"
                "Al terminar, responde con un resumen breve de lo que hiciste.\n\n"
                "REGLA DE NOTIFICACIÓN: Si no hay novedades relevantes para el usuario "
                "(sin cambios, sin información nueva, todo igual que antes), inicia tu "
                "respuesta EXACTAMENTE con el prefijo [SILENCIOSO] — el sistema suprimirá "
                "la notificación automáticamente. Usa [SILENCIOSO] solo cuando no haya "
                "nada útil que comunicar.\n\n"
                "DETECCIÓN AUTOMÁTICA DE SEGUIMIENTOS: Si durante tu ejecución encuentras "
                "correos o información sobre envíos, transacciones bancarias, reservas o "
                "cualquier proceso con número de referencia/tracking que esté cambiando de "
                "estado, usa el skill 'seguimiento' (ejecutar_script_skill) para registrar "
                "o actualizar ese seguimiento automáticamente."
            )

            # Ejecutar el agente con timeout en un sub-thread
            resultado_container: list = [None]
            error_container: list = [None]

            def _run_agent():
                try:
                    resultado_container[0] = agente.chat(
                        prompt_con_contexto,
                        send_file_callback=_send_file_cb,
                        send_photo_url_callback=_send_photo_url_cb,
                        chat_id=chat_id,
                    )
                except Exception as e:
                    error_container[0] = e

            hilo_agente = threading.Thread(target=_run_agent, daemon=True,
                                           name=f"agenda-agent-{accion_id}")
            hilo_agente.start()
            hilo_agente.join(timeout=TIMEOUT_EJECUCION)

            if hilo_agente.is_alive():
                raise TimeoutError(
                    f"La ejecución superó el límite de {TIMEOUT_EJECUCION // 60} minutos."
                )

            if error_container[0]:
                raise error_container[0]

            resultado = resultado_container[0] or "(sin respuesta del agente)"
            exito = True

            # Detectar prefijo [SILENCIOSO]: el sub-agente indica que no hay novedades
            _PREFIJO_SILENCIOSO = "[SILENCIOSO]"
            silencioso = resultado.strip().upper().startswith(_PREFIJO_SILENCIOSO)
            if silencioso:
                # Guardar el texto sin el prefijo (para el historial)
                resultado = resultado.strip()[len(_PREFIJO_SILENCIOSO):].strip()
                logger.info(f"Acción #{accion_id} completada sin novedades (silenciosa).")
            else:
                # Enviar resultado al usuario solo si hay novedades
                if self._notifier and chat_id:
                    self._notifier.enviar(
                        chat_id,
                        f"📅 *Agenda — {nombre}*\n\n{resultado}"
                    )
                logger.info(f"Acción #{accion_id} completada y notificada.")

        except TimeoutError as e:
            resultado = str(e)
            logger.warning(f"Timeout en acción #{accion_id}: {e}")
            if self._notifier and chat_id:
                self._notifier.enviar(
                    chat_id,
                    f"📅 *Agenda — {nombre}*\n\n⏱️ Tiempo agotado: {e}"
                )

        except Exception as e:
            resultado = f"{type(e).__name__}: {e}"
            logger.error(f"Error en acción #{accion_id}: {e}", exc_info=True)

            # Auto-recuperación: modelo no disponible
            if self._intentar_recuperar_modelo(e, chat_id):
                pass  # ya notificó al usuario con el nuevo modelo
            elif self._notifier and chat_id:
                self._notifier.enviar(
                    chat_id,
                    f"📅 *Agenda — {nombre}*\n\n❌ Error al ejecutar: {e}"
                )

        finally:
            registrar_ejecucion(accion_id, resultado or "Error desconocido", exito)

    # ── Auto-recuperación de modelo ───────────────────────────────────────────

    def _intentar_recuperar_modelo(self, error: Exception, chat_id: int) -> bool:
        """
        Si el error es 503 model_not_available, selecciona el mejor modelo
        disponible usando las evaluaciones y actualiza .env + self._agenda_model.
        Retorna True si se recuperó (para suprimir el mensaje de error genérico).
        """
        import re
        error_str = str(error)

        if "model_not_available" not in error_str and "No hay workers disponibles" not in error_str:
            return False

        # Extraer lista de modelos disponibles del mensaje de error
        match = re.search(r"Modelos disponibles:\s*([^\}'\"]+)", error_str)
        if not match:
            return False

        disponibles = [m.strip() for m in match.group(1).split(",") if m.strip()]
        logger.info(f"Modelos disponibles detectados: {disponibles}")

        # Elegir el mejor según evaluaciones
        mejor = self._mejor_modelo_por_evaluacion(disponibles)
        if not mejor:
            return False

        modelo_anterior = self._agenda_model
        self._agenda_model = mejor
        self._actualizar_env("AGENDA_MODEL", mejor)

        logger.info(f"Modelo de agenda cambiado: {modelo_anterior} → {mejor}")

        if self._notifier and chat_id:
            self._notifier.enviar(
                chat_id,
                f"⚙️ *Agenda — modelo no disponible*\n\n"
                f"El modelo `{modelo_anterior}` ya no está cargado.\n"
                f"Cambiado automáticamente a: `{mejor}`\n"
                f"_(basado en evaluaciones previas)_"
            )
        return True

    def _mejor_modelo_por_evaluacion(self, disponibles: list) -> str:
        """
        Lee los archivos evaluacion_llm_lmstudio_*.md y devuelve el modelo
        disponible con mayor score. Ignora embeddings y TTS.
        """
        import glob
        import re

        # Filtrar modelos no-LLM
        candidatos = [
            m for m in disponibles
            if not any(x in m.lower() for x in ("embedding", "tts", "nomic"))
        ]
        if not candidatos:
            return disponibles[0] if disponibles else None

        # Leer scores de evaluaciones
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        archivos = glob.glob(os.path.join(root, "evaluacion_llm_lmstudio_*.md"))

        scores = {}  # modelo_eval → mejor_score
        for path in archivos:
            try:
                with open(path, encoding="utf-8") as f:
                    contenido = f.read()
                m_model = re.search(r"# Evaluaci[oó]n LLM [—-] (.+)", contenido)
                m_score = re.search(r"Score global:\*\*\s*([\d.]+)/5", contenido)
                if m_model and m_score:
                    nombre = m_model.group(1).strip()
                    score = float(m_score.group(1))
                    if nombre not in scores or scores[nombre] < score:
                        scores[nombre] = score
            except Exception:
                continue

        if not scores:
            logger.warning("Sin archivos de evaluación — usando primer candidato.")
            return candidatos[0]

        # Cruzar candidatos con scores (matching flexible)
        def _score_candidato(candidato: str) -> float:
            c_norm = candidato.lower().replace("/", "-").replace(":", "-").replace(".", "-")
            mejor = 0.0
            for eval_name, sc in scores.items():
                e_norm = eval_name.lower().replace("/", "-").replace(":", "-").replace(".", "-")
                # Coincidencia si comparten tokens significativos (>3 chars)
                c_tokens = set(t for t in c_norm.split("-") if len(t) > 3)
                e_tokens = set(t for t in e_norm.split("-") if len(t) > 3)
                if c_tokens & e_tokens:
                    mejor = max(mejor, sc)
            return mejor

        ranked = sorted(candidatos, key=_score_candidato, reverse=True)
        elegido = ranked[0]
        logger.info(
            f"Ranking modelos: "
            + ", ".join(f"{m}({_score_candidato(m):.2f})" for m in ranked)
        )
        return elegido

    def _actualizar_env(self, clave: str, valor: str):
        """Actualiza una variable en el archivo .env del proyecto."""
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(root, ".env")
        if not os.path.exists(env_path):
            logger.warning(f".env no encontrado en {env_path}")
            return
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            encontrado = False
            nuevas = []
            for line in lines:
                if line.startswith(f"{clave}="):
                    nuevas.append(f"{clave}={valor}\n")
                    encontrado = True
                else:
                    nuevas.append(line)
            if not encontrado:
                nuevas.append(f"{clave}={valor}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(nuevas)
            logger.info(f".env actualizado: {clave}={valor}")
        except Exception as e:
            logger.error(f"Error actualizando .env: {e}")

    def detener(self):
        """Graceful shutdown: señaliza el stop y espera hasta 5 segundos."""
        self._stop_event.set()
        self.join(timeout=5)
        logger.info("AgendaScheduler detenido.")
