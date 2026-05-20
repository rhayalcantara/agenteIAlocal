"""Wrapper sobre claude_agent_sdk.query — emite chunks de texto."""
from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent  # C:\proyectos\agenteIAlocal


def _options(session_id: str | None = None) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        cwd=str(PROJECT_DIR),
        permission_mode="bypassPermissions",
        resume=session_id,
    )


async def run_prompt(
    prompt: str, session_id: str | None = None
) -> AsyncIterator[dict]:
    """Yields dicts:
       {"type":"text_chunk","text": "..."}
       {"type":"done","session_id": "...","cost": ...,"total_input": ...,"total_output": ...}
       {"type":"error","error": "..."}
    """
    try:
        async for msg in query(prompt=prompt, options=_options(session_id)):
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text = (block.text or "").strip()
                        if text:
                            yield {"type": "text_chunk", "text": text}
            elif isinstance(msg, ResultMessage):
                yield {
                    "type": "done",
                    "session_id": getattr(msg, "session_id", None),
                    "cost_usd": getattr(msg, "total_cost_usd", None),
                    "duration_ms": getattr(msg, "duration_ms", None),
                    "is_error": getattr(msg, "is_error", False),
                }
    except Exception as e:
        yield {"type": "error", "error": f"{type(e).__name__}: {e}"}
