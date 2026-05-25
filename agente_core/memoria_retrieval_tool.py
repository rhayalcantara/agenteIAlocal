"""Memoria con recuperación — POC Fase 1 + Fase 1.5 (bloques).

Persiste en `agente_core/data/memoria_retrieval.db`:
  • messages — un mensaje user/assistant por fila (Fase 1).
  • bloques  — resúmenes rodantes que produce el compactador del agente,
               indexados semánticamente (Fase 1.5 añadida 25-may-2026).

Embeddings: sentence-transformers, `intfloat/multilingual-e5-small` por defecto.
Tool agéntica `buscar_memoria(query, k)` recupera tanto mensajes como bloques
unificados, ordenados por score, cada uno marcado con campo `tipo`.

Es una CAPA NUEVA AL LADO — no toca `memoria.py` / `memoria.json` /
`messages.json` ni el código del compactador en sí. El hook que llena `bloques`
desde el compactador es opcional y daemon-thread (no rompe el turno).

API (vía dispatcher `ejecutar(operacion, **kwargs) -> str`):
    ejecutar("ingestar", rol="user", texto="...", session_id="global")
    ejecutar("ingestar_bloque", resumen="...", desde_ts="...", hasta_ts="...",
             n_mensajes=10, session_id="global")
    ejecutar("buscar", query="...", k=5, tipo="ambos"|"msg"|"bloque",
             session_id=None, rol=None, dias_max=None)
    ejecutar("estado")
    ejecutar("limpiar", antes_de_ts=None, session_id=None, tipo="ambos"|"msg"|"bloque")
    ejecutar("reindexar")  # stub

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
    """Crea tablas e índices si no existen. Idempotente, lazy (no en import)."""
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
        # Fase 1.5: resúmenes rodantes que produce el compactador del agente.
        c.execute("""
            CREATE TABLE IF NOT EXISTS bloques (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id  TEXT NOT NULL DEFAULT 'global',
              resumen     TEXT NOT NULL,
              desde_ts    TEXT,
              hasta_ts    TEXT,
              n_mensajes  INTEGER,
              ts          TEXT NOT NULL,
              embedding   BLOB NOT NULL,
              embed_dim   INTEGER NOT NULL,
              embed_model TEXT NOT NULL
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS ix_blq_ts      ON bloques(ts)")
        c.execute("CREATE INDEX IF NOT EXISTS ix_blq_session ON bloques(session_id)")
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


def ingestar_bloque(resumen: str, desde_ts: str = None, hasta_ts: str = None,
                    n_mensajes: int = None, session_id: str = "global") -> str:
    """Persiste un resumen rodante (output del compactador) con embedding.

    Llamado por el hook del compactador en `agent.py:compactar_historial`.
    Tolerante a fallo: en daemon thread, no rompe el turno si falla.
    """
    if not resumen or not str(resumen).strip():
        return "OK (resumen vacío, ignorado)"
    texto_clean = str(resumen)[:MAX_TEXTO]
    emb = _embed(texto_clean, is_query=False)
    if emb is None:
        return "⚠️ degradado: encoder no disponible"
    blob = emb.tobytes()
    dim = int(emb.shape[0])
    _init_db()
    with _write_lock, _connect() as c:
        cur = c.execute(
            """INSERT INTO bloques
                 (session_id, resumen, desde_ts, hasta_ts, n_mensajes, ts,
                  embedding, embed_dim, embed_model)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id or "global", texto_clean, desde_ts, hasta_ts,
             int(n_mensajes) if n_mensajes else None, _now_iso(),
             blob, dim, EMBED_MODEL),
        )
        blq_id = cur.lastrowid
    return f"OK id={blq_id} bloque ({n_mensajes or '?'} mensajes)"


def buscar(query: str, k: int = 5, tipo: str = "ambos", session_id: str = None,
           rol: str = None, dias_max: int = None) -> str:
    """Top-K resultados semánticamente similares (cosine numpy in-memory).

    `tipo`: "msg" (solo mensajes), "bloque" (solo resúmenes), "ambos" (default).
    Cada resultado lleva campo `tipo` para que el LLM lo distinga.

    Retorna JSON: [{id, tipo, rol|n_mensajes, ts, texto, score}, ...]
    """
    if not query or not str(query).strip():
        return json.dumps([], ensure_ascii=False)
    try:
        k = max(1, min(int(k or 5), 20))
    except (TypeError, ValueError):
        k = 5
    if tipo not in ("ambos", "msg", "bloque"):
        tipo = "ambos"

    q_emb = _embed(str(query), is_query=True)
    if q_emb is None:
        return json.dumps({"error": "⚠️ degradado: sentence-transformers no instalado"},
                          ensure_ascii=False)
    q_dim = int(q_emb.shape[0])

    _init_db()
    cutoff = None
    if dias_max:
        cutoff = (datetime.now(timezone.utc)
                  - timedelta(days=int(dias_max))).strftime("%Y-%m-%dT%H:%M:%SZ")

    # ── messages ────────────────────────────────────────────────────────
    msg_rows = []
    if tipo in ("ambos", "msg"):
        where, params = [], []
        if session_id:
            where.append("session_id = ?"); params.append(session_id)
        if rol:
            where.append("rol = ?"); params.append(rol)
        if cutoff:
            where.append("ts >= ?"); params.append(cutoff)
        sql = "SELECT id, session_id, rol, texto, ts, embedding, embed_dim FROM messages"
        if where:
            sql += " WHERE " + " AND ".join(where)
        with _connect() as c:
            msg_rows = c.execute(sql, params).fetchall()

    # ── bloques ─────────────────────────────────────────────────────────
    blq_rows = []
    if tipo in ("ambos", "bloque"):
        where, params = [], []
        if session_id:
            where.append("session_id = ?"); params.append(session_id)
        if cutoff:
            where.append("ts >= ?"); params.append(cutoff)
        sql = ("SELECT id, session_id, resumen, n_mensajes, desde_ts, hasta_ts, ts, "
               "embedding, embed_dim FROM bloques")
        if where:
            sql += " WHERE " + " AND ".join(where)
        with _connect() as c:
            blq_rows = c.execute(sql, params).fetchall()

    if not msg_rows and not blq_rows:
        return json.dumps([], ensure_ascii=False)

    # ── candidatos unificados ──────────────────────────────────────────
    cands = []  # tuplas (embed, dict_resultado_sin_score)
    descartadas = 0
    for r in msg_rows:
        if r["embed_dim"] != q_dim:
            descartadas += 1; continue
        cands.append((
            np.frombuffer(r["embedding"], dtype=np.float32),
            {
                "id": int(r["id"]),
                "tipo": "msg",
                "rol": r["rol"],
                "ts": r["ts"],
                "texto": r["texto"][:600],
            },
        ))
    for r in blq_rows:
        if r["embed_dim"] != q_dim:
            descartadas += 1; continue
        cands.append((
            np.frombuffer(r["embedding"], dtype=np.float32),
            {
                "id": int(r["id"]),
                "tipo": "bloque",
                "n_mensajes": r["n_mensajes"],
                "desde_ts": r["desde_ts"],
                "hasta_ts": r["hasta_ts"],
                "ts": r["ts"],
                "texto": r["resumen"][:600],
            },
        ))
    if descartadas:
        logger.warning(f"buscar_memoria: ignoradas {descartadas} filas con dim distinto")
    if not cands:
        return json.dumps([], ensure_ascii=False)

    M = np.vstack([c[0] for c in cands])
    scores = (M @ q_emb).astype(float)

    if len(scores) <= k:
        idxs = np.argsort(-scores)
    else:
        idxs = np.argpartition(-scores, k)[:k]
        idxs = idxs[np.argsort(-scores[idxs])]

    out = []
    for i in idxs[:k]:
        item = dict(cands[int(i)][1])  # copia
        item["score"] = round(float(scores[int(i)]), 4)
        out.append(item)
    return json.dumps(out, ensure_ascii=False)


def estado() -> str:
    """Stats: mensajes + bloques + modelo + tamaño DB."""
    _init_db()
    with _connect() as c:
        msg_total = c.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
        por_rol = dict(c.execute(
            "SELECT rol, COUNT(*) FROM messages GROUP BY rol").fetchall())
        msg_ultimo = c.execute("SELECT MAX(ts) FROM messages").fetchone()[0]
        blq_total = c.execute("SELECT COUNT(*) FROM bloques").fetchone()[0]
        blq_ultimo = c.execute("SELECT MAX(ts) FROM bloques").fetchone()[0]
        blq_sum_n = c.execute("SELECT COALESCE(SUM(n_mensajes), 0) FROM bloques").fetchone()[0]
        modelos = sorted(set(
            [r[0] for r in c.execute("SELECT DISTINCT embed_model FROM messages").fetchall()] +
            [r[0] for r in c.execute("SELECT DISTINCT embed_model FROM bloques").fetchall()]
        ))
    enc = _get_encoder()
    try:
        bytes_db = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    except Exception:
        bytes_db = 0
    return json.dumps({
        "mensajes": {
            "total": msg_total,
            "por_rol": por_rol,
            "ultimo_ts": msg_ultimo,
        },
        "bloques": {
            "total": blq_total,
            "ultimo_ts": blq_ultimo,
            "mensajes_resumidos_acumulados": blq_sum_n,
        },
        "modelo_actual": EMBED_MODEL,
        "modelos_en_db": modelos,
        "modelo_cargado": enc is not None,
        "bytes_db": bytes_db,
        "db_path": DB_PATH,
    }, ensure_ascii=False, indent=2)


def limpiar(antes_de_ts: str = None, session_id: str = None, tipo: str = "ambos") -> str:
    """Borra mensajes y/o bloques filtrados. `tipo` = "ambos"|"msg"|"bloque".
    Retorna cuántos por tabla."""
    if tipo not in ("ambos", "msg", "bloque"):
        return f"❌ tipo '{tipo}' no válido (use ambos|msg|bloque)"
    _init_db()
    where, params = [], []
    if antes_de_ts:
        where.append("ts < ?"); params.append(antes_de_ts)
    if session_id:
        where.append("session_id = ?"); params.append(session_id)
    suffix = " WHERE " + " AND ".join(where) if where else ""

    counts = {}
    with _write_lock, _connect() as c:
        if tipo in ("ambos", "msg"):
            counts["mensajes"] = c.execute("DELETE FROM messages" + suffix, params).rowcount
        if tipo in ("ambos", "bloque"):
            counts["bloques"] = c.execute("DELETE FROM bloques" + suffix, params).rowcount
    return json.dumps({"borrados": counts}, ensure_ascii=False)


def reindexar(modelo_nuevo: str = None) -> str:
    """Stub Fase 1.5: cambiar de modelo requiere recomputar embeddings."""
    return ("⚠️ reindexar pendiente Fase 1.5 — para cambiar de modelo, borra la DB "
            "con limpiar() y reingresta. O implementar batch re-embed.")


# ── Dispatcher ───────────────────────────────────────────────────────────

_OPERACIONES = {
    "ingestar": ingestar,
    "ingestar_bloque": ingestar_bloque,
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
