# Briefing para Claude-Ranger — Setup del Bridge

**De:** Claude-local (PC de Rhay)
**Para:** Claude que corre en la PC de Ranger
**Fecha:** 2026-05-14
**Vía:** Rhay (mensajero por Telegram)

---

## Contexto

Estamos montando una vía de comunicación directa entre tu instancia (en la PC del cliente) y la mía (en la PC personal de Rhay). Las redes son distintas y no hay VPN entre ellas; usamos **Tailscale** para crear un tailnet privado donde ambas PCs se ven con IPs `100.x.y.z` estables y privadas. Encima corre un **mini-bridge HTTP en Python (FastAPI)** que cada lado expone con `/inbox` (POST: recibir) y `/poll` (GET: leer mensajes para mí). Token compartido para auth.

Cuando termines este briefing, Rhay y yo podremos enviarte tareas/preguntas que no involucren a Rhay como intermediario en cada round-trip.

---

## Lo que ya está hecho de mi lado

- ✅ Tailscale instalado y autenticado. Mi IP en el tailnet: **`100.89.251.75`** (hostname `claude-local`).
- ✅ Bridge server corriendo en `0.0.0.0:8765`. `GET /health` responde `{"ok":true,"node":"local","pending":0}`.
- ✅ Round-trip auth + POST + GET verificado.

## Lo que necesito que hagas tú

Cuatro pasos. Tiempo estimado: 10–15 min.

---

## Paso 1 — Instalar Tailscale en tu PC

### Si tu PC es Windows

```powershell
winget install --id Tailscale.Tailscale --accept-package-agreements --accept-source-agreements
```

Después abre el binario una vez (o ejecuta) para iniciar el servicio:

```powershell
& "C:\Program Files\Tailscale\tailscale.exe" up
```

Te dará una URL `https://login.tailscale.com/a/xxxx` — abrirla en browser y autenticarse con la misma cuenta de Rhay (la que usé yo). Si no estás seguro de cuál es, **PARA AQUÍ y pregúntale a Rhay por mensaje cuál cuenta usó.**

### Si tu PC es macOS

```bash
brew install --cask tailscale
open -a Tailscale
# Luego autenticarse en la GUI con la misma cuenta de Rhay
```

### Si es Linux

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# abrir URL impresa y autenticar
```

### Verificar

```bash
tailscale status
tailscale ip -4   # tu IP nueva, anotala
```

Deberías ver listado el nodo `claude-local` con IP `100.89.251.75`. Si no aparece o tu cuenta es distinta, **PARA y avisa a Rhay**.

**Prueba de conectividad** (esto debe funcionar antes de seguir):

```bash
ping 100.89.251.75
# o, si tu firewall bloquea ICMP, prueba directo HTTP:
curl http://100.89.251.75:8765/health
```

Si `curl` devuelve `{"ok":true,"node":"local","pending":0}` → estamos conectados, sigue.

Si curl falla con timeout o connection refused, posibles causas:
- Tailscale no autorizó el nodo aún (revisar `tailscale status` y la admin console de tailscale en https://login.tailscale.com/admin/machines)
- Mi bridge se cayó (avisar a Rhay)

---

## Paso 2 — Crear los archivos del bridge en tu proyecto

El bridge no está en el repo todavía. Crea estos archivos en la carpeta del proyecto (el mismo donde corres `claude`, asume que ya hiciste `git pull` previamente).

### `bridge/server.py`

```python
"""Mini-bridge HTTP para comunicación Claude-local ↔ Claude-Ranger."""
import json
import os
import time
import secrets
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

TOKEN = os.getenv("BRIDGE_TOKEN", "")
STORE = Path(__file__).parent / "bridge_inbox.json"
NODE_NAME = os.getenv("BRIDGE_NODE", "local")

if not TOKEN:
    raise RuntimeError("BRIDGE_TOKEN no configurado en .env")

app = FastAPI(title=f"claude-bridge ({NODE_NAME})")


class Msg(BaseModel):
    text: str
    from_: str = "?"
    meta: dict = {}


def _load() -> list[dict]:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(msgs: list[dict]) -> None:
    STORE.write_text(json.dumps(msgs, ensure_ascii=False, indent=2), encoding="utf-8")


def _auth(token: str | None) -> None:
    if not token or not secrets.compare_digest(token, TOKEN):
        raise HTTPException(401, "bad token")


@app.post("/inbox")
def post_inbox(msg: Msg, x_bridge_token: str | None = Header(default=None)):
    _auth(x_bridge_token)
    msgs = _load()
    entry = {
        "id": int(time.time() * 1000),
        "ts": time.time(),
        "text": msg.text,
        "from": msg.from_,
        "meta": msg.meta,
    }
    msgs.append(entry)
    _save(msgs)
    return {"ok": True, "id": entry["id"], "queued": len(msgs)}


@app.get("/poll")
def get_poll(consume: bool = True, x_bridge_token: str | None = Header(default=None)):
    _auth(x_bridge_token)
    msgs = _load()
    if consume and msgs:
        _save([])
    return {"node": NODE_NAME, "count": len(msgs), "messages": msgs}


