from __future__ import annotations


def build_measure_mobile_html() -> str:
    return """<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#10233a" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <link rel="manifest" href="/measure-mobile.webmanifest" />
  <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png" />
  <link rel="apple-touch-icon" sizes="192x192" href="/icon-192.png" />
  <title>TECH_modul - Pomiary Mobile</title>
  <style>
    :root {
      --bg: #0e1b2f;
      --bg2: #142746;
      --panel: rgba(19, 34, 58, 0.92);
      --line: rgba(255,255,255,0.16);
      --text: #edf4ff;
      --muted: #b6c7e6;
      --accent: #56b6ff;
      --ok: #2dcf7f;
      --warn: #f0b95a;
      --bad: #ff7979;
    }
    * { box-sizing: border-box; }
    html, body { min-height: 100%; }
    body {
      margin: 0;
      color: var(--text);
      background: linear-gradient(165deg, var(--bg), var(--bg2));
      font-family: "Segoe UI", "Trebuchet MS", Arial, sans-serif;
      padding: 12px;
    }
    .wrap {
      max-width: 640px;
      margin: 0 auto;
      display: grid;
      gap: 10px;
    }
    .panel {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: var(--panel);
      padding: 12px;
    }
    h1 { margin: 0 0 6px; font-size: 1.34rem; line-height: 1.2; }
    p { margin: 0; color: var(--muted); font-size: 0.94rem; line-height: 1.35; }
    .row2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .field { display: grid; gap: 6px; }
    label { font-size: 0.82rem; color: var(--muted); }
    input, select, textarea, button {
      width: 100%;
      min-height: 44px;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.22);
      color: var(--text);
      padding: 0 11px;
      font-size: 0.95rem;
    }
    textarea { min-height: 76px; padding: 10px 11px; resize: vertical; }
    button {
      cursor: pointer;
      font-weight: 800;
      background: linear-gradient(180deg, #2f5fa2, #274f87);
      border-color: rgba(86,182,255,0.42);
    }
    button.ok { background: linear-gradient(180deg, #2f8f61, #23724c); border-color: rgba(45,207,127,0.44); }
    button.warn { background: linear-gradient(180deg, #8a6f2f, #6f581f); border-color: rgba(240,185,90,0.44); }
    button.bad { background: linear-gradient(180deg, #90435a, #742e43); border-color: rgba(255,121,121,0.44); }
    .status {
      min-height: 38px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.18);
      padding: 8px 10px;
      display: flex;
      align-items: center;
      color: var(--muted);
      font-size: 0.93rem;
    }
    .status.ok { border-color: rgba(45,207,127,0.5); color: #dbffe9; }
    .status.bad { border-color: rgba(255,121,121,0.5); color: #ffd8d8; }
    .canvas-wrap {
      border-radius: 12px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.32);
      overflow: hidden;
      min-height: 220px;
      position: relative;
    }
    canvas {
      width: 100%;
      display: block;
      touch-action: none;
      background: rgba(0,0,0,0.18);
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
    }
    .chip {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 0.85rem;
      color: var(--muted);
      background: rgba(0,0,0,0.15);
    }
    .value {
      font-size: 1.15rem;
      font-weight: 800;
      color: #eaf3ff;
      margin-top: 2px;
    }
    .hint { color: var(--muted); font-size: 0.84rem; line-height: 1.3; }
    @media (max-width: 520px) {
      .row2 { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h1>Pomiary Mobile</h1>
      <p>Widok telefoniczny jak skaner: kalibracja, pomiar 2-punktowy i zapis do projektu.</p>
    </section>

    <section class="panel">
      <div class="field">
        <label for="projectSelect">Projekt (Sciana)</label>
        <select id="projectSelect"></select>
      </div>
      <div class="row2" style="margin-top:8px;">
        <div class="field">
          <label for="quoteRef">Powiazanie z wycena</label>
          <input id="quoteRef" placeholder="np. WSTEPNA-001 / Szafa A" />
        </div>
        <div class="field">
          <label for="photoFile">Zdjecie z telefonu</label>
          <input id="photoFile" type="file" accept="image/*" capture="environment" />
        </div>
      </div>
      <div style="margin-top:8px;" id="status" class="status">Wybierz projekt i zdjecie.</div>
    </section>

    <section class="panel">
      <div class="canvas-wrap">
        <canvas id="photoCanvas" width="600" height="340"></canvas>
      </div>
      <div class="hint" style="margin-top:8px;">Dotknij 2 punkty. Najpierw ustaw kalibracje na znanym odcinku, potem wykonaj pomiar.</div>
      <div class="chips">
        <div class="chip" id="pxChip">Odcinek px: -</div>
        <div class="chip" id="scaleChip">Skala mm/px: -</div>
      </div>
      <div class="value" id="mmValue">Pomiar: - mm</div>
      <div class="row2" style="margin-top:8px;">
        <div class="field">
          <label for="knownMm">Znany odcinek (kalibracja)</label>
          <input id="knownMm" type="number" min="1" step="0.1" value="1000" />
        </div>
        <div class="field" style="align-self:end;">
          <button id="calibrateBtn" class="warn" type="button">Ustaw kalibracje</button>
        </div>
      </div>
      <div class="row2" style="margin-top:8px;">
        <button id="resetPointsBtn" class="bad" type="button">Wyczysc punkty</button>
        <button id="computeBtn" class="ok" type="button">Przelicz pomiar</button>
      </div>
    </section>

    <section class="panel">
      <div class="row2">
        <div class="field">
          <label for="measureName">Nazwa pomiaru</label>
          <input id="measureName" placeholder="np. Sciana A netto" />
        </div>
        <div class="field">
          <label for="measureKind">Typ</label>
          <select id="measureKind">
            <option value="distance">Odleglosc</option>
            <option value="width">Szerokosc</option>
            <option value="height">Wysokosc</option>
            <option value="depth">Glebokosc</option>
          </select>
        </div>
      </div>
      <div class="field" style="margin-top:8px;">
        <label for="measureNote">Notatka</label>
        <textarea id="measureNote" placeholder="Uwagi do pomiaru"></textarea>
      </div>
      <div class="row2" style="margin-top:8px;">
        <button id="saveBtn" class="ok" type="button">Zapisz pomiar do projektu</button>
        <button id="reloadBtn" type="button">Odswiez projekty</button>
      </div>
    </section>
  </div>

  <script>
    const els = {
      projectSelect: document.getElementById("projectSelect"),
      quoteRef: document.getElementById("quoteRef"),
      photoFile: document.getElementById("photoFile"),
      status: document.getElementById("status"),
      photoCanvas: document.getElementById("photoCanvas"),
      pxChip: document.getElementById("pxChip"),
      scaleChip: document.getElementById("scaleChip"),
      mmValue: document.getElementById("mmValue"),
      knownMm: document.getElementById("knownMm"),
      calibrateBtn: document.getElementById("calibrateBtn"),
      resetPointsBtn: document.getElementById("resetPointsBtn"),
      computeBtn: document.getElementById("computeBtn"),
      measureName: document.getElementById("measureName"),
      measureKind: document.getElementById("measureKind"),
      measureNote: document.getElementById("measureNote"),
      saveBtn: document.getElementById("saveBtn"),
      reloadBtn: document.getElementById("reloadBtn"),
    };

    const state = {
      projects: [],
      selectedProjectName: "",
      img: null,
      imgWidth: 0,
      imgHeight: 0,
      points: [],
      mmPerPx: 0,
      fileName: "",
      render: { x: 0, y: 0, w: 0, h: 0 },
    };

    function setStatus(text, ok = null) {
      els.status.textContent = String(text || "");
      els.status.classList.remove("ok", "bad");
      if (ok === true) els.status.classList.add("ok");
      if (ok === false) els.status.classList.add("bad");
    }

    function normalizeWallsPayload(payload) {
      const raw = payload && payload.data;
      if (Array.isArray(raw)) return raw;
      if (raw && typeof raw === "object" && raw.items && typeof raw.items === "object") {
        return Object.values(raw.items);
      }
      if (raw && typeof raw === "object") return Object.values(raw);
      return [];
    }

    async function apiJson(url, options = {}) {
      const res = await fetch(url, options);
      const text = await res.text();
      let data = {};
      try { data = text ? JSON.parse(text) : {}; } catch (e) { data = {}; }
      if (!res.ok) {
        const msg = (data && (data.error || data.message)) || `HTTP ${res.status}`;
        throw new Error(msg);
      }
      return data;
    }

    function fillProjectSelect(projects) {
      els.projectSelect.innerHTML = "";
      if (!projects.length) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "[brak projektow]";
        els.projectSelect.appendChild(opt);
        return;
      }
      projects.forEach((p) => {
        const name = String((p && p.name) || "").trim();
        if (!name) return;
        const client = String((p && p.client_name) || "").trim();
        const order = String((p && p.order_name) || "").trim();
        const extra = [client, order].filter(Boolean).join(" / ");
        const opt = document.createElement("option");
        opt.value = name;
        opt.textContent = extra ? `${name} (${extra})` : name;
        els.projectSelect.appendChild(opt);
      });
      if (!els.projectSelect.options.length) {
        const opt = document.createElement("option");
        opt.value = "";
        opt.textContent = "[brak projektow]";
        els.projectSelect.appendChild(opt);
      }
    }

    function selectedProject() {
      const name = String(state.selectedProjectName || "").trim();
      return state.projects.find((p) => String((p && p.name) || "").trim() === name) || null;
    }

    function updateProjectHints() {
      const p = selectedProject();
      if (!p) return;
      const ref = String((p.quote_item_reference || p.quote_item_name || "") || "").trim();
      if (ref && !String(els.quoteRef.value || "").trim()) els.quoteRef.value = ref;
    }

    async function loadProjects() {
      setStatus("Ladowanie projektow...", null);
      try {
        const payload = await apiJson("/api/walls");
        state.projects = normalizeWallsPayload(payload).filter((x) => x && typeof x === "object");
        fillProjectSelect(state.projects);
        if (state.projects.length) {
          const wanted = state.selectedProjectName;
          const exists = state.projects.some((p) => String((p && p.name) || "").trim() === wanted);
          state.selectedProjectName = exists ? wanted : String((state.projects[0].name || "")).trim();
          els.projectSelect.value = state.selectedProjectName;
          updateProjectHints();
          setStatus(`Wczytano projekty: ${state.projects.length}`, true);
        } else {
          state.selectedProjectName = "";
          setStatus("Brak projektow w bazie Sciana.", false);
        }
      } catch (err) {
        setStatus(`Blad ladowania projektow: ${err.message || err}`, false);
      }
    }

    function mapClientPointToImage(clientX, clientY) {
      const r = els.photoCanvas.getBoundingClientRect();
      const x = clientX - r.left;
      const y = clientY - r.top;
      const rr = state.render;
      if (!rr.w || !rr.h) return null;
      if (x < rr.x || y < rr.y || x > rr.x + rr.w || y > rr.y + rr.h) return null;
      const rx = (x - rr.x) / rr.w;
      const ry = (y - rr.y) / rr.h;
      return {
        x: Math.max(0, Math.min(state.imgWidth, rx * state.imgWidth)),
        y: Math.max(0, Math.min(state.imgHeight, ry * state.imgHeight)),
      };
    }

    function pxDistance() {
      if (state.points.length < 2) return 0;
      const a = state.points[0];
      const b = state.points[1];
      const dx = (b.x - a.x);
      const dy = (b.y - a.y);
      return Math.hypot(dx, dy);
    }

    function recalcLabels() {
      const px = pxDistance();
      els.pxChip.textContent = px > 0 ? `Odcinek px: ${px.toFixed(2)}` : "Odcinek px: -";
      els.scaleChip.textContent = state.mmPerPx > 0 ? `Skala mm/px: ${state.mmPerPx.toFixed(6)}` : "Skala mm/px: -";
      if (px > 0 && state.mmPerPx > 0) {
        els.mmValue.textContent = `Pomiar: ${(px * state.mmPerPx).toFixed(1)} mm`;
      } else {
        els.mmValue.textContent = "Pomiar: - mm";
      }
    }

    function clearCanvas() {
      const c = els.photoCanvas;
      const ctx = c.getContext("2d");
      ctx.clearRect(0, 0, c.width, c.height);
      ctx.fillStyle = "rgba(0,0,0,0.25)";
      ctx.fillRect(0, 0, c.width, c.height);
      ctx.fillStyle = "#b6c7e6";
      ctx.font = "16px Segoe UI";
      ctx.fillText("Wybierz zdjecie z telefonu", 14, 28);
    }

    function drawCanvas() {
      const c = els.photoCanvas;
      const ctx = c.getContext("2d");
      const w = c.width;
      const h = c.height;
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = "rgba(0,0,0,0.18)";
      ctx.fillRect(0, 0, w, h);

      if (!state.img) {
        clearCanvas();
        recalcLabels();
        return;
      }

      const imgW = state.imgWidth;
      const imgH = state.imgHeight;
      const scale = Math.min(w / imgW, h / imgH);
      const dw = imgW * scale;
      const dh = imgH * scale;
      const dx = (w - dw) / 2;
      const dy = (h - dh) / 2;
      state.render = { x: dx, y: dy, w: dw, h: dh };
      ctx.drawImage(state.img, dx, dy, dw, dh);

      function drawPoint(p) {
        const px = dx + (p.x / imgW) * dw;
        const py = dy + (p.y / imgH) * dh;
        ctx.beginPath();
        ctx.arc(px, py, 6, 0, Math.PI * 2);
        ctx.fillStyle = "#4aa7ff";
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#ffffff";
        ctx.stroke();
      }

      state.points.forEach(drawPoint);
      if (state.points.length >= 2) {
        const a = state.points[0];
        const b = state.points[1];
        const ax = dx + (a.x / imgW) * dw;
        const ay = dy + (a.y / imgH) * dh;
        const bx = dx + (b.x / imgW) * dw;
        const by = dy + (b.y / imgH) * dh;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.lineWidth = 2;
        ctx.strokeStyle = "#ff6f6f";
        ctx.stroke();
      }
      recalcLabels();
    }

    function setCanvasSizeFromElement() {
      const dpr = Math.max(1, window.devicePixelRatio || 1);
      const rect = els.photoCanvas.getBoundingClientRect();
      const w = Math.max(300, Math.floor(rect.width * dpr));
      const h = Math.max(220, Math.floor((rect.width * 0.62) * dpr));
      els.photoCanvas.width = w;
      els.photoCanvas.height = h;
      drawCanvas();
    }

    function setImageFromFile(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const img = new Image();
        img.onload = () => {
          state.img = img;
          state.imgWidth = img.naturalWidth || img.width;
          state.imgHeight = img.naturalHeight || img.height;
          state.points = [];
          state.mmPerPx = 0;
          state.fileName = String(file.name || "");
          drawCanvas();
          setStatus("Zdjecie wczytane. Ustaw kalibracje.", true);
        };
        img.onerror = () => setStatus("Nie udalo sie wczytac obrazu.", false);
        img.src = String(reader.result || "");
      };
      reader.onerror = () => setStatus("Blad odczytu pliku.", false);
      reader.readAsDataURL(file);
    }

    function addPointFromClient(clientX, clientY) {
      if (!state.img) {
        setStatus("Najpierw wybierz zdjecie.", false);
        return;
      }
      const p = mapClientPointToImage(clientX, clientY);
      if (!p) return;
      if (state.points.length >= 2) state.points = [];
      state.points.push(p);
      drawCanvas();
    }

    async function saveMeasurement() {
      const projectName = String(state.selectedProjectName || "").trim();
      if (!projectName) {
        setStatus("Wybierz projekt.", false);
        return;
      }
      if (state.points.length < 2) {
        setStatus("Zaznacz 2 punkty pomiarowe.", false);
        return;
      }
      if (state.mmPerPx <= 0) {
        setStatus("Najpierw ustaw kalibracje.", false);
        return;
      }
      const measureName = String(els.measureName.value || "").trim() || "Pomiar ze zdjecia";
      const measureKind = String(els.measureKind.value || "distance").trim() || "distance";
      const note = String(els.measureNote.value || "").trim();
      const quoteRef = String(els.quoteRef.value || "").trim();
      const px = pxDistance();
      const valueMm = Math.max(0, px * state.mmPerPx);
      const photoPath = state.fileName ? `[phone-upload] ${state.fileName}` : "[phone-upload]";

      setStatus("Zapisywanie pomiaru...", null);
      try {
        const selected = selectedProject();
        const wall = selected && typeof selected === "object" ? JSON.parse(JSON.stringify(selected)) : null;
        if (!wall) throw new Error("Nie znaleziono projektu do zapisu.");

        if (!Array.isArray(wall.measurements)) wall.measurements = [];
        wall.measurements.push({
          name: measureName,
          kind: measureKind,
          value_mm: Number(valueMm.toFixed(1)),
          photo_path: photoPath,
          note: note,
        });
        if (quoteRef) wall.quote_item_reference = quoteRef;

        await apiJson("/api/walls", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ data: wall }),
        });
        setStatus(`Zapisano pomiar: ${valueMm.toFixed(1)} mm`, true);
      } catch (err) {
        setStatus(`Blad zapisu: ${err.message || err}`, false);
      }
    }

    els.projectSelect.addEventListener("change", () => {
      state.selectedProjectName = String(els.projectSelect.value || "").trim();
      updateProjectHints();
    });

    els.photoFile.addEventListener("change", (ev) => {
      const input = ev.target;
      const file = input && input.files && input.files[0];
      if (file) setImageFromFile(file);
    });

    els.calibrateBtn.addEventListener("click", () => {
      const px = pxDistance();
      const known = Number(els.knownMm.value || 0);
      if (px <= 0) {
        setStatus("Kliknij 2 punkty kalibracji.", false);
        return;
      }
      if (!known || known <= 0) {
        setStatus("Podaj dodatni znany odcinek w mm.", false);
        return;
      }
      state.mmPerPx = known / px;
      drawCanvas();
      setStatus(`Kalibracja OK: ${state.mmPerPx.toFixed(6)} mm/px`, true);
    });

    els.computeBtn.addEventListener("click", () => {
      const px = pxDistance();
      if (px <= 0) {
        setStatus("Kliknij 2 punkty pomiarowe.", false);
        return;
      }
      if (state.mmPerPx <= 0) {
        setStatus("Najpierw ustaw kalibracje.", false);
        return;
      }
      drawCanvas();
      setStatus("Pomiar przeliczony.", true);
    });

    els.resetPointsBtn.addEventListener("click", () => {
      state.points = [];
      drawCanvas();
      setStatus("Wyczyszczono punkty.", null);
    });

    els.saveBtn.addEventListener("click", () => { saveMeasurement(); });
    els.reloadBtn.addEventListener("click", () => { loadProjects(); });

    els.photoCanvas.addEventListener("pointerdown", (ev) => {
      ev.preventDefault();
      addPointFromClient(ev.clientX, ev.clientY);
    });

    window.addEventListener("resize", setCanvasSizeFromElement);

    (async function init() {
      setCanvasSizeFromElement();
      clearCanvas();
      await loadProjects();
    })();
  </script>
</body>
</html>
"""
