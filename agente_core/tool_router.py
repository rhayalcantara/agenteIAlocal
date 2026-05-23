"""Tool Router — Selecciona herramientas relevantes antes de enviar al LLM principal.

Un modelo ligero analiza el mensaje del usuario y decide cuales herramientas
son relevantes (0-5 max). El LLM principal solo recibe esas, reduciendo
tokens de ~30k a ~1-3k.
"""
import os
import json
from openai import OpenAI
from logger import get_logger

logger = get_logger("tool_router")

# Catalogo: nombre -> descripcion corta + keywords para matching
TOOL_CATALOG = {
    # Archivos y sistema
    "list_files_in_dir": {"cat": "archivos", "kw": ["listar", "directorio", "carpeta", "archivos", "ls"]},
    "read_file": {"cat": "archivos", "kw": ["leer", "archivo", "contenido", "abrir", "ver archivo"]},
    "edit_file": {"cat": "archivos", "kw": ["editar", "crear", "escribir", "modificar", "archivo"]},
    "execute_bash": {"cat": "sistema", "kw": ["ejecutar", "comando", "terminal", "bash", "script", "node", "python", "instalar"]},
    "execute_command": {"cat": "sistema", "kw": ["ejecutar", "comando"]},

    # Web y busqueda
    "buscar_en_internet": {"cat": "web", "kw": ["buscar", "busca", "buscame", "busqueda", "internet", "google", "web", "investigar", "investiga", "manual", "manuales", "informacion", "info", "averiguar", "averigua", "encontrar", "encuentra", "como", "explica", "explicame", "dime como", "muestrame"]},
    "scrape_url": {"cat": "web", "kw": ["scrape", "pagina", "url", "extraer", "web"]},

    # Browser
    "browser_navegar": {"cat": "browser", "kw": ["navegar", "abrir", "pagina", "url", "browser", "web"]},
    "browser_screenshot": {"cat": "browser", "kw": ["screenshot", "captura", "pantalla"]},
    "browser_click": {"cat": "browser", "kw": ["click", "clic", "boton", "presionar"]},
    "browser_escribir": {"cat": "browser", "kw": ["escribir", "formulario", "input", "campo"]},
    "browser_obtener_texto": {"cat": "browser", "kw": ["texto", "leer", "pagina", "obtener"]},
    "browser_ejecutar_js": {"cat": "browser", "kw": ["javascript", "js", "ejecutar"]},

    # Memoria y conocimiento
    "guardar_memoria": {"cat": "memoria", "kw": ["recordar", "guardar", "memoria", "anotar", "recuerda"]},
    "consultar_memoria": {"cat": "memoria", "kw": ["recuerdas", "memoria", "sabes", "guardaste"]},
    "leer_wiki": {"cat": "wiki", "kw": ["wiki", "conocimiento", "documentacion"]},
    "escribir_wiki": {"cat": "wiki", "kw": ["wiki", "documentar", "escribir wiki"]},
    "buscar_wiki": {"cat": "wiki", "kw": ["buscar wiki", "wiki"]},
    "listar_wiki": {"cat": "wiki", "kw": ["wiki", "paginas", "listar wiki"]},
    "actualizar_index_wiki": {"cat": "wiki", "kw": ["wiki", "indice"]},

    # Skills
    "listar_skills": {"cat": "skills", "kw": ["skills", "habilidades", "que puedes", "capacidades"]},
    "activar_skill": {"cat": "skills", "kw": ["skill", "activar", "usar skill"]},
    "crear_skill": {"cat": "skills", "kw": ["crear skill", "nueva skill"]},
    "ejecutar_script_skill": {"cat": "skills", "kw": ["ejecutar", "script", "skill", "noticias", "scraper", "gmail", "seguimiento"]},

    # Telegram
    "enviar_archivo_telegram": {"cat": "telegram", "kw": ["enviar", "archivo", "documento", "telegram"]},
    "enviar_foto_telegram": {"cat": "telegram", "kw": ["enviar", "foto", "imagen", "telegram"]},

    # Dominio: hogar
    "lista_compras": {"cat": "hogar", "kw": ["compras", "lista", "supermercado", "comprar"]},
    "distribucion_casa": {"cat": "hogar", "kw": ["casa", "habitacion", "cuarto", "distribucion", "hogar"]},
    "ubicaciones": {"cat": "hogar", "kw": ["ubicacion", "lugar", "donde", "direccion", "mapa", "agrega", "agregar", "poner", "mover", "cosina", "cocina", "cuarto", "sala", "bano", "maquina", "aparato", "item"]},
    "recetas": {"cat": "hogar", "kw": ["receta", "cocina", "comida", "ingrediente", "cocinar"]},
    "gastos": {"cat": "finanzas", "kw": ["gasto", "gaste", "gastado", "dinero", "presupuesto", "pago", "cobro", "factura", "cuanto", "compre"]},
    "mantenimiento": {"cat": "hogar", "kw": ["mantenimiento", "reparar", "arreglar", "roto"]},
    "contactos_servicios": {"cat": "hogar", "kw": ["contacto", "servicio", "telefono", "llamar", "plomero", "electricista"]},
    "documentos": {"cat": "hogar", "kw": ["documento", "cedula", "pasaporte", "contrato", "papel"]},

    # Gmail
    "gmail": {"cat": "gmail", "kw": ["correo", "email", "gmail", "mail", "bandeja", "mensaje"]},

    # Agenda
    "agenda": {"cat": "agenda", "kw": ["agenda", "programar", "horario", "recordatorio", "tarea", "accion", "automatica"]},

    # Excel
    "excel": {"cat": "excel", "kw": ["excel", "hoja", "calculo", "tabla", "csv", "spreadsheet"]},

    # TV
    "google_tv": {"cat": "tv", "kw": ["tv", "tele", "television", "encender", "apagar", "volumen", "youtube", "netflix", "disney", "prime", "spotify", "hdmi", "canal", "pelicula", "serie", "pon", "poner"]},
}


