"""WikiManager — Base de conocimiento persistente en markdown."""
import os
import re
from datetime import datetime
from logger import get_logger

logger = get_logger("wiki_manager")
SECCIONES = ("personas", "proyectos", "conceptos", "sintesis")


class WikiManager:
    def __init__(self, wiki_dir: str = None):
        if wiki_dir is None:
            _core = os.path.dirname(os.path.abspath(__file__))
            wiki_dir = os.path.join(os.path.dirname(_core), "wiki")
        self.wiki_dir = wiki_dir
        self._inicializar()

    def _inicializar(self):
        os.makedirs(self.wiki_dir, exist_ok=True)
        for s in SECCIONES:
            os.makedirs(os.path.join(self.wiki_dir, s), exist_ok=True)
        for nombre, plantilla in [("index.md", _PLANTILLA_INDEX), ("log.md", _PLANTILLA_LOG)]:
            ruta = os.path.join(self.wiki_dir, nombre)
            if not os.path.exists(ruta):
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(plantilla)

    def leer(self, pagina: str) -> str:
        ruta = self._resolver_ruta(pagina)
        if not os.path.exists(ruta):
            sugerencias = self._paginas_cercanas(pagina)
            msg = f"[wiki] Página no encontrada: {pagina}"
            if sugerencias:
                msg += f"\nSimilares: {', '.join(sugerencias)}"
            return msg
        try:
            with open(ruta, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"[wiki] Error leyendo: {e}"

    def listar(self) -> str:
        return self.leer("index")

    def buscar(self, query: str) -> str:
        terminos = [t.lower() for t in query.split() if len(t) > 2]
        resultados = []
        index_path = os.path.join(self.wiki_dir, "index.md")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                for linea in f:
                    if any(t in linea.lower() for t in terminos):
                        resultados.append(linea.rstrip())
        for seccion in SECCIONES:
            seccion_dir = os.path.join(self.wiki_dir, seccion)
            if os.path.isdir(seccion_dir):
                for nombre in os.listdir(seccion_dir):
                    if nombre.endswith(".md") and any(t in nombre.lower() for t in terminos):
                        ruta_rel = f"{seccion}/{nombre[:-3]}"
                        if not any(ruta_rel in r for r in resultados):
                            resultados.append(f"- [[{ruta_rel}]]")
        if not resultados:
            return f"[wiki] Sin resultados para: {query!r}"
        return f"## Búsqueda: {query!r}\n\n" + "\n".join(resultados)

    def escribir(self, pagina: str, contenido: str) -> str:
        ruta = self._resolver_ruta(pagina)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        es_nueva = not os.path.exists(ruta)
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                f.write(contenido)
            accion = "creada" if es_nueva else "actualizada"
            self._log(f"write | {pagina} — {accion}")
            return f"[wiki] Página {pagina!r} {accion}."
        except Exception as e:
            return f"[wiki] Error escribiendo: {e}"

    def actualizar_index(self, pagina: str, resumen: str) -> str:
        index_path = os.path.join(self.wiki_dir, "index.md")
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                contenido = f.read()
            nueva_linea = f"- [[{pagina}]] — {resumen}"
            patron = re.compile(rf"^- \[\[{re.escape(pagina)}\]\].*$", re.MULTILINE)
            if patron.search(contenido):
                contenido = patron.sub(nueva_linea, contenido)
            else:
                seccion = pagina.split("/")[0] if "/" in pagina else "otros"
                header = f"### {seccion.capitalize()}"
                if header in contenido:
                    contenido = contenido.replace(header + "\n", header + "\n" + nueva_linea + "\n")
                else:
                    contenido = contenido.rstrip() + f"\n\n{header}\n{nueva_linea}\n"
            with open(index_path, "w", encoding="utf-8") as f:
                f.write(contenido)
            return f"[wiki] Índice actualizado: {pagina!r}"
        except Exception as e:
            return f"[wiki] Error actualizando índice: {e}"

    def _log(self, descripcion: str):
        log_path = os.path.join(self.wiki_dir, "log.md")
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n## [{ts}] {descripcion}\n")
        except Exception:
            pass

    def log_actividad(self, tipo: str, descripcion: str):
        self._log(f"{tipo} | {descripcion}")

    def _resolver_ruta(self, pagina: str) -> str:
        if pagina.endswith(".md"):
            pagina = pagina[:-3]
        return os.path.join(self.wiki_dir, pagina.replace("\\", "/") + ".md")

    def _paginas_cercanas(self, pagina: str) -> list:
        nombre = os.path.basename(pagina).lower()
        similares = []
        for entry in os.listdir(self.wiki_dir):
            seccion_dir = os.path.join(self.wiki_dir, entry)
            if os.path.isdir(seccion_dir):
                for archivo in os.listdir(seccion_dir):
                    if archivo.endswith(".md") and nombre in archivo.lower():
                        similares.append(f"{entry}/{archivo[:-3]}")
        return similares[:5]

    def estadisticas(self) -> dict:
        paginas = []
        # Contar archivos .md en la raiz de la wiki
        for f in os.listdir(self.wiki_dir):
            if f.endswith(".md"):
                paginas.append(f[:-3])
        # Contar archivos .md en TODAS las subcarpetas (no solo SECCIONES)
        for entry in os.listdir(self.wiki_dir):
            d = os.path.join(self.wiki_dir, entry)
            if os.path.isdir(d):
                for f in os.listdir(d):
                    if f.endswith(".md"):
                        paginas.append(f"{entry}/{f[:-3]}")
        return {"total_paginas": len(paginas), "wiki_dir": self.wiki_dir}


_PLANTILLA_INDEX = """\
# Wiki — Índice

### Personas

### Proyectos

### Conceptos

### Sintesis

---
*Mantenido por el Agente IA*
"""

_PLANTILLA_LOG = """\
# Wiki — Log de Actividad
Formato: `## [YYYY-MM-DD HH:MM] tipo | descripción`

---
"""
