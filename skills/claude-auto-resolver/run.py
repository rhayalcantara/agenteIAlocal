"""
claude-auto-resolver: consulta al proveedor de IA activo para resolver dudas o errores del agente.
Reutiliza provider_config.py del proyecto para usar el mismo proveedor que el agente.
"""
import os
import sys

MAX_OUTPUT_CHARS = 8000

# Agregar agente_core al path para importar provider_config
_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
_CORE = os.path.join(_ROOT, "agente_core")
for _p in (_ROOT, _CORE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Cargar .env antes de importar provider_config
def _load_env():
    env_path = os.path.join(_ROOT, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

_load_env()


def run_claude_prompt(prompt: str, timeout: int = 60) -> str:
    """
    Consulta al proveedor de IA activo para resolver dudas o errores rápidos.

    Args:
        prompt:  La pregunta o descripción del error.
        timeout: Segundos máximos de espera (default 60).

    Returns:
        Respuesta del modelo como string, o mensaje de error.
    """
    if not prompt or not prompt.strip():
        return "Error: el prompt no puede estar vacío."

    try:
        from provider_config import obtener_configuracion, crear_cliente
    except ImportError as e:
        return f"Error importando provider_config: {e}"

    config = obtener_configuracion(non_interactive=True)
    if not config:
        return "Error: no hay proveedores de IA configurados en .env"

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=config["api_key"],
            base_url=config["base_url"],
            timeout=timeout,
            default_headers=config.get("headers", {}),
        )
        response = client.chat.completions.create(
            model=config["model"],
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un ingeniero senior especializado en Python y desarrollo de software. "
                        "Responde de forma concisa y directa, máximo 4 oraciones. "
                        "Si la respuesta requiere código, incluye solo lo esencial."
                    ),
                },
                {"role": "user", "content": prompt.strip()},
            ],
            max_tokens=512,
        )
        output = response.choices[0].message.content or ""
        if len(output) > MAX_OUTPUT_CHARS:
            output = output[:MAX_OUTPUT_CHARS] + "\n... [respuesta truncada]"
        return output
    except Exception as e:
        return f"Error consultando IA ({config.get('nombre', '?')}): {e}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python run.py "<pregunta o error>"')
        sys.exit(1)
    prompt = " ".join(sys.argv[1:])
    print(run_claude_prompt(prompt))
