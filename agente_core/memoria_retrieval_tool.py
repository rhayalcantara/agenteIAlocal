"""Memoria con recuperación — POC Fase 1.

Persiste cada mensaje user/assistant con embedding (sentence-transformers,
`intfloat/multilingual-e5-small` por defecto) en `agente_core/data/memoria_retrieval.db`
y expone la tool agéntica `buscar_memoria(query, k)` para que el LLM
recupere contexto antiguo cuando el usuario referencia algo de hace tiempo.

Es una CAPA NUEVA AL LADO — no toca `memoria.py` / `memoria.json` /
`messages.json` ni el compactador. Reversible: basta no cargar la tool.

API (vía dispatcher `ejecutar(operacion, **kwargs) -> str`):
    ejecutar("ingestar", rol="user", texto="...", session_id="global")
    ejecutar("buscar", query="...", k=5, session_id=None, rol=None, dias_max=None)
    ejecutar("estado")
    ejecutar("limpiar", antes_de_ts=None, session_id=None)
    ejecutar("reindexar")  # stub Fase 1

Tolerante a fallo: si `sentence-transformers` no está instalado, retorna
"⚠️ degradado" en vez de romper el turno del agente.
"""
import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta

import numpy as np

logger = logging.getLogger(__name__)

# ── Configuración ────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(_ROOT, "data", "memoria_retrieval.db")
EMBED_MODEL = os.getenv("MEMORIA_RETRIEVAL_MODEL", "intfloat/multilingual-e5-small")
EMBED_DEVICE = os.getenv("MEMORIA_RETRIEVAL_DEVICE", "cpu")
MAX_TEXTO = 8000  # truncar al ingestar para no romper el tokenizer

_encoder = None
_encoder_lock = threading.Lock()
_write_lock = threading.Lock()
_initialized = False


# ── SQLite (patrón job_manager/db.py) ────────────────────────────────────

