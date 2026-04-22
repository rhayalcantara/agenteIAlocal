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
            "execute_bash", "guardar_memoria",
            "buscar_en_internet", "listar_skills", "activar_skill", "crear_skill",
            "leer_wiki", "buscar_wiki",
            "enviar_archivo_telegram",
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
                 tool_profile: str = None):
        self._model = model
        self._provider = provider

        # Crear cliente OpenAI-compat
        kwargs = {"api_key": api_key or "no-key"}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

        # Determinar perfil de herramientas
        if tool_profile is None:
            tool_profile = self.PROVIDER_PROFILES.get(provider, "full")

        self._tool_profile = tool_profile
        self._tools_enabled = tool_profile != "none"
        self._tool_fail_count = 0
        self.setup_tools(tool_profile)

        self.memoria = Memoria()

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
        self.messages = [system_msg] + recientes
        self._actualizar_system_prompt()
        self._save_messages_debug()
        print(f"✅ Historial compactado: {len(self.messages)} mensajes")
        return True

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
             "description": "Ejecuta un comando bash persistente. Tiene filtro de comandos peligrosos.",
             "parameters": {"type": "object", "properties": {
                 "command": {"type": "string"}, "timeout": {"type": "number"},
             }, "required": ["command"]}},
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
             "description": "Ejecuta un script de una skill",
             "parameters": {"type": "object", "properties": {
                 "skill": {"type": "string"}, "script": {"type": "string"}, "args": {"type": "string"},
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
             "description": "Envía un archivo local al usuario por Telegram (máx 50 MB). Usar después de crear o descargar un archivo.",
             "parameters": {"type": "object", "properties": {
                 "ruta": {"type": "string", "description": "Ruta absoluta o relativa del archivo a enviar"},
                 "caption": {"type": "string", "description": "Texto descriptivo opcional para acompañar el archivo"},
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
            result = iatools.execute_bash(**args)
        elif fn_name == "guardar_memoria":
            result = self.memoria.agregar_hecho(**args)
        elif fn_name == "consultar_memoria":
            hechos = self.memoria.listar_hechos(**args)
            result = json.dumps(hechos, ensure_ascii=False) if hechos else "Sin hechos"
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
            result = self.skill_loader.ejecutar_script(
                args.get("skill", ""), args.get("script", ""), args.get("args", "")
            )
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
        elif fn_name == "enviar_archivo_telegram":
            ruta = args.get("ruta", "")
            caption = args.get("caption", "")
            cb = getattr(self, "_send_file_callback", None)
            if cb:
                ok = cb(ruta, caption)
                result = f"✅ Archivo enviado: {ruta}" if ok else f"❌ No se pudo enviar: {ruta}"
            else:
                result = "⚠️ enviar_archivo_telegram no disponible fuera de Telegram."
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
             stream_callback=None) -> str:
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
