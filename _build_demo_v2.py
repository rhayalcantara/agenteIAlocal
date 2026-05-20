"""Builds DEMO_OPERACIONES_RANGER_v2.html with embedded screenshots."""
import sys, json, base64
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

b64 = json.loads(Path("_demo_b64.json").read_text())

def img(fn):
    return f"data:image/png;base64,{b64[fn]}"

TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OperacionesRanger - Demo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=DM+Sans:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
:root {
  --bg: #0a0e1a; --bg-2: #141a2b; --ink: #e8eef7; --mute: #8a96b0;
  --gold: #d4a843; --red: #c43225; --rule: #2a334d;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; background: var(--bg); color: var(--ink); font-family: "DM Sans", system-ui, sans-serif; overflow: hidden; }
body { display: flex; align-items: center; justify-content: center; }
.stage { width: min(100vw, 1440px); height: min(100vh, 900px); max-height: 92vh; aspect-ratio: 16/10; position: relative; overflow: hidden; border: 1px solid var(--rule); background: var(--bg); }
.hud { position: absolute; top: 14px; left: 24px; right: 24px; display: flex; justify-content: space-between; align-items: center; font-family: "Space Mono", monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--mute); text-transform: uppercase; z-index: 30; pointer-events: none; text-shadow: 0 0 8px rgba(10,14,26,0.9); }
.hud .left { display: flex; align-items: center; gap: 10px; }
.hud .dot { width: 8px; height: 8px; background: var(--red); border-radius: 50%; animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.3; } }
.hud .right { display: flex; gap: 18px; }
.progress { position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: rgba(42, 51, 77, 0.5); z-index: 30; }
.progress-fill { height: 100%; background: var(--gold); width: 0; animation: prog 40s linear forwards; }
@keyframes prog { to { width: 100%; } }
.panel { position: absolute; inset: 0; opacity: 0; pointer-events: none; }
.panel.with-shot .shot { position: absolute; inset: 0; background-size: cover; background-position: center; background-repeat: no-repeat; }
.panel.with-shot .overlay { position: absolute; left: 0; top: 0; bottom: 0; width: 44%; background: linear-gradient(to right, rgba(10,14,26,0.96) 0%, rgba(10,14,26,0.92) 60%, rgba(10,14,26,0) 100%); padding: 60px 48px 60px 56px; display: flex; flex-direction: column; justify-content: center; }
.panel.with-shot.overlay-right .overlay { left: auto; right: 0; background: linear-gradient(to left, rgba(10,14,26,0.96) 0%, rgba(10,14,26,0.92) 60%, rgba(10,14,26,0) 100%); padding: 60px 56px 60px 48px; align-items: flex-end; text-align: right; }
@media (max-width: 760px) {
  .panel.with-shot .overlay { width: 100%; padding: 40px 28px; background: linear-gradient(to bottom, rgba(10,14,26,0.95), rgba(10,14,26,0.85)); }
  .panel.with-shot.overlay-right .overlay { text-align: left; align-items: flex-start; }
}
.tag { font-family: "Space Mono", monospace; font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase; color: var(--gold); margin-bottom: 16px; }
.tag::before { content: "BLK "; letter-spacing: 0; }
h2.title { font-family: "Anton", sans-serif; font-size: clamp(36px, 4.5vw, 60px); line-height: 0.95; letter-spacing: -0.01em; text-transform: uppercase; margin-bottom: 16px; }
h2.title .gold { color: var(--gold); }
p.body { font-size: 17px; color: var(--mute); line-height: 1.5; max-width: 460px; }
p.body strong { color: var(--ink); font-weight: 600; }
.panel-1 { animation: fade1 4s ease forwards; display: flex; flex-direction: column; justify-content: center; padding: 80px; }
@keyframes fade1 { 0% { opacity:0; transform: translateY(8px); } 12%,90% { opacity:1; transform: translateY(0); } 100% { opacity:0; } }
.brand-tag { font-family: "Space Mono", monospace; font-size: 12px; letter-spacing: 0.3em; text-transform: uppercase; color: var(--gold); margin-bottom: 24px; }
h1.hero { font-family: "Anton", sans-serif; font-size: clamp(60px, 9vw, 124px); line-height: 0.88; letter-spacing: -0.015em; text-transform: uppercase; }
h1.hero .gold { color: var(--gold); }
p.lead { font-family: "DM Sans", sans-serif; font-size: clamp(18px, 2.2vw, 26px); color: var(--mute); margin-top: 20px; max-width: 760px; }
.panel-2 { animation: fade2 5s ease forwards; animation-delay: 4s; }
@keyframes fade2 { 0% { opacity:0; } 10%,92% { opacity:1; } 100% { opacity:0; } }
.panel-3 { animation: fade3 7s ease forwards; animation-delay: 9s; }
@keyframes fade3 { 0% { opacity:0; } 8%,93% { opacity:1; } 100% { opacity:0; } }
.panel-4 { animation: fade4 7s ease forwards; animation-delay: 16s; }
@keyframes fade4 { 0% { opacity:0; } 8%,93% { opacity:1; } 100% { opacity:0; } }
.panel-5 { animation: fade5 6s ease forwards; animation-delay: 23s; }
@keyframes fade5 { 0% { opacity:0; } 9%,92% { opacity:1; } 100% { opacity:0; } }
.panel-6 { animation: fade6 6s ease forwards; animation-delay: 29s; }
@keyframes fade6 { 0% { opacity:0; } 9%,92% { opacity:1; } 100% { opacity:0; } }
.panel-7 { animation: fade7 5s ease forwards; animation-delay: 35s; display:flex; flex-direction:column; justify-content:center; padding: 80px; text-align: center; }
@keyframes fade7 { 0% { opacity:0; transform: translateY(8px); } 12% { opacity:1; transform: translateY(0); } 100% { opacity:1; } }
.close-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; max-width: 980px; margin: 0 auto 36px; }
.cs .v { font-family: "Anton", sans-serif; font-size: clamp(40px, 5.5vw, 76px); line-height:1; color: var(--gold); }
.cs .l { font-family: "Space Mono", monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--mute); text-transform: uppercase; margin-top: 6px; }
.cta { font-family: "Anton", sans-serif; font-size: clamp(40px, 6vw, 78px); line-height: 1; text-transform: uppercase; }
.cta .gold { color: var(--gold); }
.cta-sub { font-family: "DM Sans", sans-serif; color: var(--mute); font-size: 18px; margin-top: 16px; }
.replay { position: absolute; bottom: 22px; right: 22px; background: transparent; border: 1px solid var(--gold); color: var(--gold); padding: 8px 16px; font-family: "Space Mono", monospace; font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase; cursor: pointer; opacity: 0; animation: showR 1s ease 39s forwards; z-index: 31; }
@keyframes showR { to { opacity: 1; } }
.replay:hover { background: var(--gold); color: var(--bg); }
</style>
</head>
<body>
<div class="stage">
  <div class="hud">
    <div class="left"><span class="dot"></span><span id="hud-label">DEMO 01/07</span></div>
    <div class="right"><span>OPERACIONESRANGER - CAPTURAS REALES</span><span id="hud-time">00:00</span></div>
  </div>

  <div class="panel panel-1">
    <div class="brand-tag">Demo - 40 segundos</div>
    <h1 class="hero">Operaciones<span class="gold">Ranger</span></h1>
    <p class="lead">Sistema de gestion de turnos para guardianes de seguridad. Calculo automatico, integrado con nomina. <strong style="color:var(--ink)">Backend + Frontend listos.</strong></p>
  </div>

  <div class="panel panel-2 with-shot">
    <div class="shot" style="background-image:url('__LOGIN__')"></div>
    <div class="overlay">
      <div class="tag">Acceso seguro - paso 1</div>
      <h2 class="title">Login con <span class="gold">JWT + Bcrypt.</span></h2>
      <p class="body">Acceso por usuario y contrasena, roles ADMIN / SUPERVISOR / CONSULTA. Tokens con refresh automatico. Auditoria de cada login y cambio de datos.</p>
    </div>
  </div>

  <div class="panel panel-3 with-shot overlay-right">
    <div class="shot" style="background-image:url('__DASH__')"></div>
    <div class="overlay">
      <div class="tag">Vista general - paso 2</div>
      <h2 class="title">Dashboard <span class="gold">en vivo.</span></h2>
      <p class="body">Turnos del mes, guardianes activos, pendientes de procesar, horas totales. Todo se actualiza en tiempo real desde la base de datos.</p>
    </div>
  </div>

  <div class="panel panel-4 with-shot">
    <div class="shot" style="background-image:url('__TURNOS__')"></div>
    <div class="overlay">
      <div class="tag">Gestion de turnos - paso 3</div>
      <h2 class="title">Calculo <span class="gold">automatico.</span></h2>
      <p class="body">El sistema separa solo: <strong>horas normales</strong> (10) y <strong>extras</strong> (2), tipo <strong>diurno/nocturno</strong>, detecta feriados. Filtros por fecha, tipo y estado de procesamiento. <strong>Cero calculo manual.</strong></p>
    </div>
  </div>

  <div class="panel panel-5 with-shot overlay-right">
    <div class="shot" style="background-image:url('__FERIA__')"></div>
    <div class="overlay">
      <div class="tag">Calendario - paso 4</div>
      <h2 class="title">Feriados <span class="gold">sincronizados.</span></h2>
      <p class="body">Calendario anual con feriados <strong>NACIONALES</strong> + <strong>DECRETO</strong>. El sistema aplica recargo automatico en cada turno trabajado en feriado. Sin reclamos por horas mal pagadas.</p>
    </div>
  </div>

  <div class="panel panel-6 with-shot">
    <div class="shot" style="background-image:url('__REP__')"></div>
    <div class="overlay">
      <div class="tag">Integracion nomina - paso 5</div>
      <h2 class="title">Un clic <span class="gold">a</span> nomina.</h2>
      <p class="body">Genera reportes CSV por periodo (quincena) listos para tu sistema de nomina. Incluye normales, extras, incentivos y feriados. Historial completo de reportes generados.</p>
    </div>
  </div>

  <div class="panel panel-7">
    <div class="close-stats">
      <div class="cs"><div class="v">12h a 5min</div><div class="l">Por quincena</div></div>
      <div class="cs"><div class="v">0%</div><div class="l">Error de calculo</div></div>
      <div class="cs"><div class="v">100%</div><div class="l">Integrado con nomina</div></div>
    </div>
    <h2 class="cta">Lo activamos?<br><span class="gold">Demo en vivo cuando quieran.</span></h2>
    <p class="cta-sub">Backend Node.js + Frontend Angular ya construidos. Solo falta tu OK para produccion.</p>
  </div>

  <button class="replay" onclick="location.reload()">REPLAY</button>
  <div class="progress"><div class="progress-fill"></div></div>
