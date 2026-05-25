"""
Agent — Agente IA con herramientas, memoria, skills y wiki.

Mejoras respecto al código base:
- Ejecuta TODOS los tool calls de una respuesta (no solo el primero)
- Filtro de comandos peligrosos en execute_bash/execute_command
- Soporte de progress_callback para notificaciones externas (Telegram)
- Wiki persistente integrado
- Perfiles de herramientas por proveedor
"""
import os
import sys
import json
import re
import traceback
import time
import threading
from datetime import datetime

try:
    import tiktoken
    _TIKTOKEN_OK = True
except ImportError:
    _TIKTOKEN_OK = False

from openai import OpenAI
from tools import Tool
from memoria import Memoria
from skill_loader import SkillLoader
from wiki_manager import WikiManager
from web_scraper import scrape_url
from browser_tool import (browser_navegar, browser_screenshot, browser_click,
                           browser_escribir, browser_obtener_texto, browser_ejecutar_js)
from logger import get_logger

logger = get_logger("agent")
iatools = Tool()

_orchestrator = None


def set_orchestrator(orch):
    global _orchestrator
    _orchestrator = orch


class Agent:
    MAX_MENSAJES = 16        # compacta al llegar a 16 mensajes (~4 turnos con tool calls)
    MENSAJES_CONSERVAR = 6   # conserva solo los 6 más recientes tras compactar
    MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "80000"))  # umbral de tokens para autocompactar

    TOOL_PROFILES = {
        "full": None,
        "local": [
            "list_files_in_dir", "read_file", "edit_file",
            "execute_bash", "execute_long", "job_status", "job_list", "job_cancel",
            "qa_ask", "qa_check",
            "guardar_memoria", "buscar_memoria",
            "buscar_en_internet", "listar_skills", "activar_skill", "crear_skill",
            "leer_wiki", "buscar_wiki",
            "enviar_archivo_telegram", "lista_compras", "distribucion_casa",
            "ubicaciones", "recetas", "gastos", "mantenimiento",
            "contactos_servicios", "documentos", "gmail", "agenda", "presencia", "google_tv",
        ],
        "none": [],
    }

    PROVIDER_PROFILES = {
        "openrouter": "full",
        "openai": "full",
        "claude": "full",
        "gemini": "full",
        "lmstudio": "local",
    }

    def __init__(self, model: str, api_key: str,
                 base_url: str = None, provider: str = "openai",
                 tool_profile: str = None, memoria_path: str = None):
        self._model = model
        self._provider = provider

        # Crear cliente OpenAI-compat
        kwargs = {"api_key": api_key or "no-key"}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

        # Proveedores locales solo soportan /v1/chat/completions.
        # El adaptador hace que ese endpoint se vea como /v1/responses
        # para que el resto del agente no necesite cambiar nada.
        _API_MODE_POR_PROVEEDOR = {
            "lmstudio": "chat",
            "gateway":  "chat",
            "openrouter": "responses",
            "openai":     "responses",
            "claude":     "responses",
            "gemini":     "responses",
        }
        api_mode = (os.getenv("AGENT_API_MODE")
                    or _API_MODE_POR_PROVEEDOR.get(provider, "responses"))
        if api_mode == "chat":
            from responses_adapter import ResponsesAdapter
            self._client = ResponsesAdapter(self._client)
            logger.info(f"Modo API: chat/completions (proveedor={provider})")

        # Determinar perfil de herramientas
        if tool_profile is None:
            tool_profile = self.PROVIDER_PROFILES.get(provider, "full")

        self._tool_profile = tool_profile
        self._tools_enabled = tool_profile != "none"
        self._tool_fail_count = 0
        self.setup_tools(tool_profile)

        # Tool Router: filtra herramientas por mensaje para reducir tokens
        from tool_router import ToolRouter
        _use_router = os.getenv("TOOL_ROUTER_ENABLED", "true").lower() == "true"
        _router_llm = os.getenv("TOOL_ROUTER_LLM", "false").lower() == "true"
        _router_model = os.getenv("TOOL_ROUTER_MODEL", "lfm2:latest")
        _router_url = os.getenv("TOOL_ROUTER_URL", base_url)
        _router_key = os.getenv("TOOL_ROUTER_KEY", api_key)
        self._tool_router = ToolRouter(
            model=_router_model,
            use_llm=_router_llm,
            base_url=_router_url,
            api_key=_router_key,
        ) if _use_router else None

        self.memoria = Memoria(ruta=memoria_path) if memoria_path else Memoria()

        try:
            self.wiki = WikiManager()
            stats = self.wiki.estadisticas()
            print(f"📖 Wiki listo: {stats['total_paginas']} páginas")
        except Exception as e:
            logger.warning(f"Wiki no disponible: {e}")
            self.wiki = None

        try:
            self.skill_loader = SkillLoader()
            n = len(self.skill_loader.skills)
            if n:
                print(f"🧩 Skills: {n} ({', '.join(self.skill_loader.skills.keys())})")
        except Exception as e:
            logger.warning(f"SkillLoader no disponible: {e}")
            self.skill_loader = type("_", (), {"skills": {}, "listar": lambda s: [],
                                               "obtener_cuerpo": lambda s, n: None,
                                               "obtener_skill": lambda s, n: None,
                                               "ejecutar_script": lambda s, *a: "No disponible",
                                               "generar_resumen_para_prompt": lambda s: ""})()

        self._ultima_ejecucion: dict = {}
        self._system_message_base = ""
        self._compaction_thread: "threading.Thread | None" = None
        system_content = "Eres un asistente útil que habla español y eres muy conciso."

        agent_md = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent.md")
        agent_md = os.path.normpath(agent_md)
        if os.path.exists(agent_md):
            try:
                with open(agent_md, "r", encoding="utf-8") as f:
                    system_content = f.read()
                print(f"✅ agent.md cargado")
            except Exception as e:
                print(f"⚠️ No se pudo leer agent.md: {e}")

        self._system_message_base = system_content
        self._actualizar_system_prompt()
        self._cargar_historial()

    # ── System prompt ─────────────────────────────────────────────────────────

    def _actualizar_system_prompt(self):
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"Fecha y hora: {fecha}\n\n{self._system_message_base}"
        ctx = self.memoria.obtener_contexto()
        if ctx:
            content += "\n\n" + ctx
        if self.skill_loader.skills:
            content += "\n\n" + self.skill_loader.generar_resumen_para_prompt()

        if hasattr(self, "messages") and self.messages:
            self.messages[0] = {"role": "system", "content": content}
        else:
            self.messages = [{"role": "system", "content": content}]

    # ── Debug messages JSON ───────────────────────────────────────────────────

    def _messages_debug_path(self):
        logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
        os.makedirs(logs_dir, exist_ok=True)
        return os.path.join(logs_dir, "messages.json")

    def _save_messages_debug(self):
        try:
            with open(self._messages_debug_path(), "w", encoding="utf-8") as f:
                json.dump(self.messages, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.warning(f"No se pudo guardar messages.json: {e}")

    def _rename_messages_debug(self, sufijo: str):
        src = self._messages_debug_path()
        if not os.path.exists(src):
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        logs_dir = os.path.dirname(src)
        dst = os.path.join(logs_dir, f"messages_{sufijo}_{ts}.json")
        try:
            os.rename(src, dst)
        except Exception as e:
            logger.warning(f"No se pudo renombrar messages.json: {e}")

    def _cargar_historial(self):
        """Carga messages.json al iniciar si existe, reemplazando el system prompt."""
        path = self._messages_debug_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                mensajes = json.load(f)
            if not isinstance(mensajes, list) or len(mensajes) < 2:
                return
            # Conservar todo menos el system prompt (se regeneró arriba)
            self.messages = [self.messages[0]] + mensajes[1:]
            print(f"📂 Historial restaurado: {len(self.messages) - 1} mensajes previos")
        except Exception as e:
            logger.warning(f"No se pudo cargar historial: {e}")

    def _contar_tokens(self) -> int:
        """Cuenta los tokens del array messages usando tiktoken.
        Si tiktoken no está disponible, estima por caracteres (÷4)."""
        texto = json.dumps(self.messages, ensure_ascii=False, default=str)
        if _TIKTOKEN_OK:
            try:
                enc = tiktoken.get_encoding("cl100k_base")
                return len(enc.encode(texto))
            except Exception as e:
                logger.warning(f"tiktoken error: {e} — usando estimación por chars")
        return len(texto) // 4

    # ── Compactación ──────────────────────────────────────────────────────────

    def compactar_historial(self, forzar: bool = False):
        tokens = self._contar_tokens()
        supera_tokens = tokens >= self.MAX_TOKENS
        supera_mensajes = len(self.messages) > self.MAX_MENSAJES
        if not forzar and not supera_tokens and not supera_mensajes:
            return False
        motivo = f"{tokens} tokens" if supera_tokens else f"{len(self.messages)} mensajes"
        print(f"📦 Compactando historial ({motivo})...")
        n_antes = len(self.messages)
        self._rename_messages_debug(f"compactado_{n_antes}msgs_{tokens}tk")
        system_msg = self.messages[0]
        antiguos = self.messages[1:-self.MENSAJES_CONSERVAR]
        recientes = self.messages[-self.MENSAJES_CONSERVAR:]
        textos = []
        for msg in antiguos:
            if isinstance(msg, dict):
                role = msg.get("role")
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = " ".join(p.get("text", "") for p in content if isinstance(p, dict))
                if role == "user":
                    textos.append(f"Usuario: {str(content)[:150]}")
                elif role == "assistant":
                    textos.append(f"Asistente: {str(content)[:150]}")
        if textos:
            try:
                resp = self._client.responses.create(
                    model=self._model,
                    input=[{"role": "user", "content":
                            "Resume en 1-2 oraciones muy breves:\n" + "\n".join(textos[:10])}]
                )
                for out in resp.output:
                    if out.type == "message":
                        resumen = "\n".join(p.text for p in out.content)
                        self.memoria.agregar_resumen(resumen)
                        break
            except Exception as e:
                logger.warning(f"Error generando resumen: {e}")
        recientes = self._descartar_outputs_huerfanos(recientes)
        self.messages = [system_msg] + recientes
        self._actualizar_system_prompt()
        self._save_messages_debug()
        print(f"✅ Historial compactado: {len(self.messages)} mensajes")
        return True

    def _descartar_outputs_huerfanos(self, mensajes: list) -> list:
        """Elimina function_call_output cuyo call_id no tenga una function_call
        previa en la misma ventana. Tras compactar, un slice puede empezar con
        el output de una llamada cuyo function_call quedó fuera; el LLM lo
        interpreta como contexto huérfano y suele responder con plantillas de la
        última ejecución (visible cuando el agente respondía con [SILENCIOSO]
        a un saludo).
        """
        call_ids_validos: set = set()
        filtrados: list = []
        for msg in mensajes:
            if not isinstance(msg, dict):
                filtrados.append(msg)
                continue
            tipo = msg.get("type")
            if tipo == "function_call":
                cid = msg.get("call_id")
                if cid:
                    call_ids_validos.add(cid)
                filtrados.append(msg)
            elif tipo == "function_call_output":
                cid = msg.get("call_id")
                if cid and cid in call_ids_validos:
                    filtrados.append(msg)
                else:
                    logger.info(
                        f"compactar: descartado function_call_output huérfano "
                        f"(call_id={cid})"
                    )
            else:
                filtrados.append(msg)
        return filtrados

    # ── Setup de herramientas ─────────────────────────────────────────────────

    def setup_tools(self, perfil: str = "full"):
        self._tool_profile = perfil
        if perfil == "none":
            self.tools = []
            return

        self.tools = [
            {"type": "function", "name": "list_files_in_dir",
             "description": "Lista archivos en un directorio",
             "parameters": {"type": "object", "properties": {
                 "directory": {"type": "string", "description": "Directorio (por defecto '.')"}
             }, "required": []}},
            {"type": "function", "name": "read_file",
             "description": "Lee el contenido de un archivo",
             "parameters": {"type": "object", "properties": {
                 "path": {"type": "string", "description": "Ruta del archivo"},
                 "encodings": {"type": "string", "description": "Encoding (default utf-8)"},
             }, "required": ["path"]}},
            {"type": "function", "name": "edit_file",
             "description": "Crea o edita un archivo. Si prev_text está vacío, crea el archivo.",
             "parameters": {"type": "object", "properties": {
                 "path": {"type": "string"}, "new_text": {"type": "string"},
                 "prev_text": {"type": "string", "description": "Texto a reemplazar (vacío = archivo nuevo)"},
             }, "required": ["path", "new_text"]}},
            {"type": "function", "name": "execute_bash",
             "description": (
                 "Ejecuta un comando en la terminal persistente. Para tareas rápidas (<60s): "
                 "ls, git status, cat, cd, grep, ejecutar scripts cortos, etc. "
                 "Default timeout 180s (configurable). Tiene filtro de comandos peligrosos.\n"
                 "Tips:\n"
                 "• Argumentos con espacios → comillas dobles: node script.js \"NOMBRE\" 5.\n"
                 "• Para correr en otro dir sin cambiar el cwd persistente, usa el parámetro `cwd`.\n"
                 "• El terminal mantiene cwd y env vars entre llamadas (es persistente).\n"
                 "NO usar para: descargas (yt-dlp, wget largo), conversiones (ffmpeg), "
                 "transcripciones (whisper), doblaje, scripts python pesados — esos van con execute_long."
             ),
             "parameters": {"type": "object", "properties": {
                 "command": {"type": "string", "description": "Comando shell a ejecutar."},
                 "timeout": {"type": "number", "description": "Segundos antes de Error: Timeout. Default 180."},
                 "cwd": {"type": "string", "description": "Directorio donde correr el comando (no afecta el cwd persistente). Opcional."},
             }, "required": ["command"]}},
            {"type": "function", "name": "execute_long",
             "description": (
                 "Encola un proceso largo en el job_manager (corre en background, no bloquea el agente). "
                 "Úsalo para: descargas, transcripciones, conversión de video/audio, doblaje, "
                 "scripts Python que tarden más de 30 segundos. Retorna un job_id que puedes consultar "
                 "luego con job_status. Si pasas 'steps', se ejecuta como pipeline secuencial respetando depends_on."
             ),
             "parameters": {"type": "object", "properties": {
                 "name": {"type": "string", "description": "Nombre legible (e.g. 'video-doblaje-abril')"},
                 "command": {"type": "string", "description": "Comando shell (omitir si usas steps)"},
                 "steps": {"type": "array", "description": "Lista de pasos para pipeline; cada paso {id, command, depends_on?: [step_ids]}",
                           "items": {"type": "object"}},
                 "cwd": {"type": "string", "description": "Directorio de trabajo (default: root del proyecto)"},
             }, "required": ["name"]}},
            {"type": "function", "name": "job_status",
             "description": "Consulta el estado de un job encolado (queued/running/done/failed/cancelled). Incluye últimas líneas de output si pides incluir_output=true.",
             "parameters": {"type": "object", "properties": {
                 "job_id": {"type": "string"},
                 "incluir_output": {"type": "boolean", "description": "Si true, incluye últimas N líneas de stdout/stderr"},
                 "lineas": {"type": "number", "description": "Cuántas líneas de output (default 30)"},
             }, "required": ["job_id"]}},
            {"type": "function", "name": "job_list",
             "description": "Lista jobs recientes en el job_manager. Filtrable por estado.",
             "parameters": {"type": "object", "properties": {
                 "estado": {"type": "string", "enum": ["queued", "running", "done", "failed", "cancelled"]},
                 "limite": {"type": "number"},
             }, "required": []}},
            {"type": "function", "name": "job_cancel",
             "description": "Cancela un job en curso (manda SIGTERM, espera 5s, luego SIGKILL).",
             "parameters": {"type": "object", "properties": {
                 "job_id": {"type": "string"},
             }, "required": ["job_id"]}},
            {"type": "function", "name": "qa_ask",
             "description": (
                 "Pide al usuario una o varias preguntas mediante el form web en http://localhost:8090/qa. "
                 "Úsalo cuando necesites una respuesta concreta del usuario (preferencias, datos, decisión) "
                 "y la conversación en chat no es el canal natural. Las preguntas quedan persistentes hasta "
                 "que el usuario las responda; tú las recoges luego con qa_check. "
                 "Retorna {ok, id} con el id del set para correlacionar."
             ),
             "parameters": {"type": "object", "properties": {
                 "questions": {
                     "type": "array",
                     "items": {
                         "type": "object",
                         "properties": {
                             "text": {"type": "string", "description": "El texto de la pregunta"},
                             "type": {"type": "string", "enum": ["text", "options", "yesno"], "description": "Tipo de input (default: text)"},
                             "options": {"type": "array", "items": {"type": "string"}, "description": "Solo si type=options"},
                             "id": {"type": "string", "description": "Identificador local opcional dentro del set"},
                         },
                         "required": ["text"],
                     },
                     "description": "Lista de preguntas a presentar al usuario",
                 },
                 "context": {"type": "string", "description": "Contexto/explicación opcional que ayude al usuario a responder"},
             }, "required": ["questions"]}},
            {"type": "function", "name": "qa_check",
             "description": (
                 "Revisa si el usuario respondió alguna pregunta pendiente del form /qa. "
                 "Por defecto consume las respuestas (las archiva tras leerlas). "
                 "Retorna {ok, data: {count, items}} con las respuestas pendientes."
             ),
             "parameters": {"type": "object", "properties": {
                 "consume": {"type": "boolean", "description": "Si true (default) archiva las respuestas leídas"},
             }, "required": []}},
            {"type": "function", "name": "execute_command",
             "description": "Ejecuta un comando simple (no persistente). Tiene filtro de seguridad.",
             "parameters": {"type": "object", "properties": {
                 "command": {"type": "string"},
             }, "required": ["command"]}},
            {"type": "function", "name": "guardar_memoria",
             "description": "Guarda un hecho en la memoria a largo plazo",
             "parameters": {"type": "object", "properties": {
                 "contenido": {"type": "string"},
                 "categoria": {"type": "string", "enum": ["preferencia", "proyecto", "hecho", "instruccion"]},
             }, "required": ["contenido", "categoria"]}},
            {"type": "function", "name": "consultar_memoria",
             "description": "Consulta la memoria a largo plazo",
             "parameters": {"type": "object", "properties": {
                 "categoria": {"type": "string", "enum": ["preferencia", "proyecto", "hecho", "instruccion"]},
             }, "required": []}},
            {"type": "function", "name": "buscar_memoria",
             "description": ("Busca SEMÁNTICAMENTE en el historial completo de la conversación, "
                             "más allá de la ventana visible y de los tramos ya compactados. "
                             "Úsala cuando el usuario referencia algo de hace tiempo: "
                             "'¿qué dije sobre…?', '¿recuerdas cuando hablamos de…?', "
                             "modelos/nombres/fechas que probablemente ya no están en los últimos turnos. "
                             "NO la uses si el dato está claramente en los mensajes visibles. "
                             "Retorna JSON con [{id, rol, ts, texto, score}] ordenado por relevancia."),
             "parameters": {"type": "object", "properties": {
                 "query": {"type": "string", "description": "Pregunta o tema en lenguaje natural."},
                 "k": {"type": "number", "description": "Cuántos resultados (default 5, máx 20)."},
                 "rol": {"type": "string", "enum": ["user", "assistant"], "description": "Filtrar por rol (opcional)."},
                 "dias_max": {"type": "number", "description": "Limitar a los últimos N días (opcional)."},
             }, "required": ["query"]}},
            {"type": "function", "name": "buscar_en_internet",
             "description": "Busca en internet con DuckDuckGo",
             "parameters": {"type": "object", "properties": {
                 "query": {"type": "string"}, "max_results": {"type": "number"},
             }, "required": ["query"]}},
            {"type": "function", "name": "leer_pagina_web",
             "description": "Lee el contenido de texto de una URL",
             "parameters": {"type": "object", "properties": {
                 "url": {"type": "string"}, "max_chars": {"type": "number"},
             }, "required": ["url"]}},
            {"type": "function", "name": "listar_skills",
             "description": "Lista las skills disponibles",
             "parameters": {"type": "object", "properties": {}, "required": []}},
            {"type": "function", "name": "crear_skill",
             "description": "Crea una nueva skill persistente con instrucciones y opcionalmente un script Python. La skill queda disponible de inmediato sin reiniciar.",
             "parameters": {"type": "object", "properties": {
                 "nombre": {"type": "string", "description": "Identificador de la skill (slug, ej: 'youtube-downloader')"},
                 "instrucciones": {"type": "string", "description": "Contenido del SKILL.md — describe qué hace la skill, cómo usarla y ejemplos"},
                 "script_nombre": {"type": "string", "description": "Nombre del archivo .py opcional (ej: 'run.py')"},
                 "script_code": {"type": "string", "description": "Código Python del script opcional"},
             }, "required": ["nombre", "instrucciones"]}},
            {"type": "function", "name": "activar_skill",
             "description": "Carga las instrucciones de una skill al contexto",
             "parameters": {"type": "object", "properties": {
                 "name": {"type": "string"},
             }, "required": ["name"]}},
            {"type": "function", "name": "ejecutar_script_skill",
             "description": "Ejecuta un script de una skill instalada. Ejemplo: skill='gmail-reader', script='run.py', args='buscar --query \"from:amazon.com\"'",
             "parameters": {"type": "object", "properties": {
                 "skill":      {"type": "string", "description": "Nombre de la skill (ej: 'gmail-reader', 'seguimiento')"},
                 "script":     {"type": "string", "description": "Nombre del script a ejecutar (ej: 'run.py')"},
                 "args":       {"type": "string", "description": "Argumentos CLI para el script (ej: 'buscar --query \"from:amazon.com\"')"},
             }, "required": ["skill", "script"]}},
            # ── Wiki ──────────────────────────────────────────────────────────
            {"type": "function", "name": "leer_wiki",
             "description": "Lee una página del wiki de conocimiento persistente (ej: 'personas/usuario')",
             "parameters": {"type": "object", "properties": {
                 "pagina": {"type": "string"},
             }, "required": ["pagina"]}},
            {"type": "function", "name": "escribir_wiki",
             "description": "Crea o reemplaza una página del wiki",
             "parameters": {"type": "object", "properties": {
                 "pagina": {"type": "string"}, "contenido": {"type": "string"},
             }, "required": ["pagina", "contenido"]}},
            {"type": "function", "name": "actualizar_index_wiki",
             "description": "Actualiza la entrada de una página en index.md del wiki",
             "parameters": {"type": "object", "properties": {
                 "pagina": {"type": "string"}, "resumen": {"type": "string"},
             }, "required": ["pagina", "resumen"]}},
            {"type": "function", "name": "buscar_wiki",
             "description": "Busca páginas relevantes en el wiki",
             "parameters": {"type": "object", "properties": {
                 "query": {"type": "string"},
             }, "required": ["query"]}},
            {"type": "function", "name": "listar_wiki",
             "description": "Lista todas las páginas del wiki (lee index.md)",
             "parameters": {"type": "object", "properties": {}, "required": []}},
            {"type": "function", "name": "enviar_archivo_telegram",
             "description": (
                 "Envía un ARCHIVO REAL existente en disco al usuario por Telegram (máx 50 MB). "
                 "Solo úsalo cuando ACABAS de crear o descargar un archivo concreto y el usuario debe recibirlo. "
                 "NO lo uses para enviar texto, resúmenes, listas, mensajes o respuestas conversacionales: "
                 "esos van como texto de tu respuesta final y el sistema los entrega solo. "
                 "Si no tienes una ruta válida que exista, NO llames esta herramienta."
             ),
             "parameters": {"type": "object", "properties": {
                 "ruta": {"type": "string", "description": "Ruta absoluta o relativa de un archivo que EXISTE en disco"},
                 "caption": {"type": "string", "description": "Texto descriptivo opcional para acompañar el archivo (no para enviar texto suelto)"},
             }, "required": ["ruta"]}},
            # ── Browser (Playwright) ──────────────────────────────────────────
            {"type": "function", "name": "browser_navegar",
             "description": "Abre una URL en el browser y devuelve el texto visible de la página. Soporta JS y páginas dinámicas.",
             "parameters": {"type": "object", "properties": {
                 "url": {"type": "string", "description": "URL a navegar"},
                 "esperar": {"type": "string", "description": "Evento de espera: domcontentloaded, load, networkidle"},
             }, "required": ["url"]}},
            {"type": "function", "name": "browser_screenshot",
             "description": "Toma un screenshot de la página actual. Devuelve la ruta del archivo PNG (luego usa enviar_archivo_telegram para enviarlo).",
             "parameters": {"type": "object", "properties": {
                 "nombre": {"type": "string", "description": "Nombre base del archivo (sin extensión)"},
             }, "required": []}},
            {"type": "function", "name": "browser_click",
             "description": "Hace clic en un elemento de la página por texto visible o selector CSS.",
             "parameters": {"type": "object", "properties": {
                 "selector": {"type": "string", "description": "Texto visible del botón/enlace o selector CSS"},
             }, "required": ["selector"]}},
            {"type": "function", "name": "browser_escribir",
             "description": "Escribe texto en un campo de formulario (input, textarea). Usa selector CSS.",
             "parameters": {"type": "object", "properties": {
                 "selector": {"type": "string", "description": "Selector CSS del campo"},
                 "texto": {"type": "string", "description": "Texto a escribir"},
             }, "required": ["selector", "texto"]}},
            {"type": "function", "name": "browser_obtener_texto",
             "description": "Devuelve el texto visible de un elemento o de toda la página.",
             "parameters": {"type": "object", "properties": {
                 "selector": {"type": "string", "description": "Selector CSS (por defecto 'body')"},
             }, "required": []}},
            {"type": "function", "name": "browser_ejecutar_js",
             "description": "Ejecuta JavaScript en la página actual del browser.",
             "parameters": {"type": "object", "properties": {
                 "script": {"type": "string", "description": "Código JavaScript a ejecutar"},
             }, "required": ["script"]}},
            # ── Excel ─────────────────────────────────────────────────────────
            {"type": "function", "name": "excel",
             "description": (
                 "Herramienta completa para leer, crear y manipular archivos Excel (.xlsx). "
                 "Operaciones disponibles:\n"
                 "  LECTURA   : info, leer, leer_formulas, listar_hojas, buscar\n"
                 "  ESCRITURA : escribir, crear, reemplazar\n"
                 "  HOJAS     : crear_hoja, eliminar_hoja, renombrar_hoja, copiar_hoja, mover_hoja\n"
                 "  ESTRUCTURA: insertar_filas, eliminar_filas, insertar_columnas, eliminar_columnas, ordenar\n"
                 "  FORMATO   : formato_celdas, auto_ajustar_columnas, formato_condicional\n"
                 "  OBJETOS   : crear_tabla, agregar_grafico, proteger_hoja, hipervinculo"
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operación a realizar (ver lista en descripción)",
                     "enum": [
                         "info", "leer", "leer_formulas", "listar_hojas", "buscar",
                         "escribir", "crear", "reemplazar",
                         "crear_hoja", "eliminar_hoja", "renombrar_hoja", "copiar_hoja", "mover_hoja",
                         "insertar_filas", "eliminar_filas", "insertar_columnas", "eliminar_columnas", "ordenar",
                         "formato_celdas", "auto_ajustar_columnas", "formato_condicional",
                         "crear_tabla", "agregar_grafico", "proteger_hoja", "hipervinculo",
                     ]
                 },
                 "ruta": {"type": "string", "description": "Ruta del archivo Excel (.xlsx)"},
                 "hoja": {"type": "string", "description": "Nombre de la hoja (None = hoja activa)"},
                 "rango": {"type": "string", "description": "Rango de celdas ej: 'A1:D10'"},
                 "datos": {"type": "array", "description": "Lista de listas para escribir [[col1,col2],[val1,val2]]"},
                 "celda_inicio": {"type": "string", "description": "Celda de inicio para escribir, ej: 'A1'"},
                 "hojas": {"type": "array", "description": "Lista de nombres de hojas para crear"},
                 "texto": {"type": "string", "description": "Texto a buscar"},
                 "texto_buscar": {"type": "string", "description": "Texto a buscar para reemplazar"},
                 "texto_reemplazar": {"type": "string", "description": "Texto de reemplazo"},
                 "nombre": {"type": "string", "description": "Nombre de hoja o tabla"},
                 "nombre_actual": {"type": "string", "description": "Nombre actual de la hoja"},
                 "nombre_nuevo": {"type": "string", "description": "Nuevo nombre de la hoja"},
                 "origen": {"type": "string", "description": "Hoja de origen para copiar"},
                 "destino": {"type": "string", "description": "Nombre de la hoja destino al copiar"},
                 "posicion": {"type": "number", "description": "Posición (índice) de la hoja"},
                 "fila": {"type": "number", "description": "Número de fila (1-based)"},
                 "columna": {"type": "number", "description": "Número de columna (1-based)"},
                 "cantidad": {"type": "number", "description": "Cantidad de filas/columnas a insertar o eliminar"},
                 "ascendente": {"type": "boolean", "description": "True = orden ascendente"},
                 "fila_inicio": {"type": "number", "description": "Fila desde donde empezar a ordenar (default 2 para omitir encabezado)"},
                 "negrita": {"type": "boolean", "description": "Aplicar negrita"},
                 "cursiva": {"type": "boolean", "description": "Aplicar cursiva"},
                 "color_fondo": {"type": "string", "description": "Color de fondo hex sin '#', ej: 'FFFF00'"},
                 "color_texto": {"type": "string", "description": "Color de texto hex sin '#', ej: 'FF0000'"},
                 "tamanio_fuente": {"type": "number", "description": "Tamaño de fuente en puntos"},
                 "alineacion": {"type": "string", "enum": ["left", "center", "right"],
                                "description": "Alineación horizontal"},
                 "tipo": {"type": "string",
                          "description": "Tipo de formato condicional: mayor_que|menor_que|igual_a|contiene|entre. O tipo de gráfico: barras|barras_apiladas|lineas|pastel|area|dispersion"},
                 "valor": {"type": "string", "description": "Valor para formato condicional. Para 'entre' usar 'v1,v2'"},
                 "estilo": {"type": "string", "description": "Estilo de tabla Excel, ej: 'TableStyleMedium9'"},
                 "rango_datos": {"type": "string", "description": "Rango de datos para el gráfico, ej: 'A1:B10'"},
                 "titulo": {"type": "string", "description": "Título del gráfico"},
                 "celda_posicion": {"type": "string", "description": "Celda donde anclar el gráfico, ej: 'E2'"},
                 "contrasena": {"type": "string", "description": "Contraseña para proteger la hoja (None = desproteger)"},
                 "celda": {"type": "string", "description": "Celda donde insertar el hipervínculo, ej: 'A1'"},
                 "url": {"type": "string", "description": "URL del hipervínculo"},
                 "max_filas": {"type": "number", "description": "Máximo de filas a leer (default 100)"},
             }, "required": ["operacion", "ruta"]}},
            # ── Google TV ─────────────────────────────────────────────────────
            {"type": "function", "name": "google_tv",
             "description": (
                 "Control remoto de Google TVs por red local. Sin ADB ni modo desarrollador.\n"
                 "Operaciones:\n"
                 "  parear       — Inicia pairing con un TV (nombre + IP del TV)\n"
                 "  confirmar    — Confirma codigo de pairing mostrado en el TV\n"
                 "  estado       — Estado de TVs (encendido, app actual, volumen)\n"
                 "  encender     — Enciende un TV por nombre\n"
                 "  apagar       — Apaga un TV por nombre\n"
                 "  volumen      — Controla volumen (subir, bajar, mute)\n"
                 "  app          — Abre una app (youtube, netflix, disney+, spotify, etc.)\n"
                 "  control      — Navegacion (arriba, abajo, ok, back, home, play, pausa)\n"
                 "  escribir     — Escribe texto en el TV (busquedas)\n"
                 "  apagar_todos — Apaga todos los TVs\n"
                 "  listar       — Lista TVs registrados"
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["parear", "confirmar", "estado", "encender", "apagar",
                              "volumen", "app", "control", "escribir", "apagar_todos", "listar"]
                 },
                 "nombre": {"type": "string", "description": "Nombre del TV (TV Sala, TV Cuarto, etc.)"},
                 "ip": {"type": "string", "description": "IP del TV en la red local (para parear)"},
                 "codigo": {"type": "string", "description": "Codigo de pairing mostrado en el TV"},
                 "accion": {"type": "string", "description": "Accion de volumen: subir, bajar, mute"},
                 "nivel": {"type": "number", "description": "Pasos de volumen (default 1)"},
                 "aplicacion": {"type": "string", "description": "App a abrir: youtube, netflix, disney+, spotify, prime, hbo, etc."},
                 "comando": {"type": "string", "description": "Comando de control: arriba, abajo, ok, back, home, play, pausa, stop, mute"},
                 "texto": {"type": "string", "description": "Texto a escribir en el TV"},
             }, "required": ["operacion"]}},
            # ── Presencia (WiFi Sensing) ──────────────────────────────────────
            {"type": "function", "name": "presencia",
             "description": (
                 "Deteccion de personas por WiFi (RuView + ESP32). Sin camaras.\n"
                 "Operaciones:\n"
                 "  estado     — Quien esta en casa, en que areas\n"
                 "  vitales    — Signos vitales: respiracion y pulso sin contacto\n"
                 "  actividad  — Nivel de actividad por zona (area opcional)\n"
                 "  historial  — Registro de presencia ultimas horas\n"
                 "  alertas    — Caidas, inactividad prolongada, anomalias\n"
                 "  sensores   — Estado de los ESP32 conectados\n"
                 "  config     — Ver o modificar configuracion del servidor"
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["estado", "vitales", "actividad", "historial", "alertas", "sensores", "config"]
                 },
                 "area": {"type": "string", "description": "Filtrar por area de la casa (para actividad, historial)"},
                 "horas": {"type": "number", "description": "Horas de historial a consultar (default 4)"},
                 "ruview_url": {"type": "string", "description": "URL del servidor RuView (para config)"},
                 "mapear_zona": {"type": "string", "description": "Nombre de zona en RuView (para config)"},
                 "a_area": {"type": "string", "description": "Nombre de area en distribucion_casa (para config)"},
                 "umbral_inactividad_min": {"type": "number", "description": "Minutos sin movimiento para alerta (para config)"},
             }, "required": ["operacion"]}},
            # ── Distribucion de la Casa ───────────────────────────────────────
            {"type": "function", "name": "distribucion_casa",
             "description": (
                 "Mapa de areas del hogar/oficina. Registra cada area (sala, cocina, "
                 "dormitorio, bano, etc.) con foto y descripcion. Base para ubicar objetos.\n"
                 "Operaciones:\n"
                 "  agregar_area  — Registra un area nueva con nombre, descripcion y foto\n"
                 "  listar_areas  — Lista todas las areas registradas\n"
                 "  ver_area      — Detalle de un area con su foto\n"
                 "  editar_area   — Modifica nombre, descripcion o foto de un area\n"
                 "  eliminar_area — Elimina un area del mapa\n\n"
                 "Si el usuario envia una foto del area, pasa el image_path en 'imagen'."
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["agregar_area", "listar_areas", "ver_area", "editar_area", "eliminar_area"]
                 },
                 "nombre": {"type": "string", "description": "Nombre del area (sala, cocina, dormitorio, etc.)"},
                 "descripcion": {"type": "string", "description": "Descripcion del area"},
                 "nuevo_nombre": {"type": "string", "description": "Nuevo nombre para renombrar el area (solo editar_area)"},
                 "imagen": {"type": "string", "description": "Ruta de la imagen del area (image_path del mensaje Telegram)"},
             }, "required": ["operacion"]}},
            # ── Ubicaciones de Objetos ────────────────────────────────────────
            {"type": "function", "name": "ubicaciones",
             "description": (
                 "Registro de objetos y su ubicacion en la casa/oficina. "
                 "Vinculado al mapa de areas (distribucion_casa).\n"
                 "Operaciones:\n"
                 "  registrar — Registra un objeto con area, lugar exacto, descripcion y foto\n"
                 "  buscar    — Busca un objeto por nombre (acepta coincidencia parcial)\n"
                 "  listar    — Lista objetos (todos o filtrados por area)\n"
                 "  mover     — Cambia la ubicacion de un objeto a otra area/lugar\n"
                 "  eliminar  — Elimina un objeto del registro\n"
                 "  resumen   — Resumen por areas y objetos mas reubicados\n\n"
                 "Si el usuario envia foto del objeto/lugar, pasa el image_path en 'imagen'."
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["registrar", "buscar", "listar", "mover", "eliminar", "resumen"]
                 },
                 "nombre": {"type": "string", "description": "Nombre del objeto (regleta, taladro, tijeras, etc.)"},
                 "area": {"type": "string", "description": "Area de la casa donde esta el objeto (debe existir en distribucion_casa)"},
                 "lugar_exacto": {"type": "string", "description": "Ubicacion precisa dentro del area (detras del escritorio, estante 2, cajon derecho, etc.)"},
                 "descripcion": {"type": "string", "description": "Descripcion adicional del objeto"},
                 "imagen": {"type": "string", "description": "Ruta de la imagen (image_path del mensaje Telegram)"},
             }, "required": ["operacion"]}},
            # ── Recetas ──────────────────────────────────────────────────────
            {"type": "function", "name": "recetas",
             "description": (
                 "Registro de recetas de cocina con cruce a lista de compras.\n"
                 "Operaciones:\n"
                 "  agregar      — Guarda receta con ingredientes, pasos y foto\n"
                 "  ver          — Muestra receta completa\n"
                 "  listar       — Lista recetas (filtrar por categoria o ingrediente)\n"
                 "  editar       — Modifica una receta existente\n"
                 "  eliminar     — Elimina una receta\n"
                 "  que_cocinar  — Sugiere recetas segun lo que tienes en lista_compras\n"
                 "  preparar     — Revisa ingredientes, agrega faltantes a lista_compras\n"
                 "  favoritas    — Muestra las recetas mas preparadas\n\n"
                 "Los ingredientes son una lista de objetos: "
                 '[{"nombre": "arroz", "cantidad": "2", "unidad": "tazas"}, ...]\n'
                 "Los pasos son una lista de strings: "
                 '["Lavar el arroz", "Hervir agua", ...]'
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["agregar", "ver", "listar", "editar", "eliminar",
                              "que_cocinar", "preparar", "favoritas"]
                 },
                 "nombre": {"type": "string", "description": "Nombre de la receta"},
                 "nuevo_nombre": {"type": "string", "description": "Nuevo nombre (solo editar)"},
                 "ingredientes": {
                     "type": "array",
                     "description": "Lista de ingredientes [{nombre, cantidad, unidad}, ...]",
                     "items": {"type": "object", "properties": {
                         "nombre": {"type": "string"},
                         "cantidad": {"type": "string"},
                         "unidad": {"type": "string"},
                     }, "required": ["nombre"]}
                 },
                 "pasos": {
                     "type": "array",
                     "description": "Lista de pasos de preparacion",
                     "items": {"type": "string"}
                 },
                 "categoria": {"type": "string", "description": "Categoria (desayuno, almuerzo, cena, postre, snack)"},
                 "porciones": {"type": "number", "description": "Numero de porciones"},
                 "ingrediente": {"type": "string", "description": "Ingrediente para filtrar en listar"},
                 "imagen": {"type": "string", "description": "Ruta de la imagen (image_path del mensaje Telegram)"},
             }, "required": ["operacion"]}},
            # ── Gastos ───────────────────────────────────────────────────────
            {"type": "function", "name": "gastos",
             "description": (
                 "Tracking de gastos personales con presupuestos.\n"
                 "Operaciones:\n"
                 "  registrar   — Registra un gasto (monto, categoria, descripcion, foto de recibo)\n"
                 "  listar      — Lista gastos (filtrar por mes, categoria, ultimos N)\n"
                 "  resumen     — Resumen mensual: totales, por categoria, top gastos\n"
                 "  eliminar    — Elimina un gasto por ID\n"
                 "  presupuesto — Define o consulta presupuesto mensual por categoria\n"
                 "  comparar    — Compara gastos entre dos meses\n\n"
                 "Si el usuario envia foto del recibo, pasa el image_path en 'imagen'."
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["registrar", "listar", "resumen", "eliminar", "presupuesto", "comparar"]
                 },
                 "monto": {"type": "number", "description": "Monto del gasto"},
                 "categoria": {"type": "string", "description": "Categoria (comida, transporte, servicios, entretenimiento, salud, etc.)"},
                 "descripcion": {"type": "string", "description": "Descripcion del gasto"},
                 "fecha": {"type": "string", "description": "Fecha del gasto ISO (default: hoy)"},
                 "mes": {"type": "string", "description": "Mes en formato YYYY-MM (para listar, resumen, comparar)"},
                 "mes1": {"type": "string", "description": "Primer mes para comparar (YYYY-MM)"},
                 "mes2": {"type": "string", "description": "Segundo mes para comparar (YYYY-MM)"},
                 "ultimos": {"type": "number", "description": "Mostrar solo los ultimos N gastos"},
                 "id": {"type": "number", "description": "ID del gasto (para eliminar)"},
                 "imagen": {"type": "string", "description": "Ruta de imagen del recibo (image_path)"},
             }, "required": ["operacion"]}},
            # ── Mantenimiento ────────────────────────────────────────────────
            {"type": "function", "name": "mantenimiento",
             "description": (
                 "Calendario de mantenimiento de objetos/equipos del hogar.\n"
                 "Operaciones:\n"
                 "  registrar   — Registra item con frecuencia (dias) y area\n"
                 "  listar      — Lista todos los items de mantenimiento\n"
                 "  pendientes  — Muestra que esta atrasado o toca esta semana\n"
                 "  completar   — Marca un mantenimiento como realizado hoy\n"
                 "  historial   — Historial de mantenimientos de un item\n"
                 "  eliminar    — Elimina un item del calendario\n\n"
                 "Frecuencias comunes: 7=semanal, 30=mensual, 90=trimestral, 180=semestral, 365=anual"
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["registrar", "listar", "pendientes", "completar", "historial", "eliminar"]
                 },
                 "nombre": {"type": "string", "description": "Nombre del item (filtro AC, aceite carro, limpieza nevera, etc.)"},
                 "frecuencia_dias": {"type": "number", "description": "Frecuencia en dias (7=semanal, 30=mensual, 90=trimestral, 365=anual)"},
                 "area": {"type": "string", "description": "Area de la casa donde esta el item"},
                 "descripcion": {"type": "string", "description": "Descripcion de que hacer en el mantenimiento"},
                 "nota": {"type": "string", "description": "Nota al completar un mantenimiento"},
                 "ultimo_mantenimiento": {"type": "string", "description": "Fecha ISO del ultimo mantenimiento (default: hoy)"},
             }, "required": ["operacion"]}},
            # ── Contactos Servicios ──────────────────────────────────────────
            {"type": "function", "name": "contactos_servicios",
             "description": (
                 "Directorio de proveedores de servicios (plomero, electricista, etc.).\n"
                 "Operaciones:\n"
                 "  agregar          — Registra contacto (nombre, oficio, telefono, email, notas, calificacion)\n"
                 "  buscar           — Busca por nombre u oficio (parcial)\n"
                 "  listar           — Lista contactos (filtrar por oficio)\n"
                 "  editar           — Modifica datos de un contacto\n"
                 "  registrar_visita — Registra que vino a hacer un trabajo (costo, nota)\n"
                 "  historial        — Historial de visitas de un contacto\n"
                 "  eliminar         — Elimina un contacto"
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["agregar", "buscar", "listar", "editar", "registrar_visita", "historial", "eliminar"]
                 },
                 "nombre": {"type": "string", "description": "Nombre del contacto"},
                 "nuevo_nombre": {"type": "string", "description": "Nuevo nombre (solo editar)"},
                 "oficio": {"type": "string", "description": "Oficio o especialidad (plomero, electricista, AC, pintor, etc.)"},
                 "telefono": {"type": "string", "description": "Numero de telefono"},
                 "email": {"type": "string", "description": "Correo electronico"},
                 "notas": {"type": "string", "description": "Notas sobre el contacto"},
                 "calificacion": {"type": "number", "description": "Calificacion 1-5 estrellas"},
                 "texto": {"type": "string", "description": "Texto a buscar (nombre u oficio)"},
                 "trabajo": {"type": "string", "description": "Descripcion del trabajo realizado (para registrar_visita)"},
                 "costo": {"type": "number", "description": "Costo del trabajo"},
                 "nota": {"type": "string", "description": "Nota adicional sobre la visita"},
             }, "required": ["operacion"]}},
            # ── Documentos ───────────────────────────────────────────────────
            {"type": "function", "name": "documentos",
             "description": (
                 "Registro de documentos importantes y su ubicacion fisica.\n"
                 "Operaciones:\n"
                 "  registrar — Registra documento con tipo, area, ubicacion exacta, foto\n"
                 "  buscar    — Busca por nombre, tipo o descripcion (parcial)\n"
                 "  ver       — Detalle completo con foto\n"
                 "  listar    — Lista documentos (filtrar por tipo o area). Alerta vencimientos\n"
                 "  mover     — Cambia la ubicacion fisica del documento\n"
                 "  eliminar  — Elimina un documento del registro\n\n"
                 "Tipos comunes: legal, financiero, medico, vehiculo, hogar, personal, educacion.\n"
                 "Si el usuario envia foto del documento, pasa el image_path en 'imagen'."
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["registrar", "buscar", "ver", "listar", "mover", "eliminar"]
                 },
                 "nombre": {"type": "string", "description": "Nombre del documento (escritura, pasaporte, seguro carro, etc.)"},
                 "tipo": {"type": "string", "description": "Tipo de documento (legal, financiero, medico, vehiculo, hogar, personal)"},
                 "area": {"type": "string", "description": "Area de la casa donde esta el documento"},
                 "ubicacion_exacta": {"type": "string", "description": "Lugar preciso (carpeta azul, gaveta 2, sobre manila, etc.)"},
                 "descripcion": {"type": "string", "description": "Descripcion adicional"},
                 "fecha_vencimiento": {"type": "string", "description": "Fecha de vencimiento YYYY-MM-DD (pasaporte, seguro, etc.)"},
                 "texto": {"type": "string", "description": "Texto a buscar"},
                 "imagen": {"type": "string", "description": "Ruta de la imagen (image_path del mensaje Telegram)"},
             }, "required": ["operacion"]}},
            # ── Lista de Compras ──────────────────────────────────────────────
            {"type": "function", "name": "lista_compras",
             "description": (
                 "Gestiona la lista de compras del supermercado. "
                 "Operaciones:\n"
                 "  agregar      — Agrega un item (con foto opcional si el usuario envia imagen)\n"
                 "  listar       — Muestra items (filtro: todos, pendientes, comprados)\n"
                 "  comprado     — Marca un item como comprado\n"
                 "  ver_imagen   — Obtiene la foto guardada de un producto\n"
                 "  eliminar     — Elimina un item de la lista\n"
                 "  estadisticas — Resumen: productos frecuentes, categorias, tasa de compra\n"
                 "  limpiar      — Elimina todos los items ya comprados\n\n"
                 "Si el usuario envia una foto junto con el pedido de agregar un producto, "
                 "pasa el image_path en el parametro 'imagen' para asociar la foto al item."
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["agregar", "listar", "comprado", "ver_imagen", "eliminar", "estadisticas", "limpiar"]
                 },
                 "nombre": {"type": "string", "description": "Nombre del producto (para agregar, comprado, ver_imagen, eliminar)"},
                 "cantidad": {"type": "number", "description": "Cantidad (default 1)"},
                 "unidad": {"type": "string", "description": "Unidad de medida (kg, litros, paquetes, etc.)"},
                 "categoria": {"type": "string", "description": "Categoria del producto (frutas, lacteos, limpieza, etc.)"},
                 "filtro": {"type": "string", "enum": ["todos", "pendientes", "comprados"],
                            "description": "Filtro para listar (default: todos)"},
                 "imagen": {"type": "string", "description": "Ruta de la imagen del producto (image_path del mensaje Telegram)"},
             }, "required": ["operacion"]}},
            # ── Gmail Reader ─────────────────────────────────────────────────
            {"type": "function", "name": "gmail",
             "description": (
                 "Lee correos de Gmail via API OAuth2.\n"
                 "Operaciones:\n"
                 "  leer    — Lee los ultimos N correos (default: 10 no leidos)\n"
                 "  buscar  — Busca con query de Gmail (from:, subject:, after:, label:, etc.)\n"
                 "  resumen — Cuantos no leidos + remitentes frecuentes"
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "description": "Operacion a realizar",
                     "enum": ["leer", "buscar", "resumen"]
                 },
                 "cantidad": {"type": "number", "description": "Cantidad de correos a leer (default 10, max 50)"},
                 "query": {"type": "string", "description": "Query de Gmail (ej: 'from:banco', 'is:unread after:2026/04/01', 'subject:factura')"},
             }, "required": ["operacion"]}},
            {"type": "function", "name": "enviar_foto_telegram",
             "description": (
                 "Envía una imagen al usuario por Telegram usando una URL pública. "
                 "Ideal para noticias: envía cada noticia como foto + titular en el caption. "
                 "El caption soporta formato Markdown (*negrita*, _cursiva_). "
                 "Llama esta función una vez por noticia."
             ),
             "parameters": {"type": "object", "properties": {
                 "url": {"type": "string", "description": "URL pública de la imagen"},
                 "caption": {"type": "string", "description": "Titular o descripción (máx 1024 chars, soporta Markdown)"},
             }, "required": ["url"]}},
            # ── Agenda de Acciones ────────────────────────────────────────────
            {"type": "function", "name": "agenda",
             "description": (
                 "Agenda de acciones automáticas programadas.\n\n"
                 "**OBLIGATORIO:** SIEMPRE incluir el campo 'operacion' (string) en los args.\n"
                 "NO pases args como {'listar': true} — usa {'operacion': 'listar'}.\n\n"
                 "Operaciones válidas (valor exacto del campo 'operacion'):\n"
                 "  'agregar'    — Crea una nueva acción programada (requiere: nombre, tipo, prompt)\n"
                 "  'listar'     — Muestra todas las acciones (opcional: filtro)\n"
                 "  'ver'        — Detalle completo de una acción (requiere: id)\n"
                 "  'activar'    — Activa una acción pausada (requiere: id)\n"
                 "  'desactivar' — Pausa una acción temporalmente (requiere: id)\n"
                 "  'eliminar'   — Elimina una acción (requiere: id)\n"
                 "  'historial'  — Últimas ejecuciones de una acción (requiere: id)\n\n"
                 "Tipos de acción (campo 'tipo' al agregar):\n"
                 "  'diaria'             — Todos los días (o días específicos) a una hora fija\n"
                 "  'recurrente_ventana' — Cada N minutos dentro de un rango horario\n"
                 "  'recurrente'         — Cada N minutos sin restricción de horario\n\n"
                 "Días de semana: 1=lunes, 2=martes, ..., 7=domingo\n\n"
                 "Ejemplo correcto: {\"operacion\": \"listar\", \"filtro\": \"activas\"}"
             ),
             "parameters": {"type": "object", "properties": {
                 "operacion": {
                     "type": "string",
                     "enum": ["agregar", "listar", "ver", "activar", "desactivar", "eliminar", "historial"],
                     "description": "Operación a realizar"
                 },
                 "id": {"type": "number", "description": "ID de la acción (para ver, activar, desactivar, eliminar, historial)"},
                 "nombre": {"type": "string", "description": "Nombre corto descriptivo de la acción"},
                 "tipo": {
                     "type": "string",
                     "enum": ["diaria", "recurrente_ventana", "recurrente"],
                     "description": "Tipo de programación de la acción"
                 },
                 "prompt": {"type": "string", "description": "Instrucción completa que el agente ejecutará automáticamente"},
                 "descripcion": {"type": "string", "description": "Descripción larga opcional"},
                 "hora": {"type": "string", "description": "Hora de ejecución HH:MM (solo tipo 'diaria', ej: '08:30')"},
                 "dias_semana": {
                     "type": "array", "items": {"type": "number"},
                     "description": "Días de la semana [1=lunes..7=domingo]. Omitir = todos los días"
                 },
                 "intervalo_minutos": {"type": "number", "description": "Minutos entre ejecuciones (tipos recurrentes)"},
                 "hora_inicio": {"type": "string", "description": "Hora inicio de ventana HH:MM (tipo 'recurrente_ventana', ej: '09:00')"},
                 "hora_fin": {"type": "string", "description": "Hora fin de ventana HH:MM (tipo 'recurrente_ventana', ej: '18:00')"},
                 "filtro": {
                     "type": "string", "enum": ["todos", "activas", "inactivas"],
                     "description": "Filtro para la operación 'listar' (default: todos)"
                 },
                 "ultimas": {"type": "number", "description": "Cantidad de entradas a mostrar en 'historial' (default 5)"},
             }, "required": ["operacion"]}},
        ]

        if perfil == "local":
            allowed = set(self.TOOL_PROFILES["local"])
            self.tools = [t for t in self.tools if t["name"] in allowed]

    # ── Parseo de argumentos ─────────────────────────────────────────────────

    def _parse_tool_arguments(self, raw):
        if not raw or (isinstance(raw, str) and not raw.strip()):
            return {}, None
        if isinstance(raw, dict):
            return raw, None
        cleaned = raw.strip()
        try:
            parsed = json.loads(cleaned)
            return (parsed, None) if isinstance(parsed, dict) else ({}, None)
        except Exception:
            pass
        m = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', cleaned, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group())
                if isinstance(parsed, dict):
                    return parsed, None
            except Exception:
                pass
        return None, f"No se pudieron parsear args: {raw[:200]}"

    # ── Memoria con recuperación (ingestión no bloqueante) ───────────────────

    def _ingestar_retrieval(self, rol: str, texto: str):
        """Indexa un mensaje en `memoria_retrieval_tool` en background.

        Tolerante a fallo: si sentence-transformers no está, si el embed peta,
        o si la DB falla, solo se loggea — NUNCA debe romper el turno del agente.
        """
        if not texto or not str(texto).strip():
            return
        try:
            from memoria_retrieval_tool import ejecutar as _mr_ejecutar
            threading.Thread(
                target=_mr_ejecutar,
                args=("ingestar",),
                kwargs={
                    "rol": rol,
                    "texto": str(texto)[:8000],
                    "session_id": str(getattr(self, "_current_chat_id", 0) or "global"),
                },
                daemon=True,
            ).start()
        except Exception as e:
            logger.warning(f"retrieval ingest fallo (ignorado): {e}")

    # ── Ejecución de una herramienta ─────────────────────────────────────────

    def _ejecutar_tool(self, fn_name: str, args: dict) -> str:
        if fn_name == "list_files_in_dir":
            result = iatools.list_files_in_dir(**args)
        elif fn_name == "read_file":
            result = iatools.read_file(**args)
        elif fn_name == "edit_file":
            result = iatools.edit_file(**args)
        elif fn_name == "execute_command":
            result = iatools.execute_command(**args)
        elif fn_name == "execute_bash":
            # Guardrail: si el comando matchea patrones de comandos largos,
            # rechazar y empujar al LLM a usar execute_long.
            import re as _re_eb
            _cmd_eb = args.get("command", "")
            _patrones_largos = r"\b(yt-dlp|youtube-dl|whisper(\b|\.py)|ffmpeg|moviepy|doblador|tsr-stress|transcribir|doblar|train\.py|fine.?tune)\b"
            if _re_eb.search(_patrones_largos, _cmd_eb, _re_eb.IGNORECASE):
                result = ("⚠️ Este comando parece ser largo (descarga/transcripción/conversión de video). "
                          "Usa la herramienta `execute_long` en su lugar — encola el proceso en el job_manager "
                          "y puedes consultar progreso con `job_status`. No bloquea el agente.")
            else:
                result = iatools.execute_bash(**args)
        elif fn_name == "execute_long":
            from job_client import submit_job, submit_pipeline
            _name = args.get("name", "tarea-sin-nombre")
            _cwd = args.get("cwd")
            if args.get("steps"):
                resp = submit_pipeline(_name, args["steps"], cwd=_cwd)
            elif args.get("command"):
                resp = submit_job(_name, args["command"], cwd=_cwd)
            else:
                resp = {"ok": False, "error": "execute_long requiere 'command' o 'steps'"}
            result = json.dumps(resp, ensure_ascii=False)
        elif fn_name == "job_status":
            from job_client import status as _job_status
            resp = _job_status(args["job_id"],
                               incluir_output=args.get("incluir_output", False),
                               lineas=int(args.get("lineas", 30)))
            result = json.dumps(resp, ensure_ascii=False)
        elif fn_name == "job_list":
            from job_client import list_jobs as _job_list
            resp = _job_list(estado=args.get("estado"), limite=int(args.get("limite", 20)))
            result = json.dumps(resp, ensure_ascii=False)
        elif fn_name == "job_cancel":
            from job_client import cancel as _job_cancel
            resp = _job_cancel(args["job_id"])
            result = json.dumps(resp, ensure_ascii=False)
        elif fn_name == "qa_ask":
            from job_client import qa_ask as _qa_ask
            resp = _qa_ask(args.get("questions", []), context=args.get("context"))
            result = json.dumps(resp, ensure_ascii=False)
        elif fn_name == "qa_check":
            from job_client import qa_answers as _qa_answers
            resp = _qa_answers(consume=args.get("consume", True))
            result = json.dumps(resp, ensure_ascii=False)
        elif fn_name == "guardar_memoria":
            result = self.memoria.agregar_hecho(**args)
        elif fn_name == "consultar_memoria":
            # listar_hechos solo acepta `categoria`; ignoramos cualquier kwarg que
            # el LLM pueda alucinar (visto 'contexto' del 11-may en agenda id 8,
            # rompió con TypeError y dejó la acción muerta hasta el 25-may).
            cat = args.get("categoria")
            hechos = self.memoria.listar_hechos(categoria=cat) if cat else self.memoria.listar_hechos()
            result = json.dumps(hechos, ensure_ascii=False) if hechos else "Sin hechos"
        elif fn_name == "buscar_memoria":
            from memoria_retrieval_tool import ejecutar as _mr_ejecutar
            args.setdefault("k", 5)
            result = _mr_ejecutar("buscar", **args)
        elif fn_name == "buscar_en_internet":
            result = iatools.web_search(**args)
        elif fn_name == "leer_pagina_web":
            result = scrape_url(**args)
        elif fn_name == "browser_navegar":
            result = browser_navegar(**args)
        elif fn_name == "browser_screenshot":
            result = browser_screenshot(**args)
        elif fn_name == "browser_click":
            result = browser_click(**args)
        elif fn_name == "browser_escribir":
            # Normalizar alias: el LLM a veces envía 'text' en lugar de 'texto'
            if "text" in args and "texto" not in args:
                args["texto"] = args.pop("text")
            result = browser_escribir(**args)
        elif fn_name == "browser_obtener_texto":
            result = browser_obtener_texto(**args)
        elif fn_name == "browser_ejecutar_js":
            result = browser_ejecutar_js(**args)
        elif fn_name == "listar_skills":
            items = self.skill_loader.listar()
            result = json.dumps(items, ensure_ascii=False, indent=2) if items else "Sin skills"
        elif fn_name == "activar_skill":
            nombre = args.get("name", "")
            cuerpo = self.skill_loader.obtener_cuerpo(nombre)
            if cuerpo:
                skill = self.skill_loader.obtener_skill(nombre)
                scripts = f"\nScripts: {', '.join(skill['scripts'])}" if skill and skill.get("scripts") else ""
                result = f"[SKILL: {nombre}]{scripts}\n\n{cuerpo}"
            else:
                disponibles = [s["name"] for s in self.skill_loader.listar()]
                result = f"Skill '{nombre}' no encontrada. Disponibles: {', '.join(disponibles)}"
        elif fn_name == "ejecutar_script_skill":
            # Aceptar alias que LLMs locales tienden a usar
            skill_name = (args.get("skill") or args.get("skill_name")
                          or args.get("name") or args.get("nombre") or "")
            script_file = (args.get("script") or args.get("script_file")
                           or args.get("archivo") or args.get("script_nombre") or "run.py")
            _raw_args = (args.get("args") or args.get("arguments")
                         or args.get("argumentos") or args.get("script_code") or "")
            # Si el LLM mandó una lista en vez de string, convertirla
            if isinstance(_raw_args, list):
                import shlex as _sx
                _raw_args = " ".join(_sx.quote(str(a)) for a in _raw_args)
            result = self.skill_loader.ejecutar_script(skill_name, script_file, _raw_args)
        elif fn_name == "crear_skill":
            result = self.skill_loader.crear_skill(
                nombre=args.get("nombre", ""),
                instrucciones=args.get("instrucciones", ""),
                script_nombre=args.get("script_nombre"),
                script_code=args.get("script_code"),
            )
            # Actualizar system prompt para reflejar la nueva skill
            self._actualizar_system_prompt()
        # ── Wiki ──────────────────────────────────────────────────────────────
        elif fn_name == "leer_wiki":
            result = self.wiki.leer(args.get("pagina", "")) if self.wiki else "Wiki no disponible"
        elif fn_name == "escribir_wiki":
            result = self.wiki.escribir(args.get("pagina", ""), args.get("contenido", "")) if self.wiki else "Wiki no disponible"
        elif fn_name == "actualizar_index_wiki":
            result = self.wiki.actualizar_index(args.get("pagina", ""), args.get("resumen", "")) if self.wiki else "Wiki no disponible"
        elif fn_name == "buscar_wiki":
            result = self.wiki.buscar(args.get("query", "")) if self.wiki else "Wiki no disponible"
        elif fn_name == "listar_wiki":
            result = self.wiki.listar() if self.wiki else "Wiki no disponible"
        elif fn_name == "excel":
            from excel_tool import ejecutar as excel_ejecutar
            operacion = args.pop("operacion")
            result = excel_ejecutar(operacion, **args)
        elif fn_name == "google_tv":
            from google_tv_tool import ejecutar as tv_ejecutar
            operacion = args.pop("operacion")
            result = tv_ejecutar(operacion, **args)
        elif fn_name == "presencia":
            from presencia_tool import ejecutar as presencia_ejecutar
            operacion = args.pop("operacion")
            result = presencia_ejecutar(operacion, **args)
        elif fn_name == "distribucion_casa":
            from distribucion_casa_tool import ejecutar as casa_ejecutar
            operacion = args.pop("operacion")
            # Inyectar imagen del turno si aplica
            if operacion in ("agregar_area", "editar_area") and not args.get("imagen"):
                img = getattr(self, "_current_image_path", None)
                if img:
                    args["imagen"] = img
            result = casa_ejecutar(operacion, **args)
            # Si ver_area retorna imagen, enviarla por Telegram
            if operacion == "ver_area" and "IMAGEN:" in result:
                lineas = result.split("\n")
                texto_limpio = []
                for linea in lineas:
                    if linea.startswith("IMAGEN:"):
                        ruta_img = linea[7:]
                        cb = getattr(self, "_send_file_callback", None)
                        if cb:
                            cb(ruta_img, "")
                    else:
                        texto_limpio.append(linea)
                result = "\n".join(texto_limpio) + "\nFoto enviada."
        elif fn_name == "recetas":
            from recetas_tool import ejecutar as recetas_ejecutar
            operacion = args.pop("operacion")
            if operacion in ("agregar", "editar") and not args.get("imagen"):
                img = getattr(self, "_current_image_path", None)
                if img:
                    args["imagen"] = img
            result = recetas_ejecutar(operacion, **args)
            # Si ver retorna imagen, enviarla por Telegram
            if operacion == "ver" and "IMAGEN:" in result:
                lineas = result.split("\n")
                texto_limpio = []
                for linea in lineas:
                    if linea.startswith("IMAGEN:"):
                        ruta_img = linea[7:]
                        cb = getattr(self, "_send_file_callback", None)
                        if cb:
                            cb(ruta_img, "")
                    else:
                        texto_limpio.append(linea)
                result = "\n".join(texto_limpio) + "\nFoto enviada."
        elif fn_name == "gastos":
            from gastos_tool import ejecutar as gastos_ejecutar
            operacion = args.pop("operacion")
            if operacion == "registrar" and not args.get("imagen"):
                img = getattr(self, "_current_image_path", None)
                if img:
                    args["imagen"] = img
            result = gastos_ejecutar(operacion, **args)
        elif fn_name == "mantenimiento":
            from mantenimiento_tool import ejecutar as mant_ejecutar
            operacion = args.pop("operacion")
            result = mant_ejecutar(operacion, **args)
        elif fn_name == "contactos_servicios":
            from contactos_servicios_tool import ejecutar as cont_ejecutar
            operacion = args.pop("operacion")
            result = cont_ejecutar(operacion, **args)
        elif fn_name == "documentos":
            from documentos_tool import ejecutar as doc_ejecutar
            operacion = args.pop("operacion")
            if operacion in ("registrar", "mover") and not args.get("imagen"):
                img = getattr(self, "_current_image_path", None)
                if img:
                    args["imagen"] = img
            result = doc_ejecutar(operacion, **args)
            if operacion in ("ver", "buscar") and "IMAGEN:" in result:
                lineas = result.split("\n")
                texto_limpio = []
                for linea in lineas:
                    if linea.startswith("IMAGEN:"):
                        ruta_img = linea[7:]
                        cb = getattr(self, "_send_file_callback", None)
                        if cb:
                            cb(ruta_img, "")
                    else:
                        texto_limpio.append(linea)
                result = "\n".join(texto_limpio) + "\nFoto enviada."
        elif fn_name == "ubicaciones":
            from ubicaciones_tool import ejecutar as ubic_ejecutar
            operacion = args.pop("operacion")
            if operacion in ("registrar", "mover") and not args.get("imagen"):
                img = getattr(self, "_current_image_path", None)
                if img:
                    args["imagen"] = img
            result = ubic_ejecutar(operacion, **args)
            # Si buscar retorna imagen, enviarla por Telegram
            if operacion == "buscar" and "IMAGEN:" in result:
                lineas = result.split("\n")
                texto_limpio = []
                for linea in lineas:
                    if linea.startswith("IMAGEN:"):
                        ruta_img = linea[7:]
                        cb = getattr(self, "_send_file_callback", None)
                        if cb:
                            cb(ruta_img, "")
                    else:
                        texto_limpio.append(linea)
                result = "\n".join(texto_limpio) + "\nFoto enviada."
        elif fn_name == "lista_compras":
            from lista_compras_tool import ejecutar as compras_ejecutar
            operacion = args.pop("operacion")
            # Si hay imagen en el turno y el LLM no la pasó, inyectarla para agregar
            if operacion == "agregar" and not args.get("imagen"):
                img = getattr(self, "_current_image_path", None)
                if img:
                    args["imagen"] = img
            result = compras_ejecutar(operacion, **args)
            # Si ver_imagen retorna una ruta, enviarla como foto por Telegram
            if operacion == "ver_imagen" and result.startswith("IMAGEN:"):
                ruta_img = result[7:]
                cb = getattr(self, "_send_file_callback", None)
                if cb:
                    cb(ruta_img, "")
                result = f"Foto de '{args.get('nombre', '')}' enviada."
        elif fn_name == "enviar_archivo_telegram":
            ruta = args.get("ruta", "") or args.get("path", "") or args.get("archivo", "")
            caption = args.get("caption", "")
            if not ruta:
                result = ("❌ enviar_archivo_telegram requiere 'ruta' a un archivo real existente. "
                          "No la uses para enviar texto: el texto va en tu respuesta final.")
            elif not os.path.exists(ruta):
                result = (f"❌ El archivo no existe: {ruta}. "
                          "No envíes archivos al azar — si solo quieres mandar texto, "
                          "ponlo en tu respuesta final, no en esta herramienta.")
            else:
                cb = getattr(self, "_send_file_callback", None)
                if cb:
                    ok = cb(ruta, caption)
                    result = f"✅ Archivo enviado: {ruta}" if ok else f"❌ No se pudo enviar: {ruta}"
                else:
                    result = "⚠️ enviar_archivo_telegram no disponible fuera de Telegram."
        elif fn_name == "gmail":
            import subprocess, sys as _sys, shlex as _shlex
            _gmail_script = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "skills", "gmail-reader", "run.py"
            )
            operacion = args.pop("operacion", "leer")
            # Build CLI args from kwargs
            _cli_parts = [operacion]
            for _k, _v in args.items():
                if _v is None:
                    continue
                _flag = f"--{_k.replace('_', '-')}"
                if isinstance(_v, bool):
                    if _v:
                        _cli_parts.append(_flag)
                else:
                    _cli_parts.extend([_flag, str(_v)])
            _cmd = [_sys.executable, _gmail_script] + _cli_parts
            try:
                _proc = subprocess.run(
                    _cmd, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=60
                )
                result = (_proc.stdout + _proc.stderr).strip() or "(sin salida)"
            except subprocess.TimeoutExpired:
                result = "Error: gmail timeout (60s)"
            except Exception as _e:
                result = f"Error gmail: {_e}"
        elif fn_name == "agenda":
            from agenda_tool import ejecutar as agenda_ejecutar
            operacion = args.pop("operacion", None)
            # Fallback: si el LLM no paso "operacion", inferir de los args
            if not operacion:
                if args.get("nombre") and args.get("tipo") and args.get("prompt"):
                    operacion = "agregar"
                elif args.get("ultimas") is not None:
                    operacion = "historial"
                elif args.get("listar") or args.get("filtro") is not None:
                    operacion = "listar"
                elif args.get("id") is not None and not args.get("nombre"):
                    # id solo es ambiguo (ver/activar/desactivar/eliminar);
                    # default a "ver" por ser no destructivo
                    operacion = "ver"
                else:
                    operacion = "listar"
                try:
                    print(f"[agenda] operacion ausente, inferida='{operacion}' desde args={list(args.keys())}", flush=True)
                except Exception:
                    pass
            # Limpiar args invalidos del tool schema
            args.pop("listar", None)
            # Filtrar args al subconjunto valido por operacion
            args_validos_por_op = {
                "agregar": {"nombre", "tipo", "prompt", "chat_id", "descripcion", "hora",
                            "dias_semana", "intervalo_minutos", "hora_inicio", "hora_fin"},
                "listar": {"filtro"},
                "ver": {"id"},
                "activar": {"id"},
                "desactivar": {"id"},
                "eliminar": {"id"},
                "historial": {"id", "ultimas"},
            }
            permitidos = args_validos_por_op.get(operacion, set())
            args = {k: v for k, v in args.items() if k in permitidos}
            if operacion == "agregar" and not args.get("chat_id"):
                args["chat_id"] = getattr(self, "_current_chat_id", 0)
            result = agenda_ejecutar(operacion, **args)
        elif fn_name == "enviar_foto_telegram":
            url = args.get("url", "")
            caption = args.get("caption", "")
            cb = getattr(self, "_send_photo_url_callback", None)
            if cb:
                ok = cb(url, caption)
                result = f"✅ Foto enviada: {url[:80]}" if ok else f"❌ No se pudo enviar foto: {url[:80]}"
            else:
                result = "⚠️ enviar_foto_telegram no disponible fuera de Telegram."
        else:
            result = f"Herramienta desconocida: {fn_name}"

        MAX_LEN = 8000
        result_str = str(result) if result is not None else ""
        if len(result_str) > MAX_LEN:
            result_str = result_str[:MAX_LEN] + "\n... [TRUNCADO]"
        return result_str

    # ── Llamada al LLM con retry ──────────────────────────────────────────────

    _RETRY_CODES = {429, 500, 502, 503, 504}
    _MAX_RETRIES  = int(os.getenv("AGENT_MAX_RETRIES", "3"))
    _RETRY_DELAY  = float(os.getenv("AGENT_RETRY_DELAY", "5"))   # segundos base

    def _llamar_llm(self, kwargs: dict):
        """Llama al LLM con reintentos exponenciales para errores transitorios."""
        ultimo_error = None
        for intento in range(self._MAX_RETRIES):
            try:
                return self._client.responses.create(**kwargs)
            except Exception as e:
                ultimo_error = e
                codigo = getattr(getattr(e, "response", None), "status_code", None)
                if codigo not in self._RETRY_CODES:
                    logger.error(f"Error llamando al LLM (no reintentable): {e}", exc_info=True)
                    raise
                espera = self._RETRY_DELAY * (2 ** intento)
                logger.warning(f"Error LLM {codigo} (intento {intento+1}/{self._MAX_RETRIES}), reintentando en {espera:.0f}s: {e}")
                time.sleep(espera)
        logger.error(f"Error llamando al LLM tras {self._MAX_RETRIES} intentos: {ultimo_error}", exc_info=True)
        raise ultimo_error

    def _llamar_llm_stream(self, kwargs: dict, text_callback=None):
        """Llama al LLM con streaming. Imprime tokens via text_callback y retorna la respuesta final.

        text_callback(chunk: str | None):
          - None  → señal de primer token (imprimir prefijo "Asistente: ")
          - str   → delta de texto a imprimir
        """
        ultimo_error = None
        for intento in range(self._MAX_RETRIES):
            try:
                with self._client.responses.stream(**kwargs) as stream:
                    texto_iniciado = False
                    for event in stream:
                        if (text_callback and
                                getattr(event, "type", None) == "response.output_text.delta"):
                            if not texto_iniciado:
                                text_callback(None)   # prefijo
                                texto_iniciado = True
                            text_callback(event.delta)
                    return stream.get_final_response(), texto_iniciado
            except Exception as e:
                ultimo_error = e
                codigo = getattr(getattr(e, "response", None), "status_code", None)
                if codigo not in self._RETRY_CODES:
                    logger.error(f"Error LLM stream (no reintentable): {e}", exc_info=True)
                    raise
                espera = self._RETRY_DELAY * (2 ** intento)
                logger.warning(f"Error LLM stream {codigo} (intento {intento+1}/{self._MAX_RETRIES}), reintentando en {espera:.0f}s")
                time.sleep(espera)
        logger.error(f"Error LLM stream tras {self._MAX_RETRIES} intentos: {ultimo_error}", exc_info=True)
        raise ultimo_error

    # ── API pública ───────────────────────────────────────────────────────────

    @property
    def bash_proceso_activo(self) -> dict | None:
        """Retorna info del comando bash en ejecución, o None si no hay ninguno.

        Estructura: {"comando": str, "inicio": datetime, "pid": int}
        """
        return getattr(iatools.terminal, "proceso_activo", None)

    def limpiar_historial(self):
        """Borra el historial de conversación (mantiene solo el system prompt)."""
        self._rename_messages_debug("limpiado")
        self.messages = []
        self._actualizar_system_prompt()
        self._save_messages_debug()

    def chat(self, mensaje: str, progress_callback=None,
             send_file_callback=None, send_photo_url_callback=None,
             image_path: str = None, contexto: dict = None,
             stream_callback=None, chat_id: int = None) -> str:
        """Procesa un mensaje del usuario y retorna la respuesta final.

        Ejecuta el loop de tool calls de forma interna hasta que el LLM
        entregue una respuesta sin herramientas.

        Args:
            contexto: dict opcional con metadata del turno (fuente, usuario, etc.)
                      Se inyecta como prefijo en el mensaje enviado al LLM.
                      Ejemplo: {"fuente": "telegram", "usuario": "rhay", "chat_id": 123}
        """
        self._send_file_callback = send_file_callback
        self._send_photo_url_callback = send_photo_url_callback
        self._current_image_path = image_path
        self._current_chat_id = chat_id or 0
        self._actualizar_system_prompt()

        # Prefijo de contexto si viene metadata del turno
        if contexto:
            partes = " | ".join(f"{k}={v}" for k, v in contexto.items())
            mensaje_llm = f"[Contexto: {partes}]\n{mensaje}"
        else:
            mensaje_llm = mensaje

        # Construir mensaje de usuario (visión si hay imagen)
        if image_path and os.path.exists(image_path):
            import base64
            with open(image_path, "rb") as _f:
                _b64 = base64.b64encode(_f.read()).decode()
            _ext = os.path.splitext(image_path)[1].lower().lstrip(".")
            _mime = "jpeg" if _ext in ("jpg", "jpeg") else _ext or "jpeg"
            logger.info(f"Procesando imagen vision: {image_path}")
            self.messages.append({
                "role": "user",
                "content": [
                    {"type": "input_image", "image_url": f"data:image/{_mime};base64,{_b64}"},
                    {"type": "input_text", "text": mensaje_llm},
                ]
            })
        else:
            self.messages.append({"role": "user", "content": mensaje_llm})

        # Indexar mensaje del usuario en memoria con recuperación (no bloquea).
        # Usamos `mensaje` (texto crudo), NO `mensaje_llm` (que puede traer
        # prefijos tipo "[Contexto: ...]" que contaminarían el retrieval).
        self._ingestar_retrieval(rol="user", texto=mensaje)

        # Esperar compactación anterior si aún está en progreso
        if self._compaction_thread and self._compaction_thread.is_alive():
            print("⏳ Finalizando compactación...", flush=True)
            self._compaction_thread.join(timeout=30)

        last_reply = ""
        max_tokens = int(os.getenv("TELEGRAM_MAX_OUTPUT_TOKENS", "8192"))
        _herramientas_usadas: list = []
        _iteraciones: int = 0

        while True:
            _iteraciones += 1
            self._save_messages_debug()
            kwargs = {
                "model": self._model,
                "input": self.messages,
                "max_output_tokens": max_tokens,
            }
            if self.tools:
                # Tool Router: filtrar herramientas relevantes para reducir tokens
                if self._tool_router and _iteraciones == 1:
                    routed = self._tool_router.route(mensaje, self.tools)
                    if routed:
                        kwargs["tools"] = routed
                    # Si routed es vacio, no enviar tools (conversacion general)
                else:
                    kwargs["tools"] = self.tools

            if stream_callback:
                response, texto_impreso = self._llamar_llm_stream(kwargs, stream_callback)
                if texto_impreso:
                    stream_callback("\n")   # salto de línea al terminar el bloque de texto
            else:
                response = self._llamar_llm(kwargs)
                texto_impreso = False

            # Capturar el texto de la respuesta antes de procesar tool calls
            for out in response.output:
                if out.type == "message":
                    texto = "\n".join(p.text for p in out.content)
                    if texto:
                        last_reply = texto
                elif out.type == "function_call":
                    _herramientas_usadas.append(out.name)

            hubo_tool = self.process_response(
                response,
                texto_ya_impreso=texto_impreso,
                progress_callback=progress_callback,
            )
            if not hubo_tool:
                break

        # Indexar la respuesta final del assistant en memoria con recuperación.
        # Solo el texto entregado al usuario; tool calls intermedios son ruido.
        if last_reply:
            self._ingestar_retrieval(rol="assistant", texto=last_reply)

        self._ultima_ejecucion = {
            "herramientas_usadas": _herramientas_usadas,
            "iteraciones": _iteraciones,
            "tokens_aprox": self._contar_tokens(),
        }

        # Compactar en background si es necesario (no bloquea al usuario)
        tokens = self._contar_tokens()
        if len(self.messages) > self.MAX_MENSAJES or tokens >= self.MAX_TOKENS:
            self._compaction_thread = threading.Thread(
                target=self.compactar_historial, kwargs={"forzar": True}, daemon=True
            )
            self._compaction_thread.start()

        return last_reply

    # ── process_response ─────────────────────────────────────────────────────

    def process_response(self, response, texto_ya_impreso: bool = False,
                         progress_callback=None) -> bool:
        """Procesa la respuesta del LLM.

        Ejecuta TODOS los tool calls de la respuesta antes de retornar.
        Returns True si se ejecutó al menos una herramienta.
        """
        self.messages += [
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in response.output
        ]
        hubo_tool_call = False

        for output in response.output:
            if output.type == "function_call":
                fn_name = output.name
                args, parse_error = self._parse_tool_arguments(output.arguments)

                if args is None:
                    self._tool_fail_count += 1
                    logger.warning(f"Args malformados #{self._tool_fail_count}: {fn_name} → {parse_error}")
                    self.messages.append({
                        "type": "function_call_output",
                        "call_id": output.call_id,
                        "output": json.dumps({"error": f"Args malformados: {parse_error}"}),
                    })
                    hubo_tool_call = True
                    continue

                self._tool_fail_count = 0
                logger.info(f"Tool: {fn_name} args={args}")
                print(f"  - Herramienta: {fn_name} | args: {args}")

                if progress_callback:
                    try:
                        progress_callback(fn_name)
                    except Exception:
                        pass

                result_str = self._ejecutar_tool(fn_name, args)
                logger.debug(f"Resultado {fn_name}: {result_str[:200]}")
                print(f"  ✓ Resultado: {result_str[:300]}...")

                self.messages.append({
                    "type": "function_call_output",
                    "call_id": output.call_id,
                    "output": json.dumps({"files": result_str}),
                })
                hubo_tool_call = True

            elif output.type == "message":
                reply = "\n".join(p.text for p in output.content)
                if not texto_ya_impreso:
                    print(f"Asistente: {reply}")

        return hubo_tool_call
