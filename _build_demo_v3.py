"""Builds DEMO_OPERACIONES_RANGER_v3.html with: screenshots prominent + captions below + audio narration."""
import sys, json, base64
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

b64 = json.loads(Path("_demo_b64.json").read_text())

def img(fn):
    return f"data:image/png;base64,{b64[fn]}"

audio_b64 = base64.b64encode(Path("narration.mp3").read_bytes()).decode()
audio_uri = f"data:audio/mpeg;base64,{audio_b64}"

HTML = """<!DOCTYPE html>
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

.stage {
  width: min(100vw, 1440px);
  height: min(100vh, 900px);
  max-height: 96vh;
  aspect-ratio: 16/10;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--rule);
  background: var(--bg);
}

/* HUD */
.hud {
  position: absolute; top: 14px; left: 24px; right: 24px;
  display: flex; justify-content: space-between; align-items: center;
  font-family: "Space Mono", monospace; font-size: 11px;
  letter-spacing: 0.14em; color: var(--mute); text-transform: uppercase;
  z-index: 40; pointer-events: none;
  text-shadow: 0 1px 6px rgba(10,14,26,0.95), 0 0 14px rgba(10,14,26,0.6);
}
.hud .left { display:flex; align-items:center; gap:10px; }
.hud .dot { width: 8px; height: 8px; background: var(--red); border-radius: 50%; animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 50% { opacity: 0.3; } }
.hud .right { display:flex; gap:18px; }

/* PROGRESS */
.progress {
  position: absolute; bottom: 0; left: 0; right: 0;
  height: 3px; background: rgba(42, 51, 77, 0.5); z-index: 40;
}
.progress-fill { height: 100%; background: var(--gold); width: 0; }
.playing .progress-fill { animation: prog 40.4s linear forwards; }
@keyframes prog { to { width: 100%; } }

/* PANEL — full bleed screenshot up top, caption strip bottom */
.panel { position: absolute; inset: 0; opacity: 0; pointer-events: none; }

.panel.shot-panel .shot-wrap {
  position: absolute; left: 0; right: 0;
  top: 0; bottom: 22%;
  overflow: hidden;
  background: var(--bg-2);
}
.panel.shot-panel .shot {
  position: absolute; inset: 0;
  background-size: contain;
  background-position: center;
  background-repeat: no-repeat;
}
.panel.shot-panel .caption-strip {
  position: absolute; left: 0; right: 0; bottom: 0;
  height: 22%;
  background: linear-gradient(180deg, rgba(10,14,26,0.0) 0%, rgba(10,14,26,1) 18%, rgba(10,14,26,1) 100%);
  padding: 22px 56px 30px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
@media (max-width: 720px) {
  .panel.shot-panel .shot-wrap { bottom: 28%; }
  .panel.shot-panel .caption-strip { height: 28%; padding: 18px 22px 22px; }
}

.tag {
  font-family: "Space Mono", monospace;
  font-size: 11px; letter-spacing: 0.22em; text-transform: uppercase;
  color: var(--gold); margin-bottom: 8px;
}
.tag::before { content: ">> "; letter-spacing: 0; }

.title {
  font-family: "Anton", sans-serif;
  font-size: clamp(28px, 3.6vw, 46px);
  line-height: 1; letter-spacing: -0.005em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.title .gold { color: var(--gold); }

.subtext {
  font-size: 15px; color: var(--mute); line-height: 1.45;
  max-width: 900px;
}
.subtext strong { color: var(--ink); font-weight: 600; }

/* Panel 1 — Hook text only */
.panel-1 { display: flex; flex-direction: column; justify-content: center; padding: 80px; }
.brand-tag { font-family: "Space Mono", monospace; font-size: 12px; letter-spacing: 0.3em; text-transform: uppercase; color: var(--gold); margin-bottom: 24px; }
h1.hero { font-family: "Anton", sans-serif; font-size: clamp(60px, 9vw, 124px); line-height: 0.88; letter-spacing: -0.015em; text-transform: uppercase; }
h1.hero .gold { color: var(--gold); }
p.lead { font-family: "DM Sans", sans-serif; font-size: clamp(18px, 2.2vw, 26px); color: var(--mute); margin-top: 20px; max-width: 760px; }

/* Panel 7 — CTA text only */
.panel-7 { display:flex; flex-direction:column; justify-content:center; padding: 80px; text-align: center; }
.close-stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px; max-width: 980px; margin: 0 auto 36px; }
.cs .v { font-family: "Anton", sans-serif; font-size: clamp(40px, 5.5vw, 76px); line-height:1; color: var(--gold); }
.cs .l { font-family: "Space Mono", monospace; font-size: 11px; letter-spacing: 0.14em; color: var(--mute); text-transform: uppercase; margin-top: 6px; }
.cta { font-family: "Anton", sans-serif; font-size: clamp(40px, 6vw, 78px); line-height: 1; text-transform: uppercase; }
.cta .gold { color: var(--gold); }
.cta-sub { font-family: "DM Sans", sans-serif; color: var(--mute); font-size: 18px; margin-top: 16px; }

/* Animations triggered by .playing on stage */
.playing .panel-1 { animation: fade1 4s ease forwards; }
.playing .panel-2 { animation: fade2 5s ease forwards; animation-delay: 4s; }
.playing .panel-3 { animation: fade3 7s ease forwards; animation-delay: 9s; }
.playing .panel-4 { animation: fade4 7s ease forwards; animation-delay: 16s; }
.playing .panel-5 { animation: fade5 6s ease forwards; animation-delay: 23s; }
.playing .panel-6 { animation: fade6 6s ease forwards; animation-delay: 29s; }
.playing .panel-7 { animation: fade7 6s ease forwards; animation-delay: 35s; }

@keyframes fade1 { 0% { opacity:0; transform: translateY(8px); } 12%,90% { opacity:1; transform: translateY(0); } 100% { opacity:0; } }
@keyframes fade2 { 0% { opacity:0; } 10%,92% { opacity:1; } 100% { opacity:0; } }
@keyframes fade3 { 0% { opacity:0; } 8%,93% { opacity:1; } 100% { opacity:0; } }
@keyframes fade4 { 0% { opacity:0; } 8%,93% { opacity:1; } 100% { opacity:0; } }
@keyframes fade5 { 0% { opacity:0; } 9%,92% { opacity:1; } 100% { opacity:0; } }
@keyframes fade6 { 0% { opacity:0; } 9%,92% { opacity:1; } 100% { opacity:0; } }
@keyframes fade7 { 0% { opacity:0; transform: translateY(8px); } 12% { opacity:1; transform: translateY(0); } 100% { opacity:1; } }

/* Play button overlay (before first play) */
.play-veil {
  position: absolute; inset: 0;
  background: rgba(10, 14, 26, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 50;
  cursor: pointer;
  transition: opacity 0.4s ease;
}
.play-veil.hidden { opacity: 0; pointer-events: none; }
.play-icon {
  width: 110px; height: 110px;
  border: 3px solid var(--gold);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  background: rgba(212, 168, 67, 0.1);
  transition: transform 0.2s ease, background 0.2s ease;
}
.play-veil:hover .play-icon { transform: scale(1.05); background: rgba(212, 168, 67, 0.2); }
.play-icon::before {
  content: "";
  width: 0; height: 0;
  border-left: 36px solid var(--gold);
  border-top: 22px solid transparent;
  border-bottom: 22px solid transparent;
  margin-left: 10px;
}
.play-label {
  margin-top: 22px;
  font-family: "Anton", sans-serif;
  font-size: 28px;
  letter-spacing: 0.04em;
  color: var(--ink);
  text-transform: uppercase;
}
.play-sub {
  margin-top: 6px;
  font-family: "Space Mono", monospace;
  font-size: 12px;
  letter-spacing: 0.16em;
  color: var(--mute);
  text-transform: uppercase;
}

.replay {
  position: absolute; bottom: 22px; right: 22px;
  background: transparent; border: 1px solid var(--gold); color: var(--gold);
  padding: 8px 16px; font-family: "Space Mono", monospace; font-size: 11px;
  letter-spacing: 0.16em; text-transform: uppercase; cursor: pointer;
  opacity: 0; z-index: 41;
  transition: opacity 0.4s ease;
}
.replay.show { opacity: 1; }
.replay:hover { background: var(--gold); color: var(--bg); }

/* mute/unmute */
.audio-toggle {
  position: absolute; bottom: 22px; left: 22px;
  background: transparent; border: 1px solid var(--rule); color: var(--mute);
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; opacity: 0; z-index: 41;
  font-size: 16px;
  transition: opacity 0.4s ease, border-color 0.2s, color 0.2s;
}
.audio-toggle.show { opacity: 0.7; }
.audio-toggle:hover { opacity: 1; border-color: var(--gold); color: var(--gold); }
</style>
</head>
<body>
<div class="stage" id="stage">

  <div class="hud">
    <div class="left"><span class="dot"></span><span id="hud-label">DEMO 01/07</span></div>
    <div class="right"><span>OPERACIONESRANGER - CAPTURAS REALES</span><span id="hud-time">00:00</span></div>
  </div>

  <!-- 1: Hook -->
  <div class="panel panel-1">
    <div class="brand-tag">Demo - 40 segundos</div>
    <h1 class="hero">Operaciones<span class="gold">Ranger</span></h1>
    <p class="lead">Sistema de gestion de turnos para guardianes de seguridad. <strong style="color:var(--ink)">Backend + Frontend listos para produccion.</strong></p>
  </div>

  <!-- 2: Login -->
  <div class="panel panel-2 shot-panel">
    <div class="shot-wrap"><div class="shot" style="background-image:url('__LOGIN__')"></div></div>
    <div class="caption-strip">
      <div class="tag">Paso 1 - Acceso seguro</div>
      <div class="title">Login con <span class="gold">JWT + Bcrypt</span></div>
      <p class="subtext">Tres roles: <strong>administrador</strong>, <strong>supervisor</strong>, <strong>consulta</strong>. Tokens con refresh automatico. Auditoria de cada acceso.</p>
    </div>
  </div>

  <!-- 3: Dashboard -->
  <div class="panel panel-3 shot-panel">
    <div class="shot-wrap"><div class="shot" style="background-image:url('__DASH__')"></div></div>
    <div class="caption-strip">
      <div class="tag">Paso 2 - Vista general</div>
      <div class="title">Dashboard <span class="gold">en vivo</span></div>
      <p class="subtext">Turnos del mes, guardianes activos, pendientes de procesar, horas totales. Actualizado en tiempo real desde la base de datos.</p>
    </div>
  </div>

  <!-- 4: Turnos -->
  <div class="panel panel-4 shot-panel">
    <div class="shot-wrap"><div class="shot" style="background-image:url('__TURNOS__')"></div></div>
    <div class="caption-strip">
      <div class="tag">Paso 3 - Gestion de turnos</div>
      <div class="title">Calculo <span class="gold">automatico</span></div>
      <p class="subtext">Horas normales, extras, diurno/nocturno detectados solo. Filtros por fecha, tipo y estado. <strong>Cero calculo manual.</strong></p>
    </div>
  </div>

  <!-- 5: Feriados -->
  <div class="panel panel-5 shot-panel">
    <div class="shot-wrap"><div class="shot" style="background-image:url('__FERIA__')"></div></div>
    <div class="caption-strip">
      <div class="tag">Paso 4 - Calendario</div>
      <div class="title">Feriados <span class="gold">sincronizados</span></div>
      <p class="subtext">Nacionales y por decreto. El sistema aplica recargo automatico en cada turno trabajado en feriado.</p>
    </div>
  </div>

  <!-- 6: Reportes -->
  <div class="panel panel-6 shot-panel">
    <div class="shot-wrap"><div class="shot" style="background-image:url('__REP__')"></div></div>
    <div class="caption-strip">
      <div class="tag">Paso 5 - Integracion nomina</div>
      <div class="title">Un clic <span class="gold">a nomina</span></div>
      <p class="subtext">Genera reportes CSV por quincena listos para el sistema de nomina. Incluye normales, extras, incentivos y feriados.</p>
    </div>
  </div>

  <!-- 7: CTA -->
  <div class="panel panel-7">
    <div class="close-stats">
      <div class="cs"><div class="v">12h a 5min</div><div class="l">Por quincena</div></div>
      <div class="cs"><div class="v">0%</div><div class="l">Error de calculo</div></div>
      <div class="cs"><div class="v">100%</div><div class="l">Integrado con nomina</div></div>
    </div>
    <h2 class="cta">Lo activamos?<br><span class="gold">Demo en vivo cuando quieran.</span></h2>
    <p class="cta-sub">Backend Node.js + Frontend Angular ya construidos. Solo falta su OK para produccion.</p>
  </div>

  <button class="replay" id="replay" onclick="location.reload()">REPLAY</button>
  <button class="audio-toggle" id="audioToggle" title="Mute/Unmute">SND</button>

  <div class="play-veil" id="playVeil">
    <div class="play-icon"></div>
    <div class="play-label">Reproducir demo</div>
    <div class="play-sub">40 segundos - con narracion</div>
  </div>

  <div class="progress"><div class="progress-fill"></div></div>

  <audio id="narration" preload="auto" src="__AUDIO__"></audio>
</div>

<script>
const stage = document.getElementById('stage');
const veil = document.getElementById('playVeil');
const audio = document.getElementById('narration');
const replay = document.getElementById('replay');
const audioToggle = document.getElementById('audioToggle');

const labels = [
  { until: 4,  text: 'DEMO 01/07 - HOOK' },
  { until: 9,  text: 'DEMO 02/07 - LOGIN' },
  { until: 16, text: 'DEMO 03/07 - DASHBOARD' },
  { until: 23, text: 'DEMO 04/07 - TURNOS' },
  { until: 29, text: 'DEMO 05/07 - FERIADOS' },
  { until: 35, text: 'DEMO 06/07 - REPORTES' },
  { until: 41, text: 'DEMO 07/07 - CIERRE' },
];

let startMs = 0;
function tick() {
  const t = (Date.now() - startMs) / 1000;
  const mm = String(Math.floor(t / 60)).padStart(2,'0');
  const ss = String(Math.floor(t % 60)).padStart(2,'0');
  document.getElementById('hud-time').textContent = mm + ':' + ss;
  const lab = labels.find(l => t < l.until);
  if (lab) document.getElementById('hud-label').textContent = lab.text;
  if (t < 42) requestAnimationFrame(tick);
  else { replay.classList.add('show'); }
}

function start() {
  veil.classList.add('hidden');
  audioToggle.classList.add('show');
  startMs = Date.now();
  stage.classList.add('playing');
  audio.play().catch(e => console.warn('audio play blocked:', e));
  tick();
}

veil.addEventListener('click', start);

audioToggle.addEventListener('click', () => {
  audio.muted = !audio.muted;
  audioToggle.textContent = audio.muted ? 'OFF' : 'SND';
});
</script>
</body>
</html>"""

html = HTML
html = html.replace("__LOGIN__", img("01_login.png"))
html = html.replace("__DASH__",  img("03_dashboard.png"))
html = html.replace("__TURNOS__",img("04_turnos.png"))
html = html.replace("__FERIA__", img("05_feriados.png"))
html = html.replace("__REP__",   img("08_reportes.png"))
html = html.replace("__AUDIO__", audio_uri)

out = Path("DEMO_OPERACIONES_RANGER_v3.html")
out.write_text(html, encoding="utf-8")
print(f"OK: {out} -> {out.stat().st_size//1024}KB")