@contextmanager
def _connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def _init_db():
    """Crea tabla e índices si no existen. Idempotente, lazy (no en import)."""
    global _initialized
    if _initialized:
        return
    with _connect() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS messages (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id  TEXT NOT NULL DEFAULT 'global',
              rol         TEXT NOT NULL,
              texto       TEXT NOT NULL,
              ts          TEXT NOT NULL,
              tokens      INTEGER,
              embedding   BLOB NOT NULL,
              embed_dim   INTEGER NOT NULL,
              embed_model TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS ix_msg_ts      ON messages(ts)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_msg_session ON messages(session_id)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_msg_rol     ON messages(rol)")
    _initialized = True


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Encoder lazy (sentence-transformers) ─────────────────────────────────

def _get_encoder():
    """Singleton lazy. Importa sentence-transformers solo en primer uso.
    Si no está instalado o falla, retorna None (modo degradado)."""
    global _encoder
    if _encoder is not None:
        return _encoder
    with _encoder_lock:
        if _encoder is not None:
            return _encoder
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Cargando encoder '{EMBED_MODEL}' en {EMBED_DEVICE}…")
            _encoder = SentenceTransformer(EMBED_MODEL, device=EMBED_DEVICE)
            logger.info("Encoder cargado")
            return _encoder
        except ImportError as e:
            logger.warning(f"sentence-transformers no disponible: {e}")
            return None
        except Exception as e:
            logger.error(f"fallo cargando encoder '{EMBED_MODEL}': {e}", exc_info=True)
            return None


def _embed(texto: str, *, is_query: bool):
    """Devuelve un np.ndarray float32 con prefijo e5 ('query:'/'passage:')
    y normalizado, o None si el encoder no está disponible."""
    enc = _get_encoder()
    if enc is None:
        return None
    prefijo = "query: " if is_query else "passage: "
    vec = enc.encode(prefijo + texto, normalize_embeddings=True)
    return np.asarray(vec, dtype=np.float32)


# ── Operaciones ──────────────────────────────────────────────────────────

def ingestar(rol: str, texto: str, session_id: str = "global",
             tokens: int = None) -> str:
    """Persiste un mensaje con su embedding. Tolerante a fallo."""
    if not texto or not str(texto).strip():
        return "OK (texto vacío, ignorado)"
    if rol not in ("user", "assistant", "system_summary"):
        return f"❌ rol '{rol}' no válido (use user|assistant|system_summary)"
    texto_clean = str(texto)[:MAX_TEXTO]
    emb = _embed(texto_clean, is_query=False)
    if emb is None:
        return "⚠️ degradado: sentence-transformers no instalado o encoder falló"
    blob = emb.tobytes()
    dim = int(emb.shape[0])
    _init_db()
    with _write_lock, _connect() as c:
        cur = c.execute(
            """INSERT INTO messages
                 (session_id, rol, texto, ts, tokens, embedding, embed_dim, embed_model)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id or "global", rol, texto_clean, _now_iso(),
             int(tokens) if tokens else None, blob, dim, EMBED_MODEL),
        )
        msg_id = cur.lastrowid
    return f"OK id={msg_id}"


def buscar(query: str, k: int = 5, session_id: str = None, rol: str = None,
           dias_max: int = None) -> str:
    """Top-K mensajes semánticamente similares (cosine numpy in-memory).
    Retorna JSON: [{id, rol, ts, texto, score}, ...]"""
    if not query or not str(query).strip():
        return json.dumps([], ensure_ascii=False)
    try:
        k = max(1, min(int(k or 5), 20))
    except (TypeError, ValueError):
        k = 5

    q_emb = _embed(str(query), is_query=True)
    if q_emb is None:
        return json.dumps({"error": "⚠️ degradado: sentence-transformers no instalado"},
                          ensure_ascii=False)

    _init_db()
    where, params = [], []
    if session_id:
        where.append("session_id = ?"); params.append(session_id)
    if rol:
        where.append("rol = ?"); params.append(rol)
    if dias_max:
        cutoff = (datetime.now(timezone.utc)
                  - timedelta(days=int(dias_max))).strftime("%Y-%m-%dT%H:%M:%SZ")
        where.append("ts >= ?"); params.append(cutoff)

    sql = "SELECT id, session_id, rol, texto, ts, embedding, embed_dim FROM messages"
    if where:
        sql += " WHERE " + " AND ".join(where)
    with _connect() as c:
        rows = c.execute(sql, params).fetchall()

    if not rows:
        return json.dumps([], ensure_ascii=False)

    q_dim = int(q_emb.shape[0])
    valid_rows = []
    embeds = []
    descartadas = 0
    for r in rows:
        if r["embed_dim"] != q_dim:
            descartadas += 1
            continue
        valid_rows.append(r)
        embeds.append(np.frombuffer(r["embedding"], dtype=np.float32))
    if descartadas:
        logger.warning(f"buscar_memoria: ignoradas {descartadas} filas con dim distinto")
    if not valid_rows:
        return json.dumps([], ensure_ascii=False)

    M = np.vstack(embeds)
    scores = (M @ q_emb).astype(float)

    # top-K eficiente
    if len(scores) <= k:
        idxs = np.argsort(-scores)
    else:
        idxs = np.argpartition(-scores, k)[:k]
        idxs = idxs[np.argsort(-scores[idxs])]

    out = []
    for i in idxs[:k]:
        r = valid_rows[int(i)]
        out.append({
            "id": int(r["id"]),
            "rol": r["rol"],
            "ts": r["ts"],
            "texto": r["texto"][:600],  # truncar al LLM para no inflar contexto
            "score": round(float(scores[int(i)]), 4),
        })
    return json.dumps(out, ensure_ascii=False)


def estado() -> str:
    """Stats: total mensajes, por rol, último ts, modelo, tamaño DB."""
    _init_db()
    with _connect() as c:
        total = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        por_rol = dict(c.execute(
            "SELECT rol, COUNT(*) FROM messages GROUP BY rol").fetchall())
        ultimo = c.execute("SELECT MAX(ts) FROM messages").fetchone()[0]
        modelos = [r[0] for r in c.execute(
            "SELECT DISTINCT embed_model FROM messages").fetchall()]
    enc = _get_encoder()
    try:
        bytes_db = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    except Exception:
        bytes_db = 0
    return json.dumps({
        "total": total,
        "por_rol": por_rol,
        "ultimo_ts": ultimo,
        "modelo_actual": EMBED_MODEL,
        "modelos_en_db": modelos,
        "modelo_cargado": enc is not None,
        "bytes_db": bytes_db,
        "db_path": DB_PATH,
    }, ensure_ascii=False, indent=2)


def limpiar(antes_de_ts: str = None, session_id: str = None) -> str:
    """Borra mensajes filtrados. Retorna cuántos."""
    _init_db()
    where, params = [], []
    if antes_de_ts:
        where.append("ts < ?"); params.append(antes_de_ts)
    if session_id:
        where.append("session_id = ?"); params.append(session_id)
    sql = "DELETE FROM messages"
    if where:
        sql += " WHERE " + " AND ".join(where)
    with _write_lock, _connect() as c:
        cur = c.execute(sql, params)
        n = cur.rowcount
    return f"OK: {n} borrados"


def reindexar(modelo_nuevo: str = None) -> str:
    """Stub Fase 1.5: cambiar de modelo requiere recomputar embeddings."""
    return ("⚠️ reindexar pendiente Fase 1.5 — para cambiar de modelo, borra la DB "
            "con limpiar() y reingresta. O implementar batch re-embed.")


# ── Dispatcher ───────────────────────────────────────────────────────────

_OPERACIONES = {
    "ingestar": ingestar,
    "buscar": buscar,
    "estado": estado,
    "limpiar": limpiar,
    "reindexar": reindexar,
}


def ejecutar(operacion: str, **kwargs) -> str:
    fn = _OPERACIONES.get(operacion)
    if fn is None:
        disp = ", ".join(sorted(_OPERACIONES.keys()))
        return f"❌ Operacion '{operacion}' no existe. Disponibles: {disp}"
    try:
        return fn(**kwargs)
    except TypeError as e:
        return f"❌ Parametros incorrectos para '{operacion}': {e}"
    except Exception as e:
        logger.error(f"memoria_retrieval.ejecutar({operacion}): {e}", exc_info=True)
        return f"❌ Error en '{operacion}': {e}"


if __name__ == "__main__":
    # CLI mínima: python memoria_retrieval_tool.py <operacion> [k=v ...]
    import sys
    if len(sys.argv) > 1:
        op = sys.argv[1]
        kv = {}
        for arg in sys.argv[2:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                kv[k] = v
        print(ejecutar(op, **kv))
    else:
        print(estado())
