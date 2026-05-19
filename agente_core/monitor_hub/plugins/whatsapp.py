"""Plugin WhatsApp para Monitor Hub.

Lee mensajes nuevos del archivo whatsapp_nuevos.json que genera
whatsapp_monitor.js (proceso Node.js persistente separado).
"""
import os
import json
import subprocess
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
        self._last_count = 0
        self._node_process = None

    def connect(self) -> bool:
        # Verificar que el script y la sesion existen
        if not os.path.exists(self._monitor_script):
            return False
        auth_dir = os.path.join(self._root, ".wwebjs_auth")
        if not os.path.isdir(auth_dir):
            return False

        # Iniciar el proceso Node.js persistente
        try:
            args = ["node", self._monitor_script] + self.watch_groups
            self._node_process = subprocess.Popen(
                args, cwd=self._root,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                encoding="utf-8", errors="replace"
            )
            # Inicializar archivo si no existe
            if not os.path.exists(self._json_file):
                with open(self._json_file, "w", encoding="utf-8") as f:
                    json.dump([], f)
            # Leer count actual para no reportar mensajes viejos
            try:
                with open(self._json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._last_count = len(data)
            except Exception:
                self._last_count = 0
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
