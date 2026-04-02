from __future__ import annotations


def build_package_scanner_html() -> str:
    return """<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, viewport-fit=cover" />
  <meta name="theme-color" content="#0f172a" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <link rel="manifest" href="/pack-scanner.webmanifest" />
  <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png" />
  <link rel="apple-touch-icon" sizes="192x192" href="/icon-192.png" />
  <title>TECH_modul - Skaner formatek</title>
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111c34;
      --text: #eff6ff;
      --muted: #b8c7e6;
      --ok: #22c55e;
      --bad: #ef4444;
      --line: rgba(255,255,255,0.16);
      --accent: #60a5fa;
    }
    * { box-sizing: border-box; }
    html, body { min-height: 100%; margin: 0; }
    body {
      color: var(--text);
      background: linear-gradient(165deg, #0b1224, #152341);
      font-family: "Segoe UI", "Trebuchet MS", Arial, sans-serif;
      padding: 12px;
    }
    .wrap {
      max-width: 560px;
      margin: 0 auto;
      display: grid;
      gap: 10px;
    }

    /* ── Topbar ── */
    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(17, 28, 52, 0.92);
      padding: 12px 14px;
    }
    .topbar h1 { margin: 0; font-size: 1.2rem; }
    .pill-clock {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 11px;
      border-radius: 999px;
      background: rgba(255,255,255,0.06);
      border: 1px solid var(--line);
      font-size: 0.88rem;
    }
    .dot { width: 9px; height: 9px; border-radius: 50%; background: #f6c768; }
    .dot.ok { background: #22c55e; }

    .panel {
      border: 1px solid var(--line);
      border-radius: 14px;
      background: rgba(17, 28, 52, 0.92);
      padding: 12px;
    }

    /* ── Buttons ── */
    .btn {
      min-height: 52px;
      border-radius: 12px;
      border: 1px solid var(--line);
      color: var(--text);
      background: #1d2f55;
      font-weight: 800;
      font-size: 1rem;
      cursor: pointer;
      padding: 0 14px;
      width: 100%;
    }
    .btn.main {
      background: linear-gradient(180deg, #2c5aa0, #234a87);
      border-color: rgba(96,165,250,0.5);
    }
    .btn.good {
      background: linear-gradient(180deg, #2f8f5f, #24774f);
      border-color: rgba(34,197,94,0.5);
    }
    .btn[hidden] { display: none; }

    /* ── Status ── */
    .status {
      min-height: 38px;
      border-radius: 10px;
      border: 1px solid var(--line);
      background: rgba(0,0,0,0.2);
      padding: 8px 10px;
      display: flex;
      align-items: center;
      color: var(--muted);
      font-size: 0.93rem;
    }
    .status.ok  { border-color: rgba(34,197,94,0.5);  color: #d7ffe6; }
    .status.bad { border-color: rgba(239,68,68,0.5);  color: #ffd7d7; }

    /* ── Camera ── */
    .video {
      width: 100%;
      border-radius: 12px;
      border: 1px solid var(--line);
      background: #000;
      min-height: 210px;
      max-height: 360px;
      object-fit: cover;
      display: none;
      margin-top: 8px;
    }

    /* Ukryty input dla skanera USB — nie otwiera klawiatury */
    .scan-input-hidden {
      position: absolute;
      left: -9999px;
      width: 1px; height: 1px;
      opacity: 0;
      pointer-events: none;
    }

    /* ── Pack result ── */
    .badge {
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      border: 1px solid rgba(96,165,250,0.42);
      background: rgba(96,165,250,0.2);
      font-size: 0.98rem;
      font-weight: 900;
      letter-spacing: 0.03em;
      margin-bottom: 8px;
    }
    .grid2 {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .field {
      border: 1px solid var(--line);
      border-radius: 10px;
      padding: 7px 9px;
      background: rgba(0,0,0,0.16);
    }
    .k { color: var(--muted); font-size: 0.8rem; margin-bottom: 2px; }
    .v { font-size: 0.95rem; font-weight: 700; word-break: break-word; }
    .raw {
      margin-top: 8px;
      border: 1px dashed var(--line);
      border-radius: 10px;
      padding: 8px 10px;
      color: var(--muted);
      font-size: 0.82rem;
      word-break: break-all;
      background: rgba(0,0,0,0.14);
    }

    /* ── Big confirm overlay ── */
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
      border-radius: 20px; padding: 28px 22px;
      text-align: center; max-width: min(88vw, 380px);
    }
    .big-confirm.good .big-confirm-card { border-color: rgba(34,197,94,0.5); }
    .big-confirm-title  { font-size: clamp(1.4rem, 5vw, 2rem); font-weight: 900; letter-spacing: 0.05em; text-transform: uppercase; color: #eaf7ff; }
    .big-confirm-detail { margin-top: 6px; font-size: 0.97rem; color: #c6d8f8; line-height: 1.4; }

    @media (max-width: 460px) {
      .grid2 { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="wrap">

    <!-- Topbar -->
    <header class="topbar">
      <h1>TECH_modul &middot; formatki</h1>
      <span class="pill-clock">
        <span id="healthDot" class="dot"></span>
        <strong id="clock">--:--:--</strong>
      </span>
    </header>

    <!-- Panel skanera -->
    <section class="panel">
      <!-- Ukryty input dla skanerów USB/klawiaturowych -->
      <input id="scanInput" class="scan-input-hidden"
             inputmode="none" autocomplete="off" autocapitalize="off"
             autocorrect="off" spellcheck="false"
             tabindex="-1" aria-hidden="true" />

      <!-- Kamera -->
      <button id="cameraBtn" class="btn main" type="button">Włącz kamerę QR</button>
      <video id="video" class="video" autoplay playsinline muted></video>

      <!-- Status -->
      <div id="status" class="status" style="margin-top:8px">Gotowe do skanowania.</div>
    </section>

    <!-- Wynik formatki -->
    <section class="panel">
      <div class="badge" id="packBadge">PACZKA --/--</div>
      <div class="grid2">
        <div class="field"><div class="k">Klient</div><div id="fClient" class="v">-</div></div>
        <div class="field"><div class="k">Zamówienie</div><div id="fOrder" class="v">-</div></div>
        <div class="field"><div class="k">ID zamówienia</div><div id="fOrderId" class="v">-</div></div>
        <div class="field"><div class="k">Pomieszczenie</div><div id="fRoom" class="v">-</div></div>
        <div class="field"><div class="k">Wyrób</div><div id="fItem" class="v">-</div></div>
        <div class="field"><div class="k">Paczka</div><div id="fPack" class="v">-</div></div>
      </div>
      <div id="rawText" class="raw">RAW: -</div>
      <button id="copyBtn" class="btn good" type="button" style="margin-top:10px">Kopiuj wynik</button>
    </section>

  </div>

  <div id="bigConfirm" class="big-confirm" role="status" aria-live="assertive"></div>

  <script>
    const els = {
      clock:      document.getElementById("clock"),
      healthDot:  document.getElementById("healthDot"),
      cameraBtn:  document.getElementById("cameraBtn"),
      video:      document.getElementById("video"),
      status:     document.getElementById("status"),
      scanInput:  document.getElementById("scanInput"),
      packBadge:  document.getElementById("packBadge"),
      fClient:    document.getElementById("fClient"),
      fOrder:     document.getElementById("fOrder"),
      fOrderId:   document.getElementById("fOrderId"),
      fRoom:      document.getElementById("fRoom"),
      fItem:      document.getElementById("fItem"),
      fPack:      document.getElementById("fPack"),
      rawText:    document.getElementById("rawText"),
      copyBtn:    document.getElementById("copyBtn"),
      bigConfirm: document.getElementById("bigConfirm"),
    };

    const camera = { stream: null, detector: null, running: false, busy: false, lastText: "" };
    const scannerState = { buffer: "", clearTimer: null };

    function norm(v) { return String(v || "").trim(); }

    function setStatus(msg, kind = "") {
      els.status.className = "status" + (kind ? " " + kind : "");
      els.status.textContent = String(msg || "");
    }

    let bigTimer = null;
    function showBigConfirm(title, detail = "") {
      if (!els.bigConfirm) return;
      if (bigTimer) clearTimeout(bigTimer);
      els.bigConfirm.className = "big-confirm show good";
      els.bigConfirm.innerHTML =
        '<div class="big-confirm-card">'
        + '<div class="big-confirm-title">' + escapeHtml(title) + "</div>"
        + (detail ? '<div class="big-confirm-detail">' + escapeHtml(detail) + "</div>" : "")
        + "</div>";
      bigTimer = setTimeout(() => {
        els.bigConfirm.className = "big-confirm";
        els.bigConfirm.innerHTML = "";
        bigTimer = null;
      }, 2200);
    }

    function escapeHtml(t) {
      return String(t ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
    }

    function showPackResult(data) {
      if (!data) {
        els.packBadge.textContent = "PACZKA --/--";
        ["fClient","fOrder","fOrderId","fRoom","fItem","fPack"].forEach(id => { els[id].textContent = "-"; });
        els.rawText.textContent = "RAW: -";
        return;
      }
      const idx = Number(data.package_index || 0);
      const total = Number(data.package_total || 0);
      const pack = norm(data.package_raw) || (idx > 0 ? idx + "/" + (total || "--") : "-");
      els.packBadge.textContent = "PACZKA " + pack;
      els.fClient.textContent  = norm(data.client)     || "-";
      els.fOrder.textContent   = norm(data.order_code) || "-";
      els.fOrderId.textContent = norm(data.order_id)   || "-";
      els.fRoom.textContent    = norm(data.room)        || "-";
      els.fItem.textContent    = norm(data.item)        || "-";
      els.fPack.textContent    = pack;
      els.rawText.textContent  = "RAW: " + (norm(data.raw_text) || "-");
    }

    async function scanText(raw) {
      const text = norm(raw);
      if (!text) return;
      try {
        const resp = await fetch("/api/pack/parse", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ qr_text: text }),
        });
        const payload = await resp.json().catch(() => ({}));
        if (!resp.ok) throw new Error(payload.error || payload.message || "HTTP " + resp.status);
        showPackResult(payload.data || null);
        const label = payload.data && (norm(payload.data.item) || norm(payload.data.order_code));
        setStatus("Odczytano formatke.", "ok");
        if (label) showBigConfirm(label, norm(payload.data.client) || "");
      } catch (err) {
        showPackResult(null);
        setStatus("Nie rozpoznano: " + err.message, "bad");
      }
    }

    /* ── Kamera ── */
    function stopCamera() {
      camera.running = false;
      camera.busy = false;
      if (camera.stream) { camera.stream.getTracks().forEach(t => t.stop()); camera.stream = null; }
      if (els.video) { els.video.srcObject = null; els.video.style.display = "none"; }
      els.cameraBtn.textContent = "Włącz kamerę QR";
    }

    async function scanFrame() {
      if (!camera.running) return;
      if (!camera.detector || camera.busy || !els.video || els.video.readyState < 2) {
        setTimeout(scanFrame, 120); return;
      }
      camera.busy = true;
      try {
        const codes = await camera.detector.detect(els.video);
        if (codes && codes.length > 0) {
          const txt = norm(codes[0].rawValue);
          if (txt && txt !== camera.lastText) {
            camera.lastText = txt;
            stopCamera();
            await scanText(txt);
          }
        }
      } catch (_e) { /* ignoruj błędy klatki */ }
      camera.busy = false;
      if (camera.running) setTimeout(scanFrame, 140);
    }

    async function startCamera() {
      if (!window.isSecureContext) {
        setStatus("Kamera wymaga HTTPS (lub localhost).", "bad"); return;
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatus("Przeglądarka nie obsługuje kamery.", "bad"); return;
      }
      if (!window.BarcodeDetector) {
        setStatus("Brak BarcodeDetector. Użyj Chrome na Androidzie.", "bad"); return;
      }
      try {
        camera.detector = new BarcodeDetector({ formats: ["qr_code"] });
      } catch (_e) {
        try { camera.detector = new BarcodeDetector(); } catch (e2) {
          setStatus("Nie można uruchomić detektora QR.", "bad"); return;
        }
      }
      try {
        camera.stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 } },
          audio: false,
        });
        camera.running = true;
        camera.lastText = "";
        els.video.srcObject = camera.stream;
        els.video.style.display = "block";
        await els.video.play();
        els.cameraBtn.textContent = "Wyłącz kamerę";
        setStatus("Kamera aktywna. Skieruj na kod QR.", "ok");
        scanFrame();
      } catch (err) {
        setStatus("Błąd kamery: " + err.message, "bad");
      }
    }

    els.cameraBtn.addEventListener("click", () => {
      if (camera.running) { stopCamera(); setStatus("Kamera wyłączona.", ""); }
      else startCamera();
    });

    /* ── Kopiuj ── */
    els.copyBtn.addEventListener("click", async () => {
      const raw = norm(els.rawText.textContent).replace(/^RAW:\s*/i, "");
      if (!raw || raw === "-") { setStatus("Brak danych do kopiowania.", "bad"); return; }
      try {
        await navigator.clipboard.writeText(raw);
        setStatus("Skopiowano.", "ok");
      } catch (_e) {
        setStatus("Nie udało się skopiować.", "bad");
      }
    });

    /* ── Skaner USB/klawiaturowy ── */
    document.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        const text = scannerState.buffer.trim();
        scannerState.buffer = "";
        if (scannerState.clearTimer) { clearTimeout(scannerState.clearTimer); scannerState.clearTimer = null; }
        if (text) scanText(text);
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
    async function checkHealth() {
      try {
        const resp = await fetch("/api/health");
        const d = await resp.json().catch(() => ({}));
        els.healthDot.className = "dot" + (d.status === "ok" ? " ok" : "");
      } catch (_e) {
        els.healthDot.className = "dot";
      }
    }

    setInterval(updateClock, 1000);
    setInterval(checkHealth, 15000);
    updateClock();
    checkHealth();
    showPackResult(null);
    // NIE skupiamy inputa — zapobiega wyskakiwaniu klawiatury
  </script>
</body>
</html>
"""
