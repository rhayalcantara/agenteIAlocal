"""
Configuración del supervisor — lee desde .env en la raíz del proyecto.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Raíz del proyecto (un nivel arriba de supervisor/)
ROOT = Path(__file__).parent.parent

load_dotenv(ROOT / ".env")

# ── Bot de Telegram del supervisor (token DISTINTO al del agente core) ─────────
SUPERVISOR_BOT_TOKEN: str = os.getenv("SUPERVISOR_BOT_TOKEN", "")
SUPERVISOR_CHAT_ID: int   = int(os.getenv("SUPERVISOR_CHAT_ID", "0"))

# ── Parámetros de monitoreo ────────────────────────────────────────────────────
# Si no hay heartbeat en N segundos → agente congelado
HEARTBEAT_TIMEOUT: int = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "120"))

# Frecuencia del health-check
CHECK_INTERVAL: int = int(os.getenv("CHECK_INTERVAL_SECONDS", "30"))

# Modo: "manual" → siempre alerta al usuario antes de actuar
#        "auto"   → el LLM decide y actúa solo (luego informa)
SUPERVISOR_MODE: str = os.getenv("SUPERVISOR_MODE", "manual")

# Comando para lanzar el agente core (desde la raíz del proyecto)
# Por defecto monitorea el bot de Telegram (servicio persistente)
AGENTE_COMMAND: str = os.getenv("AGENTE_COMMAND", "python telegram_agente.py")

# Máximo de intentos de auto-recuperación consecutivos antes de escalar al usuario
MAX_RECOVERY_ATTEMPTS: int = int(os.getenv("MAX_RECOVERY_ATTEMPTS", "3"))

# ── Paths ──────────────────────────────────────────────────────────────────────
HEARTBEAT_FILE: Path = ROOT / "heartbeat.json"
LOG_DIR: Path        = ROOT / "logs"
AGENTE_LOG_FILE: Path = LOG_DIR / "agente_core.log"
SUPERVISOR_LOG_FILE: Path = LOG_DIR / "supervisor.log"
