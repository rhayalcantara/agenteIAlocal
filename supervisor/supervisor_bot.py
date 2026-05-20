"""
Supervisor Bot — monitorea agente_core y permite controlarlo via Telegram.

Requiere un bot de Telegram SEPARADO al del agente core (token distinto).

Comandos:
  /estado      — Estado actual del proceso y heartbeat
  /reiniciar   — Reinicia el agente (pide confirmación)
  /detener     — Detiene el agente (pide confirmación)
  /iniciar     — Inicia el agente si está detenido
  /logs [N]    — Últimas N líneas del log (default: 30, máx: 100)
  /modo        — Muestra o cambia el modo (auto | manual)
  /ayuda       — Lista de comandos
"""
import sys
import os
import re
import time
import atexit
import logging
import threading
import requests
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agente_core"))

from supervisor.config import (
    SUPERVISOR_BOT_TOKEN,
    SUPERVISOR_CHAT_ID,
    CHECK_INTERVAL,
    SUPERVISOR_MODE,
    MAX_RECOVERY_ATTEMPTS,
    LOG_DIR,
    SUPERVISOR_LOG_FILE,
)
from supervisor import health_checker, process_manager, decision_engine

# Importar claude-auto-resolver (nombre con guiones, no es paquete estándar)
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    "claude_auto_resolver", ROOT / "skills" / "claude-auto-resolver" / "run.py"
)
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
run_claude_prompt = _mod.run_claude_prompt

# ── Logger del supervisor ──────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
_handler_file = RotatingFileHandler(
    SUPERVISOR_LOG_FILE, maxBytes=3 * 1024 * 1024, backupCount=2, encoding="utf-8"
)
_handler_file.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%Y-%m-%d %H:%M:%S")
)
_handler_console = logging.StreamHandler()
_handler_console.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", "%H:%M:%S")
)
logger = logging.getLogger("supervisor")
logger.setLevel(logging.DEBUG)
logger.addHandler(_handler_file)
logger.addHandler(_handler_console)

# ── Estado global ──────────────────────────────────────────────────────────────
_modo: str = SUPERVISOR_MODE                      # "manual" | "auto"
_confirmaciones: dict[int, str] = {}              # chat_id → acción pendiente de confirmar
_seleccion_modelos: dict[int, list] = {}          # chat_id → lista de modelos disponibles
_intentos: int = 0                                # intentos de recuperación consecutivos

_AYUDA = (
    "*Supervisor Bot — Comandos*\n\n"
    "/estado — Estado actual del agente\n"
    "/info — LLM activo, tokens de contexto y tiempo de vida\n"
    "/reiniciar — Reinicia el agente (pide confirmación)\n"
    "/detener — Detiene el agente (pide confirmación)\n"
    "/iniciar — Inicia el agente si está detenido\n"
    "/logs \\[N\\] — Últimas N líneas de log \\(default: 30\\)\n"
    "/llm — Lista modelos del gateway y permite cambiar el LLM activo\n"
    "/modo auto|manual — Cambia el modo de supervisión\n"
    "/ayuda — Esta ayuda"
)


# ── Telegram helpers ───────────────────────────────────────────────────────────