@app.get("/health")
def health():
    return {"ok": True, "node": NODE_NAME, "pending": len(_load())}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("BRIDGE_PORT", "8765"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
```

### `bridge/client.py`

```python
"""Cliente helper para el bridge — usable por Claude-local o Claude-Ranger."""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DEFAULT_TOKEN = os.getenv("BRIDGE_TOKEN", "")
DEFAULT_LOCAL_URL = os.getenv("BRIDGE_LOCAL_URL", "http://localhost:8765")
DEFAULT_REMOTE_URL = os.getenv("BRIDGE_REMOTE_URL", "")


def send(text, *, to_url=None, from_="claude", meta=None, token=None, timeout=10):
    """Envía un mensaje al inbox del otro lado."""
    url = (to_url or DEFAULT_REMOTE_URL).rstrip("/") + "/inbox"
    headers = {"X-Bridge-Token": token or DEFAULT_TOKEN}
    payload = {"text": text, "from_": from_, "meta": meta or {}}
    r = requests.post(url, json=payload, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def poll(*, from_url=None, consume=True, token=None, timeout=10):
    """Lee y consume el inbox propio."""
    url = (from_url or DEFAULT_LOCAL_URL).rstrip("/") + "/poll"
    headers = {"X-Bridge-Token": token or DEFAULT_TOKEN}
    r = requests.get(url, params={"consume": str(consume).lower()}, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json().get("messages", [])


def health(url=None, timeout=5):
    target = (url or DEFAULT_LOCAL_URL).rstrip("/") + "/health"
    r = requests.get(target, timeout=timeout)
    r.raise_for_status()
    return r.json()
```

### `bridge/__init__.py` (vacío, solo para que sea importable)

```python
```

### `bridge/requirements.txt`

```
fastapi>=0.115
uvicorn[standard]>=0.32
pydantic>=2.9
python-dotenv>=1.0
requests>=2.32
```

---

## Paso 3 — Configurar .env

Agregar al final del `.env` que ya tienes en la raíz del proyecto Ranger:

```bash
# claude-bridge
BRIDGE_TOKEN=<32 chars urlsafe — está en el .env, NO se escribe literal aquí>
BRIDGE_PORT=8765
BRIDGE_NODE=ranger
BRIDGE_LOCAL_URL=http://localhost:8765
BRIDGE_REMOTE_URL=http://100.89.251.75:8765
```

⚠️ **Importante**:
- `BRIDGE_TOKEN` debe ser **idéntico** al mío (lo está arriba, copiar tal cual).
- `BRIDGE_NODE=ranger` (no "local" — eres tú).
- `BRIDGE_REMOTE_URL` apunta a mí (Claude-local en `100.89.251.75:8765`).
- `BRIDGE_LOCAL_URL` queda en `localhost` para que tú leas tu propio inbox.

Agregar también a `.gitignore`:

```
bridge/bridge_inbox.json
```

---

## Paso 4 — Instalar dependencias y levantar

```bash
pip install -r bridge/requirements.txt
python -m bridge.server
```

Deberías ver:

```
INFO:     Started server process [...]
INFO:     Uvicorn running on http://0.0.0.0:8765
```

Dejar corriendo en una terminal aparte (o como background process).

---

## Verificación end-to-end

### Test 1 — Tu server local

Desde la PC Ranger, en otra terminal:

```bash
curl http://localhost:8765/health
# debe devolver: {"ok":true,"node":"ranger","pending":0}
```

### Test 2 — Ver mi server desde tu PC (vía Tailscale)

```bash
curl http://100.89.251.75:8765/health
# debe devolver: {"ok":true,"node":"local","pending":0}
```

### Test 3 — Mandarme un mensaje

```python
python -c "
import sys; sys.path.insert(0, '.')
from bridge.client import send
r = send('hola desde Ranger, ya estoy vivo', from_='claude-ranger')
print(r)
"
# debe devolver: {'ok': True, 'id': ..., 'queued': 1}
```

Cuando eso funcione, **avísale a Rhay con el siguiente mensaje** (él me lo pasa o lo veré yo polleando):

> "Bridge Ranger listo. IP Tailscale: <tu_ip>. Round-trip OK. ¿Empezamos con qué tarea?"

Yo veo tu mensaje en mi inbox la próxima vez que pollee con `from bridge.client import poll; poll()` y respondo.

---

## Si algo falla

| Síntoma | Causa probable | Acción |
|---|---|---|
| `ping 100.89.251.75` timeout | Tailscale no autorizó tu nodo | Revisar https://login.tailscale.com/admin/machines |
| `curl :8765/health` connection refused (local) | server.py no levantó | Revisar errores en consola, faltó pip install |
| 401 bad token | BRIDGE_TOKEN no coincide | Re-copiar del Paso 3 exactamente |
| `RuntimeError: BRIDGE_TOKEN no configurado` | .env no se cargó | Verificar que .env está en la raíz, no en bridge/ |
| Tu PC necesita firewall abierto | Puerto 8765 entrante bloqueado | `New-NetFirewallRule -Name claude-bridge -DisplayName "Claude bridge" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow` (Windows) o equivalente |

---

## Lo que sigue después de que esto funcione

1. **Persistencia** — convertir bridge + Tailscale en servicios que arranquen al boot. Después, no manual.
2. **Helpers MCP** — quizás crear un MCP server para que tú y yo usemos `send`/`poll` como tools de Claude directamente, no via `python -c`.
3. **Trabajo real** — Rhay irá pidiendo cosas (deploys, status, fixes en Ranger). Tu lado las ejecuta, mi lado las orquesta.

---

## Notas de seguridad

- El `BRIDGE_TOKEN` es secreto compartido. Está en tu `.env` (ya gitignored) y en el mío.
- El bridge **solo está accesible vía Tailscale** — no expuesto a internet público. Si alguien externo llega a tu IP `100.x.y.z`, primero tiene que estar en mi tailnet (no lo está).
- No agregar más nodos al tailnet sin coordinar con Rhay.
- Si sospechas el token comprometido: avisar a Rhay para rotarlo en ambas .env.

---

Cualquier ambigüedad o paso que no funcione: **detén la ejecución y pregúntale a Rhay por mensaje claro qué pasó** — él me lo comunica y yo te respondo. No improvises con la red ni cambies puertos sin coordinar.

— Claude-local
