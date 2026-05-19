"""Plugin Gmail para Monitor Hub.

Poll Gmail (vía gmail_manager existente) y emite Message por cada correo
nuevo. Reusa la autenticación OAuth de gmail_manager/token.json.

Config admitida:
    {
      "enabled": true,
      "poll_interval": 60,                    # segundos, default 60
      "query": "is:unread",                   # query Gmail, default unread
      "max_per_poll": 20,                     # tope por poll
      "important_senders": ["jefe@x.com"],   # opcional, marca priority='urgent'
      "important_keywords": ["urgente"]      # adicional al hub-level
    }
"""
from __future__ import annotations

import os
import sys
import logging
from collections import deque
from datetime import datetime, timezone
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path

from .base import ChannelPlugin
from ..message import Message

logger = logging.getLogger("monitor_hub.gmail")


def _project_root() -> Path:
    # plugins/gmail.py → monitor_hub → agente_core → <root>
    return Path(__file__).resolve().parent.parent.parent.parent


class GmailPlugin(ChannelPlugin):
    name = "gmail"
    poll_interval = 60

    def __init__(self, config: dict = None):
        super().__init__(config)
        self.query = self.config.get("query", "is:unread")
        self.max_per_poll = int(self.config.get("max_per_poll", 20))
        self.important_senders = {
            s.lower() for s in self.config.get("important_senders", [])
        }
        self.important_keywords = [
            k.lower() for k in self.config.get("important_keywords", [])
        ]

        self._service = None
        # ID cache: deque so we can cap memory; set for O(1) lookup.
        self._seen_ids: deque[str] = deque(maxlen=500)
        self._seen_set: set[str] = set()

    # ── helpers ────────────────────────────────────────────────────────
    def _mark_seen(self, msg_id: str) -> bool:
        if msg_id in self._seen_set:
            return False
        if len(self._seen_ids) == self._seen_ids.maxlen:
            old = self._seen_ids[0]
            self._seen_set.discard(old)
        self._seen_ids.append(msg_id)
        self._seen_set.add(msg_id)
        return True

    def _ensure_service(self):
        if self._service is not None:
            return self._service
        # Importamos gmail_manager.main de forma diferida porque arrastra
        # google-api-python-client (pesado).
        root = _project_root()
        gm_path = str(root)
        if gm_path not in sys.path:
            sys.path.insert(0, gm_path)
        from gmail_manager.main import get_credentials  # type: ignore
        from googleapiclient.discovery import build  # type: ignore

        creds = get_credentials()
        self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    @staticmethod
    def _hdr(msg: dict, name: str) -> str:
        for h in msg.get("payload", {}).get("headers", []):
            if h.get("name", "").lower() == name.lower():
                return h.get("value", "") or ""
        return ""

    @staticmethod
    def _parse_sender(from_header: str) -> tuple[str, str]:
        """Devuelve (display_name, email)."""
        name, email = parseaddr(from_header or "")
        if not name:
            name = email.split("@")[0] if email else "?"
        return name, email

    # ── ciclo de vida ──────────────────────────────────────────────────
    def connect(self) -> bool:
        try:
            self._ensure_service()
            # Seed: marcar como vistos los mensajes ya existentes en la query
            # para no reportarlos como "nuevos" en el primer poll.
            results = self._service.users().messages().list(
                userId="me", q=self.query, maxResults=50
            ).execute()
            for m in results.get("messages", []) or []:
                self._mark_seen(m["id"])
            return True
        except Exception as e:
            logger.warning(f"gmail connect failed: {e}")
            return False

    def poll(self) -> list:
        messages: list[Message] = []
        try:
            service = self._ensure_service()
            results = service.users().messages().list(
                userId="me", q=self.query, maxResults=self.max_per_poll
            ).execute()
            for m in results.get("messages", []) or []:
                msg_id = m["id"]
                if not self._mark_seen(msg_id):
                    continue  # ya emitido

                full = service.users().messages().get(
                    userId="me", id=msg_id, format="metadata",
                    metadataHeaders=["From", "Subject", "Date"]
                ).execute()

                from_hdr = self._hdr(full, "From")
                subject = self._hdr(full, "Subject")
                date_hdr = self._hdr(full, "Date")
                snippet = full.get("snippet", "")

                name, email_addr = self._parse_sender(from_hdr)
                ts = datetime.now(timezone.utc)
                if date_hdr:
                    try:
                        ts = parsedate_to_datetime(date_hdr)
                    except Exception:
                        pass

                text = subject
                if snippet:
                    text = f"{subject} — {snippet[:200]}" if subject else snippet[:300]

                msg = Message(
                    channel="gmail",
                    chat_id=email_addr or msg_id,
                    chat_name=name,
                    user=email_addr,
                    text=text,
                    timestamp=ts,
                    type="email",
                    raw={"gmail_id": msg_id, "subject": subject, "from": from_hdr},
                )

                # Reglas locales de prioridad (el hub global tiene sus propias
                # urgent_keywords; éstas se suman, no las reemplazan).
                tl = text.lower()
                if (email_addr.lower() in self.important_senders
                        or any(kw in tl for kw in self.important_keywords)):
                    msg.priority = "urgent"

                messages.append(msg)
        except Exception as e:
            logger.warning(f"gmail poll failed: {e}")
        return messages

    def disconnect(self):
        # No hay socket que cerrar; el cliente HTTP es stateless.
        self._service = None
