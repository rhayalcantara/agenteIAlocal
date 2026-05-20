"""
Decision Engine — consulta al LLM para decidir qué hacer ante un problema.

Usa el mismo proveedor configurado en el proyecto para no añadir dependencias extra.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agente_core"))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# Reutilizamos la config de proveedor ya existente en el proyecto
try:
    from agente_core.provider_config import obtener_configuracion
    _cfg = obtener_configuracion(non_interactive=True)
except Exception:
    _cfg = None

_ACCIONES_VALIDAS = {"auto_restart", "alert_user", "alert_and_restart", "wait"}

_PROMPT_TEMPLATE = """\
Eres el sistema de supervisión de un agente de IA en producción.
Detectaste el siguiente problema:

Estado: {estado}
Detalle: {detalle}
Intentos de recuperación anteriores: {intentos}
Últimos logs del agente:
{logs}

Elige UNA acción. Responde ÚNICAMENTE con JSON válido, sin texto extra:
{{"accion": "<ACCION>", "razon": "<razón concisa en español>"}}

Opciones de acción:
- "auto_restart"       → el problema es un crash simple; reiniciar debería bastar
- "alert_user"         → el problema es grave o incierto; el usuario debe decidir
- "alert_and_restart"  → reiniciar automáticamente Y notificar al usuario
- "wait"               → el problema es muy reciente; esperar antes de actuar

Regla obligatoria: si los intentos anteriores son >= 2, la acción DEBE ser "alert_user".
"""


def decidir(situacion: dict) -> dict:
    """
    Consulta al LLM y retorna la decisión.

    Args:
        situacion: dict con claves "estado", "detalle", "intentos", "logs"

    Returns:
        dict con "accion" y "razon"
    """
    if _cfg is None:
        return {
            "accion": "alert_user",
            "razon": "No hay proveedor LLM configurado para tomar decisiones automáticas.",
        }

    prompt = _PROMPT_TEMPLATE.format(
        estado=situacion.get("estado", "?"),
        detalle=situacion.get("detalle", "?"),
        intentos=situacion.get("intentos", 0),
        logs=situacion.get("logs", "(sin logs)")[-600:],
    )

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=_cfg["api_key"],
            base_url=_cfg.get("base_url"),
        )
        resp = client.chat.completions.create(
            model=_cfg["model"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1,
        )
        content = resp.choices[0].message.content.strip()

        # Extraer el JSON de la respuesta (el LLM a veces añade texto extra)
        match = re.search(r"\{.*?\}", content, re.DOTALL)
        if match:
            datos = json.loads(match.group())
            accion = datos.get("accion", "alert_user")
            if accion not in _ACCIONES_VALIDAS:
                accion = "alert_user"
            # Aplicar regla forzada de seguridad
            if situacion.get("intentos", 0) >= 2 and accion != "alert_user":
                accion = "alert_user"
                datos["razon"] += " [Forzado a alert_user por exceso de intentos]"
            return {"accion": accion, "razon": datos.get("razon", "")}

    except Exception as e:
        pass

    return {
        "accion": "alert_user",
        "razon": "No se pudo obtener decisión del LLM. Se recomienda intervención manual.",
    }
