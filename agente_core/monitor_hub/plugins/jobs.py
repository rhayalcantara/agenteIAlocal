"""Plugin Jobs — tail incremental de logs/jobs/events.log del job_manager.

Cada línea en events.log es un evento standard:
    <ts> JOB|<evento>|<id>|<name>|<estado>|<k=v>|<k=v>...

Este plugin:
  1. En connect() lee el offset persistido (para no reportar eventos viejos al
     reiniciar el monitor_hub).
  2. En poll() lee líneas nuevas desde el offset y las convierte en Message.
  3. Marca como `priority=urgent` los eventos `failed` y `cancelled` para que
     el dispatcher del hub los pueda destacar.

No filtra eventos por tipo: emite todos. Si quieres silenciar `submitted` o
`step_started`, ajusta `events_filter` en el config:
    "events_filter": ["done", "failed", "cancelled"]
"""
import os
import re
from datetime import datetime
from .base import ChannelPlugin
from ..message import Message

_LINEA_RE = re.compile(
    r"^(?P<ts>\S+)\s+JOB\|(?P<evento>\w+)\|(?P<id>[^|]+)\|(?P<name>[^|]+)\|(?P<estado>[^|]+)(?:\|(?P<extra>.*))?$"
)
_URGENT_EVENTS = {"failed", "cancelled", "step_failed"}


class JobsPlugin(ChannelPlugin):
    name = "jobs"
    poll_interval = 3

    def __init__(self, config: dict = None):
        super().__init__(config)
        # Raíz del proyecto: 4 niveles arriba de plugins/jobs.py
        self._root = self.config.get(
            "project_root",
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))))),
        )
        self._events_file = os.path.join(self._root, "agente_core", "logs", "jobs", "events.log")
        self._offset_file = os.path.join(self._root, "agente_core", "logs", "jobs", ".monitor_offset")
        self._offset = 0
        # Filtro opcional de eventos (lista de eventos a emitir; vacío = todos)
        self._events_filter = set(self.config.get("events_filter", []))

    def connect(self) -> bool:
        # Crear el archivo si no existe (evita que el primer poll falle)
        os.makedirs(os.path.dirname(self._events_file), exist_ok=True)
        if not os.path.exists(self._events_file):
            try:
                open(self._events_file, "a", encoding="utf-8").close()
            except Exception:
                return False
        # Cargar offset persistido (líneas ya emitidas)
        if os.path.exists(self._offset_file):
            try:
                with open(self._offset_file, "r", encoding="utf-8") as f:
                    self._offset = int(f.read().strip() or "0")
            except Exception:
                self._offset = 0
        else:
            # Primera vez: arrancar al final del archivo (no spamear histórico)
            try:
                with open(self._events_file, "r", encoding="utf-8") as f:
                    self._offset = sum(1 for _ in f)
                self._guardar_offset()
            except Exception:
                self._offset = 0
        return True

    def poll(self) -> list:
        if not os.path.exists(self._events_file):
            return []
        try:
            with open(self._events_file, "r", encoding="utf-8") as f:
                todas = f.readlines()
        except Exception:
            return []
        nuevas = todas[self._offset:]
        if not nuevas:
            return []

        mensajes = []
        for linea in nuevas:
            linea = linea.rstrip("\n")
            m = _LINEA_RE.match(linea)
            if not m:
                continue
            evento = m.group("evento")
            if self._events_filter and evento not in self._events_filter:
                continue
            extra_str = (m.group("extra") or "").strip()
            extra_dict = self._parse_extra(extra_str)

            # Construir el texto legible
            partes = [f"[{evento}]"]
            if extra_dict.get("step"):
                partes.append(f"step={extra_dict['step']}")
            if "exit" in extra_dict:
                partes.append(f"exit={extra_dict['exit']}")
            if "err" in extra_dict:
                partes.append(f"err={extra_dict['err']}")
            if "dur" in extra_dict:
                partes.append(f"dur={extra_dict['dur']}")
            if "steps" in extra_dict:
                partes.append(f"steps={extra_dict['steps']}")
            text = " ".join(partes)

            try:
                ts = datetime.strptime(m.group("ts"), "%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                ts = datetime.now()

            prio = "urgent" if evento in _URGENT_EVENTS else "normal"
            mensajes.append(Message(
                channel="jobs",
                chat_id=m.group("id"),
                chat_name=m.group("name"),
                user="job_manager",
                text=text,
                timestamp=ts,
                type="event",
                priority=prio,
                raw={"evento": evento, "estado": m.group("estado"), **extra_dict},
            ))
        # Avanzar offset y persistir
        self._offset += len(nuevas)
        self._guardar_offset()
        return mensajes

    def _parse_extra(self, extra: str) -> dict:
        d = {}
        for parte in extra.split("|"):
            if "=" in parte:
                k, _, v = parte.partition("=")
                d[k.strip()] = v.strip()
        return d

    def _guardar_offset(self):
        try:
            with open(self._offset_file, "w", encoding="utf-8") as f:
                f.write(str(self._offset))
        except Exception:
            pass

    def disconnect(self):
        self._guardar_offset()
