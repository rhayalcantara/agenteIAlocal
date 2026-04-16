"""Implementación de herramientas disponibles para el agente."""
import os
import subprocess
from bash_terminal import BashTerminal
from logger import get_logger

logger = get_logger("tools")


class Tool:
    def __init__(self):
        self.terminal = BashTerminal()

    # ── Bash persistente ──────────────────────────────────────────────────────

    def execute_bash(self, command: str, timeout: float = 600) -> str:
        """Ejecuta un comando en la terminal bash persistente con filtro de seguridad."""
        logger.info(f"execute_bash: {command[:100]}")
        print(f"=== Terminal Bash ===\n$ {command}")
        resultado = self.terminal.ejecutar(command, timeout=timeout)
        print(resultado)
        return resultado

    def cerrar_terminal(self):
        self.terminal.cerrar()

    # ── Comandos simples ──────────────────────────────────────────────────────

    def execute_command(self, command: str) -> str:
        """Ejecuta un comando simple (no persistente). También aplica filtro de seguridad."""
        from bash_terminal import es_comando_peligroso
        peligroso, razon = es_comando_peligroso(command)
        if peligroso:
            msg = f"🚫 COMANDO BLOQUEADO: {razon}"
            logger.warning(msg)
            return msg

        logger.info(f"execute_command: {command[:100]}")
        try:
            result = subprocess.run(
                command, shell=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=60,
            )
            output = result.stdout
            print("=== Salida ===\n" + output)
            return output
        except subprocess.TimeoutExpired:
            return "Error: Timeout de 60s excedido."
        except Exception as e:
            return f"Error: {e}"

    # ── Archivos ──────────────────────────────────────────────────────────────

    def read_file(self, path: str, encodings: str = "utf-8") -> str:
        logger.info(f"read_file: {path}")
        print(f"   ReadFile: {path}")
        try:
            with open(path, "r", encoding=encodings) as f:
                content = f.read()
            print(f"✓  ReadFile: {path}")
            return content
        except Exception as e:
            logger.error(f"Error leyendo {path}: {e}")
            return str(e)

    def edit_file(self, path: str, new_text: str, prev_text: str = "") -> str:
        logger.info(f"edit_file: {path}")
        try:
            if not os.path.exists(path):
                print(f"   Add File: {path}")
                dir_path = os.path.dirname(path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(new_text)
                print(f"✓  Added File: {path}")
                return "Archivo creado."
            print(f"   Edit File: {path}")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if prev_text and prev_text not in content:
                return "Texto a reemplazar no encontrado."
            updated = content.replace(prev_text, new_text) if prev_text else new_text
            with open(path, "w", encoding="utf-8") as f:
                f.write(updated)
            print(f"✓  Edited File: {path}")
            return "Archivo actualizado."
        except Exception as e:
            logger.error(f"Error editando {path}: {e}")
            return str(e)

    def list_files_in_dir(self, directory: str = ".") -> list:
        try:
            return sorted(os.listdir(directory))
        except Exception as e:
            return [str(e)]

    # ── Web ───────────────────────────────────────────────────────────────────

    def web_search(self, query: str, max_results: int = 5) -> str:
        """Busca en DuckDuckGo y retorna resultados."""
        logger.info(f"web_search: {query}")
        print(f"   🔍 Buscando: {query}")
        try:
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                resultados = list(ddgs.text(query, max_results=int(max_results)))
            if not resultados:
                return "No se encontraron resultados."
            salida = []
            for i, r in enumerate(resultados, 1):
                salida.append(
                    f"{i}. {r.get('title', 'Sin título')}\n"
                    f"   {r.get('href', '')}\n"
                    f"   {r.get('body', '')[:200]}"
                )
            return "\n\n".join(salida)
        except ImportError:
            return "Error: instala ddgs (pip install ddgs)"
        except Exception as e:
            logger.error(f"Error en búsqueda: {e}")
            return f"Error en búsqueda: {e}"
