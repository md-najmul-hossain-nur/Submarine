const el = (id) => document.getElementById(id);
const formatNumber = (n, digits = 1) => (n === null || n === undefined ? "--" : Number(n).toFixed(digits));
let manualEnabled = true;
let pollingStarted = false;

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API ${path} failed`);
  return res.json();
}

async function refreshHealth() {
  try {
    const data = await api("/api/health");
    el("healthStatus").textContent = `Server ok · ${data.time}`;
  } catch (err) {
    el("healthStatus").textContent = "Health check failed";
  }
}

async function refreshTelemetry() {
  try {
    const rows = await api("/api/telemetry/latest?limit=30");
    if (!rows.length) return;
    const latest = rows[rows.length - 1];
    el("batteryStat").textContent = `${formatNumber(latest.battery_v, 2)} V`;
    el("turbidityStat").textContent = `${formatNumber(latest.turbidity, 2)} NTU`;

    const grid = el("telemetryGrid");
    grid.innerHTML = "";
    const items = [
      ["Yaw", `${formatNumber(latest.yaw, 2)} °`],
      ["Pitch", `${formatNumber(latest.pitch, 2)} °`],
      ["Roll", `${formatNumber(latest.roll, 2)} °`],
      ["Battery I", `${formatNumber(latest.battery_i, 2)} A`],
      ["Water temp", `${formatNumber(latest.water_temp, 2)} °C`],
      ["Internal temp", `${formatNumber(latest.internal_temp, 2)} °C`],
      ["Turbidity", `${formatNumber(latest.turbidity, 2)} NTU`],
      ["Leak", latest.leak ? "True" : "False"],
    ];
    items.forEach(([label, value]) => {
      const div = document.createElement("div");
      div.className = "telemetry-item";
      div.innerHTML = `<p>${label}</p><h4>${value}</h4>`;
      grid.appendChild(div);
    });
  } catch (err) {
    console.error(err);
  }
}

async function refreshEvents() {
  try {
    const rows = await api("/api/events?limit=20");
    const list = el("eventsList");
    list.innerHTML = "";
    const clearBtn = document.createElement("div");
    clearBtn.className = "btn-row";
    clearBtn.innerHTML = `<button class="pill subtle" id="clearEventsBtn">Delete all</button>`;
    list.appendChild(clearBtn);
    rows.reverse().forEach((evt) => {
      const li = document.createElement("li");
      const level = evt.level || "info";
      li.innerHTML = `
        <div class="event-row">
          <div>
            <div class="badge ${level === "critical" ? "critical" : level === "warn" ? "warn" : "info"}">${level.toUpperCase()}</div>
            <div class="meta">${new Date(evt.timestamp).toLocaleTimeString()}</div>
            <div>${evt.message}</div>
          </div>
          <button class="pill subtle" data-delete-event="${evt.id}">Delete</button>
        </div>`;
      list.appendChild(li);
    });

    list.querySelectorAll("[data-delete-event]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-delete-event");
        try {
          await api(`/api/events/${id}`, { method: "DELETE" });
          refreshEvents();
        } catch (err) {
          alert("Delete failed");
        }
      });
    });

    const clear = el("clearEventsBtn");
    if (clear) {
      clear.onclick = async () => {
        try {
          await api("/api/events", { method: "DELETE" });
          refreshEvents();
        } catch (err) {
          alert("Delete all failed");
        }
      };
    }
  } catch (err) {
    console.error(err);
  }
}

async function refreshMissions() {
  try {
    const missions = await api("/api/missions");
    const container = el("missionList");
    container.innerHTML = "";
    missions.forEach((m) => {
      const card = document.createElement("div");
      card.className = "mission-card";
      card.innerHTML = `
        <div class="mission-head">
          <div>
            <h4>${m.name}</h4>
            <div class="meta">${m.status} · ${m.mode} · ${new Date(m.created_at).toLocaleString()}</div>
          </div>
          <button class="pill subtle" data-delete-mission="${m.id}">Delete</button>
        </div>
      `;
      container.appendChild(card);
    });
    if (missions[0]) {
      el("modeLabel").textContent = missions[0].mode;
      el("targetMissionId").value = missions[0].id;
    } else {
      el("modeLabel").textContent = "Manual";
    }

    container.querySelectorAll("[data-delete-mission]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-delete-mission");
        try {
          await api(`/api/missions/${id}`, { method: "DELETE" });
          refreshMissions();
          refreshEvents();
        } catch (err) {
          alert("Delete failed");
        }
      });
    });
  } catch (err) {
    console.error(err);
  }
}

async function refreshClips() {
  try {
    const clips = await api("/api/video-clips");
    const list = el("clipsList");
    list.innerHTML = "";
    const clearRow = document.createElement("div");
    clearRow.className = "btn-row";
    clearRow.innerHTML = `<button class="pill subtle" id="clearClipsBtn">Delete all</button>`;
    list.appendChild(clearRow);

    clips.forEach((c) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <div class="event-row">
          <div>
            <strong>${c.label}</strong>
            <div class="meta">${new Date(c.timestamp).toLocaleString()}</div>
            <div>${c.url}</div>
          </div>
          <button class="pill subtle" data-delete-clip="${c.id}">Delete</button>
        </div>`;
      list.appendChild(li);
    });

    list.querySelectorAll("[data-delete-clip]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-delete-clip");
        try {
          await api(`/api/video-clips/${id}`, { method: "DELETE" });
          refreshClips();
        } catch (err) {
          alert("Delete failed");
        }
      });
    });

    const clear = el("clearClipsBtn");
    if (clear) {
      clear.onclick = async () => {
        try {
          await api("/api/video-clips", { method: "DELETE" });
          refreshClips();
        } catch (err) {
          alert("Delete all failed");
        }
      };
    }
  } catch (err) {
    console.error(err);
  }
}