</div>

<script>
const labels = [
  { until: 4,  text: 'DEMO 01/07 - HOOK' },
  { until: 9,  text: 'DEMO 02/07 - LOGIN' },
  { until: 16, text: 'DEMO 03/07 - DASHBOARD' },
  { until: 23, text: 'DEMO 04/07 - TURNOS' },
  { until: 29, text: 'DEMO 05/07 - FERIADOS' },
  { until: 35, text: 'DEMO 06/07 - REPORTES' },
  { until: 41, text: 'DEMO 07/07 - CIERRE' },
];
const start = Date.now();
const tick = () => {
  const t = (Date.now() - start) / 1000;
  const mm = String(Math.floor(t / 60)).padStart(2,'0');
  const ss = String(Math.floor(t % 60)).padStart(2,'0');
  document.getElementById('hud-time').textContent = mm + ':' + ss;
  const lab = labels.find(l => t < l.until);
  if (lab) document.getElementById('hud-label').textContent = lab.text;
  if (t < 42) requestAnimationFrame(tick);
};
tick();
</script>
</body>
</html>"""

html = TEMPLATE
html = html.replace("__LOGIN__", img("01_login.png"))
html = html.replace("__DASH__",  img("03_dashboard.png"))
html = html.replace("__TURNOS__",img("04_turnos.png"))
html = html.replace("__FERIA__", img("05_feriados.png"))
html = html.replace("__REP__",   img("08_reportes.png"))

out = Path("DEMO_OPERACIONES_RANGER_v2.html")
out.write_text(html, encoding="utf-8")
print(f"OK: {out} -> {out.stat().st_size//1024}KB")
