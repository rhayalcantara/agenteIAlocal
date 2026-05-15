"""Lee historial reciente de WhatsApp desde el cache JSON del monitor persistente.

Resuelve el problema de que `whatsapp_leer.js` no puede levantar otro browser
mientras `whatsapp_monitor.js` mantiene el lock de `.wwebjs_auth/`. El monitor
acumula todos los mensajes nuevos en `whatsapp_nuevos.json`, este script los
consulta sin tocar la sesion de Puppeteer.

Uso:
    python whatsapp_leer_cache.py "SISTEMA RAY" 20       # ultimos 20 del grupo
    python whatsapp_leer_cache.py 120363424666838458@g.us 10  # por chat_id
    python whatsapp_leer_cache.py --list                  # chats unicos vistos
    python whatsapp_leer_cache.py --since 2026-05-14 "SISTEMA RAY"
    python whatsapp_leer_cache.py "SISTEMA RAY" 5 --json  # salida JSON

Notas:
- La busqueda por nombre es case-insensitive y por substring (ej. "ray" matchea
  "SISTEMA RAY"). Si hay multiples chats que matchean se imprime un error y
  hay que ser mas especifico.
- El cache es solo desde que arranco el monitor. Para historial mas viejo, hay
  que detener el monitor y usar el `whatsapp_leer.js` original (browser).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Forzar UTF-8 en stdout/stderr para no fallar con emojis en nombres (Windows cp1252)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


CACHE_PATH = Path(__file__).parent / "whatsapp_nuevos.json"


def cargar_cache() -> list[dict]:
    if not CACHE_PATH.exists():
        print(f"ERROR: no existe {CACHE_PATH}", file=sys.stderr)
        sys.exit(2)
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON invalido en {CACHE_PATH}: {e}", file=sys.stderr)
        sys.exit(2)


def listar_chats(msgs: list[dict]) -> None:
    """Imprime chats distintos con conteo y ultima actividad."""
    chats: dict[str, dict] = {}
    for m in msgs:
        cid = m.get("chat_id", "")
        if not cid:
            continue
        if cid not in chats:
            chats[cid] = {
                "name": m.get("chat_name", ""),
                "is_group": m.get("is_group", False),
                "count": 0,
                "last_ts": "",
                "last_user": "",
            }
        entry = chats[cid]
        entry["count"] += 1
        ts = m.get("timestamp", "")
        if ts > entry["last_ts"]:
            entry["last_ts"] = ts
            entry["last_user"] = m.get("user", "")
    ordered = sorted(chats.items(), key=lambda kv: kv[1]["last_ts"], reverse=True)
    if not ordered:
        print("(no hay chats en el cache)")
        return
    print(f"{'TIPO':<6} {'CHAT_NAME':<32} {'MSGS':>5}  ULTIMO  ID")
    for cid, info in ordered:
        tipo = "GRUPO" if info["is_group"] else "DM"
        name = (info["name"] or "(sin nombre)")[:32]
        print(f"{tipo:<6} {name:<32} {info['count']:>5}  {info['last_ts'][:19]}  {cid}")


def _seleccionar_chat(msgs: list[dict], busqueda: str) -> tuple[str, str] | None:
    """Devuelve (chat_id, chat_name) si busqueda matchea uno solo. None si 0 o >1.
    Si busqueda parece un chat_id literal (contiene '@'), lo usa directo."""
    if "@" in busqueda:
        match = next((m for m in msgs if m.get("chat_id") == busqueda), None)
        if match:
            return busqueda, match.get("chat_name", "")
        return busqueda, ""  # chat_id no visto en cache aun

    q = busqueda.lower()
    candidatos = {}  # chat_id -> name
    for m in msgs:
        name = m.get("chat_name", "") or ""
        if q in name.lower():
            candidatos[m["chat_id"]] = name
    if len(candidatos) == 0:
        return None
    if len(candidatos) > 1:
        print(f"ERROR: '{busqueda}' matchea {len(candidatos)} chats. Se mas especifico:", file=sys.stderr)
        for cid, name in candidatos.items():
            print(f"  - {name} ({cid})", file=sys.stderr)
        sys.exit(3)
    cid = next(iter(candidatos))
    return cid, candidatos[cid]


def _parse_since(s: str) -> str:
    """Acepta YYYY-MM-DD o ISO 8601 completo. Devuelve ISO con Z."""
    # Permitir YYYY-MM-DD como medianoche UTC
    if len(s) == 10:
        s = s + "T00:00:00Z"
    try:
        # Validar
        datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        print(f"ERROR: --since debe ser YYYY-MM-DD o ISO 8601: '{s}'", file=sys.stderr)
        sys.exit(2)
    return s


def _formato_local(iso_ts: str) -> str:
    """Convierte timestamp UTC ISO a HH:MM:SS local."""
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%m-%d %H:%M:%S")
    except Exception:
        return iso_ts[:19]


def main():
    ap = argparse.ArgumentParser(description="Lee historial WhatsApp del cache JSON.")
    ap.add_argument("chat", nargs="?", help="Nombre o chat_id del chat. Omite con --list.")
    ap.add_argument("n", nargs="?", type=int, default=20, help="N ultimos mensajes (default 20).")
    ap.add_argument("--list", action="store_true", help="Lista chats unicos con conteo.")
    ap.add_argument("--since", help="Solo mensajes desde fecha (YYYY-MM-DD o ISO).")
    ap.add_argument("--json", action="store_true", help="Salida JSON en vez de texto.")
    args = ap.parse_args()

    msgs = cargar_cache()

    if args.list:
        listar_chats(msgs)
        return

    if not args.chat:
        ap.error("Se requiere 'chat' o --list")

    sel = _seleccionar_chat(msgs, args.chat)
    if sel is None:
        print(f"ERROR: no se encontro chat con '{args.chat}'. Usa --list para ver disponibles.", file=sys.stderr)
        sys.exit(4)
    chat_id, chat_name = sel

    relevantes = [m for m in msgs if m.get("chat_id") == chat_id]
    if args.since:
        cutoff = _parse_since(args.since)
        relevantes = [m for m in relevantes if m.get("timestamp", "") >= cutoff]

    relevantes = relevantes[-args.n:] if args.n > 0 else relevantes

    if args.json:
        print(json.dumps(relevantes, ensure_ascii=False, indent=2))
        return

    print(f"Chat: {chat_name} ({chat_id})")
    print(f"Mostrando {len(relevantes)} mensajes" + (f" desde {args.since}" if args.since else "") + ":")
    print("-" * 80)
    for m in relevantes:
        hora = _formato_local(m.get("timestamp", ""))
        user = m.get("user", "?")
        tipo = m.get("type", "text")
        text = (m.get("text") or "").strip()
        marca = ""
        if tipo == "media":
            marca = "[MEDIA] "
        text_disp = text if text else "(sin texto)"
        if len(text_disp) > 200:
            text_disp = text_disp[:200] + "..."
        print(f"[{hora}] {user}: {marca}{text_disp}")
    print("-" * 80)
    print(f"({len(relevantes)} mensajes)")


if __name__ == "__main__":
    main()
