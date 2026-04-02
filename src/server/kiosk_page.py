from __future__ import annotations


def build_kiosk_html(lite: bool = False) -> str:
    return """<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#101623" />
  <title>TECH_modul - Kiosk czasu pracy</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0b1020;
      --bg2: #11192b;
      --panel: rgba(16, 22, 35, 0.92);
      --border: rgba(255, 255, 255, 0.10);
      --text: #f3f7ff;
      --muted: #aeb8cf;
      --accent: #6ee7ff;
      --good: #2fd18c;
      --warn: #f6c768;
      --bad: #ff7b7b;
      --shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
      --radius: 24px;
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; margin: 0; }
    body {
      font-family: "Trebuchet MS", "Gill Sans", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(110, 231, 255, 0.14), transparent 32%),
        radial-gradient(circle at top right, rgba(124, 156, 255, 0.18), transparent 28%),
        linear-gradient(160deg, var(--bg), var(--bg2));
      color: var(--text);
    }

    .shell {
      min-height: 100vh;
      padding: 14px;
      display: grid;
      gap: 14px;
      grid-template-rows: auto 1fr;
    }

    /* ── Topbar ── */
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 14px 18px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: rgba(255, 255, 255, 0.04);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }
    .brand h1 {
      margin: 0;
      font-size: clamp(1.1rem, 3vw, 1.6rem);
      letter-spacing: 0.02em;
    }
    .brand p { display: none; }   /* ukryj opis — nie potrzebny */

    .status-row {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 8px;
      align-items: center;
      text-align: right;
    }
    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border);
      font-size: 0.92rem;
      color: var(--text);
    }
    .dot {
      width: 10px; height: 10px;
      border-radius: 50%;
      background: var(--warn);
      box-shadow: 0 0 0 5px rgba(246, 199, 104, 0.12);
    }
    .dot.ok  { background: var(--good); box-shadow: 0 0 0 5px rgba(47, 209, 140, 0.14); }
    .dot.bad { background: var(--bad);  box-shadow: 0 0 0 5px rgba(255, 123, 123, 0.12); }

    /* ── Main layout ── */
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
      gap: 14px;
      align-items: start;
    }

    .panel {
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }
    .panel-body { padding: 16px 18px 18px; }

    /* ── Scan box ── */
    .scan-box { display: grid; gap: 12px; }

    /* Input ukryty wizualnie, ale słucha klawiatury USB skanera */
    .scan-input-hidden {
      position: absolute;
      left: -9999px;
      width: 1px; height: 1px;
      opacity: 0;
      pointer-events: none;
    }

    /* ── Camera ── */
    .camera-box {
      display: grid;
      gap: 10px;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.04);
    }
    .camera-row {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }
    .camera-video {
      width: 100%;
      max-height: 280px;
      min-height: 160px;
      border-radius: 16px;
      background: #000;
      object-fit: cover;
      border: 1px solid rgba(255,255,255,0.10);
      display: none;
    }

    /* ── Selected worker ── */
    .selected-card {
      display: grid;
      gap: 8px;
      padding: 14px 16px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03));
      border: 1px solid rgba(255,255,255,0.08);
    }
    .selected-card strong { font-size: 1.2rem; }

    /* ── Buttons ── */
    .action-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .btn {
      appearance: none;
      border: 0;
      border-radius: 16px;
      min-height: 70px;
      padding: 14px 16px;
      font-size: 1rem;
      font-weight: 700;
      color: #08101c;
      background: linear-gradient(160deg, var(--accent), #9be7ff);
      cursor: pointer;
      transition: transform 0.08s ease, filter 0.15s ease, opacity 0.15s ease;
    }
    .btn:hover  { filter: brightness(1.04); }
    .btn:active { transform: translateY(1px) scale(0.996); }
    .btn:disabled { opacity: 0.35; cursor: not-allowed; }
    .btn.secondary {
      color: var(--text);
      background: linear-gradient(160deg, rgba(124,156,255,0.22), rgba(110,231,255,0.16));
      border: 1px solid rgba(255,255,255,0.12);
    }
    .btn.good { background: linear-gradient(160deg, #36e39d, #90f0c3); }
    .btn.warn { background: linear-gradient(160deg, #f6c768, #ffd98f); }
    .btn.bad  { background: linear-gradient(160deg, #ff8a8a, #ffb8b8); }

    /* ── Message ── */
    .message {
      min-height: 52px;
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(0,0,0,0.2);
      color: var(--text);
      white-space: pre-wrap;
      font-size: 1rem;
    }
    .message.ok  { border-color: rgba(47, 209, 140, 0.34); }
    .message.bad { border-color: rgba(255, 123, 123, 0.34); }
    .message.loaded {
      background: rgba(47, 209, 140, 0.12);
      border-color: rgba(47, 209, 140, 0.5);
      font-weight: 700;
      font-size: 1.1rem;
      letter-spacing: 0.06em;
      text-align: center;
      text-transform: uppercase;
    }

    /* ── Worker cards ── */
    .panel-header {
      padding: 16px 18px 0;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .panel-header h2 { margin: 0; font-size: 1.1rem; }

    .worker-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 10px;
    }
    .worker-card {
      text-align: left;
      min-height: 110px;
      padding: 14px;
      border-radius: 16px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.05);
      color: var(--text);
      cursor: pointer;
      transition: transform 0.08s ease, background 0.15s ease, border-color 0.15s ease;
    }
    .worker-card:hover  { transform: translateY(-1px); background: rgba(255,255,255,0.07); }
    .worker-card.active { border-color: rgba(110, 231, 255, 0.5); background: linear-gradient(180deg, rgba(110,231,255,0.16), rgba(255,255,255,0.05)); }
    .worker-card .name  { font-size: 1rem; font-weight: 700; margin-bottom: 4px; }
    .worker-card .meta  { display: grid; gap: 2px; font-size: 0.9rem; color: var(--muted); }
    .badge {
      display: inline-flex; align-items: center;
      padding: 4px 9px; border-radius: 999px;
      font-size: 0.78rem; color: #08101c; background: #b7c8ff; margin-bottom: 8px;
    }
    .badge.ok  { background: #9ff4c8; }
    .badge.off { background: #dfe6f7; }

    /* ── Big confirmation overlay ── */
    .big-confirm {
      position: fixed; inset: 0;
      display: flex; align-items: center; justify-content: center;
      background: rgba(0,0,0,0.55);
      backdrop-filter: blur(8px);
      opacity: 0; pointer-events: none;
      transition: opacity 0.2s ease;
      z-index: 100;
    }
    .big-confirm.show { opacity: 1; pointer-events: auto; }
    .big-confirm-card {
      background: #162030; border: 1px solid rgba(255,255,255,0.15);
      border-radius: 24px; padding: 32px 28px;
      text-align: center; max-width: min(88vw, 420px);
    }
    .big-confirm.good .big-confirm-card { border-color: rgba(47, 209, 140, 0.5); }
    .big-confirm.bad  .big-confirm-card { border-color: rgba(255, 123, 123, 0.5); }
    .big-confirm-title  { font-size: clamp(1.6rem, 5vw, 2.2rem); font-weight: 900; letter-spacing: 0.06em; text-transform: uppercase; color: #eaf7ff; }
    .big-confirm-detail { margin-top: 8px; font-size: clamp(0.95rem, 2.8vw, 1.2rem); color: #c6d8f8; line-height: 1.4; }

    /* ── Responsive ── */
    @media (max-width: 1000px) {
      .layout { grid-template-columns: 1fr; }
    }
    @media (max-width: 640px) {
      .shell { padding: 10px; gap: 10px; }
      .action-grid { grid-template-columns: 1fr; }
      .status-row { justify-content: flex-start; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <h1>TECH_modul &middot; czas pracy</h1>
      </div>
      <div class="status-row">
        <span class="pill"><span id="healthDot" class="dot"></span><span id="healthText">Łączenie...</span></span>
        <span class="pill">Czas: <strong id="clock" style="margin-left:4px">--:--:--</strong></span>
      </div>
    </header>

    <main class="layout">
      <!-- Lewa kolumna: skaner + akcje -->
      <section class="panel">
        <div class="panel-body">
          <div class="scan-box">
            <!-- Ukryty input dla skanerów USB/klawiaturowych — NIE pokazuje klawiatury ekranowej -->
            <input id="scanInput" class="scan-input-hidden"
                   inputmode="none" autocomplete="off" autocapitalize="off"
                   autocorrect="off" spellcheck="false"
                   tabindex="-1" aria-hidden="true" />

            <!-- Kamera QR -->
            <div class="camera-box">
              <div class="camera-row">
                <button id="cameraBtn" class="btn secondary" type="button">Włącz kamerę QR</button>
                <span id="cameraStatus" style="font-size:0.88rem;color:var(--muted)"></span>
              </div>
              <video id="cameraPreview" class="camera-video" autoplay playsinline muted></video>
            </div>

            <!-- Wybrany pracownik -->
            <div class="selected-card">
              <strong id="selectedName">Nie wybrano pracownika</strong>
              <div style="color:var(--muted);font-size:0.95rem" id="selectedMeta">Zeskanuj QR pracownika.</div>
            </div>

            <!-- Przyciski akcji -->
            <div class="action-grid">
              <button class="btn good" id="startBtn"  type="button" disabled>Start pracy</button>
              <button class="btn warn" id="breakStartBtn" type="button" disabled>Przerwa +</button>
              <button class="btn secondary" id="breakEndBtn" type="button" disabled>Przerwa -</button>
              <button class="btn bad"  id="finishBtn" type="button" disabled>Koniec pracy</button>
            </div>

            <div id="message" class="message loaded">-DANE WCZYTANE-</div>
          </div>
        </div>
      </section>

      <!-- Prawa kolumna: lista pracowników -->
      <section class="panel">
        <div class="panel-header">
          <h2>Pracownicy</h2>
          <span style="display:inline-flex;align-items:center;gap:6px;font-size:0.88rem;color:var(--muted)">
            <span class="dot ok" style="width:8px;height:8px"></span>Dotknij kartę
          </span>
        </div>
        <div class="panel-body">
          <div id="workerGrid" class="worker-grid"></div>
        </div>
      </section>
    </main>
  </div>

  <div id="bigConfirm" class="big-confirm" role="status" aria-live="assertive"></div>

  <script>
    const API = "/api/kiosk";

    const state = {
      workers: [],
      selected: null,
    };

    const cameraState = {
      stream: null,
      detector: null,
      running: false,
      busy: false,
    };

    const scannerState = {
      buffer: "",
      clearTimer: null,
    };

    // Na urządzeniach dotykowych / mobilnych NIE skupiamy pola tekstowego (nie wyskakuje klawiatura)
    const IS_TOUCH = !!("ontouchstart" in window || navigator.maxTouchPoints > 0);

    const els = {
      clock:        document.getElementById("clock"),
      healthDot:    document.getElementById("healthDot"),
      healthText:   document.getElementById("healthText"),
      scanInput:    document.getElementById("scanInput"),
      workerGrid:   document.getElementById("workerGrid"),
      selectedName: document.getElementById("selectedName"),
      selectedMeta: document.getElementById("selectedMeta"),
      message:      document.getElementById("message"),
      startBtn:     document.getElementById("startBtn"),
      breakStartBtn:document.getElementById("breakStartBtn"),
      breakEndBtn:  document.getElementById("breakEndBtn"),
      finishBtn:    document.getElementById("finishBtn"),
      cameraBtn:    document.getElementById("cameraBtn"),
      cameraStatus: document.getElementById("cameraStatus"),
      cameraPreview:document.getElementById("cameraPreview"),
      bigConfirm:   document.getElementById("bigConfirm"),
    };

    /* ── Utilities ── */
    function escapeHtml(text) {
      return String(text ?? "")
        .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
    }

    function setMessage(text, kind = "") {
      els.message.className = "message" + (kind ? " " + kind : "");
      els.message.textContent = text || "";
    }

    let bigTimer = null;
    function showBigConfirm(title, detail = "", tone = "good") {
      if (!els.bigConfirm) return;
      if (bigTimer) clearTimeout(bigTimer);
      els.bigConfirm.className = "big-confirm show " + (tone === "bad" ? "bad" : "good");
      els.bigConfirm.innerHTML =
        '<div class="big-confirm-card">'
        + '<div class="big-confirm-title">' + escapeHtml(title) + '</div>'
        + (detail ? '<div class="big-confirm-detail">' + escapeHtml(detail) + '</div>' : "")
        + "</div>";
      bigTimer = setTimeout(() => {
        els.bigConfirm.className = "big-confirm";
        els.bigConfirm.innerHTML = "";
        bigTimer = null;
      }, 2400);
    }

    /* ── Buttons state ── */
    function updateButtons() {
      const ok = !!state.selected;
      els.startBtn.disabled = !ok;
      els.breakStartBtn.disabled = !ok;
      els.breakEndBtn.disabled = !ok;
      els.finishBtn.disabled = !ok;
    }

    function formatSession(session) {
      if (!session) return "";
      return [
        session.started_at_iso ? "Start: " + session.started_at_iso : "",
        "Przerwa: " + Number(session.break_total_minutes || 0).toFixed(0) + " min",
        session.work_type ? "Rodzaj: " + session.work_type : "",
      ].filter(Boolean).join("  |  ");
    }

    function renderSelected() {
      if (!state.selected) {
        els.selectedName.textContent = "Nie wybrano pracownika";
        els.selectedMeta.textContent = "Zeskanuj QR pracownika.";
        updateButtons();
        return;
      }
      els.selectedName.textContent = (state.selected.name || state.selected.worker_id || "?")
        + (state.selected.worker_id ? " (" + state.selected.worker_id + ")" : "");
      const parts = [
        state.selected.role ? "Rola: " + state.selected.role : "",
        formatSession(state.selected.session),
      ].filter(Boolean);
      els.selectedMeta.textContent = parts.join("  \n") || "Brak sesji.";
      updateButtons();
    }

    function renderWorkers() {
      els.workerGrid.innerHTML = "";
      if (!state.workers.length) {
        els.workerGrid.innerHTML = '<div style="color:var(--muted);font-size:0.9rem">Brak pracowników w bazie.</div>';
        return;
      }
      for (const w of state.workers) {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "worker-card"
          + (state.selected && state.selected.worker_id === w.worker_id ? " active" : "");
        card.innerHTML =
          '<div class="badge ' + (w.active ? "ok" : "off") + '">'
          + (w.active ? "Aktywny" : "Gotowy") + "</div>"
          + '<div class="name">' + escapeHtml(w.name || w.worker_id) + "</div>"
          + '<div class="meta">'
          + "<span>ID: " + escapeHtml(w.worker_id || "-") + "</span>"
          + "<span>PIN: " + escapeHtml(w.pin_code || "-") + "</span>"
          + "<span>" + escapeHtml(w.role || "") + "</span>"
          + "</div>";
        card.addEventListener("click", () => selectWorker(w));
        els.workerGrid.appendChild(card);
      }
    }

    /* ── API ── */
    async function apiFetch(path, options = {}) {
      const resp = await fetch(API + path, { headers: { "Content-Type": "application/json" }, ...options });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok) throw new Error(data.error || data.message || "HTTP " + resp.status);
      return data;
    }

    async function checkHealth() {
      try {
        const resp = await fetch("/api/health");
        const data = await resp.json().catch(() => ({}));
        els.healthDot.className = "dot ok";
        els.healthText.textContent = data.status === "ok" ? "Połączono" : "OK";
      } catch (_e) {
        els.healthDot.className = "dot bad";
        els.healthText.textContent = "Brak połączenia";
      }
    }

    async function loadWorkers(silent = false) {
      try {
        const data = await apiFetch("/workers", { method: "GET" });
        state.workers = Array.isArray(data.workers) ? data.workers : [];
        renderWorkers();
      } catch (e) {
        if (!silent) setMessage("Błąd ładowania pracowników: " + e.message, "bad");
      }
    }

    async function selectWorker(w) {
      state.selected = w || null;
      renderSelected();
      renderWorkers();
      if (!state.selected) return;
      try {
        const data = await apiFetch("/state?worker_id=" + encodeURIComponent(state.selected.worker_id));
        if (data.worker) {
          state.selected = { ...state.selected, ...data.worker, session: data.session || null };
          renderSelected();
          renderWorkers();
        }
        setMessage(data.message || "Pracownik wybrany.", "ok");
      } catch (e) {
        setMessage("Błąd: " + e.message, "bad");
      }
    }

    async function processQr(text) {
      const qr = String(text || "").trim();
      if (!qr) return;
      try {
        const data = await apiFetch("/scan", {
          method: "POST",
          body: JSON.stringify({ qr_text: qr }),
        });
        if (!data.ok) { setMessage(data.message || "Nie rozpoznano QR.", "bad"); return; }
        state.selected = data.worker || null;
        if (state.selected) state.selected.session = data.session || null;
        setMessage(data.message || "Pracownik wybrany.", "ok");
        if (data.worker && data.worker.name) showBigConfirm(data.worker.name, data.message || "");
        renderSelected();
        await loadWorkers(true);
      } catch (e) {
        setMessage("Błąd skanowania: " + e.message, "bad");
      }
    }

    async function perform(action) {
      if (!state.selected) { setMessage("Najpierw wybierz pracownika.", "bad"); return; }
      try {
        const data = await apiFetch("/action", {
          method: "POST",
          body: JSON.stringify({ worker_id: state.selected.worker_id, action, work_type: "" }),
        });
        if (!data.ok) { setMessage(data.message || "Akcja nie powiodła się.", "bad"); return; }
        if (data.worker) state.selected = { ...state.selected, ...data.worker, session: data.session || null };
        setMessage(data.message || "Zapisano.", "ok");
        const label = { start: "START", break_start: "PRZERWA +", break_end: "PRZERWA -", finish: "KONIEC" }[action] || action;
        showBigConfirm(label, (state.selected && state.selected.name) || "");
        renderSelected();
        await loadWorkers(true);
      } catch (e) {
        setMessage("Błąd zapisu: " + e.message, "bad");
      }
    }

    /* ── Kamera QR ── */
    async function startCamera() {
      try {
        cameraState.stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
        });
        els.cameraPreview.srcObject = cameraState.stream;
        els.cameraPreview.style.display = "block";
        cameraState.running = true;
        els.cameraBtn.textContent = "Wyłącz kamerę";
        els.cameraStatus.textContent = "";
        scanCameraLoop();
      } catch (e) {
        els.cameraStatus.textContent = "Błąd kamery: " + (e.message || "brak dostępu");
      }
    }

    function stopCamera() {
      cameraState.running = false;
      if (cameraState.stream) {
        cameraState.stream.getTracks().forEach(t => t.stop());
        cameraState.stream = null;
      }
      els.cameraPreview.srcObject = null;
      els.cameraPreview.style.display = "none";
      els.cameraBtn.textContent = "Włącz kamerę QR";
      els.cameraStatus.textContent = "";
    }

    async function scanCameraLoop() {
      if (!cameraState.running) return;
      if (cameraState.busy) { requestAnimationFrame(scanCameraLoop); return; }
      cameraState.busy = true;
      try {
        if (window.BarcodeDetector) {
          if (!cameraState.detector) {
            cameraState.detector = new BarcodeDetector({ formats: ["qr_code"] });
          }
          const codes = await cameraState.detector.detect(els.cameraPreview);
          if (codes.length > 0) {
            const text = codes[0].rawValue;
            stopCamera();
            await processQr(text);
          }
        }
      } catch (_e) { /* ignoruj błędy klatki */ }
      cameraState.busy = false;
      if (cameraState.running) {
        setTimeout(scanCameraLoop, 180);
      }
    }

    els.cameraBtn.addEventListener("click", () => {
      if (cameraState.running) stopCamera();
      else startCamera();
    });

    /* ── Skaner USB/klawiaturowy ── */
    // Nasłuchuje wszystkich klawiszy — bez skupiania inputa (brak wyskakiwania klawiatury)
    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const text = scannerState.buffer.trim();
        scannerState.buffer = "";
        if (scannerState.clearTimer) { clearTimeout(scannerState.clearTimer); scannerState.clearTimer = null; }
        if (text) processQr(text);
        return;
      }
      if (e.key.length === 1) {
        scannerState.buffer += e.key;
        if (scannerState.clearTimer) clearTimeout(scannerState.clearTimer);
        scannerState.clearTimer = setTimeout(() => { scannerState.buffer = ""; }, 600);
      }
    });

    /* ── Zegar + health ── */
    function updateClock() {
      els.clock.textContent = new Date().toLocaleTimeString("pl-PL", { hour12: false });
    }
    setInterval(updateClock, 1000);
    setInterval(checkHealth, 15000);

    /* ── Przyciski akcji ── */
    els.startBtn.addEventListener("click", () => perform("start"));
    els.breakStartBtn.addEventListener("click", () => perform("break_start"));
    els.breakEndBtn.addEventListener("click", () => perform("break_end"));
    els.finishBtn.addEventListener("click", () => perform("finish"));

    /* ── Init ── */
    updateClock();
    checkHealth();
    loadWorkers(true).catch(() => {});
    renderSelected();
    // NIE skupiamy inputa — zapobiega wyskakiwaniu klawiatury na telefonie
  </script>
</body>
</html>"""
