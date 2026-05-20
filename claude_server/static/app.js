// Cliente: chat sobre /inbox + SSE /stream
const TOKEN_KEY = "claude_bridge_token";
const DEVICE_KEY = "claude_bridge_device_id";
const NODE_KEY = "claude_bridge_node";
const VOICE_KEY = "claude_bridge_voice_output";

function genDeviceId() {
  return "dev_" + Math.random().toString(36).slice(2, 10);
}

const $ = (id) => document.getElementById(id);
const chatEl = $("chat");

let deviceId = localStorage.getItem(DEVICE_KEY) || genDeviceId();
localStorage.setItem(DEVICE_KEY, deviceId);
$("device-name").value = deviceId;

let node = localStorage.getItem(NODE_KEY) || "local";
$("node-select").value = node;

let token = localStorage.getItem(TOKEN_KEY) || "";
let voiceOutput = localStorage.getItem(VOICE_KEY) === "1";
$("voice-toggle").textContent = voiceOutput ? "🔊" : "🔇";
let evtSource = null;
let lastSeenId = 0;
// Cola de audio chunks por reproducir secuencialmente.
const audioQueue = [];
let audioPlaying = false;
let currentInGroup = null; // bubble que vamos acumulando para chunks consecutivos del mismo from_node

function setStatus(on) {
  $("conn-status").classList.toggle("on", on);
  $("conn-status").classList.toggle("off", !on);
}

function appendBubble({ kind, direction, from_node, content, meta }) {
  if (kind === "text_chunk" && direction === "in") {
    // Acumular en burbuja existente si es del mismo emisor.
    if (currentInGroup && currentInGroup.dataset.from === from_node) {
      currentInGroup.firstChild.textContent += content;
    } else {
      const div = document.createElement("div");
      div.className = "msg in";
      div.dataset.from = from_node;
      const body = document.createElement("div");
      body.textContent = content;
      div.appendChild(body);
      chatEl.appendChild(div);
      currentInGroup = div;
    }
  } else if (kind === "text" && direction === "out") {
    const div = document.createElement("div");
    div.className = "msg out";
    if (content) {
      const body = document.createElement("div");
      body.textContent = content;
      div.appendChild(body);
    }
    if (meta?.attachments?.length) {
      const att = document.createElement("div");
      att.className = "attachments";
      for (const a of meta.attachments) {
        if (a.kind === "image") {
          const img = document.createElement("img");
          img.src = a.url; img.alt = a.filename || "imagen";
          att.appendChild(img);
        } else if (a.kind === "audio") {
          const au = document.createElement("audio");
          au.controls = true; au.src = a.url;
          att.appendChild(au);
        } else {
          const link = document.createElement("a");
          link.href = a.url; link.textContent = "📎 " + (a.filename || a.url);
          link.target = "_blank";
          att.appendChild(link);
        }
      }
      div.appendChild(att);
    }
    chatEl.appendChild(div);
    currentInGroup = null;
  } else if (kind === "done") {
    const cost = meta?.cost_usd ? `· $${meta.cost_usd.toFixed(4)}` : "";
    const dur = meta?.duration_ms ? `· ${Math.round(meta.duration_ms)}ms` : "";
    if (currentInGroup) {
      const m = document.createElement("div");
      m.className = "meta";
      m.textContent = `[fin] ${cost} ${dur}`.trim();
      currentInGroup.appendChild(m);
    }
    currentInGroup = null;
  } else if (kind === "audio_chunk" && direction === "in") {
    // Encolar para reproducir en orden.
    audioQueue.push(content);
    playNextAudio();
  } else if (kind === "error") {
    const div = document.createElement("div");
    div.className = "msg error";
    div.textContent = "Error: " + content;
    chatEl.appendChild(div);
    currentInGroup = null;
  } else if (kind === "system") {
    const div = document.createElement("div");
    div.className = "msg system";
    div.textContent = content;
    chatEl.appendChild(div);
  }
  chatEl.scrollTop = chatEl.scrollHeight;
}

function connectSSE() {
  if (!token) return;
  if (evtSource) evtSource.close();
  const url = `/stream/${encodeURIComponent(node)}?after=${lastSeenId}&token=${encodeURIComponent(token)}`;
  evtSource = new EventSource(url);
  evtSource.onopen = () => setStatus(true);
  evtSource.onerror = () => setStatus(false);
  evtSource.addEventListener("message", (e) => {
    let m;
    try { m = JSON.parse(e.data); } catch { return; }
    lastSeenId = Math.max(lastSeenId, m.id);

    // El stream del nodo {node} ve mensajes para node_id=node.
    // Filtramos: solo nos importan los que van dirigidos a nuestro deviceId
    // (cuando ranger u otros emitan a inbox/{deviceId}), o los out de nosotros mismos.
    // Para fase 1 (node=local), los chunks vienen al inbox del deviceId.
    if (m.node_id !== deviceId && m.node_id !== node) return;
    appendBubble(m);
  });
}

