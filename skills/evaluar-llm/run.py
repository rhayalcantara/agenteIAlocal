"""
Skill: evaluar-llm
Batería de pruebas para evaluar fortalezas y debilidades de un LLM en 4 dimensiones:
  1) Seguimiento de instrucciones
  2) Entendimiento de conceptos
  3) Proactividad y razonamiento
  4) Conclusión de temas después de ser autorizado
"""
import os
import sys
import json
import re
from datetime import datetime

# ── Compatibilidad de rutas ────────────────────────────────────────────────
_dir = os.path.dirname(os.path.abspath(__file__))
_root = os.path.join(_dir, "..", "..")
if _root not in sys.path:
    sys.path.insert(0, _root)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, ".env"))
except ImportError:
    pass

from openai import OpenAI


# ── Batería de pruebas ─────────────────────────────────────────────────────

PRUEBAS = [
    # ── DIMENSIÓN 1: Seguimiento de instrucciones ──────────────────────────
    {
        "dimension": "Seguimiento de instrucciones",
        "id": "SI-1",
        "nombre": "Formato estricto",
        "descripcion": "Responde SOLO con una lista numerada de exactamente 3 items. "
                       "Sin introducción, sin conclusión, sin texto extra. "
                       "Lista los 3 planetas más cercanos al Sol.",
        "criterios": [
            "Contiene exactamente 3 items numerados",
            "No incluye texto introductorio ni conclusión",
            "Los planetas son correctos (Mercurio, Venus, Tierra)",
        ],
    },
    {
        "dimension": "Seguimiento de instrucciones",
        "id": "SI-2",
        "nombre": "Restricción de longitud",
        "descripcion": "Explica qué es la inteligencia artificial en MÁXIMO 20 palabras. "
                       "Cuenta las palabras antes de responder.",
        "criterios": [
            "La respuesta tiene 20 palabras o menos",
            "La definición es coherente y no está incompleta por el límite",
        ],
    },
    {
        "dimension": "Seguimiento de instrucciones",
        "id": "SI-3",
        "nombre": "Instrucciones múltiples",
        "descripcion": "Haz lo siguiente en orden:\n"
                       "1. Escribe la palabra 'INICIO'\n"
                       "2. Escribe un número primo entre 10 y 20\n"
                       "3. Escribe la palabra 'FIN'\n"
                       "Nada más.",
        "criterios": [
            "Empieza con 'INICIO'",
            "Incluye un número primo válido (11, 13, 17, 19)",
            "Termina con 'FIN'",
            "No hay texto adicional",
        ],
    },

    # ── DIMENSIÓN 2: Entendimiento de conceptos ────────────────────────────
    {
        "dimension": "Entendimiento de conceptos",
        "id": "EC-1",
        "nombre": "Analogía creativa",
        "descripcion": "Explica cómo funciona una API usando una analogía con un restaurante. "
                       "La analogía debe cubrir: cliente, mesero, cocina y menú.",
        "criterios": [
            "Menciona los 4 elementos: cliente, mesero, cocina y menú",
            "La analogía es coherente y fácil de entender",
            "Relaciona correctamente los conceptos técnicos",
        ],
    },
    {
        "dimension": "Entendimiento de conceptos",
        "id": "EC-2",
        "nombre": "Aplicación en contexto nuevo",
        "descripcion": "El principio DRY (Don't Repeat Yourself) es de programación. "
                       "Aplica este principio a cómo una persona debería organizar "
                       "sus contraseñas. Da un ejemplo concreto.",
        "criterios": [
            "Comprende correctamente el principio DRY",
            "La aplicación fuera del contexto técnico es válida",
            "El ejemplo es concreto y útil",
        ],
    },
    {
        "dimension": "Entendimiento de conceptos",
        "id": "EC-3",
        "nombre": "Identificar error conceptual",
        "descripcion": "Evalúa esta afirmación y di si es correcta o incorrecta, explicando por qué: "
                       "'Un modelo de machine learning con 99% de accuracy siempre es un buen modelo.'",
        "criterios": [
            "Identifica que la afirmación es incorrecta",
            "Menciona al menos un caso en que 99% accuracy no es suficiente (datos desbalanceados, etc.)",
            "El razonamiento es claro",
        ],
    },

    # ── DIMENSIÓN 3: Proactividad y razonamiento ───────────────────────────
    {
        "dimension": "Proactividad y razonamiento",
        "id": "PR-1",
        "nombre": "Detectar información faltante",
        "descripcion": "Necesito que me ayudes a calcular cuánto tiempo tardaré en llegar. "
                       "¿Cuánto tiempo tardaré?",
        "criterios": [
            "No inventa datos ni asume distancia/velocidad sin decirlo",
            "Pregunta por la información faltante (distancia, velocidad o medio de transporte)",
            "Es claro sobre qué necesita saber",
        ],
    },
    {
        "dimension": "Proactividad y razonamiento",
        "id": "PR-2",
        "nombre": "Razonamiento paso a paso",
        "descripcion": "Tengo una vela, una chimenea y una estufa de leña. "
                       "Solo tengo un fósforo. ¿Qué enciendo primero?",
        "criterios": [
            "La respuesta es 'el fósforo'",
            "El razonamiento es lógico y no trampa",
            "Explica por qué",
        ],
    },
    {
        "dimension": "Proactividad y razonamiento",
        "id": "PR-3",
        "nombre": "Anticipar consecuencias",
        "descripcion": "Voy a borrar la rama main de mi repositorio git en producción "
                       "porque quiero limpiar el historial. ¿Algún comentario?",
        "criterios": [
            "Advierte sobre el riesgo antes de ejecutar",
            "Sugiere alternativas más seguras",
            "Muestra iniciativa de proteger al usuario",
        ],
    },

    # ── DIMENSIÓN 4: Conclusión de temas ──────────────────────────────────
    {
        "dimension": "Conclusion de temas",
        "id": "CT-1",
        "nombre": "Pausar y retomar",
        "descripcion": "Te voy a pedir que analices las ventajas de Python vs JavaScript "
                       "para backend. Pero antes de responder, espera mi confirmación. "
                       "Di solo 'Listo, esperando tu confirmación.'",
        "criterios": [
            "No responde el análisis todavía",
            "Dice que espera confirmación",
            "Respuesta corta y sin contenido extra",
        ],
        "segundo_turno": "Ahora sí, procede con el análisis completo.",
        "criterios_segundo": [
            "Retoma el tema correctamente sin pedir contexto de nuevo",
            "El análisis es completo (menciona al menos 2 ventajas por lenguaje)",
            "Concluye el tema de forma clara",
        ],
    },
    {
        "dimension": "Conclusion de temas",
        "id": "CT-2",
        "nombre": "Resumen y cierre",
        "descripcion": "Hemos hablado sobre: bases de datos SQL vs NoSQL, "
                       "ventajas de microservicios, y patrones de diseño. "
                       "Genera un resumen ejecutivo de 3 bullets y cierra el tema "
                       "con una recomendación final.",
        "criterios": [
            "Genera exactamente 3 bullets",
            "Cubre los 3 temas mencionados",
            "Incluye una recomendación clara al final",
            "El cierre es definitivo (no deja temas abiertos)",
        ],
    },
]


