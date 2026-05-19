"""Plugin Telegram para Monitor Hub."""
import os
import requests
from datetime import datetime
from .base import ChannelPlugin
from ..message import Message


class TelegramPlugin(ChannelPlugin):
    name = "telegram"
    poll_interval = 5

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = self.config.get("name", "telegram")
        self.token = self.config.get("token") or os.getenv("TELEGRAM_TOKEN", "")
        self.api = f"https://api.telegram.org/bot{self.token}"
        self._offset = 0
        self.allowed_chats = set(self.config.get("allowed_chats", []))
        # poll_enabled=False → plugin solo se usa como sink de .send() para
        # relays cruzados. Evita conflicto de getUpdates cuando otro proceso
        # (ej. mcp_telegram.py) ya está poll-eando el mismo bot.
        self.poll_enabled = bool(self.config.get("poll_enabled", True))
        # Carpeta de descarga de medios (fotos, documentos)
        _root = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))))
        self.media_dir = self.config.get(
            "media_dir",
            os.path.join(_root, "agente_core", "data", "telegram_media")
        )
        os.makedirs(self.media_dir, exist_ok=True)

    def _download_file(self, file_id: str, suffix: str = "") -> str | None:
        """Descarga un archivo de Telegram por file_id. Retorna ruta local o None."""
        try:
            r = requests.get(f"{self.api}/getFile",
                             params={"file_id": file_id}, timeout=10)
            data = r.json()
            if not data.get("ok"):
                return None
            file_path = data["result"]["file_path"]
            url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = os.path.splitext(file_path)[1] or suffix or ""
            local = os.path.join(self.media_dir, f"{ts}_{file_id[:12]}{ext}")
            with requests.get(url, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                with open(local, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
            return local
        except Exception:
            return None

    def connect(self) -> bool:
        if not self.token:
            return False
        try:
            resp = requests.get(f"{self.api}/getMe", timeout=10)
            data = resp.json()
            if data.get("ok"):
                self._bot_name = data["result"].get("username", "?")
                return True
        except Exception:
            pass
        return False

    def poll(self) -> list:
        if not self.poll_enabled:
            return []  # send-only mode: no consumir updates del bot
        messages = []
        try:
            resp = requests.get(f"{self.api}/getUpdates", params={
                "offset": self._offset,
                "timeout": 3,
                "allowed_updates": ["message"]
            }, timeout=10)
            data = resp.json()
            if not data.get("ok"):
                return []

            for update in data.get("result", []):
                self._offset = update["update_id"] + 1
                msg = update.get("message", {})
                if not msg:
                    continue

                chat_id = str(msg.get("chat", {}).get("id", ""))
                if self.allowed_chats and int(chat_id) not in self.allowed_chats:
                    continue

                user = (msg.get("from", {}).get("first_name", "")
                        or msg.get("from", {}).get("username", "?"))
                chat_name = msg.get("chat", {}).get("title", f"DM:{user}")
                text = msg.get("text", "")

                # Determinar tipo + descargar media
                msg_type = "text"
                local_path = None
                if msg.get("voice"):
                    msg_type = "voice"
                    local_path = self._download_file(msg["voice"]["file_id"], ".ogg")
                elif msg.get("photo"):
                    msg_type = "image"
                    text = text or msg.get("caption", "")
                    largest = msg["photo"][-1]
                    local_path = self._download_file(largest["file_id"], ".jpg")
                elif msg.get("document"):
                    msg_type = "document"
                    text = text or msg.get("caption", "")
                    local_path = self._download_file(msg["document"]["file_id"])

                if local_path:
                    text = (text + " " if text else "") + f"[saved:{local_path}]"

                if not text and msg_type == "text":
                    continue

                ts = datetime.fromtimestamp(msg.get("date", 0))
                messages.append(Message(
                    channel="telegram",
                    chat_id=chat_id,
                    chat_name=chat_name,
                    user=user,
                    text=text,
                    timestamp=ts,
                    type=msg_type,
                    raw=msg
                ))
        except Exception:
            pass
        return messages

    def send(self, chat_id: str, text: str) -> bool:
        try:
            resp = requests.post(f"{self.api}/sendMessage", json={
                "chat_id": int(chat_id),
                "text": text
            }, timeout=10)
            return resp.json().get("ok", False)
        except Exception:
            return False

    def disconnect(self):
        pass
