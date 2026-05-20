const PENDIENTES = [
  // ===== BUGS =====
  {
    titulo: "KeyError 'operacion' en agenda",
    categoria: "bug",
    estado: "bug",
    desc: "El LLM llama agenda con {'listar': True} pero el handler espera args.pop('operacion').",
    items: [
      "Archivo: agente_core/agent.py:1067",
      "Validar que 'operacion' exista o usar default",
      "Ajustar descripción del tool para que el LLM siempre lo incluya"
    ],
    tags: ["agent.py", "agenda", "LLM"]
  },

  // ===== MONITOR HUB =====
  {
    titulo: "Monitor Hub — Fase 1",
    categoria: "monitor_hub",
    estado: "enprogreso",
    desc: "Refactorizar monitor actual como plugin + hub central.",
    items: ["Diseño en design_monitor_hub.md"],
    tags: ["refactor", "arquitectura"]
  },
  {
    titulo: "Monitor Hub — Fase 2",
    categoria: "monitor_hub",
    estado: "pendiente",
    desc: "Plugin WhatsApp (grupo SISTEMA RAY).",
    items: ["Grupo prioritario: 120363424666838458@g.us"],
    tags: ["whatsapp", "plugin"]
  },
  {
    titulo: "Monitor Hub — Fase 3",
    categoria: "monitor_hub",
    estado: "pendiente",
    desc: "Dashboard web con FastAPI.",
    items: ["Puerto 8080"],
    tags: ["fastapi", "dashboard"]
  },
  {
    titulo: "Monitor Hub — Fase 4",
    categoria: "monitor_hub",
    estado: "pendiente",
    desc: "Plugin Gmail + sistema de prioridades.",
    items: [],
    tags: ["gmail", "prioridades"]
  },

  // ===== JOB MANAGER =====
  {
    titulo: "Job Manager — backend FastAPI",
    categoria: "job_manager",
    estado: "pendiente",
    desc: "Servicio aparte para encolar procesos largos. Decisiones aprobadas 2026-04-30.",
    items: [
      "FastAPI + SQLite en puerto 8090",
      "Cancelación SIGTERM (grace 5s) → SIGKILL",
      "Stdout/stderr → logs/jobs/<job_id>.log",
      "Spawnear desde el supervisor"
    ],
    tags: ["fastapi", "sqlite", "8090"]
  },
  {
    titulo: "Job Manager — pipelines DAG",
    categoria: "job_manager",
    estado: "pendiente",
    desc: "Soporte de pipelines (DAG con depends_on) para descargar → transcribir → doblar.",
    items: ["Modelo: id, name, command, estado, parent_id, exit_code"],
    tags: ["pipelines", "DAG"]
  },
  {
    titulo: "Job Manager — endpoints REST",
    categoria: "job_manager",
    estado: "pendiente",
    desc: "API que consume el agente directo.",
    items: [
      "POST /jobs",
      "GET /jobs, GET /jobs/:id",
      "GET /jobs/:id/output?desde=N",
      "DELETE /jobs/:id",
      "GET /pipelines/:id"
    ],
    tags: ["REST", "API"]
  },
  {
    titulo: "Job Manager — tools del agente",
    categoria: "job_manager",
    estado: "pendiente",
    desc: "Cliente desde agente_core/job_client.py.",
    items: ["job_submit", "job_status", "job_list", "job_cancel"],
    tags: ["tools", "agente"]
  },
  {
    titulo: "Job Manager — estructura de archivos",
    categoria: "job_manager",
    estado: "pendiente",
    desc: "Crear directorio job_manager/ con los módulos.",
    items: ["server.py", "worker.py", "db.py", "dashboard.html"],
    tags: ["estructura"]
  },

  // ===== PRESENCIA =====
  {
    titulo: "Recibir y flashear ESP32-S3",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Hardware comprado, esperando envío. Instalar junto con cámaras.",
    items: ["Cambiar CSI_SOURCE=esp32 en docker-compose", "Flashear firmware en los ESP32-S3"],
    tags: ["hardware", "ESP32"]
  },
  {
    titulo: "Calibrar zonas reales",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Verificar mapeo zone_1-7 → áreas reales con detección real.",
    items: [],
    tags: ["calibración"]
  },
  {
    titulo: "Alertas proactivas",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Supervisor revisa presencia y notifica caídas/inactividad por Telegram.",
    items: [],
    tags: ["alertas", "telegram"]
  },
  {
    titulo: "Cruce presencia + mantenimiento",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Ej: 'AC encendido y nadie en la sala hace 1 hora'.",
    items: [],
    tags: ["cruce-datos"]
  },
  {
    titulo: "Historial automático",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Polling cada minuto para detectar patrones.",
    items: [],
    tags: ["historial"]
  },
  {
    titulo: "Detección multi-persona",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Saber quién está dónde.",
    items: [],
    tags: ["multi-persona"]
  },
  {
    titulo: "Signos vitales sin contacto",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Monitoreo de respiración y pulso.",
    items: [],
    tags: ["vitales"]
  },
  {
    titulo: "Detección de caídas",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Alerta inmediata por Telegram.",
    items: [],
    tags: ["caídas", "alertas"]
  },
  {
    titulo: "Integrar cámaras",
    categoria: "presencia",
    estado: "pendiente",
    desc: "Evaluar si se pueden cruzar con presencia WiFi.",
    items: [],
    tags: ["cámaras"]
  },

  // ===== WHATSAPP =====
  {
    titulo: "Agente local guarde SISTEMA RAY auto",
    categoria: "whatsapp",
    estado: "pendiente",
    desc: "El agente local guarde mensajes en .md sin intervención.",
    items: ["Workflow: agente local guarda → Claude analiza"],
    tags: ["automatización", "MD"]
  },
  {
    titulo: "Pulir execute_bash",
    categoria: "whatsapp",
    estado: "pendiente",
    desc: "Comillas en 'SISTEMA RAY', esperar output completo.",
    items: [],
    tags: ["bash", "fix"]
  },
  {
    titulo: "MCP server de WhatsApp",
    categoria: "whatsapp",
    estado: "pendiente",
    desc: "Como el MCP de Telegram, exponer WhatsApp.",
    items: [],
    tags: ["MCP"]
  },

  // ===== AGENTE LOCAL =====
  {
    titulo: "Probar skill buscar-noticias",
    categoria: "agente_local",
    estado: "pendiente",
    desc: "Verificar que el agente la invoque bien tras reinicio.",
    items: [],
    tags: ["skill", "test"]
  },
  {
    titulo: "Wiki muestre 4 páginas",
    categoria: "agente_local",
    estado: "pendiente",
    desc: "Verificar que tras el fix la wiki muestre las 4 páginas.",
    items: [],
    tags: ["wiki"]
  },
  {
    titulo: "Notificaciones cruzadas",
    categoria: "agente_local",
    estado: "pendiente",
    desc: "WhatsApp urgente → Telegram.",
    items: [],
    tags: ["notificaciones"]
  },

  // ===== GATEWAY =====
  {
    titulo: "Gateway Anthropic-compatible",
    categoria: "gateway",
    estado: "pendiente",
    desc: "Para conectar Claude Desktop a modelos locales sin VPS.",
    items: [
      "PC Worker con LLMs (vía VPN o red local)",
      "PC Gateway: /v1/messages → /v1/chat/completions",
      "Cloudflare Tunnel para HTTPS gratis",
      "Costo: $0"
    ],
    tags: ["claude-desktop", "cloudflare", "$0"]
  },

  // ===== APP ANDROID =====
  {
    titulo: "App Android — terminales en casa",
    categoria: "android",
    estado: "pendiente",
    desc: "Tablets/teléfonos como terminales fijas en cada área.",
    items: [
      "Oír: micrófono → STT (Whisper)",
      "Ver: cámara → Visión (Qwen3.6)",
      "Responder: LLM → TTS",
      "Flutter/Kotlin + WebSocket o PWA con Web Speech API",
      "Integración con presencia para contexto por zona"
    ],
    tags: ["android", "STT", "TTS", "vision"]
  },

  // ===== CLAUDE RANGER =====
  {
    titulo: "Claude Ranger — bot Telegram",
    categoria: "ranger",
    estado: "pendiente",
    desc: "Instancia de Claude en servidor de Ranger recibe instrucciones nuestras.",
    items: [
      "Rhay + Claude local desarrollan → push al repo",
      "Avisar al Claude del servidor por Telegram",
      "Él hace: git pull, deploy, migrations, reportar",
      "No atiende al equipo de Ranger directamente"
    ],
    tags: ["ranger", "deploy", "telegram"]
  },

  // ===== IDEAS =====
  {
    titulo: "Dashboard centralizado FastAPI",
    categoria: "ideas",
    estado: "pendiente",
    desc: "Para todos los monitores en un solo lugar.",
    items: [],
    tags: ["fastapi", "dashboard"]
  },
  {
    titulo: "Agente local guarda, Claude analiza",
    categoria: "ideas",
    estado: "pendiente",
    desc: "Agente local guarda conversaciones, Claude analiza bajo demanda.",
    items: [],
    tags: ["arquitectura"]
  }
];