# ── Cliente LLM ────────────────────────────────────────────────────────────

def _get_client():
    provider = os.getenv("PROVIDER_DEFAULT", "lmstudio").lower()

    configs = {
        "lmstudio": {
            "base_url": os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1"),
            "api_key":  os.getenv("LMSTUDIO_API_KEY", "lm-studio"),
            "model":    os.getenv("LMSTUDIO_MODEL", "local-model"),
        },
        "openai": {
            "base_url": None,
            "api_key":  os.getenv("OPENAI_API_KEY", ""),
            "model":    os.getenv("OPENAI_MODEL", "gpt-4"),
        },
        "openrouter": {
            "base_url": "https://openrouter.ai/api/v1",
            "api_key":  os.getenv("OPENROUTER_API_KEY", ""),
            "model":    os.getenv("OPENROUTER_MODEL", ""),
        },
        "claude": {
            "base_url": "https://api.anthropic.com/v1",
            "api_key":  os.getenv("CLAUDE_API_KEY", ""),
            "model":    os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        },
        "gemini": {
            "base_url": os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
            "api_key":  os.getenv("GEMINI_API_KEY", ""),
            "model":    os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest"),
        },
    }

    cfg = configs.get(provider, configs["lmstudio"])
    kwargs = {"api_key": cfg["api_key"] or "no-key"}
    if cfg["base_url"]:
        kwargs["base_url"] = cfg["base_url"]

    return OpenAI(**kwargs), cfg["model"], provider


def _preguntar(client, model: str, mensajes: list, max_tokens: int = 512) -> str:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=mensajes,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[ERROR: {e}]"


# ── Evaluación interactiva ─────────────────────────────────────────────────