async function refreshTargets() {
  try {
    const targets = await api("/api/targets");
    const list = el("targetList");
    list.innerHTML = "";
    targets.forEach((t) => {
      const div = document.createElement("div");
      div.className = "mission-card";
      const status = t.status === "matched" ? "Matched" : "Pending";
      const matchedAt = t.matched_at ? new Date(t.matched_at).toLocaleString() : "--";
      div.innerHTML = `
        <h4>${t.label || t.filename}</h4>
        <div class="meta">${status} · created ${new Date(t.created_at).toLocaleString()} · matched ${matchedAt}</div>
        <div class="thumb-row">
          <img src="${t.url}" alt="target" class="thumb" />
          <div class="btn-row">
            <a class="pill subtle" href="${t.url}" target="_blank" rel="noreferrer">View</a>
            ${t.status === "matched" ? "" : `<button type="button" class="btn ghost" data-match="${t.id}">Mark matched</button>`}
            <button type="button" class="btn ghost" data-delete-target="${t.id}">Delete</button>
          </div>
        </div>
      `;
      list.appendChild(div);
    });

    list.querySelectorAll("[data-match]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-match");
        await api(`/api/targets/${id}/match`, { method: "POST" });
        refreshTargets();
        refreshEvents();
      });
    });

    list.querySelectorAll("[data-delete-target]").forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        const id = e.currentTarget.getAttribute("data-delete-target");
        try {
          await api(`/api/targets/${id}`, { method: "DELETE" });
          refreshTargets();
          refreshEvents();
        } catch (err) {
          alert("Delete failed");
        }
      });
    });
  } catch (err) {
    console.error(err);
  }
}

async function refreshAutoState() {
  try {
    const state = await api("/api/auto/state");
    el("autoPhase").textContent = state.phase;
    el("autoPhaseInput").value = state.phase;
    el("autoTask").value = state.task;
    el("autoNote").value = state.note || "";
    setButtonActive("armAutoBtn", state.is_enabled && state.phase === "armed");
    setButtonActive("startAutoBtn", state.is_enabled && state.phase === "running");
    setButtonActive("pauseAutoBtn", state.is_enabled && state.phase === "paused");
    setButtonActive("abortAutoBtn", !state.is_enabled || state.phase === "aborted");
    el("modeLabel").textContent = state.is_enabled ? "Auto" : "Manual";
    setManualEnabled(!state.is_enabled);
  } catch (err) {
    console.error(err);
  }
}

function setButtonActive(id, active) {
  const btn = el(id);
  if (!btn) return;
  btn.classList.toggle("is-active", Boolean(active));
}

