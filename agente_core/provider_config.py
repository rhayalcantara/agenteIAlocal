"""Configuración de proveedores de IA desde variables de entorno."""
import os
from openai import OpenAI
from logger import get_logger

logger = get_logger("provider_config")

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
        "api_key_env": "",
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
}


def cargar_proveedores() -> dict:
    """Carga y retorna los proveedores que tienen API key configurada."""
    disponibles = {}
    for key, cfg in _PROVEEDORES.items():
        api_key_env = cfg.get("api_key_env", "")
        api_key = os.getenv(api_key_env, "") if api_key_env else "no-key"
        if api_key:
            model_env = cfg.get("model_env", "")
            model = os.getenv(model_env, cfg["model_default"]) if model_env else cfg["model_default"]
            base_url = os.getenv(cfg.get("base_url_env", ""), cfg["base_url"])
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
    kwargs = {
        "base_url": config["base_url"],
        "api_key": config["api_key"],
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


def obtener_configuracion():
    """Carga proveedores, selecciona el default o pide elección interactiva."""
    proveedores = cargar_proveedores()
    if not proveedores:
        print("ERROR: No hay proveedores configurados en .env")
        return None

    default_key = os.getenv("PROVIDER_DEFAULT", "").strip().lower()
    if default_key and default_key in proveedores:
        provider_key = default_key
    elif len(proveedores) == 1:
        provider_key = list(proveedores.keys())[0]
    else:
        provider_key = seleccionar_proveedor(proveedores)

    config = proveedores[provider_key]
    client = crear_cliente(config)
    return client, config["model"], provider_key, proveedores
