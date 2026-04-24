"""Cargador de skills desde el directorio skills/."""
import os
import subprocess
from logger import get_logger

logger = get_logger("skill_loader")

SKILL_FILENAME = "SKILL.md"


class SkillLoader:
    def __init__(self, skills_dir: str = None):
        if skills_dir is None:
            _core = os.path.dirname(os.path.abspath(__file__))
            skills_dir = os.path.join(os.path.dirname(_core), "skills")
        self.skills_dir = skills_dir
        self.skills = {}
        self._cargar()

    def _cargar(self):
        if not os.path.isdir(self.skills_dir):
            logger.warning(f"Directorio de skills no encontrado: {self.skills_dir}")
            return
        for nombre in os.listdir(self.skills_dir):
            skill_path = os.path.join(self.skills_dir, nombre)
            skill_md = os.path.join(skill_path, SKILL_FILENAME)
            if os.path.isdir(skill_path) and os.path.exists(skill_md):
                try:
                    with open(skill_md, "r", encoding="utf-8") as f:
                        contenido = f.read()
                    # Buscar scripts .py en la carpeta
                    scripts = [
                        f for f in os.listdir(skill_path)
                        if f.endswith(".py")
                    ]
                    self.skills[nombre] = {
                        "name": nombre,
                        "path": skill_path,
                        "contenido": contenido,
                        "scripts": scripts,
                        "description": self._extraer_descripcion(contenido),
                    }
                    logger.info(f"Skill cargada: {nombre} ({len(scripts)} scripts)")
                except Exception as e:
                    logger.warning(f"Error cargando skill {nombre}: {e}")

    def _extraer_descripcion(self, contenido: str) -> str:
        for line in contenido.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line[:120]
        return ""

    def listar(self) -> list:
        return [
            {"name": n, "description": s["description"], "scripts": s["scripts"]}
            for n, s in self.skills.items()
        ]

    def obtener_skill(self, nombre: str) -> dict:
        return self.skills.get(nombre)

    def obtener_cuerpo(self, nombre: str) -> str:
        skill = self.skills.get(nombre)
        return skill["contenido"] if skill else None

    def ejecutar_script(self, nombre: str, script: str, args: str = "") -> str:
        import sys
        import shlex
        skill = self.skills.get(nombre)
        if not skill:
            return f"Error: skill '{nombre}' no encontrada."
        script_path = os.path.join(skill["path"], script)
        if not os.path.exists(script_path):
            return f"Error: script '{script}' no encontrado en skill '{nombre}'."
        try:
            cmd = [sys.executable, script_path] + (shlex.split(args) if args else [])
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    encoding="utf-8", errors="replace", timeout=60)
            output = result.stdout + result.stderr
            return output[:4000] or "(sin salida)"
        except subprocess.TimeoutExpired:
            return "Error: script excedió el timeout de 60s."
        except Exception as e:
            return f"Error ejecutando script: {e}"

    def recargar(self):
        """Recarga todas las skills desde disco (hot-reload sin reiniciar)."""
        self.skills = {}
        self._cargar()
        logger.info(f"Skills recargadas: {list(self.skills.keys())}")

    def crear_skill(self, nombre: str, instrucciones: str,
                    script_nombre: str = None, script_code: str = None) -> str:
        """Crea una nueva skill en disco y la carga de inmediato (hot-reload).

        Args:
            nombre: identificador de la skill (slug, ej: 'youtube-downloader')
            instrucciones: contenido del SKILL.md
            script_nombre: nombre del archivo .py opcional (ej: 'run.py')
            script_code: código Python del script opcional

        Returns:
            Mensaje de éxito o error.
        """
        if not nombre or not nombre.strip():
            return "Error: el nombre de la skill no puede estar vacío."

        nombre = nombre.strip().lower().replace(" ", "-")
        skill_path = os.path.join(self.skills_dir, nombre)

        try:
            os.makedirs(skill_path, exist_ok=True)

            # Escribir SKILL.md
            skill_md_path = os.path.join(skill_path, SKILL_FILENAME)
            with open(skill_md_path, "w", encoding="utf-8") as f:
                f.write(instrucciones)

            # Escribir script opcional
            if script_nombre and script_code:
                if not script_nombre.endswith(".py"):
                    script_nombre += ".py"
                script_path = os.path.join(skill_path, script_nombre)
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(script_code)

            # Hot-reload
            self.recargar()

            scripts_info = f" + script {script_nombre}" if script_nombre else ""
            return f"✅ Skill '{nombre}' creada{scripts_info} y cargada. Total skills: {len(self.skills)}"

        except Exception as e:
            logger.error(f"Error creando skill '{nombre}': {e}")
            return f"Error creando skill '{nombre}': {e}"

    def generar_resumen_para_prompt(self) -> str:
        if not self.skills:
            return ""
        lineas = ["## Skills disponibles"]
        for n, s in self.skills.items():
            lineas.append(f"- **{n}**: {s['description'][:80]}")
        return "\n".join(lineas)