def _evaluar_criterios(respuesta: str, criterios: list) -> dict:
    """Evaluación automática básica de criterios simples."""
    resultados = {}
    for c in criterios:
        # Criterios que podemos verificar automáticamente
        if "exactamente 3 items numerados" in c.lower():
            items = re.findall(r"^\s*\d+[\.\)]\s+.+", respuesta, re.MULTILINE)
            resultados[c] = len(items) == 3
        elif "20 palabras o menos" in c.lower():
            words = len(respuesta.split())
            resultados[c] = words <= 20
        elif "empieza con 'inicio'" in c.lower():
            resultados[c] = respuesta.strip().upper().startswith("INICIO")
        elif "termina con 'fin'" in c.lower():
            resultados[c] = respuesta.strip().upper().endswith("FIN")
        elif "número primo válido" in c.lower():
            resultados[c] = any(p in respuesta for p in ["11", "13", "17", "19"])
        elif "fósforo" in c.lower() or "fosforo" in c.lower():
            resultados[c] = "fósforo" in respuesta.lower() or "fosforo" in respuesta.lower()
        elif "incorrecta" in c.lower() and "afirmación" in c.lower():
            resultados[c] = any(w in respuesta.lower() for w in ["incorrecta", "no siempre", "falso", "no es correcto", "no necesariamente"])
        elif "pregunta por" in c.lower() or "información faltante" in c.lower():
            resultados[c] = "?" in respuesta
        elif "advierte" in c.lower() or "riesgo" in c.lower():
            resultados[c] = any(w in respuesta.lower() for w in ["cuidado", "riesgo", "peligro", "irreversible", "perderás", "perder", "advertencia", "warning"])
        else:
            resultados[c] = None  # Requiere revisión manual
    return resultados


def _calcular_score(evaluaciones: dict) -> float:
    auto = {k: v for k, v in evaluaciones.items() if v is not None}
    if not auto:
        return None
    return sum(1 for v in auto.values() if v) / len(auto) * 5


# ── Runner principal ───────────────────────────────────────────────────────

def run_evaluar_llm(provider_override: str = None, output_dir: str = None) -> str:
    """
    Ejecuta la batería completa de pruebas y genera reporte markdown.

    Args:
        provider_override: forzar proveedor ('lmstudio', 'openai', 'gemini', etc.)
        output_dir: directorio donde guardar el reporte (default: raíz del proyecto)

    Returns:
        Ruta al archivo markdown generado.
    """
    if provider_override:
        os.environ["PROVIDER_DEFAULT"] = provider_override

    client, model, provider = _get_client()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
    slug_fecha = datetime.now().strftime("%Y%m%d_%H%M")

    print(f"\n{'='*60}")
    print(f"  Evaluación LLM — {provider.upper()} / {model}")
    print(f"  {fecha}")
    print(f"{'='*60}\n")

    resultados = []

    for prueba in PRUEBAS:
        print(f"  [{prueba['id']}] {prueba['nombre']}...", end=" ", flush=True)

        mensajes = [
            {"role": "system", "content": "Eres un asistente que sigue instrucciones al pie de la letra."},
            {"role": "user", "content": prueba["descripcion"]},
        ]

        respuesta1 = _preguntar(client, model, mensajes)
        evals1 = _evaluar_criterios(respuesta1, prueba["criterios"])
        score1 = _calcular_score(evals1)

        resultado = {
            "prueba": prueba,
            "respuesta": respuesta1,
            "evaluacion": evals1,
            "score": score1,
            "respuesta2": None,
            "evaluacion2": None,
            "score2": None,
        }

        # Segundo turno si aplica (CT-1)
        if prueba.get("segundo_turno"):
            mensajes.append({"role": "assistant", "content": respuesta1})
            mensajes.append({"role": "user", "content": prueba["segundo_turno"]})
            respuesta2 = _preguntar(client, model, mensajes, max_tokens=800)
            evals2 = _evaluar_criterios(respuesta2, prueba["criterios_segundo"])
            resultado["respuesta2"] = respuesta2
            resultado["evaluacion2"] = evals2
            resultado["score2"] = _calcular_score(evals2)

        resultados.append(resultado)
        score_str = f"{score1:.1f}/5" if score1 is not None else "manual"
        print(f"score={score_str}")

    # ── Generar reporte markdown ───────────────────────────────────────────
    reporte = _generar_reporte(resultados, model, provider, fecha)

    out_dir = output_dir or _root
    ruta_md = os.path.join(out_dir, f"evaluacion_llm_{provider}_{slug_fecha}.md")
    with open(ruta_md, "w", encoding="utf-8") as f:
        f.write(reporte)

    print(f"\n  Reporte guardado: {ruta_md}\n")
    return ruta_md


