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
from datetime import datetime

from tools import Tool
from memoria import Memoria
from skill_loader import SkillLoader
from wiki_manager import WikiManager
from web_scraper import scrape_url
from logger import get_logger

logger = get_logger("agent")
iatools = Tool()

_orchestrator = None


def set_orchestrator(orch):
    global _orchestrator
    _orchestrator = orch


class Agent:
    MAX_MENSAJES = 30
    MENSAJES_CONSERVAR = 10

    TOOL_PROFILES = {
        "full": None,
        "local": [
            "list_files_in_dir", "read_file", "edit_file",
            "execute_bash", "guardar_memoria",
            "buscar_en_internet", "listar_skills", "activar_skill",
            "leer_wiki", "buscar_wiki",
        ],
        "none": [],
    }

    PROVIDER_PROFILES = {
        "openrouter": "full",
        "openai": "full",
        "claude": "full",
        "lmstudio": "local",
    }

    def __init__(self, tool_profile: str = "full"):
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

        self._system_message_base = ""
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

    # ── Compactación ──────────────────────────────────────────────────────────

    def compactar_historial(self, client, model_name):
        if len(self.messages) <= self.MAX_MENSAJES:
            return False
        print(f"📦 Compactando historial ({len(self.messages)} mensajes)...")
        system_msg = self.messages[0]
        antiguos = self.messages[1:-self.MENSAJES_CONSERVAR]
        recientes = self.messages[-self.MENSAJES_CONSERVAR:]
        textos = []
        for msg in antiguos:
            if isinstance(msg, dict):
                if msg.get("role") == "user":
                    textos.append(f"Usuario: {msg.get('content', '')[:200]}")
                elif msg.get("role") == "assistant":
                    textos.append(f"Asistente: {msg.get('content', '')[:200]}")
        if textos:
            try:
                resp = client.responses.create(
                    model=model_name,
                    input=[{"role": "user", "content":
                            "Resume en 2-3 oraciones:\n" + "\n".join(textos[:20])}]
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
        else:
            result = f"Herramienta desconocida: {fn_name}"

        MAX_LEN = 8000
        result_str = str(result) if result is not None else ""
        if len(result_str) > MAX_LEN:
            result_str = result_str[:MAX_LEN] + "\n... [TRUNCADO]"
        return result_str

    # ── process_response ─────────────────────────────────────────────────────

    def process_response(self, response, texto_ya_impreso: bool = False,
                         progress_callback=None) -> bool:
        """Procesa la respuesta del LLM.

        Ejecuta TODOS los tool calls de la respuesta antes de retornar.
        Returns True si se ejecutó al menos una herramienta.
        """
        self.messages += response.output
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