const NOMBRES_CATEGORIA = {
  bug: "Bug",
  monitor_hub: "Monitor Hub",
  job_manager: "Job Manager",
  presencia: "Presencia",
  whatsapp: "WhatsApp",
  agente_local: "Agente Local",
  gateway: "Gateway",
  android: "App Android",
  ranger: "Claude Ranger",
  ideas: "Idea futura"
};

function render(filtro) {
  const tablero = document.getElementById("tablero");
  tablero.innerHTML = "";

  const lista = filtro === "todos"
    ? PENDIENTES
    : PENDIENTES.filter(p => p.categoria === filtro);

  lista.forEach(p => {
    const card = document.createElement("article");
    card.className = `card ${p.estado}`;

    const items = p.items.length
      ? `<ul>${p.items.map(i => `<li>${escapar(i)}</li>`).join("")}</ul>`
      : "";

    const tags = p.tags
      .map(t => `<span class="tag">${escapar(t)}</span>`)
      .join("");

    card.innerHTML = `
      <h3>
        <span>${escapar(p.titulo)}</span>
        <span class="estado ${p.estado}">${nombreEstado(p.estado)}</span>
      </h3>
      <p class="desc">${escapar(p.desc)}</p>
      ${items}
      <div class="tags">
        <span class="tag">${NOMBRES_CATEGORIA[p.categoria] || p.categoria}</span>
        ${tags}
      </div>
    `;
    tablero.appendChild(card);
  });

  if (!lista.length) {
    tablero.innerHTML = `<p style="color:var(--muted);text-align:center;grid-column:1/-1">Sin pendientes en esta categoría.</p>`;
  }
}

