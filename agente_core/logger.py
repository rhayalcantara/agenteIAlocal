"""Logger centralizado con rotación de archivos."""
import os
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "agente.log")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_file_handler = None
_console_handler = None


class _SafeRotatingFileHandler(RotatingFileHandler):
    """RotatingFileHandler tolerante a locks de Windows.

    Si otro proceso mantiene abierto el archivo durante la rotación
    (WinError 32), se omite la rotación en lugar de levantar una
    Logging error en cada emit. El archivo crece un poco más hasta
    que el próximo intento pueda renombrar.
    """

    def doRollover(self):
        try:
            super().doRollover()
        except (PermissionError, OSError):
            if self.stream:
                try:
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            if not self.delay:
                self.stream = self._open()


def _get_file_handler():
    global _file_handler
    if _file_handler is None:
        _file_handler = _SafeRotatingFileHandler(
            LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3,
            encoding="utf-8", delay=True,
        )
        _file_handler.setLevel(logging.DEBUG)
        _file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    return _file_handler


def _get_console_handler():
    global _console_handler
    if _console_handler is None:
        _console_handler = logging.StreamHandler()
        _console_handler.setLevel(logging.CRITICAL)
        _console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT))
    return _console_handler


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(_get_file_handler())
        logger.addHandler(_get_console_handler())
        logger.propagate = False
    return logger
