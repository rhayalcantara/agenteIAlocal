"""Worker que consume mensajes destinados a node 'local'.

Lee un mensaje, ejecuta el SDK de Claude, escribe chunks de respuesta
al inbox del nodo emisor.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from claude_server.core.db import insert_message
from claude_server.core.sdk_wrapper import run_prompt
from claude_server.core import tts_stream

logger = logging.getLogger("claude_server.worker")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # C:\proyectos\agenteIAlocal


# session_id por (from_node) — mantiene contexto de conversación por dispositivo
_sessions: dict[str, str] = {}


def _attachment_path(url: str) -> Path | None:
    """Convierte /uploads/<name> en ruta absoluta dentro del proyecto."""
    if not url.startswith("/uploads/"):
        return None
    name = url.split("/uploads/", 1)[1]
    if "/" in name or "\\" in name or ".." in name:
        return None
    p = PROJECT_ROOT / "claude_server" / "data" / "uploads" / name
    return p if p.exists() else None


def _transcribe(audio_path: Path) -> str:
    """STT con Whisper. Reusa el modelo ya cargado por mcp_telegram si está."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "agente_core"))
        from voice_handler import transcribir
        return transcribir(str(audio_path), language="es")
    except Exception as e:
        logger.warning(f"[stt] no se pudo transcribir {audio_path.name}: {e}")
        return ""


def _build_prompt(text: str, attachments: list[dict]) -> str:
    """Combina texto del usuario con resumen de attachments en un solo prompt."""
    if not attachments:
        return text
    parts: list[str] = []
    if text.strip():
        parts.append(text.strip())

    for att in attachments:
        kind = att.get("kind", "file")
        url = att.get("url", "")
        fname = att.get("filename") or url.rsplit("/", 1)[-1]
        path = _attachment_path(url)

        if kind == "audio" and path:
            tx = _transcribe(path)
            if tx:
                parts.append(f"[Audio transcripto de {fname}]:\n{tx}")
            else:
                parts.append(f"[Audio recibido: {fname} — no se pudo transcribir. Archivo en {path}]")
        elif kind == "image" and path:
            parts.append(
                f"[Imagen adjunta: {fname}]\n"
                f"Puedes inspeccionarla con la tool Read en la ruta: {path}"
            )
        elif path:
            parts.append(f"[Archivo adjunto ({kind}): {fname}] Ruta local: {path}")
        else:
            parts.append(f"[Adjunto no resuelto: {url}]")

    return "\n\n".join(parts) if parts else "(mensaje vacío con adjuntos)"


async def process_inbound(
    *,
    from_node: str,
    prompt: str,
    attachments: list[dict] | None = None,
    client_meta: dict | None = None,
    voice_output: bool = False,
) -> None:
    """Procesa un prompt entrante y emite chunks de respuesta a inbox/{from_node}."""
    attachments = attachments or []
    if client_meta and any(k in client_meta for k in ("lat", "lon", "geo")):
        geo = client_meta.get("geo") or {"lat": client_meta.get("lat"), "lon": client_meta.get("lon")}
        if geo and geo.get("lat") is not None:
            prompt = f"{prompt}\n\n[Ubicación del usuario: lat={geo.get('lat')}, lon={geo.get('lon')}]"

    full_prompt = _build_prompt(prompt, attachments)

    session_id = _sessions.get(from_node)
    logger.info(
        f"[worker] processing from={from_node} session={session_id} "
        f"attachments={len(attachments)} prompt={full_prompt[:120]!r}"
    )

    final_session = None
    chunks_emitted = 0
    async for ev in run_prompt(full_prompt, session_id=session_id):
        if ev["type"] == "text_chunk":
            text = ev["text"]
            text_msg_id = await insert_message(
                node_id=from_node,
                from_node="local",
                direction="in",
                kind="text_chunk",
                content=text,
            )
            chunks_emitted += 1

            if voice_output and tts_stream.is_available():
                # Sintetiza en hilo aparte para no bloquear el async loop.
                audio_path = await asyncio.to_thread(
                    tts_stream.synthesize_to_file, text, "tts"
                )
                if audio_path:
                    await insert_message(
                        node_id=from_node,
                        from_node="local",
                        direction="in",
                        kind="audio_chunk",
                        content=tts_stream.public_url(audio_path),
                        meta={"after_text_id": text_msg_id, "size": audio_path.stat().st_size},
                    )
        elif ev["type"] == "done":
            final_session = ev.get("session_id")
            await insert_message(
                node_id=from_node,
                from_node="local",
                direction="in",
                kind="done",
                content=None,
                meta={
                    "session_id": final_session,
                    "cost_usd": ev.get("cost_usd"),
                    "duration_ms": ev.get("duration_ms"),
                    "is_error": ev.get("is_error"),
                },
            )
        elif ev["type"] == "error":
            await insert_message(
                node_id=from_node,
                from_node="local",
                direction="in",
                kind="error",
                content=ev["error"],
            )

    if final_session:
        _sessions[from_node] = final_session
    logger.info(f"[worker] done from={from_node} chunks={chunks_emitted} session={final_session}")


def schedule(
    *,
    from_node: str,
    prompt: str,
    attachments: list[dict] | None = None,
    client_meta: dict | None = None,
    voice_output: bool = False,
) -> asyncio.Task:
    """Lanza el procesamiento en background y devuelve la Task."""
    return asyncio.create_task(
        process_inbound(
            from_node=from_node,
            prompt=prompt,
            attachments=attachments,
            client_meta=client_meta,
            voice_output=voice_output,
        ),
        name=f"claude_local:{from_node}",
    )
