"""Memoria persistente a largo plazo basada en JSON."""
import os
import json
from datetime import datetime
from logger import get_logger

logger = get_logger("memoria")

CATEGORIAS_VALIDAS = {"preferencia", "proyecto", "hecho", "instruccion"}


class Memoria:
    def __init__(self, ruta: str = None):
        if ruta is None:
            _core = os.path.dirname(os.path.abspath(__file__))
            ruta = os.path.join(_core, "data", "memoria.json")
        self.ruta = ruta
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        self._datos = self._cargar()

    def _cargar(self) -> dict:
        if os.path.exists(self.ruta):
            try:
                with open(self.ruta, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error cargando memoria: {e}")
        return {"hechos": [], "resumenes": [], "siguiente_id": 1}

    def _guardar(self):
        try:
            with open(self.ruta, "w", encoding="utf-8") as f:
                json.dump(self._datos, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando memoria: {e}")

    def agregar_hecho(self, contenido: str, categoria: str) -> str:
        if categoria not in CATEGORIAS_VALIDAS:
            return f"Error: categoría '{categoria}' no válida. Usa: {', '.join(CATEGORIAS_VALIDAS)}"
        hecho = {
            "id": self._datos["siguiente_id"],
            "contenido": contenido,
            "categoria": categoria,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self._datos["hechos"].append(hecho)
        self._datos["siguiente_id"] += 1
        self._guardar()
        logger.info(f"Hecho guardado [{categoria}]: {contenido[:60]}")
        return f"Guardado: [{categoria}] {contenido[:60]}"

    def listar_hechos(self, categoria: str = None) -> list:
        hechos = self._datos.get("hechos", [])
        if categoria:
            hechos = [h for h in hechos if h.get("categoria") == categoria]
        return hechos

    def eliminar_hecho(self, hecho_id: int) -> bool:
        antes = len(self._datos["hechos"])
        self._datos["hechos"] = [h for h in self._datos["hechos"] if h["id"] != hecho_id]
        if len(self._datos["hechos"]) < antes:
            self._guardar()
            logger.info(f"Hecho #{hecho_id} eliminado")
            return True
        return False

    def agregar_resumen(self, texto: str):
        self._datos.setdefault("resumenes", []).append({
            "texto": texto,
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        # Mantener solo los últimos 10 resúmenes
        self._datos["resumenes"] = self._datos["resumenes"][-10:]
        self._guardar()

    def obtener_contexto(self) -> str:
        """Genera el bloque de contexto para inyectar en el system prompt."""
        partes = []
        hechos = self._datos.get("hechos", [])
        if hechos:
            lineas = [f"  [{h['categoria']}] {h['contenido']}" for h in hechos[-30:]]
            partes.append("## Memoria a largo plazo\n" + "\n".join(lineas))
        resumenes = self._datos.get("resumenes", [])
        if resumenes:
            ultimo = resumenes[-1]["texto"]
            partes.append(f"## Resumen de conversación anterior\n{ultimo}")
        return "\n\n".join(partes)
