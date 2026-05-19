"""Monitor Hub — Sistema centralizado de monitoreo multi-canal.

Uso standalone:
    python -m monitor_hub.hub
    python -m monitor_hub.hub --config monitor_config.json

Cada mensaje nuevo se imprime en stdout con formato:
    MSG|canal|chat_id|chat_name|user|type|texto

Claude Code usa Monitor para capturar estas lineas y reaccionar.
"""
import os
import sys
import json
import time
import threading
from datetime import datetime
from .plugins import PLUGINS
from .message import Message

# Cargar .env del proyecto para que los plugins reciban TELEGRAM_TOKEN, etc.
try:
    from dotenv import load_dotenv
    _ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    load_dotenv(os.path.join(_ROOT, ".env"))
except ImportError:
    pass

# Fix encoding para Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DEFAULT_CONFIG = {
    "channels": {
        "telegram": {
            "enabled": True,
            "poll_interval": 5,
            "allowed_chats": []
        },
        "whatsapp": {
            "enabled": False,
            "poll_interval": 30,
            "watch_groups": ["SISTEMA RAY"]
        }
    },
    "dispatcher": {
        "urgent_keywords": ["urgente", "error", "caido", "no funciona", "ayuda"],
        "dedup_window": 60,
        # Relay cross-channel: si un msg llega como urgente desde un canal != telegram,
        # se reenvía al chat_id de telegram aquí indicado. Vacío = no relay.
        "relay_urgent_to_telegram_chat_id": ""
    }
}


class MonitorHub:
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.plugins = {}
        self.running = False
        self._message_log = []  # ultimos N mensajes para dashboard
        self._stats = {}

    def _load_config(self, path: str = None) -> dict:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        # Buscar en raiz del proyecto
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        default_path = os.path.join(root, "monitor_config.json")
        if os.path.exists(default_path):
            with open(default_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return DEFAULT_CONFIG

    def _init_plugins(self):
        channels = self.config.get("channels", {})
        for name, cfg in channels.items():
            if not cfg.get("enabled", False):
                continue
            # Soportar multiples instancias: "telegram-ranger" usa plugin "telegram"
            plugin_type = cfg.get("type", name.split("-")[0])
            plugin_class = PLUGINS.get(plugin_type)
            if not plugin_class:
                print(f"WARN|Plugin desconocido: {plugin_type} (canal: {name})", flush=True)
                continue
            plugin = plugin_class(cfg)
            if plugin.connect():
                self.plugins[name] = plugin
                self._stats[name] = {"connected": True, "messages": 0, "errors": 0}
                print(f"CONNECTED|{name}", flush=True)
            else:
                self._stats[name] = {"connected": False, "messages": 0, "errors": 0}
                print(f"FAILED|{name}", flush=True)

    def _check_urgent(self, msg: Message):
        keywords = self.config.get("dispatcher", {}).get("urgent_keywords", [])
        text_lower = msg.text.lower()
        for kw in keywords:
            if kw in text_lower:
                msg.priority = "urgent"
                return

    def _relay_urgent(self, msg: Message):
        """Reenvía un msg urgente al chat Telegram configurado.

        Solo aplica si:
          - msg.priority == 'urgent'
          - El msg viene de un canal != 'telegram' (para no hacer eco)
          - dispatcher.relay_urgent_to_telegram_chat_id está configurado
          - Hay un plugin telegram conectado
        """
        if msg.priority != "urgent":
            return
        if msg.channel == "telegram":
            return
        chat_id = (self.config.get("dispatcher", {})
                              .get("relay_urgent_to_telegram_chat_id", "")).strip()
        if not chat_id:
            return
        # Buscar primer plugin telegram conectado (puede haber multiples instancias).
        tg = next(
            (p for n, p in self.plugins.items() if getattr(p, "name", n).startswith("telegram")),
            None,
        )
        if tg is None:
            return
        snippet = (msg.text or "").strip()[:300]
        relay_text = (
            f"🔴 URGENTE [{msg.channel}:{msg.chat_name}]\n"
            f"{msg.user}: {snippet}"
        )
        try:
            ok = tg.send(chat_id, relay_text)
            print(f"RELAY|{msg.channel}->telegram|{chat_id}|{'OK' if ok else 'FAIL'}", flush=True)
        except Exception as e:
            print(f"RELAY_ERROR|{msg.channel}->telegram|{chat_id}|{e}", flush=True)

    def _poll_channel(self, name: str, plugin):
        """Poll un canal y emite mensajes."""
        try:
            messages = plugin.poll()
            for msg in messages:
                self._check_urgent(msg)
                self._stats[name]["messages"] += 1
                self._message_log.append(msg)
                # Mantener log en tamaño razonable
                if len(self._message_log) > 200:
                    self._message_log = self._message_log[-100:]
                print(msg.to_line(), flush=True)
                if msg.priority == "urgent":
                    self._relay_urgent(msg)
        except Exception as e:
            self._stats[name]["errors"] += 1
            print(f"ERROR|{name}|{e}", flush=True)

    def run(self):
        """Loop principal del hub."""
        self._init_plugins()
        if not self.plugins:
            print("ERROR|No hay plugins conectados", flush=True)
            return

        active = ", ".join(self.plugins.keys())
        print(f"HUB_READY|{active}", flush=True)
        self.running = True

        # Cada plugin tiene su propio intervalo
        last_poll = {name: 0.0 for name in self.plugins}

        try:
            while self.running:
                now = time.time()
                for name, plugin in self.plugins.items():
                    if now - last_poll[name] >= plugin.poll_interval:
                        self._poll_channel(name, plugin)
                        last_poll[name] = now
                time.sleep(1)  # tick del loop
        except KeyboardInterrupt:
            pass
        finally:
            self.running = False
            for plugin in self.plugins.values():
                plugin.disconnect()
            print("HUB_STOPPED", flush=True)

    def get_stats(self) -> dict:
        return {
            "plugins": self._stats,
            "total_messages": sum(s["messages"] for s in self._stats.values()),
            "recent_messages": [str(m) for m in self._message_log[-20:]]
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Monitor Hub")
    parser.add_argument("--config", help="Path to config JSON")
    args = parser.parse_args()

    hub = MonitorHub(config_path=args.config)
    hub.run()


if __name__ == "__main__":
    main()
