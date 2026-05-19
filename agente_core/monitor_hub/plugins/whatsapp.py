"""Plugin WhatsApp para Monitor Hub.

Lee mensajes nuevos del archivo whatsapp_nuevos.json que genera
whatsapp_monitor.js (proceso Node.js persistente separado).

Modos:
  - spawn (default): el plugin lanza su propio whatsapp_monitor.js y lo lee.
  - consumer (auto o config): NO spawn; asume que algún otro proceso
    mantiene whatsapp_nuevos.json. Coexistencia segura con el monitor
    standalone que se arranca en el SessionStart hook.

Detección automática consumer-only:
  Si whatsapp_nuevos.json existe y su mtime es < freshness_threshold_sec
  (default 90s), asumimos que hay otro proceso activo escribiendo →
  modo consumer.

Override en config:
  {"mode": "consumer"}  → fuerza consumer-only
  {"mode": "spawn"}     → fuerza spawn (puede chocar con monitor standalone)
  {"mode": "auto"}      → autodetect (default)
"""
import os
import json
import subprocess
import time
from datetime import datetime
from .base import ChannelPlugin
from ..message import Message


class WhatsAppPlugin(ChannelPlugin):
    name = "whatsapp"
    poll_interval = 10

    def __init__(self, config: dict = None):
        super().__init__(config)
        # Raiz del proyecto: 3 niveles arriba de plugins/whatsapp.py
        self._root = self.config.get("project_root",
                                     os.path.dirname(os.path.dirname(os.path.dirname(
                                         os.path.dirname(os.path.abspath(__file__))))))
        self._json_file = os.path.join(self._root, "whatsapp_nuevos.json")
        self._monitor_script = os.path.join(self._root, "whatsapp_monitor.js")
        self.watch_groups = self.config.get("watch_groups", ["SISTEMA RAY"])
        self.mode = self.config.get("mode", "auto")  # auto | consumer | spawn
        self.freshness_threshold_sec = int(
            self.config.get("freshness_threshold_sec", 90)
        )
        self._last_count = 0
        self._node_process = None
        self._effective_mode = None  # se setea en connect()

    def _is_external_writer_active(self) -> bool:
        """True si whatsapp_nuevos.json fue tocado recientemente por OTRO proceso."""
        if not os.path.exists(self._json_file):
            return False
        try:
            mtime = os.path.getmtime(self._json_file)
        except OSError:
            return False
        age = time.time() - mtime
        return age <= self.freshness_threshold_sec

    def _seed_last_count(self):
        """Lee el JSON actual y guarda el count para no re-emitir viejos."""
        try:
            with open(self._json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._last_count = len(data)
        except Exception:
            self._last_count = 0

    def connect(self) -> bool:
        # Resolver modo efectivo
        if self.mode == "consumer":
            self._effective_mode = "consumer"
        elif self.mode == "spawn":
            self._effective_mode = "spawn"
        else:  # auto
            self._effective_mode = (
                "consumer" if self._is_external_writer_active() else "spawn"
            )

        # ── Consumer-only ─────────────────────────────────────────────
        if self._effective_mode == "consumer":
            # Necesitamos al menos que el archivo exista; si no, crear vacío.
            if not os.path.exists(self._json_file):
                try:
                    with open(self._json_file, "w", encoding="utf-8") as f:
                        json.dump([], f)
                except Exception:
                    return False
            self._seed_last_count()
            return True

        # ── Spawn (lanzamos el monitor.js nosotros) ──────────────────
        if not os.path.exists(self._monitor_script):
            return False
        auth_dir = os.path.join(self._root, ".wwebjs_auth")
        if not os.path.isdir(auth_dir):
            return False

        try:
            args = ["node", self._monitor_script] + self.watch_groups
            self._node_process = subprocess.Popen(
                args, cwd=self._root,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace"
            )
            if not os.path.exists(self._json_file):
                with open(self._json_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
            self._seed_last_count()
            return True
        except Exception:
            return False

    def poll(self) -> list:
        messages = []
        try:
            if not os.path.exists(self._json_file):
                return []
            with open(self._json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Solo mensajes nuevos desde el ultimo poll
            new_msgs = data[self._last_count:]
            self._last_count = len(data)

            for entry in new_msgs:
                messages.append(Message(
                    channel="whatsapp",
                    chat_id=entry.get("chat_id", ""),
                    chat_name=entry.get("chat_name", "?"),
                    user=entry.get("user", "?"),
                    text=entry.get("text", ""),
                    timestamp=datetime.fromisoformat(entry["timestamp"]) if entry.get("timestamp") else datetime.now(),
                    type=entry.get("type", "text"),
                    raw=entry
                ))
        except Exception:
            pass
        return messages

    def disconnect(self):
        # Solo terminar el proceso si nosotros lo spawneamos.
        # En modo consumer NO matamos al monitor externo.
        if self._node_process:
            try:
                self._node_process.terminate()
                self._node_process.wait(timeout=5)
            except Exception:
                try:
                    self._node_process.kill()
                except Exception:
                    pass
            self._node_process = None
