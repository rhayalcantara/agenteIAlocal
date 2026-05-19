"""Mensaje estandar del Monitor Hub."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    channel: str        # "telegram", "whatsapp", "gmail"
    chat_id: str        # ID del chat/grupo/thread
    chat_name: str      # "SISTEMA RAY", "DM con Rhay"
    user: str           # nombre del remitente
    text: str           # contenido
    timestamp: datetime = field(default_factory=datetime.now)
    type: str = "text"  # "text", "voice", "image", "document"
    priority: str = "normal"  # "normal", "urgent"
    raw: dict = field(default_factory=dict)

    def to_line(self) -> str:
        """Formato de salida para stdout (Claude Code lo lee)."""
        prio = "!" if self.priority == "urgent" else ""
        return f"MSG|{self.channel}|{self.chat_id}|{self.chat_name}|{self.user}|{self.type}|{prio}{self.text}"

    def __str__(self):
        return f"[{self.channel}:{self.chat_name}] {self.user}: {self.text[:100]}"
