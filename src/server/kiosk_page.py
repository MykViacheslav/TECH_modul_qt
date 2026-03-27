from __future__ import annotations


def build_kiosk_html() -> str:
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
      --panel-strong: #182135;
      --border: rgba(255, 255, 255, 0.10);
      --text: #f3f7ff;
      --muted: #aeb8cf;
      --accent: #6ee7ff;
      --accent-2: #7c9cff;
      --good: #2fd18c;
      --warn: #f6c768;
      --bad: #ff7b7b;
      --shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
      --radius: 24px;
    }

    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      font-family: "Trebuchet MS", "Gill Sans", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(110, 231, 255, 0.14), transparent 32%),
        radial-gradient(circle at top right, rgba(124, 156, 255, 0.18), transparent 28%),
        linear-gradient(160deg, var(--bg), var(--bg2));
      color: var(--text);
    }

    .shell {
      min-height: 100vh;
      padding: 18px;
      display: grid;
      gap: 18px;
      grid-template-rows: auto 1fr auto;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 22px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: rgba(255, 255, 255, 0.04);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }

    .brand {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .brand h1 {
      margin: 0;
      font-size: clamp(1.4rem, 2.2vw, 2.2rem);
      letter-spacing: 0.02em;
    }

    .brand p, .hint, .small, .meta {
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }

    .status-row {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-end;
      gap: 10px;
      align-items: center;
      text-align: right;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid var(--border);
      font-size: 0.95rem;
      color: var(--text);
    }

    .dot {
      width: 11px;
      height: 11px;
      border-radius: 50%;
      background: var(--warn);
      box-shadow: 0 0 0 6px rgba(246, 199, 104, 0.12);
    }

    .dot.ok {
      background: var(--good);
      box-shadow: 0 0 0 6px rgba(47, 209, 140, 0.14);
    }

    .dot.bad {
      background: var(--bad);
      box-shadow: 0 0 0 6px rgba(255, 123, 123, 0.12);
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
      gap: 18px;
      align-items: start;
    }

    .panel {
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--panel);
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .panel-header {
      padding: 18px 20px 0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .panel-header h2 {
      margin: 0;
      font-size: 1.2rem;
    }

    .panel-body {
      padding: 18px 20px 20px;
    }

    .scan-box {
      display: grid;
      gap: 14px;
    }

    .scan-input {
      width: 100%;
      min-height: 70px;
      padding: 16px 18px;
      border-radius: 18px;
      border: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.25);
      color: var(--text);
      font-size: 1.05rem;
      outline: none;
    }

    .scan-input:focus {
      border-color: rgba(110, 231, 255, 0.65);
      box-shadow: 0 0 0 4px rgba(110, 231, 255, 0.14);
    }

    .action-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    .btn {
      appearance: none;
      border: 0;
      border-radius: 18px;
      min-height: 74px;
      padding: 16px 18px;
      font-size: 1.04rem;
      font-weight: 700;
      color: #08101c;
      background: linear-gradient(160deg, var(--accent), #9be7ff);
      cursor: pointer;
      transition: transform 0.08s ease, filter 0.15s ease, opacity 0.15s ease;
    }

    .btn:hover { filter: brightness(1.03); }
    .btn:active { transform: translateY(1px) scale(0.995); }
    .btn:disabled { opacity: 0.35; cursor: not-allowed; }

    .btn.secondary {
      color: var(--text);
      background: linear-gradient(160deg, rgba(124, 156, 255, 0.22), rgba(110, 231, 255, 0.16));
      border: 1px solid rgba(255, 255, 255, 0.12);
    }

    .btn.good { background: linear-gradient(160deg, #36e39d, #90f0c3); }
    .btn.warn { background: linear-gradient(160deg, #f6c768, #ffd98f); }
    .btn.bad { background: linear-gradient(160deg, #ff8a8a, #ffb8b8); }

    .selected {
      display: grid;
      gap: 12px;
    }

    .selected-card {
      display: grid;
      gap: 10px;
      padding: 16px 18px;
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.03));
      border: 1px solid rgba(255,255,255,0.08);
    }

    .selected-card strong {
      font-size: 1.25rem;
    }

    .field-row {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 12px;
      align-items: end;
    }

    .field {
      display: grid;
      gap: 8px;
    }

    label {
      font-size: 0.92rem;
      color: var(--muted);
    }

    select {
      width: 100%;
      min-height: 54px;
      padding: 12px 14px;
      border-radius: 16px;
      border: 1px solid var(--border);
      background: rgba(0, 0, 0, 0.22);
      color: var(--text);
      font-size: 1rem;
    }

    .worker-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 12px;
    }

    .worker-card {
      text-align: left;
      min-height: 118px;
      padding: 16px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(255,255,255,0.05);
      color: var(--text);
      cursor: pointer;
      transition: transform 0.08s ease, background 0.15s ease, border-color 0.15s ease;
    }

    .worker-card:hover {
      transform: translateY(-1px);
      background: rgba(255,255,255,0.07);
    }

    .worker-card.active {
      border-color: rgba(110, 231, 255, 0.5);
      background: linear-gradient(180deg, rgba(110, 231, 255, 0.16), rgba(255,255,255,0.05));
    }

    .worker-card .name {
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 6px;
    }

    .worker-card .meta {
      display: grid;
      gap: 2px;
      font-size: 0.93rem;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      width: fit-content;
      font-size: 0.82rem;
      color: #08101c;
      background: #b7c8ff;
      margin-bottom: 10px;
    }

    .badge.ok { background: #9ff4c8; }
    .badge.off { background: #dfe6f7; }

    .message {
      min-height: 56px;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(255,255,255,0.08);
      background: rgba(0,0,0,0.2);
      color: var(--text);
      white-space: pre-wrap;
    }

    .message.ok { border-color: rgba(47, 209, 140, 0.34); }
    .message.bad { border-color: rgba(255, 123, 123, 0.34); }

    .footer {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      padding: 4px 2px 0;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .note {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--border);
    }

    @media (max-width: 1100px) {
      .layout { grid-template-columns: 1fr; }
    }

    @media (max-width: 700px) {
      .shell { padding: 12px; gap: 12px; }
      .topbar, .panel-body, .panel-header { padding-left: 14px; padding-right: 14px; }
      .action-grid { grid-template-columns: 1fr; }
      .field-row { grid-template-columns: 1fr; }
      .status-row { justify-content: flex-start; text-align: left; }
    }
  </style>
</head>
<body>
  <div class="shell">
    <header class="topbar">
      <div class="brand">
        <h1>TECH_modul · kiosk czasu pracy</h1>
        <p>Tablet Android + QR + duże przyciski. Skaner klawiaturowy działa od razu, kamera dołożymy w kolejnej iteracji.</p>
      </div>
      <div class="status-row">
        <span class="pill"><span id="healthDot" class="dot"></span><span id="healthText">Sprawdzanie połączenia...</span></span>
        <span class="pill">Czas: <strong id="clock" style="margin-left: 4px;">--:--:--</strong></span>
      </div>
    </header>

    <main class="layout">
      <section class="panel">
        <div class="panel-header">
          <h2>Skan i odbicie</h2>
          <span class="note">Wpisz QR i naciśnij Enter</span>
        </div>
        <div class="panel-body">
          <div class="scan-box">
            <input id="scanInput" class="scan-input" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" placeholder="Skan QR, worker_id albo PIN awaryjny..." />
            <div class="selected-card">
              <strong id="selectedName">Nie wybrano pracownika</strong>
              <div class="meta" id="selectedMeta">Zeskanuj kod lub wybierz pracownika z listy.</div>
            </div>
            <div class="field-row">
              <div class="field">
                <label for="workType">Rodzaj pracy</label>
                <select id="workType">
                  <option>Produkcja</option>
                  <option>Montaz</option>
                  <option>Magazyn</option>
                  <option>Serwis</option>
                  <option>Inne</option>
                </select>
              </div>
              <button id="refreshBtn" class="btn secondary" type="button">Odśwież listę</button>
            </div>
            <div class="action-grid">
              <button class="btn good" id="startBtn" type="button" disabled>Start pracy</button>
              <button class="btn warn" id="breakStartBtn" type="button" disabled>Przerwa start</button>
              <button class="btn secondary" id="breakEndBtn" type="button" disabled>Przerwa koniec</button>
              <button class="btn bad" id="finishBtn" type="button" disabled>Koniec pracy</button>
            </div>
            <div id="message" class="message">Gotowe do skanowania.</div>
          </div>
        </div>
      </section>

      <section class="panel">
        <div class="panel-header">
          <h2>Pracownicy</h2>
          <span class="note"><span class="dot ok"></span>Dotknij kartę, żeby wybrać</span>
        </div>
        <div class="panel-body">
          <div id="workerGrid" class="worker-grid"></div>
        </div>
      </section>
    </main>

    <footer class="footer">
      <div>Tryb web działa w Android Chrome. Kamera QR wymaga później HTTPS, więc startujemy od skanera, PIN-u i dotyku.</div>
      <div id="selectedState">Brak aktywnej sesji.</div>
    </footer>
  </div>

  <script>
    const API = "/api/kiosk";
    const state = {
      workers: [],
      selected: null,
    };

    const els = {
      clock: document.getElementById("clock"),
      healthDot: document.getElementById("healthDot"),
      healthText: document.getElementById("healthText"),
      scanInput: document.getElementById("scanInput"),
      workType: document.getElementById("workType"),
      workerGrid: document.getElementById("workerGrid"),
      selectedName: document.getElementById("selectedName"),
      selectedMeta: document.getElementById("selectedMeta"),
      selectedState: document.getElementById("selectedState"),
      message: document.getElementById("message"),
      startBtn: document.getElementById("startBtn"),
      breakStartBtn: document.getElementById("breakStartBtn"),
      breakEndBtn: document.getElementById("breakEndBtn"),
      finishBtn: document.getElementById("finishBtn"),
      refreshBtn: document.getElementById("refreshBtn"),
    };

    function escapeHtml(text) {
      return String(text ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
    }

    function setMessage(text, kind = "") {
      els.message.className = "message" + (kind ? ` ${kind}` : "");
      els.message.textContent = text || "";
    }

    function formatSession(session) {
      if (!session) return "Brak aktywnej sesji.";
      const parts = [
        `Start: ${session.started_at_iso || "-"}`,
        `Przerwa: ${Number(session.break_total_minutes || 0).toFixed(0)} min`,
        session.work_type ? `Rodzaj: ${session.work_type}` : "",
        session.worker_id ? `ID: ${session.worker_id}` : "",
      ].filter(Boolean);
      return parts.join(" | ");
    }

    function updateButtons() {
      const hasWorker = !!state.selected;
      els.startBtn.disabled = !hasWorker;
      els.breakStartBtn.disabled = !hasWorker;
      els.breakEndBtn.disabled = !hasWorker;
      els.finishBtn.disabled = !hasWorker;
    }

    function renderSelected() {
      if (!state.selected) {
        els.selectedName.textContent = "Nie wybrano pracownika";
        els.selectedMeta.textContent = "Zeskanuj kod lub wybierz pracownika z listy.";
        els.selectedState.textContent = "Brak aktywnej sesji.";
        updateButtons();
        return;
      }

      els.selectedName.textContent = `${state.selected.name} (${state.selected.worker_id})`;
      const meta = [
        state.selected.worker_id ? `ID: ${state.selected.worker_id}` : "",
        state.selected.pin_code ? `PIN: ${state.selected.pin_code}` : "",
        state.selected.role ? `Rola: ${state.selected.role}` : "",
        state.selected.pay_mode ? `Płaca: ${state.selected.pay_mode}` : "",
        state.selected.hourly_rate ? `Stawka: ${state.selected.hourly_rate}` : "",
      ].filter(Boolean).join(" | ");
      els.selectedMeta.textContent = meta || "Brak dodatkowych danych.";
      els.selectedState.textContent = formatSession(state.selected.session);
      updateButtons();
    }

    function renderWorkers() {
      els.workerGrid.innerHTML = "";
      if (!state.workers.length) {
        els.workerGrid.innerHTML = '<div class="meta">Brak pracowników w bazie.</div>';
        return;
      }

      for (const worker of state.workers) {
        const card = document.createElement("button");
        card.type = "button";
        card.className = "worker-card" + (state.selected && state.selected.worker_id === worker.worker_id ? " active" : "");
        card.innerHTML = `
          <div class="badge ${worker.active ? "ok" : "off"}">${worker.active ? "Aktywny" : "Gotowy"}</div>
          <div class="name">${escapeHtml(worker.name || worker.worker_id)}</div>
          <div class="meta">
            <span>ID: ${escapeHtml(worker.worker_id || "-")}</span>
            <span>PIN: ${escapeHtml(worker.pin_code || "-")}</span>
            <span>${escapeHtml(worker.role || "brak roli")}</span>
          </div>
        `;
        card.addEventListener("click", () => selectWorker(worker));
        els.workerGrid.appendChild(card);
      }
    }

    async function api(path, options = {}) {
      const response = await fetch(`${API}${path}`, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || data.message || `HTTP ${response.status}`);
      }
      return data;
    }

    async function checkHealth() {
      try {
        const data = await apiHealth();
        els.healthDot.className = "dot ok";
        els.healthText.textContent = data.status === "ok" ? "Połączono" : "Nieznany stan";
      } catch (error) {
        els.healthDot.className = "dot bad";
        els.healthText.textContent = "Brak połączenia";
      }
    }

    async function apiHealth() {
      const response = await fetch("/api/health");
      return response.json();
    }

    async function loadWorkers() {
      const data = await api("/workers", { method: "GET" });
      state.workers = Array.isArray(data.workers) ? data.workers : [];
      renderWorkers();
    }

    async function selectWorker(worker) {
      state.selected = worker || null;
      renderSelected();
      renderWorkers();
      if (!state.selected) return;
      try {
        const data = await api(`/state?worker_id=${encodeURIComponent(state.selected.worker_id)}`, { method: "GET" });
        if (data.worker) {
          state.selected = { ...state.selected, ...data.worker, session: data.session || null };
          renderSelected();
          renderWorkers();
        }
        setMessage(data.message || "Pracownik wybrany.", "ok");
      } catch (error) {
        setMessage(`Nie udało się pobrać stanu pracownika: ${error.message}`, "bad");
      }
      els.scanInput.focus();
    }

    async function scan() {
      const text = els.scanInput.value.trim();
      if (!text) {
        setMessage("Wpisz QR albo worker_id.", "bad");
        return;
      }
      try {
        const data = await api("/scan", {
          method: "POST",
          body: JSON.stringify({ qr_text: text }),
        });
        if (!data.ok) {
          setMessage(data.message || "Nie rozpoznano QR.", "bad");
          return;
        }
        state.selected = data.worker || null;
        if (state.selected) {
          state.selected.session = data.session || null;
        }
        setMessage(data.message || "Pracownik wybrany.", "ok");
        renderSelected();
        await loadWorkers();
      } catch (error) {
        setMessage(`Błąd skanowania: ${error.message}`, "bad");
      } finally {
        els.scanInput.value = "";
        els.scanInput.focus();
      }
    }

    async function perform(action) {
      if (!state.selected) {
        setMessage("Najpierw wybierz pracownika.", "bad");
        return;
      }
      try {
        const data = await api("/action", {
          method: "POST",
          body: JSON.stringify({
            worker_id: state.selected.worker_id,
            action,
            work_type: els.workType.value,
          }),
        });
        if (!data.ok) {
          setMessage(data.message || "Akcja nie powiodła się.", "bad");
          return;
        }
        if (data.worker) {
          state.selected = { ...state.selected, ...data.worker, session: data.session || null };
        }
        setMessage(data.message || "Zapisano.", "ok");
        renderSelected();
        await loadWorkers();
      } catch (error) {
        setMessage(`Błąd zapisu: ${error.message}`, "bad");
      } finally {
        els.scanInput.focus();
      }
    }

    function updateClock() {
      const now = new Date();
      els.clock.textContent = now.toLocaleTimeString("pl-PL", { hour12: false });
    }

    els.scanInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        scan();
      }
    });
    els.startBtn.addEventListener("click", () => perform("start"));
    els.breakStartBtn.addEventListener("click", () => perform("break_start"));
    els.breakEndBtn.addEventListener("click", () => perform("break_end"));
    els.finishBtn.addEventListener("click", () => perform("finish"));
    els.refreshBtn.addEventListener("click", async () => {
      setMessage("Odświeżanie...", "");
      await loadWorkers();
      await checkHealth();
      setMessage("Lista pracowników odświeżona.", "ok");
    });

    setInterval(updateClock, 1000);
    setInterval(checkHealth, 15000);
    updateClock();
    checkHealth();
    loadWorkers().catch(error => setMessage(`Nie udało się wczytać pracowników: ${error.message}`, "bad"));
    renderSelected();
    els.scanInput.focus();
  </script>
</body>
</html>
"""
