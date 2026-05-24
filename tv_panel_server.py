"""Panel de datos para mostrar en la TV (navegador) — sirve un dashboard y /data.json.

Uso:
    python tv_panel_server.py [--port 8095]
Luego en la TV (por ADB) abrir:  http://<IP-PC>:<port>/

Sirve un panel oscuro optimizado para 1920x1080 que muestra hora/fecha y
stats de la PC (CPU/RAM/disco), refrescando cada 2s. Es un punto de partida:
se le pueden añadir más datos en /data.json.
"""
import argparse
import json
import os
import socket
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AGENDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agente_core", "data", "agenda.json")

try:
    import psutil
except Exception:
    psutil = None

BOOT = time.time()

HTML = """<!DOCTYPE html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agente · Pendientes</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box;cursor:none}
  html,body{height:100%;background:#0a0e16;color:#e6edf3;
    font-family:-apple-system,Segoe UI,Roboto,sans-serif;overflow:hidden}
  .wrap{height:100vh;padding:36px 48px;display:flex;flex-direction:column}
  header{display:flex;justify-content:space-between;align-items:baseline;
    border-bottom:2px solid #232c3a;padding-bottom:14px;margin-bottom:10px}
  h1{font-size:42px;font-weight:800;letter-spacing:-1px}
  h1 .ico{color:#4dd4ac;margin-right:6px}
  .right{text-align:right}
  .clk{font-size:38px;color:#9aa7b4;font-variant-numeric:tabular-nums;font-weight:600}
  .clk .s{color:#4dd4ac;font-size:26px;vertical-align:super;margin-left:4px}
  .pag{font-size:14px;color:#5d6878;font-family:ui-monospace,monospace;margin-top:4px;letter-spacing:.05em}
  .pbar{height:3px;background:#161c28;border-radius:99px;margin:6px 0 12px;overflow:hidden}
  .pbar i{display:block;height:100%;background:linear-gradient(90deg,#4dd4ac,#58a6ff);
    width:0;transition:width .25s linear}
  .list{flex:1;overflow:hidden;display:flex;flex-direction:column}
  .row{display:flex;align-items:center;gap:20px;padding:11px 6px;border-bottom:1px solid #161c28}
  .dot{width:14px;height:14px;border-radius:50%;flex:0 0 auto}
  .on{background:#4dd4ac;box-shadow:0 0 12px #4dd4ac88}
  .off{background:#3d4757}
  .err{background:#f0666b;box-shadow:0 0 14px #f0666b88;animation:pulse 1.4s infinite}
  @keyframes pulse{50%{opacity:.5}}
  .main{flex:1;min-width:0}
  .nm{font-size:22px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.2}
  .meta{font-size:15px;color:#9aa7b4;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:ui-monospace,monospace}
  .meta .e{color:#f0666b}
  .meta .tipo{color:#58a6ff}
  .badge{font-size:13px;font-family:ui-monospace,monospace;padding:5px 12px;border-radius:99px;
    flex:0 0 auto;background:#141a26;border:1px solid #232c3a;color:#9aa7b4;letter-spacing:.05em}
  .badge.on{color:#4dd4ac;border-color:#4dd4ac}
  .stats{display:flex;gap:18px;padding:16px;background:#141a26;border:1px solid #232c3a;
    border-radius:12px;margin-top:14px;font-family:ui-monospace,monospace}
  .stat{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center}
  .stat .l{font-size:11px;color:#9aa7b4;text-transform:uppercase;letter-spacing:.1em}
  .stat .v{font-size:30px;font-weight:800;margin-top:4px;font-variant-numeric:tabular-nums}
  .stat .v.hi{color:#e3b341}
  .stat .v.crit{color:#f0666b}
  .foot{margin-top:10px;font-size:13px;color:#3d4757;font-family:ui-monospace,monospace;
    display:flex;justify-content:space-between}
  .empty{font-size:30px;color:#6a7785;text-align:center;margin-top:80px}
</style></head><body>
<div class="wrap">
  <header>
    <h1><span class="ico">▣</span> Agente · Pendientes</h1>
    <div class="right">
      <div class="clk"><span id="hm">--:--</span><span class="s" id="ss">00</span></div>
      <div class="pag" id="pag">Pág –/–</div>
    </div>
  </header>
  <div class="pbar"><i id="pbar"></i></div>
  <div class="list" id="list"><div class="empty">cargando…</div></div>
  <div class="stats">
    <div class="stat"><div class="l">CPU</div><div class="v" id="cpu">–</div></div>
    <div class="stat"><div class="l">RAM</div><div class="v" id="ram">–</div></div>
    <div class="stat"><div class="l">Disco</div><div class="v" id="disk">–</div></div>
    <div class="stat"><div class="l">Acciones</div><div class="v" id="nacc">–</div></div>
    <div class="stat"><div class="l">Host</div><div class="v" id="host" style="font-size:16px">–</div></div>
  </div>
  <div class="foot"><span id="fdate">—</span><span id="upd">conectando…</span></div>
</div>
<script>
function pad(n){return String(n).padStart(2,'0');}
function clk(){var d=new Date();
  document.getElementById('hm').textContent=pad(d.getHours())+':'+pad(d.getMinutes());
  document.getElementById('ss').textContent=pad(d.getSeconds());
  document.getElementById('fdate').textContent=d.toLocaleDateString('es-DO',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
}
function fecha(s){if(!s)return 'nunca';try{var d=new Date(s);
  var hoy=new Date(); var ayer=new Date(hoy); ayer.setDate(hoy.getDate()-1);
  var fmtTime=d.toLocaleTimeString('es-DO',{hour:'2-digit',minute:'2-digit'});
  if(d.toDateString()===hoy.toDateString())return 'hoy '+fmtTime;
  if(d.toDateString()===ayer.toDateString())return 'ayer '+fmtTime;
  return d.toLocaleDateString('es-DO',{day:'2-digit',month:'short'})+' '+fmtTime;
}catch(e){return s;}}
function setStat(id,v,hi,crit){var e=document.getElementById(id);e.textContent=v;
  e.classList.toggle('hi',v>=(hi||70));e.classList.toggle('crit',v>=(crit||90));}
// ── Paginación rotativa ─────────────────────────────────────
var PER_PAGE=3, ROTATE_MS=15000;
var acciones=[], pageIdx=0, rotateStart=Date.now();
function renderRow(a){
  var meta='<span class="tipo">'+(a.tipo||'')+'</span> · última '+fecha(a.ultima);
  if(a.error){meta+=' · <span class="e">'+(a.error+'').substring(0,60)+'</span>';}
  else if(a.resultado){meta+=' · '+a.resultado.substring(0,80);}
  var cls=a.error?'err':(a.activa?'on':'off');
  return '<div class="row"><div class="dot '+cls+'"></div>'+
    '<div class="main"><div class="nm">'+a.nombre+'</div><div class="meta">'+meta+'</div></div>'+
    '<div class="badge '+(a.activa?'on':'')+'">'+(a.activa?'ACTIVA':'pausada')+'</div></div>';
}
function renderPage(){
  var L=document.getElementById('list');
  if(!acciones.length){L.innerHTML='<div class="empty">No hay acciones en la agenda.</div>';
    document.getElementById('pag').textContent='Pág –/–';return;}
  var total=Math.max(1,Math.ceil(acciones.length/PER_PAGE));
  if(pageIdx>=total)pageIdx=0;
  var slice=acciones.slice(pageIdx*PER_PAGE,(pageIdx+1)*PER_PAGE);
  L.innerHTML=slice.map(renderRow).join('');
  document.getElementById('pag').textContent='Pág '+(pageIdx+1)+'/'+total;
  rotateStart=Date.now();
}
function nextPage(){pageIdx++;renderPage();}
function tickProgress(){
  var elapsed=Date.now()-rotateStart;
  var pct=Math.min(100,(elapsed/ROTATE_MS)*100);
  document.getElementById('pbar').style.width=pct+'%';
}
async function loadAg(){try{var r=await fetch('/pendientes.json',{cache:'no-store'});var j=await r.json();
  acciones=j.acciones||[];
  document.getElementById('nacc').textContent=j.total;
  renderPage();
}catch(e){}}
async function loadStats(){try{var r=await fetch('/data.json',{cache:'no-store'});var j=await r.json();
  setStat('cpu',j.cpu,70,90);setStat('ram',j.ram,70,90);setStat('disk',j.disk,80,95);
  document.getElementById('host').textContent=j.host;
  document.getElementById('upd').textContent='actualizado '+new Date().toLocaleTimeString('es-DO');
}catch(e){document.getElementById('upd').textContent='sin conexión con la PC';}}
clk();loadAg();loadStats();
setInterval(clk,1000);
setInterval(loadAg,5000);     // refresca datos sin cambiar de página
setInterval(loadStats,3000);
setInterval(nextPage,ROTATE_MS); // rota página cada 15s
setInterval(tickProgress,200);   // barra de progreso fluida
</script></body></html>"""


