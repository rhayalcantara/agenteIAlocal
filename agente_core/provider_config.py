"""Configuración de proveedores de IA desde variables de entorno."""
import os
from openai import OpenAI
from logger import get_logger

logger = get_logger("provider_config")

# Sentinel para Gemini: si GEMINI_BASE_URL tiene este valor
# se reemplaza por el endpoint OpenAI-compat de Google.
_GEMINI_SDK_SENTINEL = "gemini-sdk"
_GEMINI_COMPAT_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Definición de proveedores disponibles
_PROVEEDORES = {
    "openrouter": {
        "nombre": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "model_default": "google/gemma-4-26b-a4b",
        "headers": {
            "HTTP-Referer": "https://github.com/rhayalcantara/agenteIAlocal",
            "X-Title": "Agente IA Local",
        },
    },
    "openai": {
        "nombre": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "model_default": "gpt-4o",
        "headers": {},
    },
    "lmstudio": {
        "nombre": "LM Studio (local)",
        "base_url_env": "LMSTUDIO_BASE_URL",
        "base_url": "http://localhost:1234/v1",
        "api_key_env": "LMSTUDIO_API_KEY",
        "model_env": "LMSTUDIO_MODEL",
        "model_default": "local-model",
        "headers": {},
    },
    "claude": {
        "nombre": "Claude (Anthropic)",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "model_env": "CLAUDE_MODEL",
        "model_default": "claude-sonnet-4-5",
        "headers": {},
    },
    "gemini": {
        "nombre": "Google Gemini",
        "base_url_env": "GEMINI_BASE_URL",
        "base_url": _GEMINI_COMPAT_URL,
        "api_key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "model_default": "gemini-2.0-flash",
        "headers": {},
    },
}


def cargar_proveedores() -> dict:
    """Carga y retorna los proveedores que tienen API key configurada."""
    disponibles = {}
    for key, cfg in _PROVEEDORES.items():
        api_key_env = cfg.get("api_key_env", "")
        api_key = os.getenv(api_key_env, "") if api_key_env else "no-key"
        if not api_key:
            continue
        model_env = cfg.get("model_env", "")
        model = os.getenv(model_env, cfg["model_default"]) if model_env else cfg["model_default"]
        base_url = os.getenv(cfg.get("base_url_env", ""), cfg["base_url"])
        # Resolver sentinel gemini-sdk → endpoint OpenAI-compat de Google
        if base_url == _GEMINI_SDK_SENTINEL:
            base_url = _GEMINI_COMPAT_URL
        disponibles[key] = {
            "nombre": cfg["nombre"],
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
            "headers": cfg.get("headers", {}),
        }
    return disponibles


def crear_cliente(config: dict) -> OpenAI:
    """Crea un cliente OpenAI compatible con la configuración dada."""
    # Timeout alto para modelos locales (Ollama, LM Studio) que pueden tardar
    # varios minutos en generar una respuesta larga.
    # Configurable con AGENT_TIMEOUT_SECONDS en .env (default 300 seg).
    timeout = float(os.getenv("AGENT_TIMEOUT_SECONDS", "300"))
    kwargs = {
        "base_url": config["base_url"],
        "api_key": config["api_key"],
        "timeout": timeout,
    }
    if config.get("headers"):
        kwargs["default_headers"] = config["headers"]
    return OpenAI(**kwargs)


def crear_cliente_por_key(proveedores: dict, key: str):
    """Retorna (client, model) para el proveedor indicado, o (None, None) si no existe."""
    if key not in proveedores:
        return None, None
    cfg = proveedores[key]
    return crear_cliente(cfg), cfg["model"]


def seleccionar_proveedor(proveedores: dict, default: str = None) -> str:
    """Muestra menú interactivo y retorna la key del proveedor elegido."""
    keys = list(proveedores.keys())
    print("\n📡 Proveedores disponibles:")
    for i, k in enumerate(keys):
        marca = " (actual)" if k == default else ""
        print(f"  {i+1}. {proveedores[k]['nombre']} — {proveedores[k]['model']}{marca}")
    while True:
        try:
            idx = int(input("Elige número: ").strip()) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except ValueError:
            pass
        print("Opción inválida.")


def obtener_configuracion(non_interactive: bool = False) -> dict | None:
    """Carga proveedores, selecciona el default o pide elección interactiva.

    Retorna un dict con claves: model, api_key, base_url, provider, nombre.
    Retorna None si no hay proveedores configurados.
    """
    proveedores = cargar_proveedores()
    if not proveedores:
        print("ERROR: No hay proveedores configurados en .env")
        return None

    default_key = os.getenv("PROVIDER_DEFAULT", "").strip().lower()
    if default_key and default_key in proveedores:
        provider_key = default_key
    elif len(proveedores) == 1:
        provider_key = list(proveedores.keys())[0]
    elif non_interactive:
        provider_key = list(proveedores.keys())[0]
        logger.warning(f"PROVIDER_DEFAULT no configurado — usando '{provider_key}' por defecto.")
    else:
        provider_key = seleccionar_proveedor(proveedores)

    cfg = proveedores[provider_key]
    return {
        "provider": provider_key,
        "nombre": cfg["nombre"],
        "model": cfg["model"],
        "api_key": cfg["api_key"],
        "base_url": cfg["base_url"],
        "headers": cfg.get("headers", {}),
    }