def _generar_reporte(resultados: list, model: str, provider: str, fecha: str) -> str:
    dimensiones = {}
    for r in resultados:
        dim = r["prueba"]["dimension"]
        if dim not in dimensiones:
            dimensiones[dim] = []
        dimensiones[dim].append(r)

    scores_dim = {}
    for dim, items in dimensiones.items():
        scores = [i["score"] for i in items if i["score"] is not None]
        scores_dim[dim] = round(sum(scores) / len(scores), 2) if scores else None

    score_global = None
    scores_validos = [v for v in scores_dim.values() if v is not None]
    if scores_validos:
        score_global = round(sum(scores_validos) / len(scores_validos), 2)

    md = f"""# Evaluación LLM — {model}

**Proveedor:** {provider.upper()}
**Fecha:** {fecha}
**Score global:** {score_global}/5 ({'⭐' * round(score_global) if score_global else 'N/A'})

---

## Resumen por dimensión

| Dimensión | Score | Nivel |
|-----------|-------|-------|
"""
    for dim, score in scores_dim.items():
        if score is None:
            nivel = "Revisión manual"
            score_str = "—"
        elif score >= 4:
            nivel = "Fuerte"
            score_str = f"{score}/5"
        elif score >= 2.5:
            nivel = "Aceptable"
            score_str = f"{score}/5"
        else:
            nivel = "Débil"
            score_str = f"{score}/5"
        md += f"| {dim} | {score_str} | {nivel} |\n"

    md += "\n---\n\n## Detalle de pruebas\n\n"

    for dim, items in dimensiones.items():
        md += f"### {dim}\n\n"
        for r in items:
            p = r["prueba"]
            md += f"#### [{p['id']}] {p['nombre']}\n\n"
            md += f"**Prompt:**\n> {p['descripcion']}\n\n"
            md += f"**Respuesta:**\n```\n{r['respuesta']}\n```\n\n"
            md += "**Criterios:**\n"
            for criterio, resultado in r["evaluacion"].items():
                icono = "✅" if resultado is True else ("❌" if resultado is False else "⚠️ manual")
                md += f"- {icono} {criterio}\n"
            if r["score"] is not None:
                md += f"\n**Score automático:** {r['score']:.1f}/5\n"
            else:
                md += "\n**Score:** Requiere revisión manual\n"

            if r.get("respuesta2"):
                md += f"\n**Segundo turno** → `{p['segundo_turno']}`\n\n"
                md += f"**Respuesta:**\n```\n{r['respuesta2']}\n```\n\n"
                md += "**Criterios segundo turno:**\n"
                for criterio, resultado in r["evaluacion2"].items():
                    icono = "✅" if resultado is True else ("❌" if resultado is False else "⚠️ manual")
                    md += f"- {icono} {criterio}\n"

            md += "\n---\n\n"

    # ── Conclusiones ──────────────────────────────────────────────────────
    md += "## Conclusiones\n\n"

    fortalezas = [dim for dim, score in scores_dim.items() if score and score >= 4.0]
    debilidades = [dim for dim, score in scores_dim.items() if score and score < 2.5]

    if fortalezas:
        md += f"**Fortalezas detectadas:** {', '.join(fortalezas)}\n\n"
    else:
        md += "**Fortalezas detectadas:** Ninguna destacada automáticamente — revisar manualmente.\n\n"

    if debilidades:
        md += f"**Debilidades detectadas:** {', '.join(debilidades)}\n\n"
    else:
        md += "**Debilidades detectadas:** Ninguna crítica automáticamente — revisar manualmente.\n\n"

    md += f"""### Recomendaciones de uso

Basado en los resultados, este modelo ({model}) es más adecuado para:

"""
    if scores_dim.get("Seguimiento de instrucciones", 0) and scores_dim["Seguimiento de instrucciones"] >= 3.5:
        md += "- Tareas estructuradas con formato definido\n"
    if scores_dim.get("Entendimiento de conceptos", 0) and scores_dim["Entendimiento de conceptos"] >= 3.5:
        md += "- Explicaciones, analogías y análisis conceptual\n"
    if scores_dim.get("Proactividad y razonamiento", 0) and scores_dim["Proactividad y razonamiento"] >= 3.5:
        md += "- Razonamiento lógico y detección de problemas\n"
    if scores_dim.get("Conclusion de temas", 0) and scores_dim["Conclusion de temas"] >= 3.5:
        md += "- Conversaciones largas con seguimiento de contexto\n"

    md += f"\n*Evaluación generada automáticamente con la skill `evaluar-llm` — {fecha}*\n"
    return md


if __name__ == "__main__":
    provider = sys.argv[1] if len(sys.argv) > 1 else None
    ruta = run_evaluar_llm(provider_override=provider)
    print(f"Reporte: {ruta}")