def stats():
    d = {"host": socket.gethostname(), "ts": time.time()}
    if psutil:
        d["cpu"] = round(psutil.cpu_percent(interval=0.0))
        d["ram"] = round(psutil.virtual_memory().percent)
        try:
            d["disk"] = round(psutil.disk_usage("C:\\").percent)
        except Exception:
            d["disk"] = round(psutil.disk_usage("/").percent)
    else:
        d["cpu"] = d["ram"] = d["disk"] = 0
    return d


def pendientes():
    """Lee las acciones de la agenda del agente (sus 'pendientes')."""
    try:
        with open(AGENDA, encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        data = {}
    out = []
    for a in data.get("acciones", []):
        out.append({
            "nombre": a.get("nombre", "?"),
            "tipo": a.get("tipo", ""),
            "activa": bool(a.get("activa")),
            "ultima": a.get("ultima_ejecucion"),
            "resultado": (a.get("ultimo_resultado") or "")[:140],
            "error": a.get("ultimo_error"),
        })
    return {"acciones": out, "total": len(out), "ts": time.time()}


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        p = self.path
        if p.startswith("/data.json"):
            body = json.dumps(stats()).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
        elif p.startswith("/pendientes.json"):
            body = json.dumps(pendientes(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
        else:
            # / y /pendientes ambos sirven la vista B definitiva (Agente + stats footer)
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8095)
    args = ap.parse_args()
    if psutil:
        psutil.cpu_percent(interval=0.0)  # primar lectura
    print(f"Panel en http://0.0.0.0:{args.port}  (psutil={'si' if psutil else 'no'})", flush=True)
    ThreadingHTTPServer(("0.0.0.0", args.port), H).serve_forever()