function connectDeviceStream() {
  // En fase 1 escuchamos el inbox propio del device para recibir respuestas de Claude.
  if (!token) return;
  if (evtSource) evtSource.close();
  const url = `/stream/${encodeURIComponent(deviceId)}?after=${lastSeenId}&token=${encodeURIComponent(token)}`;
  evtSource = new EventSource(url);
  evtSource.onopen = () => setStatus(true);
  evtSource.onerror = () => setStatus(false);
  evtSource.addEventListener("message", (e) => {
    let m;
    try { m = JSON.parse(e.data); } catch { return; }
    lastSeenId = Math.max(lastSeenId, m.id);
    appendBubble(m);
  });
}

async function send(text, attachments = []) {
  if (!token) {
    alert("Configura el token primero (botón Token)");
    return;
  }
  const body = { text, from_node: deviceId, voice_output: voiceOutput };
  if (attachments.length) {
    body.attachments = attachments.map(a => ({
      url: a.url, kind: a.kind, mime: a.mime, filename: a.filename,
    }));
  }
  if (pendingGeo) {
    body.meta = { ...(body.meta || {}), geo: pendingGeo };
  }
  const res = await fetch(`/inbox/${encodeURIComponent(node)}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": "Bearer " + token,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    appendBubble({ kind: "error", direction: "in", from_node: "system",
                   content: `${res.status} ${await res.text()}` });
    return;
  }
  // Pinta nuestro mensaje localmente con los attachments.
  appendBubble({
    kind: "text", direction: "out", from_node: deviceId,
    content: text, meta: attachments.length ? { attachments: body.attachments } : null,
  });
}

// ── Attachments pendientes ───────────────────────────────────────────────
const pendingAttachments = []; // [{url, kind, mime, filename, size, localFile?}]
const trayEl = $("attach-tray");

function renderTray() {
  trayEl.innerHTML = "";
  if (pendingAttachments.length === 0) {
    trayEl.classList.add("hidden");
    return;
  }
  trayEl.classList.remove("hidden");
  pendingAttachments.forEach((a, idx) => {
    const chip = document.createElement("div");
    chip.className = "attach-chip" + (a.uploading ? " uploading" : "") + (a.error ? " error" : "");

    if (a.kind === "image" && a.url) {
      const img = document.createElement("img");
      img.className = "thumb";
      img.src = a.url;
      chip.appendChild(img);
    } else {
      const icon = document.createElement("span");
      icon.textContent = ({image:"🖼", audio:"🎙", video:"🎞", pdf:"📄", file:"📎"})[a.kind] || "📎";
      chip.appendChild(icon);
    }

    const label = document.createElement("span");
    label.textContent = a.error
      ? `× ${a.filename || "archivo"} — ${a.error}`
      : (a.uploading ? `subiendo ${a.filename || ""}…` : (a.filename || "archivo"));
    chip.appendChild(label);

    const x = document.createElement("span");
    x.className = "x";
    x.textContent = "✕";
    x.title = "Quitar";
    x.onclick = () => {
      pendingAttachments.splice(idx, 1);
      renderTray();
    };
    chip.appendChild(x);

    trayEl.appendChild(chip);
  });
}

async function uploadFile(file) {
  if (!token) {
    alert("Configura el token primero (botón Token)");
    return;
  }
  const placeholder = { uploading: true, filename: file.name, kind: "file" };
  pendingAttachments.push(placeholder);
  renderTray();
  try {
    const fd = new FormData();
    fd.append("file", file);
    const res = await fetch("/upload", {
      method: "POST",
      headers: { "Authorization": "Bearer " + token },
      body: fd,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.status);
    const idx = pendingAttachments.indexOf(placeholder);
    if (idx !== -1) pendingAttachments[idx] = data;
    renderTray();
  } catch (e) {
    placeholder.uploading = false;
    placeholder.error = e.message || String(e);
    renderTray();
  }
}

$("attach-input").addEventListener("change", async (e) => {
  for (const f of e.target.files) {
    await uploadFile(f);
  }
  e.target.value = "";
});

$("camera-input").addEventListener("change", async (e) => {
  for (const f of e.target.files) {
    await uploadFile(f);
  }
  e.target.value = "";
});

// ── Grabación de voz con MediaRecorder ───────────────────────────────────
let mediaRecorder = null;
let recChunks = [];
let recStream = null;

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia) {
    alert("Tu navegador no soporta grabación de audio. Necesitas HTTPS o estar en localhost.");
    return;
  }
  try {
    recStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    alert("Permiso de micrófono denegado o no disponible: " + e.message);
    return;
  }

  // Elegir el mejor mime soportado.
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  let mime = "";
  for (const c of candidates) {
    if (window.MediaRecorder && MediaRecorder.isTypeSupported(c)) { mime = c; break; }
  }

  mediaRecorder = new MediaRecorder(recStream, mime ? { mimeType: mime } : undefined);
  recChunks = [];
  mediaRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) recChunks.push(e.data); };
  mediaRecorder.onstop = async () => {
    const blob = new Blob(recChunks, { type: mediaRecorder.mimeType || "audio/webm" });
    const ext = (mediaRecorder.mimeType || "audio/webm").includes("ogg") ? "ogg"
              : (mediaRecorder.mimeType || "").includes("mp4") ? "m4a" : "webm";
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    const file = new File([blob], `voz_${stamp}.${ext}`, { type: blob.type });
    await uploadFile(file);
    recStream.getTracks().forEach((t) => t.stop());
    recStream = null;
    mediaRecorder = null;
    $("mic-btn").classList.remove("recording");
    $("mic-btn").textContent = "🎙";
  };
  mediaRecorder.start();
  $("mic-btn").classList.add("recording");
  $("mic-btn").textContent = "⏹";
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }
}

$("mic-btn").addEventListener("click", () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    stopRecording();
  } else {
    startRecording();
  }
});

// ── Geolocation ──────────────────────────────────────────────────────────
let pendingGeo = null; // {lat, lon, accuracy, ts}

function renderGeoChip() {
  // Limpia chips de geo previos.
  trayEl.querySelectorAll(".attach-chip.geo").forEach(c => c.remove());
  if (!pendingGeo) {
    if (pendingAttachments.length === 0) trayEl.classList.add("hidden");
    return;
  }
  trayEl.classList.remove("hidden");
  const chip = document.createElement("div");
  chip.className = "attach-chip geo";
  const icon = document.createElement("span"); icon.textContent = "📍";
  const label = document.createElement("span");
  label.textContent = `${pendingGeo.lat.toFixed(5)}, ${pendingGeo.lon.toFixed(5)} (±${Math.round(pendingGeo.accuracy)}m)`;
  const x = document.createElement("span"); x.className = "x"; x.textContent = "✕";
  x.onclick = () => { pendingGeo = null; renderGeoChip(); };
  chip.append(icon, label, x);
  trayEl.appendChild(chip);
}

$("geo-btn").addEventListener("click", () => {
  if (!navigator.geolocation) {
    alert("Tu navegador no soporta geolocalización.");
    return;
  }
  $("geo-btn").textContent = "⏳";
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      pendingGeo = {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        ts: pos.timestamp,
      };
      $("geo-btn").textContent = "📍";
      renderGeoChip();
    },
    (err) => {
      $("geo-btn").textContent = "📍";
      alert("Geolocalización falló: " + err.message + " (requiere HTTPS o localhost)");
    },
    { enableHighAccuracy: true, timeout: 8000, maximumAge: 30000 }
  );
});

function playNextAudio() {
  if (audioPlaying || audioQueue.length === 0) return;
  const url = audioQueue.shift();
  audioPlaying = true;
  const audio = new Audio(url);
  audio.onended = () => { audioPlaying = false; playNextAudio(); };
  audio.onerror = () => { audioPlaying = false; playNextAudio(); };
  audio.play().catch((e) => {
    console.warn("audio play failed:", e);
    audioPlaying = false;
    playNextAudio();
  });
}

$("voice-toggle").addEventListener("click", () => {
  voiceOutput = !voiceOutput;
  localStorage.setItem(VOICE_KEY, voiceOutput ? "1" : "0");
  $("voice-toggle").textContent = voiceOutput ? "🔊" : "🔇";
});

$("send-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = $("msg").value.trim();
  const validAtts = pendingAttachments.filter(a => !a.uploading && !a.error && a.url);
  if (!text && validAtts.length === 0) return;
  if (pendingAttachments.some(a => a.uploading)) {
    alert("Espera a que terminen las subidas");
    return;
  }
  $("send-btn").disabled = true;
  try {
    await send(text, validAtts);
    $("msg").value = "";
    pendingAttachments.length = 0;
    pendingGeo = null;
    renderTray();
    renderGeoChip();
  } finally {
    $("send-btn").disabled = false;
  }
});

$("config-btn").addEventListener("click", () => {
  $("token-input").value = token;
  $("config-dialog").showModal();
});
$("config-dialog").addEventListener("close", () => {
  if ($("config-dialog").returnValue === "ok") {
    token = $("token-input").value.trim();
    localStorage.setItem(TOKEN_KEY, token);
    connectDeviceStream();
  }
});
$("node-select").addEventListener("change", (e) => {
  node = e.target.value;
  localStorage.setItem(NODE_KEY, node);
});
$("device-name").addEventListener("change", (e) => {
  deviceId = e.target.value.trim() || genDeviceId();
  localStorage.setItem(DEVICE_KEY, deviceId);
  connectDeviceStream();
});

if (token) connectDeviceStream();

// ── Service Worker (PWA) ──────────────────────────────────────────────────
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js", { scope: "/" }).catch((e) => {
      console.warn("SW register falló:", e);
    });
  });
}
