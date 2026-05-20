# claude_server

Bridge multi-dispositivo hacia Claude vía Claude Agent SDK.

```
dispositivo ──POST /inbox/{node}──▶ ┌────────────────────┐
                                     │  claude_server     │
dispositivo ◀──SSE /stream/{node}─── │  port 8200         │
                                     │                    │
                                     │  chat.db (SQLite)  │
                                     │                    │
                                     │  worker:           │
                                     │  claude_local      │
                                     │  → Agent SDK       │
                                     │  → claude-opus-4-7 │
                                     └────────────────────┘
```

## Arranque

```bash
venv/Scripts/python.exe -m uvicorn claude_server.main:app --host 127.0.0.1 --port 8200
# para acceso por Tailscale: --host 0.0.0.0
```

Al primer arranque imprime el token del `device` default. Se guarda en
`claude_server/data/.default_token` y se cachea en la DB
(`devices.token_hash` con SHA-256).

## Endpoints

| Método | Path | Auth | Descripción |
|---|---|---|---|
| GET  | `/health` | público | smoke |
| POST | `/inbox/{node_id}` | Bearer | encola mensaje. Si `node_id=local`, kickea worker SDK |
| GET  | `/poll/{node_id}?after=N&limit=200` | Bearer | mensajes con `id > after` |
| GET  | `/stream/{node_id}?after=N&token=...` | token (header o qs) | SSE live |
| GET  | `/`, `/static/*` | público | UI standalone |

Auth: `Authorization: Bearer <token>` o `X-Bridge-Token: <token>`.
EventSource del browser usa `?token=...` porque no envía headers custom.

## Modelo de datos

```sql
messages(id, ts, node_id, from_node, direction, kind, content, meta)
devices(device_id, token_hash, name, created_at, last_seen)
```

- `node_id`: dueño del inbox (a quién va dirigido).
- `from_node`: emisor.
- `direction`: `'out'` (el dueño del inbox enviará al receptor) o `'in'` (recibido).
- `kind`: `text`, `text_chunk`, `done`, `error`, `system`.
- `meta`: JSON con `session_id`, `cost_usd`, `duration_ms`, etc.

## Conversación

El worker mantiene `session_id` por `from_node` en memoria. Cada device
retoma su propia sesión turno a turno. Reiniciar el server reinicia las
sesiones (persistencia → fase 2).

## Tests humo

```bash
TOKEN=$(cat claude_server/data/.default_token)
curl http://127.0.0.1:8200/health
curl -X POST http://127.0.0.1:8200/inbox/local \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"text":"hola","from_node":"smoketest"}'
# Esperar ~5-25s (primer turno cold)
curl "http://127.0.0.1:8200/poll/smoketest?after=0" \
  -H "Authorization: Bearer $TOKEN"
```

## Pendiente (fases siguientes)

- Persistir `_sessions` en DB.
- piper-tts streaming por párrafo + audio en UI.
- STT desde mic del browser (Whisper).
- Relay a Ranger vía bridge HTTP existente.
- NSSM para correr como servicio Windows.
- Tokens revocables por device (UI admin).
