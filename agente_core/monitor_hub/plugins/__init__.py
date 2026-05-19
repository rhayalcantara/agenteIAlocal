from .telegram import TelegramPlugin
from .whatsapp import WhatsAppPlugin
from .jobs import JobsPlugin
from .gmail import GmailPlugin

PLUGINS = {
    "telegram": TelegramPlugin,
    "whatsapp": WhatsAppPlugin,
    "jobs": JobsPlugin,
    "gmail": GmailPlugin,
}
