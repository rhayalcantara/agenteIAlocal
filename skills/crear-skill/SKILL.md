# Skill: Crear Skill

Esta skill genera automáticamente la estructura base de una nueva skill: crea la carpeta, el archivo `SKILL.md` con documentación y el archivo `run.py` con la función principal lista para implementar.

## Uso
Para usar la skill, pide algo como:
- "crea una skill para consultar el clima"
- "crear skill llamada buscar-empleado"
- "genera la estructura de una skill nueva"

## Lo que hace
1. Convierte el nombre dado a un slug kebab-case válido (ej: `buscar-clima`).
2. Crea la carpeta `skills/<nombre>/`.
3. Genera `SKILL.md` con la documentación de la interfaz.
4. Genera `run.py` con la función `run_<nombre>()` lista para implementar.

## Interfaz

### Desde Python
```python
from skills.crear_skill.run import crear_skill

# Solo nombre
resultado = crear_skill("consultar-empleados")

# Con descripción y ejemplo
resultado = crear_skill(
    nombre="consultar-empleados",
    descripcion="Consulta la base de datos de empleados por nombre o ID.",
    ejemplo_uso="busca el empleado Juan Pérez"
)
```

### Desde CLI
```bash
python skills/crear-skill/run.py <nombre> [descripcion] [ejemplo_uso]

# Ejemplos:
python skills/crear-skill/run.py "consultar-clima"
python skills/crear-skill/run.py "consultar-clima" "Obtiene el clima actual" "dime el clima de hoy"
```

## Parámetros
| Parámetro    | Tipo | Requerido | Descripción |
|--------------|------|-----------|-------------|
| `nombre`     | str  | Sí        | Nombre de la skill. Se convierte a kebab-case automáticamente. |
| `descripcion`| str  | No        | Descripción breve de lo que hace la skill. |
| `ejemplo_uso`| str  | No        | Frase de ejemplo para activar la skill. |

## Retorna
- `str` con la ruta creada y los archivos generados, o mensaje de error.

## Notas
- Si ya existe una skill con ese nombre, retorna error sin sobreescribir.
- Los acentos y caracteres especiales se normalizan automáticamente en el slug.