async function submitManual(payload) {
  try {
    await api("/api/commands/manual", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  } catch (err) {
    console.error(err);
    alert("Failed to send manual command");
  }
}

async function submitAutoState(body) {
  try {
    await api("/api/auto/state", {
      method: "POST",
      body: JSON.stringify(body),
    });
    refreshAutoState();
  } catch (err) {
    console.error(err);
    alert("Auto state update failed");
  }
}

function bindForms() {
  const manualForm = el("manualForm");
  if (manualForm) manualForm.addEventListener("submit", (e) => e.preventDefault());

  const sliders = ["thrusterSlider", "servoUp", "servoLeft", "servoRight"];
  const sendManualState = () => {
    if (!manualEnabled) return;
    updateSpeedMeter();
    submitManual({
      command: "manual_control",
      thruster: Number(el("thrusterSlider").value),
      servo_up: Number(el("servoUp").value),
      servo_left: Number(el("servoLeft").value),
      servo_right: Number(el("servoRight").value),
    });
  };
  sliders.forEach((id) => {
    const slider = el(id);
    if (slider) slider.addEventListener("input", sendManualState);
  });

  const stopBtn = el("stopBtn");
  if (stopBtn) {
    stopBtn.onclick = () => {
      if (!manualEnabled) return;
      sliders.forEach((id) => {
        const slider = el(id);
        if (slider) slider.value = 0;
      });
      updateSpeedMeter();
      submitManual({ command: "stop" });
    };
  }

  const recordBtn = el("recordBtn");
  if (recordBtn) recordBtn.onclick = () => submitManual({ command: "record_clip" });

  const autoForm = el("autoForm");
  if (autoForm) {
    autoForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const data = new FormData(autoForm);
      submitAutoState({
        is_enabled: true,
        phase: data.get("phase"),
        task: data.get("task"),
        note: data.get("note"),
      });
    });
  }

  const autoButtons = [
    ["armAutoBtn", { is_enabled: true, phase: "armed" }],
    ["startAutoBtn", { is_enabled: true, phase: "running" }],
    ["abortAutoBtn", { is_enabled: false, phase: "aborted" }],
    ["pauseAutoBtn", { is_enabled: true, phase: "paused" }],
  ];
  autoButtons.forEach(([id, payload]) => {
    const btn = el(id);
    if (btn) btn.onclick = () => submitAutoState(payload);
  });

  const newMissionBtn = el("newMissionBtn");
  if (newMissionBtn) {
    newMissionBtn.onclick = async () => {
      const name = prompt("Mission name?");
      if (!name) return;
      await api("/api/missions", {
        method: "POST",
        body: JSON.stringify({ name, status: "planned", mode: "manual" }),
      });
      refreshMissions();
    };
  }

  const targetForm = el("targetForm");
  if (targetForm) {
    targetForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const formData = new FormData(targetForm);
      try {
        await fetch("/api/targets/upload", { method: "POST", body: formData });
        targetForm.reset();
        refreshTargets();
        refreshEvents();
      } catch (err) {
        alert("Upload failed");
        console.error(err);
      }
    });
  }
}

function startPolling() {
  if (pollingStarted) return;
  refreshHealth();
  refreshTelemetry();
  refreshEvents();
  refreshMissions();
  refreshClips();
  refreshTargets();
  refreshAutoState();
  setInterval(refreshTelemetry, 2000);
  setInterval(refreshEvents, 3000);
  setInterval(refreshAutoState, 5000);
  pollingStarted = true;
}

function setupConnectButton() {
  const connectBtn = el("connectBtn");
  if (!connectBtn) return;
  connectBtn.addEventListener("click", async () => {
    connectBtn.disabled = true;
    const originalText = connectBtn.dataset.originalText || connectBtn.textContent;
    connectBtn.dataset.originalText = originalText;
    connectBtn.textContent = "Connecting…";
    try {
      const res = await fetch("http://127.0.0.1:5000/api/health");
      if (!res.ok) throw new Error("Health check failed");
      connectBtn.textContent = "Connected";
      connectBtn.classList.add("pill-success");
      startPolling();
    } catch (err) {
      console.error("Connect failed", err);
      connectBtn.textContent = "Retry Connect";
      connectBtn.disabled = false;
      alert("Could not reach Pi. Check Wi-Fi or token.");
      return;
    }
  });
}

function init() {
  bindForms();
  setupConnectButton();
  startPolling();
  updateSpeedMeter();
}

document.addEventListener("DOMContentLoaded", init);

function updateSpeedMeter() {
  const meters = [
    { sliderId: "thrusterSlider", fillId: "thrusterFill", valueId: "thrusterValue" },
    { sliderId: "servoUp", fillId: "servoUpFill", valueId: "servoUpValue" },
    { sliderId: "servoLeft", fillId: "servoLeftFill", valueId: "servoLeftValue" },
    { sliderId: "servoRight", fillId: "servoRightFill", valueId: "servoRightValue" },
  ];

  meters.forEach(({ sliderId, fillId, valueId }) => {
    const slider = el(sliderId);
    const fill = el(fillId);
    const valLabel = el(valueId);
    if (!slider || !fill || !valLabel) return;
    const pct = Math.round(Number(slider.value || 0) * 100);
    fill.style.width = `${pct}%`;
    valLabel.textContent = `${pct}%`;
  });
}

function setManualEnabled(enabled) {
  manualEnabled = enabled;
  const ids = ["thrusterSlider", "servoUp", "servoLeft", "servoRight", "stopBtn"];
  ids.forEach((id) => {
    const elRef = el(id);
    if (elRef) elRef.disabled = !enabled;
  });
}
