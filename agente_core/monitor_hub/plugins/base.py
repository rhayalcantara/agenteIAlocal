"""Plugin base para canales del Monitor Hub."""
from abc import ABC, abstractmethod


class ChannelPlugin(ABC):
    name: str = "base"
    enabled: bool = True
    poll_interval: int = 5  # segundos

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.poll_interval = self.config.get("poll_interval", self.poll_interval)

    @abstractmethod
    def connect(self) -> bool:
        """Conecta al canal. Retorna True si exitoso."""
        ...

    @abstractmethod
    def poll(self) -> list:
        """Retorna lista de Message nuevos desde el ultimo poll."""
        ...

    def send(self, chat_id: str, text: str) -> bool:
        """Envia un mensaje al canal. Override si el canal lo soporta."""
        return False

    def disconnect(self):
        """Desconecta del canal."""
        pass

    def __repr__(self):
        status = "ON" if self.enabled else "OFF"
        return f"<{self.name} [{status}] poll:{self.poll_interval}s>"
