import os
import sys
import re

SKILLS_ROOT = os.path.join(os.path.dirname(__file__), "..")

SKILL_MD_TEMPLATE = """\
# Skill: {title}

{descripcion}

## Uso
Para usar la skill, pide algo como:
- "{ejemplo_uso}"

## Lo que hace
1. [Describir paso 1]
2. [Describir paso 2]
3. [Describir paso 3]

## Interfaz

### Desde Python
```python
from skills.{nombre_python}.run import run_{nombre_funcion}

resultado = run_{nombre_funcion}()
```

### Desde CLI
```bash
python skills/{nombre}/run.py
```

## Parámetros
- *(sin parámetros por defecto — editar según necesidad)*

## Retorna
- `str` con el resultado o mensaje de error.
"""

RUN_PY_TEMPLATE = """\
import sys


def run_{nombre_funcion}():
    \"\"\"
    {descripcion}
    \"\"\"
    try:
        # TODO: implementar la lógica de la skill aquí
        return "Skill '{titulo}' ejecutada correctamente."
    except Exception as e:
        return f"Error en skill '{titulo}': {{e}}"


if __name__ == "__main__":
    print(run_{nombre_funcion}())
"""


def slugify(text: str) -> str:
    """Convierte texto a slug kebab-case válido para nombre de carpeta."""
    text = text.lower().strip()
    text = re.sub(r"[áàä]", "a", text)
    text = re.sub(r"[éèë]", "e", text)
    text = re.sub(r"[íìï]", "i", text)
    text = re.sub(r"[óòö]", "o", text)
    text = re.sub(r"[úùü]", "u", text)
    text = re.sub(r"[ñ]", "n", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def python_name(slug: str) -> str:
    """Convierte slug a nombre de módulo Python (snake_case)."""
    return slug.replace("-", "_")


def crear_skill(nombre: str, descripcion: str = "", ejemplo_uso: str = "") -> str:
    """
    Crea la estructura de una nueva skill con SKILL.md y run.py.

    Args:
        nombre:      Nombre de la skill (ej: "buscar-clima" o "Buscar Clima").
        descripcion: Descripción breve de lo que hace.
        ejemplo_uso: Frase de ejemplo para activarla.

    Returns:
        str con el resultado (ruta creada o error).
    """
    if not nombre or not nombre.strip():
        return "Error: el nombre de la skill no puede estar vacío."

    slug = slugify(nombre)
    if not slug:
        return f"Error: el nombre '{nombre}' no produce un slug válido."

    skill_dir = os.path.join(SKILLS_ROOT, slug)

    if os.path.exists(skill_dir):
        return f"Error: ya existe una skill con ese nombre en '{skill_dir}'."

    os.makedirs(skill_dir)

    nombre_python = python_name(slug)
    nombre_funcion = nombre_python
    title = nombre.title()
    descripcion = descripcion or f"Skill {title}: implementar descripción."
    ejemplo_uso = ejemplo_uso or f"ejecuta la skill {title}"

    skill_md = SKILL_MD_TEMPLATE.format(
        title=title,
        descripcion=descripcion,
        ejemplo_uso=ejemplo_uso,
        nombre_python=nombre_python,
        nombre_funcion=nombre_funcion,
        nombre=slug,
    )

    run_py = RUN_PY_TEMPLATE.format(
        nombre_funcion=nombre_funcion,
        descripcion=descripcion,
        titulo=title,
    )

    with open(os.path.join(skill_dir, "SKILL.md"), "w", encoding="utf-8") as f:
        f.write(skill_md)

    with open(os.path.join(skill_dir, "run.py"), "w", encoding="utf-8") as f:
        f.write(run_py)

    return (
        f"Skill '{slug}' creada correctamente en:\n"
        f"  {skill_dir}/\n"
        f"    ├── SKILL.md\n"
        f"    └── run.py\n\n"
        f"Edita run.py para implementar la lógica."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python run.py <nombre-skill> [descripcion] [ejemplo_de_uso]")
        print('Ejemplo: python run.py "consultar-clima" "Obtiene el clima actual" "dime el clima de hoy"')
        sys.exit(1)

    nombre = sys.argv[1]
    descripcion = sys.argv[2] if len(sys.argv) > 2 else ""
    ejemplo_uso = sys.argv[3] if len(sys.argv) > 3 else ""

    print(crear_skill(nombre, descripcion, ejemplo_uso))