function nombreEstado(e) {
  return {
    bug: "Bug",
    enprogreso: "En curso",
    pendiente: "Pendiente",
    hecho: "Listo"
  }[e] || e;
}

function escapar(s) {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function actualizarStats() {
  document.getElementById("total").textContent = PENDIENTES.length;
  document.getElementById("bugs").textContent = PENDIENTES.filter(p => p.estado === "bug").length;
  document.getElementById("enprogreso").textContent = PENDIENTES.filter(p => p.estado === "enprogreso").length;
  document.getElementById("hechos").textContent = PENDIENTES.filter(p => p.estado === "hecho").length;
}

function setFecha() {
  const hoy = new Date();
  document.getElementById("fecha").textContent = hoy.toLocaleDateString("es-DO", {
    weekday: "long", day: "numeric", month: "long", year: "numeric"
  });
}

// ============ AGENDA ============

const AGENDA = [
  {
    semana: 1, rango: "May 11–14",
    tema: "Limpieza + arranque Monitor Hub",
    sesiones: [
      { dia: "Lun", fecha: "2026-05-11", tema: "Bug <code>KeyError 'operacion'</code> en agenda + lectura del diseño Monitor Hub" },
      { dia: "Mié", fecha: "2026-05-13", tema: "Monitor Hub Fase 1: refactor monitor → plugin" },
      { dia: "Jue", fecha: "2026-05-14", tema: "Monitor Hub Fase 1: hub central + integración" }
    ]
  },
  {
    semana: 2, rango: "May 18–21",
    tema: "Job Manager (parte 1)",
    sesiones: [
      { dia: "Lun", fecha: "2026-05-18", tema: "Job Manager: estructura <code>job_manager/</code> + <code>db.py</code> (SQLite schema)" },
      { dia: "Mié", fecha: "2026-05-20", tema: "Job Manager: <code>server.py</code> (FastAPI puerto 8090) + endpoints básicos" },
      { dia: "Jue", fecha: "2026-05-21", tema: "Job Manager: <code>worker.py</code> (spawn + SIGTERM/SIGKILL)" }
    ]
  },
  {
    semana: 3, rango: "May 25–28",
    tema: "Job Manager (parte 2)",
    sesiones: [
      { dia: "Lun", fecha: "2026-05-25", tema: "Job Manager: pipelines DAG (<code>depends_on</code>)" },
      { dia: "Mié", fecha: "2026-05-27", tema: "Job Manager: <code>agente_core/job_client.py</code> + tools (<code>job_submit</code>, etc.)" },
      { dia: "Jue", fecha: "2026-05-28", tema: "Job Manager: <code>dashboard.html</code> + spawn desde supervisor" }
    ]
  },
  {
    semana: 4, rango: "Jun 1–4",
    tema: "WhatsApp + Agente local",
    sesiones: [
      { dia: "Lun", fecha: "2026-06-01", tema: "WhatsApp: pulir <code>execute_bash</code> (comillas en \"SISTEMA RAY\")" },
      { dia: "Mié", fecha: "2026-06-03", tema: "WhatsApp: auto-guardado en <code>.md</code> desde el agente local" },
      { dia: "Jue", fecha: "2026-06-04", tema: "Agente local: probar skill <code>buscar-noticias</code> + wiki 4 páginas" }
    ]
  },
  {
    semana: 5, rango: "Jun 8–11",
    tema: "Monitor Hub fases avanzadas",
    sesiones: [
      { dia: "Lun", fecha: "2026-06-08", tema: "Notificaciones cruzadas (WhatsApp urgente → Telegram)" },
      { dia: "Mié", fecha: "2026-06-10", tema: "Monitor Hub Fase 2: plugin WhatsApp" },
      { dia: "Jue", fecha: "2026-06-11", tema: "Monitor Hub Fase 3: dashboard web FastAPI" }
    ]
  },
  {
    semana: 6, rango: "Jun 15–18",
    tema: "Gateway Anthropic-compatible",
    sesiones: [
      { dia: "Lun", fecha: "2026-06-15", tema: "Monitor Hub Fase 4: plugin Gmail + prioridades" },
      { dia: "Mié", fecha: "2026-06-17", tema: "Gateway: PC Worker LLM + endpoint <code>/v1/messages</code>" },
      { dia: "Jue", fecha: "2026-06-18", tema: "Gateway: traducción a <code>/v1/chat/completions</code> + Cloudflare Tunnel" }
    ]
  }
];

function renderAgenda() {
  const cont = document.getElementById("agenda-semanas");
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);

  // próxima sesión: la primera fecha >= hoy
  let proximaFecha = null;
  for (const s of AGENDA.flatMap(w => w.sesiones)) {
    const f = new Date(s.fecha + "T00:00:00");
    if (f >= hoy) { proximaFecha = s.fecha; break; }
  }

  cont.innerHTML = AGENDA.map(w => `
    <div class="semana">
      <div class="semana-header">
        <h3>Semana ${w.semana}</h3>
        <span class="rango">${w.rango}</span>
      </div>
      <div class="semana-tema">${escapar(w.tema)}</div>
      <ul class="sesiones">
        ${w.sesiones.map(s => {
          const f = new Date(s.fecha + "T00:00:00");
          let cls = "";
          if (s.fecha === proximaFecha) cls = "proximo";
          else if (f < hoy) cls = "pasado";
          return `
            <li class="sesion ${cls}">
              <span class="dia">${s.dia}</span>
              <span class="fecha">${s.fecha}</span>
              <span class="tema">${s.tema}</span>
            </li>`;
        }).join("")}
      </ul>
    </div>
  `).join("");
}

function activarTab(nombre) {
  document.querySelectorAll(".tab").forEach(t => t.classList.toggle("activo", t.dataset.tab === nombre));
  document.querySelectorAll(".vista").forEach(v => v.classList.toggle("activa", v.id === "vista-" + nombre));
}

document.addEventListener("DOMContentLoaded", () => {
  setFecha();
  actualizarStats();
  render("todos");
  renderAgenda();

  document.querySelectorAll(".filtro").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filtro").forEach(b => b.classList.remove("activo"));
      btn.classList.add("activo");
      render(btn.dataset.filtro);
    });
  });

  document.querySelectorAll(".tab").forEach(btn => {
    btn.addEventListener("click", () => activarTab(btn.dataset.tab));
  });
});