def _normalizar(s: str) -> str:
    """Quita acentos y baja a minusculas para matching robusto.

    'informacion' debe matchear 'información', 'como' debe matchear 'cómo', etc.
    Sin esto, las queries del usuario con acentos no matchean keywords sin acentos.
    """
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _match_keywords(mensaje: str, tools_catalog: dict, max_tools: int = 5) -> list[str]:
    """Matching rapido por keywords sin LLM. Fallback si el router LLM no esta disponible.

    Normaliza acentos en ambos lados para robustez en queries en espanol con tildes.
    """
    msg_norm = _normalizar(mensaje)
    scores = {}
    for tool_name, info in tools_catalog.items():
        score = 0
        for kw in info["kw"]:
            if _normalizar(kw) in msg_norm:
                score += 1
        if score > 0:
            scores[tool_name] = score

    # Ordenar por score y retornar top N
    sorted_tools = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [t[0] for t in sorted_tools[:max_tools]]


def _route_with_llm(mensaje: str, tools_catalog: dict, client,
                     model: str, max_tools: int = 5) -> list[str]:
    """Usa un LLM ligero para decidir que herramientas son relevantes."""
    # Construir lista compacta: nombre + categoria + keywords principales
    lines = []
    for name, info in tools_catalog.items():
        kw_str = ", ".join(info["kw"][:4])
        lines.append(f"- {name} ({info['cat']}): {kw_str}")
    tool_list = "\n".join(lines)

    prompt = (
        f"Selecciona las herramientas relevantes para el mensaje del usuario (max {max_tools}). "
        f"Responde SOLO nombres, uno por linea. Si no se necesita ninguna, responde 'ninguna'.\n\n"
        f"Herramientas:\n{tool_list}\n\n"
        f"Mensaje: {mensaje}\n\n"
        f"Herramientas:"
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0,
        )
        content = resp.choices[0].message.content.strip()
        logger.info(f"Router LLM respuesta: {content[:100]}")

        if "ninguna" in content.lower():
            return []

        # Parsear nombres — soporta formatos: "nombre", "- nombre", "1. nombre"
        selected = []
        for line in content.split("\n"):
            line = line.strip().strip("-").strip("0123456789.").strip()
            # Buscar match exacto o parcial
            if line in tools_catalog:
                selected.append(line)
            else:
                # Buscar si alguna herramienta esta contenida en la linea
                for tool_name in tools_catalog:
                    if tool_name in line:
                        selected.append(tool_name)
                        break
        return list(dict.fromkeys(selected))[:max_tools]  # dedup preservando orden
    except Exception as e:
        logger.warning(f"Router LLM fallo ({e}), fallback a keywords")
        return _match_keywords(mensaje, tools_catalog, max_tools)


class ToolRouter:
    def __init__(self, client=None, model: str = None, use_llm: bool = False,
                 base_url: str = None, api_key: str = None):
        """
        Args:
            client: Cliente OpenAI existente (opcional)
            model: Modelo ligero para el router (ej: lfm2:latest)
            use_llm: Si True, usa LLM para routing. Si False, solo keywords.
            base_url: URL del gateway (si no se pasa client)
            api_key: API key del gateway (si no se pasa client)
        """
        self.model = model
        self.catalog = TOOL_CATALOG

        # Crear cliente propio si se pide LLM routing
        if use_llm:
            if client and hasattr(client, 'chat'):
                self.client = client
            elif base_url:
                self.client = OpenAI(base_url=base_url, api_key=api_key or "no-key")
            else:
                self.client = None
            self.use_llm = self.client is not None
        else:
            self.client = None
            self.use_llm = False

        if self.use_llm:
            logger.info(f"Router LLM activo: modelo={model}")
        else:
            logger.info("Router keywords activo")

    def route(self, mensaje: str, all_tools: list, max_tools: int = 5) -> list:
        """Filtra herramientas relevantes para el mensaje.

        Args:
            mensaje: Texto del usuario
            all_tools: Lista completa de tool definitions
            max_tools: Maximo de tools a retornar

        Returns:
            Lista filtrada de tool definitions (solo las relevantes)
        """
        if not mensaje or not all_tools:
            return all_tools

        # Obtener nombres relevantes
        if self.use_llm:
            selected_names = _route_with_llm(
                mensaje, self.catalog, self.client, self.model, max_tools
            )
            # Fallback hibrido: si LLM dice "ninguna" pero keywords detecta algo, usar keywords
            if not selected_names:
                kw_names = _match_keywords(mensaje, self.catalog, max_tools)
                if kw_names:
                    logger.info(f"Router: LLM dijo ninguna, keywords rescato: {kw_names}")
                    selected_names = kw_names
        else:
            selected_names = _match_keywords(mensaje, self.catalog, max_tools)

        if not selected_names:
            logger.info(f"Router: ninguna herramienta para '{mensaje[:50]}'")
            return []

        # Filtrar tool definitions
        filtered = [t for t in all_tools if t.get("name") in selected_names]
        names = [t["name"] for t in filtered]
        logger.info(f"Router: {len(filtered)}/{len(all_tools)} tools -> {names}")
        return filtered