def _api(method: str, payload: dict = None) -> dict:
    url = f"https://api.telegram.org/bot{SUPERVISOR_BOT_TOKEN}/{method}"
    try:
        r = requests.post(url, json=payload or {}, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logger.error(f"Telegram API error [{method}]: {e}")
        return {}


def enviar(texto: str, chat_id: int | None = None) -> int | None:
    """Envía un mensaje de texto. Retorna el message_id o None."""
    cid = chat_id or SUPERVISOR_CHAT_ID
    # Telegram limita a 4096 chars — si hay logs largos, truncar por el inicio
    if len(texto) > 4000:
        texto = "...(truncado)\n" + texto[-3980:]
    resp = _api("sendMessage", {
        "chat_id": cid,
        "text": texto,
        "parse_mode": "Markdown",
    })
    return resp.get("result", {}).get("message_id")


def get_updates(offset: int = 0) -> list:
    resp = _api("getUpdates", {
        "offset": offset,
        "timeout": 5,
        "allowed_updates": ["message"],
    })
    return resp.get("result", [])


# ── Respuestas de comandos ─────────────────────────────────────────────────────

def _texto_estado() -> str:
    proc = process_manager.obtener_proceso()
    salud = health_checker.verificar(proc)
    corriendo = "En ejecución" if process_manager.esta_corriendo() else "Detenido"
    return (
        f"*Estado del Agente Core*\n"
        f"Proceso: {corriendo}\n"
        f"Salud: `{salud['estado']}`\n"
        f"Detalle: {salud['detalle']}\n"
        f"Modo supervisor: `{_modo}`\n"
        f"Intentos de recuperación: {_intentos}/{MAX_RECOVERY_ATTEMPTS}"
    )


def _texto_logs(n: int = 30) -> str:
    logs = process_manager.ultimos_logs(n)
    # Escapar backticks dentro del bloque de código
    return f"*Últimas {n} líneas del log:*\n```\n{logs}\n```"


# ── Monitor de salud (hilo background) ────────────────────────────────────────

def _monitor_loop():
    global _intentos

    # Esperar a que el agente tenga tiempo de arrancar antes del primer check
    logger.info(f"Monitor iniciado. Primer check en {CHECK_INTERVAL}s.")
    time.sleep(CHECK_INTERVAL)

    while True:
        try:
            proc  = process_manager.obtener_proceso()
            salud = health_checker.verificar(proc)

            if salud["estado"] == "ok":
                if _intentos > 0:
                    logger.info("Agente recuperado. Reseteando contador de intentos.")
                _intentos = 0

            elif salud["estado"] in ("frozen", "crashed"):
                logger.warning(f"Problema detectado: {salud['estado']} — {salud['detalle']}")

                logs      = process_manager.ultimos_logs(20)
                situacion = {
                    "estado": salud["estado"],
                    "detalle": salud["detalle"],
                    "intentos": _intentos,
                    "logs": logs,
                }

                # ── Diagnóstico con claude-auto-resolver ──────────────────
                diagnostico = ""
                try:
                    prompt_diag = (
                        f"El agente de IA tuvo un problema: {salud['estado']}.\n"
                        f"Detalle: {salud['detalle']}\n"
                        f"Últimos logs:\n{logs}\n\n"
                        f"Analiza la causa raíz del error y sugiere cómo resolverlo."
                    )
                    diagnostico = run_claude_prompt(prompt_diag, timeout=30)
                    logger.info(f"Diagnóstico auto-resolver: {diagnostico[:200]}")
                except Exception as e:
                    logger.warning(f"No se pudo obtener diagnóstico: {e}")

                if _modo == "auto" and _intentos < MAX_RECOVERY_ATTEMPTS:
                    # ── Modo auto: el LLM decide ───────────────────────────
                    decision = decision_engine.decidir(situacion)
                    accion   = decision.get("accion", "alert_user")
                    razon    = decision.get("razon", "")
                    logger.info(f"Decisión LLM: {accion} — {razon}")

                    if accion == "auto_restart":
                        msg_diag = f"\n\n*Diagnóstico:*\n{diagnostico}" if diagnostico else ""
                        enviar(
                            f"*Supervisor:* Detecté `{salud['estado']}`.\n"
                            f"Reiniciando automáticamente...\n\n_{razon}_"
                            f"{msg_diag}"
                        )
                        ok, msg = process_manager.reiniciar()
                        _intentos += 1
                        logger.info(f"Reinicio automático: {msg}")
                        enviar(f"Resultado: {msg}")

                    elif accion == "wait":
                        logger.info("Decisión: esperar más tiempo antes de actuar.")

                    else:  # alert_user | alert_and_restart
                        msg_diag = f"\n\n*Diagnóstico:*\n{diagnostico}" if diagnostico else ""
                        enviar(
                            f"*ALERTA del Supervisor*\n"
                            f"Problema: `{salud['estado']}`\n"
                            f"{salud['detalle']}\n\n"
                            f"Análisis: _{razon}_"
                            f"{msg_diag}\n\n"
                            f"Usa /reiniciar para actuar o /logs para más detalles."
                        )
                        if accion == "alert_and_restart":
                            ok, msg = process_manager.reiniciar()
                            _intentos += 1
                            logger.info(f"Reinicio + alerta: {msg}")
                            enviar(f"Reinicio automático iniciado: {msg}")

                else:
                    # ── Modo manual (o intentos agotados): siempre consultar ──
                    razon_extra = ""
                    if _intentos >= MAX_RECOVERY_ATTEMPTS:
                        razon_extra = f"\n*Intentos de auto-recuperación agotados* ({_intentos}/{MAX_RECOVERY_ATTEMPTS})."
                    msg_diag = f"\n\n*Diagnóstico:*\n{diagnostico}" if diagnostico else ""
                    enviar(
                        f"*ALERTA del Supervisor*\n"
                        f"Problema: `{salud['estado']}`\n"
                        f"{salud['detalle']}"
                        f"{razon_extra}"
                        f"{msg_diag}\n\n"
                        f"Usa /reiniciar, /detener o /logs para actuar."
                    )

            # "no_iniciado" → silencioso (proceso aún arrancando)

        except Exception as e:
            logger.error(f"Error inesperado en monitor loop: {e}", exc_info=True)

        time.sleep(CHECK_INTERVAL)


# ── Info del agente ───────────────────────────────────────────────────────────

def _texto_info() -> str:
    from dotenv import dotenv_values
    import json
    from datetime import datetime

    lineas = ["*Info del Agente*\n"]

    # ── LLM activo ──────────────────────────────────────────────────────────
    env = dotenv_values(ROOT / ".env")
    provider = env.get("PROVIDER_DEFAULT", "?")
    model_key = {
        "lmstudio":   "LMSTUDIO_MODEL",
        "openrouter": "OPENROUTER_MODEL",
        "openai":     "OPENAI_MODEL",
        "claude":     "CLAUDE_MODEL",
        "gemini":     "GEMINI_MODEL",
    }.get(provider, f"{provider.upper()}_MODEL")
    model = env.get(model_key, "?")
    base_url = env.get("LMSTUDIO_BASE_URL") or env.get("GATEWAY_BASE_URL") or "?"
    lineas.append(f"🤖 *LLM activo*")
    lineas.append(f"   Provider: `{provider}`")
    lineas.append(f"   Modelo: `{model}`")
    lineas.append(f"   Endpoint: `{base_url}`")

    # ── Inicio del agente ────────────────────────────────────────────────────
    inicio = process_manager.obtener_inicio()
    ahora  = datetime.now()
    lineas.append(f"\n⏱ *Tiempo de vida del agente*")
    if inicio:
        delta   = ahora - inicio
        dias    = delta.days
        horas   = delta.seconds // 3600
        minutos = (delta.seconds % 3600) // 60
        duracion = (f"{dias}d " if dias else "") + f"{horas}h {minutos}m"
        lineas.append(f"   Iniciado: {inicio.strftime('%Y-%m-%d %H:%M:%S')}")
        lineas.append(f"   Uptime: {duracion}")
        if dias >= 1:
            lineas.append(f"   ⚠️ El agente lleva {dias} día(s) sin reiniciar — el contexto puede ser muy antiguo")
    else:
        lineas.append("   No disponible (supervisor recién iniciado)")

    # ── Contexto messages.json ───────────────────────────────────────────────
    messages_path = ROOT / "agente_core" / "logs" / "messages.json"
    lineas.append(f"\n💬 *Contexto (messages.json)*")
    if messages_path.exists():
        try:
            contenido = messages_path.read_text(encoding="utf-8", errors="ignore")
            mensajes  = json.loads(contenido)
            n_mensajes = len(mensajes)
            tokens_aprox = len(contenido) // 4

            # Fecha del primer mensaje de usuario
            primer_usuario = next(
                (m for m in mensajes if isinstance(m, dict) and m.get("role") == "user"),
                None
            )
            lineas.append(f"   Mensajes en historial: {n_mensajes}")
            lineas.append(f"   Tokens aprox: ~{tokens_aprox:,}")

            # Detectar si el contexto es viejo comparando con hoy
            stat_mtime = messages_path.stat().st_mtime
            fecha_mod  = datetime.fromtimestamp(stat_mtime)
            dias_viejo = (ahora - fecha_mod).days
            lineas.append(f"   Última modificación: {fecha_mod.strftime('%Y-%m-%d %H:%M')}")
            if dias_viejo >= 1:
                lineas.append(f"   ⚠️ El contexto tiene {dias_viejo} día(s) de antigüedad — considera usar /limpiar en el agente")
        except Exception as e:
            lineas.append(f"   Error leyendo messages.json: {e}")
    else:
        lineas.append("   Sin historial (messages.json no existe)")

    return "\n".join(lineas)


# ── Gateway / LLM ─────────────────────────────────────────────────────────────

def _consultar_modelos_gateway() -> list[dict]:
    """Consulta el endpoint /models del gateway y retorna lista de modelos."""
    env_path = ROOT / ".env"
    # Recargar .env para leer valores actualizados
    from dotenv import dotenv_values
    env = dotenv_values(env_path)

    urls_a_probar = []
    for key in ("GATEWAY_BASE_URL", "LMSTUDIO_BASE_URL", "OPENROUTER_BASE_URL"):
        url = env.get(key, "").strip()
        if url and url not in [u for u, _ in urls_a_probar]:
            # Determinar provider asociado
            prv = "gateway" if "GATEWAY" in key else ("lmstudio" if "LMSTUDIO" in key else "openrouter")
            urls_a_probar.append((url.rstrip("/"), prv))

    modelos = []
    for base_url, prv in urls_a_probar:
        api_key = env.get("GATEWAY_API_KEY") or env.get("LMSTUDIO_API_KEY") or ""
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            resp = requests.get(f"{base_url}/models", headers=headers, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                for m in data.get("data", []):
                    model_id = m.get("id", "")
                    if model_id:
                        modelos.append({
                            "id": model_id,
                            "base_url": base_url,
                            "provider": prv,
                        })
                if modelos:
                    break  # si el primero respondió bien, no seguir
        except Exception as e:
            logger.warning(f"No se pudo consultar {base_url}/models: {e}")

    return modelos


def _actualizar_env(cambios: dict):
    """Actualiza variables en el .env del proyecto."""
    env_path = ROOT / ".env"
    try:
        contenido = env_path.read_text(encoding="utf-8")
        lineas = contenido.splitlines()
        actualizadas = set()
        nuevas = []
        for linea in lineas:
            m = re.match(r"^([A-Z_][A-Z0-9_]*)\s*=", linea)
            if m and m.group(1) in cambios:
                key = m.group(1)
                nuevas.append(f"{key}={cambios[key]}")
                actualizadas.add(key)
            else:
                nuevas.append(linea)
        # Agregar las que no existían
        for key, val in cambios.items():
            if key not in actualizadas:
                nuevas.append(f"{key}={val}")
        env_path.write_text("\n".join(nuevas) + "\n", encoding="utf-8")
        logger.info(f"Variables .env actualizadas: {list(cambios.keys())}")
        return True
    except Exception as e:
        logger.error(f"Error actualizando .env: {e}")
        return False


def _texto_llm_lista(modelos: list[dict]) -> str:
    if not modelos:
        return "No se encontraron modelos activos en el gateway."
    lineas = ["*Modelos disponibles en el gateway:*\n"]
    for i, m in enumerate(modelos, 1):
        lineas.append(f"  {i}\\. `{m['id']}`")
    lineas.append("\nResponde con el *número* del modelo que quieres usar.")
    return "\n".join(lineas)


# ── Manejador de comandos Telegram ────────────────────────────────────────────

def _manejar(texto: str, chat_id: int):
    global _modo, _intentos

    # ── Selección de modelo LLM pendiente ─────────────────────────────────────
    if chat_id in _seleccion_modelos:
        modelos = _seleccion_modelos.get(chat_id, [])
        if texto.strip().lower() in ("cancelar", "cancel", "no"):
            _seleccion_modelos.pop(chat_id, None)
            enviar("Cambio de LLM cancelado.", chat_id)
            return
        if texto.strip().isdigit():
            idx = int(texto.strip()) - 1
            if 0 <= idx < len(modelos):
                modelo = modelos[idx]
                _seleccion_modelos.pop(chat_id, None)
                enviar(f"Cambiando al modelo `{modelo['id']}`...", chat_id)

                # Determinar las variables a actualizar en .env
                prv = modelo["provider"]
                env_key_model = {
                    "lmstudio": "LMSTUDIO_MODEL",
                    "gateway": "LMSTUDIO_MODEL",   # lmstudio es el provider que apunta al gateway
                    "openrouter": "OPENROUTER_MODEL",
                }.get(prv, "LMSTUDIO_MODEL")

                cambios = {
                    "PROVIDER_DEFAULT": "lmstudio",
                    env_key_model: modelo["id"],
                }
                ok_env = _actualizar_env(cambios)
                if not ok_env:
                    enviar("❌ No se pudo actualizar el .env.", chat_id)
                    return

                ok, msg = process_manager.reiniciar()
                _intentos = 0
                logger.info(f"LLM cambiado a {modelo['id']} — {msg}")
                enviar(f"✅ Modelo cambiado a `{modelo['id']}`\n{msg}", chat_id)
            else:
                enviar(f"Número inválido. Elige entre 1 y {len(modelos)}, o escribe *cancelar*.", chat_id)
            return

    # ── Confirmación de acción destructiva pendiente ───────────────────────────
    if chat_id in _confirmaciones:
        accion = _confirmaciones.pop(chat_id)
        if texto.strip().lower() in ("si", "sí", "yes", "s", "ok"):
            if accion == "reiniciar":
                ok, msg = process_manager.reiniciar()
                _intentos = 0  # reset manual
                logger.info(f"Reinicio manual: {msg}")
                enviar(msg, chat_id)
            elif accion == "detener":
                ok, msg = process_manager.detener()
                logger.info(f"Parada manual: {msg}")
                enviar(msg, chat_id)
        else:
            enviar("Acción cancelada.", chat_id)
        return

    partes = texto.strip().split()
    cmd    = partes[0].lower() if partes else ""

    if cmd == "/estado":
        enviar(_texto_estado(), chat_id)

    elif cmd == "/reiniciar":
        _confirmaciones[chat_id] = "reiniciar"
        enviar(
            "¿Confirmas reiniciar el agente core?\n"
            "Responde *si* para confirmar o cualquier otra cosa para cancelar.",
            chat_id,
        )

    elif cmd == "/detener":
        _confirmaciones[chat_id] = "detener"
        enviar(
            "¿Confirmas detener el agente core?\n"
            "Responde *si* para confirmar o cualquier otra cosa para cancelar.",
            chat_id,
        )

    elif cmd == "/iniciar":
        ok, msg = process_manager.iniciar()
        logger.info(f"Inicio manual: {msg}")
        enviar(msg, chat_id)

    elif cmd == "/logs":
        n = 30
        if len(partes) > 1 and partes[1].isdigit():
            n = min(int(partes[1]), 100)
        enviar(_texto_logs(n), chat_id)

    elif cmd == "/info":
        enviar(_texto_info(), chat_id)

    elif cmd == "/llm":
        enviar("🔍 Consultando modelos en el gateway...", chat_id)
        modelos = _consultar_modelos_gateway()
        if not modelos:
            enviar("No se encontraron modelos activos en el gateway. Verifica que esté encendido.", chat_id)
        else:
            _seleccion_modelos[chat_id] = modelos
            enviar(_texto_llm_lista(modelos), chat_id)

    elif cmd == "/modo":
        arg = partes[1].lower() if len(partes) > 1 else ""
        if arg in ("auto", "manual"):
            _modo = arg
            logger.info(f"Modo cambiado a {_modo}.")
            enviar(f"Modo cambiado a *{_modo}*.", chat_id)
        else:
            enviar(
                f"Modo actual: *{_modo}*.\n"
                f"Usa `/modo auto` o `/modo manual` para cambiarlo.",
                chat_id,
            )

    elif cmd in ("/ayuda", "/start", "/help"):
        enviar(_AYUDA, chat_id)

    else:
        enviar(f"Comando no reconocido: `{cmd}`. Usa /ayuda.", chat_id)


# ── Cierre limpio ─────────────────────────────────────────────────────────────

def _cerrar_agente():
    """Registrado en atexit — garantiza que el agente se cierra con el supervisor."""
    if process_manager.esta_corriendo():
        logger.info("Cerrando agente core por cierre del supervisor...")
        ok, msg = process_manager.detener()
        logger.info(msg)
        try:
            enviar("Supervisor detenido. Agente core cerrado.")
        except Exception:
            pass
        print(f"[Supervisor] {msg}")


# ── Main ───────────────────────────────────────────────────────────────────────

_job_manager_proc = None


def _iniciar_job_manager():
    """Lanza job_manager como subprocess detached si no está ya escuchando.
    Lo registra en atexit para apagarlo limpiamente."""
    global _job_manager_proc
    import subprocess as _sp
    port = int(os.environ.get("JOB_MANAGER_PORT", "8090"))
    # Si ya hay alguien escuchando, no spawneamos otro
    try:
        r = requests.get(f"http://127.0.0.1:{port}/stats", timeout=1)
        if r.status_code == 200:
            logger.info(f"job_manager ya estaba activo en :{port}")
            return
    except Exception:
        pass

    log_file = LOG_DIR / "job_manager.log"
    try:
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        kwargs = dict(
            cwd=str(ROOT),
            stdout=open(log_file, "a", encoding="utf-8"),
            stderr=_sp.STDOUT,
            stdin=_sp.DEVNULL,
            env=env,
        )
        if sys.platform == "win32":
            kwargs["creationflags"] = _sp.CREATE_NEW_PROCESS_GROUP
        _job_manager_proc = _sp.Popen(
            [sys.executable, "-m", "job_manager"], **kwargs,
        )
        logger.info(f"job_manager iniciado (PID {_job_manager_proc.pid}) en :{port}")
    except Exception as e:
        logger.error(f"No se pudo iniciar job_manager: {e}")


def _cerrar_job_manager():
    global _job_manager_proc
    if _job_manager_proc and _job_manager_proc.poll() is None:
        try:
            _job_manager_proc.terminate()
            _job_manager_proc.wait(timeout=5)
        except Exception:
            try:
                _job_manager_proc.kill()
            except Exception:
                pass


def main():
    if not SUPERVISOR_BOT_TOKEN:
        print("ERROR: SUPERVISOR_BOT_TOKEN no está definido en .env")
        sys.exit(1)
    if not SUPERVISOR_CHAT_ID:
        print("ERROR: SUPERVISOR_CHAT_ID no está definido en .env")
        sys.exit(1)

    logger.info(f"Supervisor arrancando. modo={_modo} check_interval={CHECK_INTERVAL}s")

    # Asegurar que el agente y job_manager se cierren cuando el supervisor termine
    atexit.register(_cerrar_agente)
    atexit.register(_cerrar_job_manager)

    # Lanzar job_manager primero (es independiente del agente)
    _iniciar_job_manager()

    # Lanzar agente core como subprocess
    ok, msg_inicio = process_manager.iniciar()
    logger.info(f"Inicio de agente: {msg_inicio}")

    enviar(
        f"*Supervisor Bot iniciado*\n"
        f"Modo: *{_modo}*\n"
        f"Check de salud cada: {CHECK_INTERVAL}s\n"
        f"Timeout heartbeat: {health_checker.HEARTBEAT_TIMEOUT}s\n\n"
        f"Agente: {msg_inicio}"
    )

    # Lanzar monitor en hilo daemon
    hilo_monitor = threading.Thread(target=_monitor_loop, daemon=True, name="monitor")
    hilo_monitor.start()

    print(f"[Supervisor] Escuchando comandos. Modo={_modo} | /ayuda para ver comandos.")

    offset = 0
    try:
        while True:
            updates = get_updates(offset)
            for upd in updates:
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                texto   = msg.get("text", "").strip()
                if not texto:
                    continue
                # Solo aceptar comandos del chat autorizado
                if chat_id != SUPERVISOR_CHAT_ID:
                    logger.warning(f"Mensaje de chat no autorizado ignorado: {chat_id}")
                    continue
                logger.info(f"Comando: {texto[:80]}")
                _manejar(texto, chat_id)
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nDeteniendo supervisor y agente...")
        # atexit se encarga de llamar _cerrar_agente()


if __name__ == "__main__":
    main()
