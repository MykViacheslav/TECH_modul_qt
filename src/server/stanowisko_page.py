"""
Strona webowa wyświetlana na monitorze przy każdym stanowisku produkcyjnym.
Dostępna pod: /stanowisko?id=cnc  (lub oklejanie / lakiernia / montaz / biuro)
Auto-odświeżanie co 60 sekund.
"""
from __future__ import annotations

STATION_LABELS: dict[str, str] = {
    "cnc":       "CNC",
    "oklejanie": "Oklejanie",
    "lakiernia": "Lakiernia",
    "montaz":    "Montaż",
    "biuro":     "Biuro",
}

EVENT_TYPE_LABELS: dict[str, str] = {
    "zlecenie":       "Zlecenie",
    "montaz":         "Montaż",
    "pomiary":        "Pomiary",
    "wstepna_wycena": "Wstępna wycena",
    "zamowienie_mat": "Zam. materiałów",
    "poprawki":       "Poprawki",
    "badania":        "Badania",
    "bhp":            "BHP",
    "urlop":          "Urlop",
    "delegacja":      "Delegacja",
    "inne":           "Inne",
}

EVENT_COLORS: dict[str, str] = {
    "zlecenie":       "#3b82f6",
    "montaz":         "#22c55e",
    "pomiary":        "#f97316",
    "wstepna_wycena": "#06b6d4",
    "zamowienie_mat": "#84cc16",
    "poprawki":       "#d97706",
    "badania":        "#a855f7",
    "bhp":            "#ef4444",
    "urlop":          "#38bdf8",
    "delegacja":      "#a8a29e",
    "inne":           "#64748b",
}


def build_stanowisko_html(station_id: str = "") -> str:
    station_id = station_id.strip().lower()
    station_label = STATION_LABELS.get(station_id, station_id.upper() or "WSZYSTKIE")
    all_stations = list(STATION_LABELS.keys())
    all_stations_json = str(all_stations).replace("'", '"')
    event_colors_js = _dict_to_js(EVENT_COLORS)
    event_labels_js = _dict_to_js(EVENT_TYPE_LABELS)

    return f"""<!doctype html>
<html lang="pl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#0d1117" />
  <title>Stanowisko — {station_label}</title>
  <style>
    :root {{
      --bg:        #0d1117;
      --bg2:       #161b22;
      --bg3:       #21262d;
      --border:    #30363d;
      --text:      #e6edf3;
      --text2:     #8b949e;
      --accent:    #58a6ff;
      --green:     #3fb950;
      --yellow:    #d29922;
      --red:       #f85149;
      --purple:    #bc8cff;
      --radius:    10px;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{ height: 100%; overflow: hidden; }}
    body {{
      background: var(--bg);
      color: var(--text);
      font-family: "Segoe UI", Arial, sans-serif;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }}

    /* ── HEADER ─────────────────────────────────────────────── */
    .header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 28px;
      background: var(--bg2);
      border-bottom: 2px solid var(--border);
      flex-shrink: 0;
      gap: 16px;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 18px;
    }}
    .station-badge {{
      font-size: 2rem;
      font-weight: 800;
      letter-spacing: .04em;
      color: var(--accent);
      background: rgba(88,166,255,.12);
      border: 1.5px solid rgba(88,166,255,.35);
      border-radius: 8px;
      padding: 4px 18px;
      white-space: nowrap;
    }}
    .header-title {{
      font-size: 1.15rem;
      color: var(--text2);
      font-weight: 500;
    }}
    .header-clock {{
      text-align: right;
    }}
    .clock-time {{
      font-size: 2.4rem;
      font-weight: 700;
      color: var(--text);
      line-height: 1;
      font-variant-numeric: tabular-nums;
    }}
    .clock-date {{
      font-size: 0.95rem;
      color: var(--text2);
      margin-top: 2px;
    }}

    /* ── TABS (wybór stanowiska) ─────────────────────────────── */
    .station-tabs {{
      display: flex;
      gap: 6px;
      padding: 10px 28px 0;
      background: var(--bg2);
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
      flex-wrap: wrap;
    }}
    .station-tab {{
      padding: 6px 18px;
      border-radius: 6px 6px 0 0;
      border: 1px solid var(--border);
      border-bottom: none;
      background: var(--bg);
      color: var(--text2);
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      transition: background .15s, color .15s;
    }}
    .station-tab:hover {{ background: var(--bg3); color: var(--text); }}
    .station-tab.active {{
      background: var(--bg3);
      color: var(--accent);
      border-color: var(--accent);
      border-bottom-color: var(--bg3);
    }}

    /* ── STATS BAR ───────────────────────────────────────────── */
    .stats-bar {{
      display: flex;
      gap: 20px;
      padding: 8px 28px;
      background: var(--bg3);
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
      align-items: center;
      flex-wrap: wrap;
    }}
    .stat-chip {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      color: var(--text2);
    }}
    .stat-dot {{
      width: 10px; height: 10px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .stat-chip.overdue  .stat-dot {{ background: var(--red); }}
    .stat-chip.today    .stat-dot {{ background: var(--green); }}
    .stat-chip.planned  .stat-dot {{ background: var(--accent); }}
    .stat-chip.workers  .stat-dot {{ background: var(--purple); }}
    .stat-num {{ color: var(--text); font-size: 1.05rem; }}
    .refresh-info {{
      margin-left: auto;
      font-size: 0.78rem;
      color: var(--text2);
      opacity: .7;
    }}
    #refreshCountdown {{ font-variant-numeric: tabular-nums; }}

    /* ── WORKERS STRIP ───────────────────────────────────────── */
    #workers-strip {{
      display: flex;
      gap: 8px;
      padding: 6px 28px;
      background: rgba(188,140,255,.06);
      border-bottom: 1px solid rgba(188,140,255,.2);
      flex-shrink: 0;
      flex-wrap: wrap;
      min-height: 0;
    }}
    #workers-strip:empty {{ display: none; }}
    .worker-chip {{
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(188,140,255,.12);
      border: 1px solid rgba(188,140,255,.3);
      border-radius: 20px;
      padding: 3px 12px 3px 8px;
      font-size: 0.82rem;
      color: var(--purple);
      font-weight: 600;
    }}
    .worker-dot {{
      width: 7px; height: 7px;
      border-radius: 50%;
      background: var(--green);
      animation: blink 2s infinite;
    }}
    @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}

    /* ── MAIN SCROLL AREA ────────────────────────────────────── */
    .main {{
      flex: 1;
      overflow-y: auto;
      padding: 18px 28px 24px;
      display: flex;
      flex-direction: column;
      gap: 22px;
    }}
    .main::-webkit-scrollbar {{ width: 6px; }}
    .main::-webkit-scrollbar-track {{ background: transparent; }}
    .main::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 3px; }}

    /* ── SECTION HEADER ──────────────────────────────────────── */
    .section-header {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 10px;
    }}
    .section-dot {{
      width: 12px; height: 12px;
      border-radius: 50%;
      flex-shrink: 0;
    }}
    .section-title {{
      font-size: 0.85rem;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .section-count {{
      background: var(--bg3);
      border-radius: 10px;
      padding: 1px 8px;
      font-size: 0.78rem;
      color: var(--text2);
      font-weight: 600;
    }}
    .section-overdue .section-dot  {{ background: var(--red); }}
    .section-overdue .section-title {{ color: var(--red); }}
    .section-today   .section-dot  {{ background: var(--green); }}
    .section-today   .section-title {{ color: var(--green); }}
    .section-planned .section-dot  {{ background: var(--accent); }}
    .section-planned .section-title {{ color: var(--accent); }}

    /* ── TASK CARDS ──────────────────────────────────────────── */
    .cards-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 12px;
    }}
    .card {{
      background: var(--bg2);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 14px 16px 12px 18px;
      border-left-width: 4px;
      display: flex;
      flex-direction: column;
      gap: 6px;
      transition: border-color .2s;
    }}
    .card:hover {{ border-color: var(--accent); }}
    .card-top {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
    }}
    .card-title {{
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text);
      line-height: 1.3;
      flex: 1;
    }}
    .card-type-badge {{
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: .05em;
      text-transform: uppercase;
      padding: 2px 8px;
      border-radius: 5px;
      white-space: nowrap;
      flex-shrink: 0;
    }}
    .card-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    .meta-chip {{
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 0.78rem;
      color: var(--text2);
    }}
    .meta-chip svg {{ width: 12px; height: 12px; flex-shrink: 0; opacity: .7; }}
    .card-dates {{
      font-size: 0.78rem;
      color: var(--text2);
      display: flex;
      gap: 6px;
      align-items: center;
    }}
    .date-range {{
      font-variant-numeric: tabular-nums;
    }}
    .overdue-badge {{
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--red);
      background: rgba(248,81,73,.12);
      border: 1px solid rgba(248,81,73,.3);
      border-radius: 4px;
      padding: 1px 6px;
    }}
    .today-badge {{
      font-size: 0.7rem;
      font-weight: 700;
      color: var(--green);
      background: rgba(63,185,80,.12);
      border: 1px solid rgba(63,185,80,.3);
      border-radius: 4px;
      padding: 1px 6px;
    }}
    .card-notes {{
      font-size: 0.75rem;
      color: var(--text2);
      font-style: italic;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}

    /* ── EMPTY STATE ─────────────────────────────────────────── */
    .empty-state {{
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 12px;
      padding: 60px 20px;
      color: var(--text2);
    }}
    .empty-icon {{ font-size: 3rem; opacity: .4; }}
    .empty-text {{ font-size: 1.1rem; font-weight: 600; opacity: .6; }}

    /* ── LOADING ─────────────────────────────────────────────── */
    #loading-overlay {{
      position: fixed; inset: 0;
      background: var(--bg);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      gap: 16px;
      z-index: 999;
    }}
    #loading-overlay.hidden {{ display: none; }}
    .spinner {{
      width: 40px; height: 40px;
      border: 3px solid var(--border);
      border-top-color: var(--accent);
      border-radius: 50%;
      animation: spin .8s linear infinite;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
  </style>
</head>
<body>

<div id="loading-overlay">
  <div class="spinner"></div>
  <div style="color:var(--text2);font-size:.9rem;">Ładowanie danych…</div>
</div>

<!-- HEADER -->
<div class="header">
  <div class="header-left">
    <div class="station-badge" id="stationBadge">{station_label}</div>
    <div class="header-title">TECH_modul — Ekran stanowiska</div>
  </div>
  <div class="header-clock">
    <div class="clock-time" id="clockTime">--:--:--</div>
    <div class="clock-date" id="clockDate">—</div>
  </div>
</div>

<!-- TABS -->
<nav class="station-tabs" id="stationTabs"></nav>

<!-- STATS -->
<div class="stats-bar">
  <div class="stat-chip overdue">
    <div class="stat-dot"></div>
    Przeterminowane: <span class="stat-num" id="cntOverdue">0</span>
  </div>
  <div class="stat-chip today">
    <div class="stat-dot"></div>
    Dziś / aktywne: <span class="stat-num" id="cntToday">0</span>
  </div>
  <div class="stat-chip planned">
    <div class="stat-dot"></div>
    Planowane: <span class="stat-num" id="cntPlanned">0</span>
  </div>
  <div class="stat-chip workers">
    <div class="stat-dot"></div>
    Pracownicy: <span class="stat-num" id="cntWorkers">0</span>
  </div>
  <div class="refresh-info">
    Odświeżenie za <span id="refreshCountdown">60</span>s
    &nbsp;·&nbsp;
    <span id="lastRefresh">—</span>
  </div>
</div>

<!-- WORKERS STRIP -->
<div id="workers-strip"></div>

<!-- MAIN -->
<div class="main" id="main">
  <!-- filled by JS -->
</div>

<script>
// ── CONFIG ───────────────────────────────────────────────────────
const REFRESH_INTERVAL = 60;   // sekund
const STATION_ID = "{station_id}";

const STATION_LABELS = {{
  cnc:       "CNC",
  oklejanie: "Oklejanie",
  lakiernia: "Lakiernia",
  montaz:    "Montaż",
  biuro:     "Biuro",
}};

const EVENT_COLORS = {event_colors_js};
const EVENT_LABELS = {event_labels_js};

// ── DOM REFS ─────────────────────────────────────────────────────
const els = {{
  clock:      document.getElementById("clockTime"),
  date:       document.getElementById("clockDate"),
  badge:      document.getElementById("stationBadge"),
  tabs:       document.getElementById("stationTabs"),
  main:       document.getElementById("main"),
  loading:    document.getElementById("loading-overlay"),
  cntOverdue: document.getElementById("cntOverdue"),
  cntToday:   document.getElementById("cntToday"),
  cntPlanned: document.getElementById("cntPlanned"),
  cntWorkers: document.getElementById("cntWorkers"),
  workers:    document.getElementById("workers-strip"),
  countdown:  document.getElementById("refreshCountdown"),
  lastRefresh:document.getElementById("lastRefresh"),
}};

// ── CLOCK ─────────────────────────────────────────────────────────
const DAY_PL = ["niedziela","poniedziałek","wtorek","środa","czwartek","piątek","sobota"];
const MON_PL = ["stycznia","lutego","marca","kwietnia","maja","czerwca",
                "lipca","sierpnia","września","października","listopada","grudnia"];

function tickClock() {{
  const now = new Date();
  const hh = String(now.getHours()).padStart(2,"0");
  const mm = String(now.getMinutes()).padStart(2,"0");
  const ss = String(now.getSeconds()).padStart(2,"0");
  els.clock.textContent = `${{hh}}:${{mm}}:${{ss}}`;
  els.date.textContent = `${{DAY_PL[now.getDay()]}}, ${{now.getDate()}} ${{MON_PL[now.getMonth()]}} ${{now.getFullYear()}}`;
}}
setInterval(tickClock, 1000);
tickClock();

// ── STATION TABS ──────────────────────────────────────────────────
function buildTabs() {{
  const tabs = [["","Wszystkie"], ...Object.entries(STATION_LABELS)];
  els.tabs.innerHTML = tabs.map(([id, label]) => {{
    const url = id ? `/stanowisko?id=${{id}}` : "/stanowisko";
    const active = id === STATION_ID ? " active" : "";
    return `<a href="${{url}}" class="station-tab${{active}}">${{label}}</a>`;
  }}).join("");
}}
buildTabs();

// ── DATE HELPERS ──────────────────────────────────────────────────
function todayStr() {{
  const d = new Date();
  return `${{d.getFullYear()}}-${{String(d.getMonth()+1).padStart(2,"0")}}-${{String(d.getDate()).padStart(2,"0")}}`;
}}

function fmtDate(iso) {{
  if (!iso) return "";
  const [y,m,d] = iso.split("-");
  if (!y||!m||!d) return iso;
  return `${{d}}.${{m}}.${{y}}`;
}}

// ── STATION FILTER (mirrors Python WallCalendarView logic) ────────
function matchesStation(ev, stationId) {{
  if (!stationId) return true;
  const wanted  = stationId.trim().toLowerCase();
  const evSt    = (ev.station || "").trim().toLowerCase();
  const evType  = (ev.event_type || "").trim().toLowerCase();
  if (wanted === "biuro") {{
    return evSt.startsWith("biuro") || evType === "projekt" || evType === "zakup";
  }}
  return evSt === wanted || evType === wanted;
}}

// ── STATUS ────────────────────────────────────────────────────────
function getStatus(ev) {{
  const today  = todayStr();
  const start  = ev.date  || "";
  const end    = ev.date_end || ev.date || "";
  if (end  && end  < today) return "overdue";
  if (start && start > today) return "planned";
  return "today";           // in range or today
}}

// ── WORKERS ───────────────────────────────────────────────────────
function renderWorkers(sessions) {{
  // sessions may be array or object
  let list = [];
  if (Array.isArray(sessions)) {{
    list = sessions;
  }} else if (sessions && typeof sessions === "object") {{
    list = Object.values(sessions);
  }}
  // filter to this station if possible (work_type or station field)
  // show all active sessions (started, not ended)
  // sessions in store = still active (removed on shift end)
  const active = list.filter(s => s.started_at_iso);
  els.cntWorkers.textContent = active.length;
  if (!active.length) {{
    els.workers.innerHTML = "";
    return;
  }}
  els.workers.innerHTML = active.map(s => {{
    const name = s.worker_name || s.worker_id || "?";
    const since = s.started_at_iso ? s.started_at_iso.substring(11,16) : "";
    return `<div class="worker-chip"><div class="worker-dot"></div>${{name}}${{since ? " od "+since : ""}}</div>`;
  }}).join("");
}}

// ── RENDER EVENTS ─────────────────────────────────────────────────
function renderEvents(events) {{
  const today = todayStr();
  const filtered = events.filter(ev => matchesStation(ev, STATION_ID));

  const overdue = filtered.filter(ev => getStatus(ev) === "overdue")
    .sort((a,b) => (a.date_end||a.date).localeCompare(b.date_end||b.date));
  const todayEvs = filtered.filter(ev => getStatus(ev) === "today")
    .sort((a,b) => (a.date||"").localeCompare(b.date||""));
  const planned  = filtered.filter(ev => getStatus(ev) === "planned")
    .sort((a,b) => (a.date||"").localeCompare(b.date||""));

  els.cntOverdue.textContent = overdue.length;
  els.cntToday.textContent   = todayEvs.length;
  els.cntPlanned.textContent = planned.length;

  const html = [];

  if (!filtered.length) {{
    html.push(`<div class="empty-state">
      <div class="empty-icon">📋</div>
      <div class="empty-text">Brak zadań dla tego stanowiska</div>
    </div>`);
  }}

  if (overdue.length) {{
    html.push(section("overdue", "Przeterminowane", overdue.length, overdue));
  }}
  if (todayEvs.length) {{
    html.push(section("today", "Dziś / Aktywne", todayEvs.length, todayEvs));
  }}
  if (planned.length) {{
    html.push(section("planned", "Planowane", planned.length, planned));
  }}

  els.main.innerHTML = html.join("");
}}

function section(cls, label, count, items) {{
  const cards = items.map(card).join("");
  return `
    <div>
      <div class="section-header section-${{cls}}">
        <div class="section-dot"></div>
        <div class="section-title">${{label}}</div>
        <div class="section-count">${{count}}</div>
      </div>
      <div class="cards-grid">${{cards}}</div>
    </div>`;
}}

function card(ev) {{
  const color  = EVENT_COLORS[ev.event_type] || "#64748b";
  const typeLabel = EVENT_LABELS[ev.event_type] || ev.event_type || "inne";
  const status = getStatus(ev);
  const today  = todayStr();

  const dateStr = ev.date_end && ev.date_end !== ev.date
    ? `${{fmtDate(ev.date)}} – ${{fmtDate(ev.date_end)}}`
    : fmtDate(ev.date);

  const statusBadge = status === "overdue"
    ? `<span class="overdue-badge">⚠ przeterminowane</span>`
    : status === "today"
      ? `<span class="today-badge">● aktywne</span>`
      : "";

  const workerChip = ev.worker_name
    ? `<div class="meta-chip"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M8 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6zm-5 6s-1 0-1-1 1-4 6-4 6 3 6 4-1 1-1 1z"/></svg>${{ev.worker_name}}</div>`
    : "";
  const orderChip = ev.order_code
    ? `<div class="meta-chip"><svg viewBox="0 0 16 16" fill="currentColor"><path d="M2 1h12a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H2a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1zm1 2v10h10V3z"/></svg>${{ev.order_code}}</div>`
    : "";

  // notes — only show if not JSON metadata and not empty
  let notesHtml = "";
  const notes = (ev.notes || "").trim();
  if (notes && !notes.startsWith("{{")) {{
    notesHtml = `<div class="card-notes">${{escHtml(notes.substring(0,100))}}</div>`;
  }}

  return `
    <div class="card" style="border-left-color:${{color}}">
      <div class="card-top">
        <div class="card-title">${{escHtml(ev.title || "—")}}</div>
        <div class="card-type-badge" style="background:${{color}}22;color:${{color}};border:1px solid ${{color}}55">${{typeLabel}}</div>
      </div>
      <div class="card-dates">
        <span class="date-range">${{dateStr || "—"}}</span>
        ${{statusBadge}}
      </div>
      <div class="card-meta">${{workerChip}}${{orderChip}}</div>
      ${{notesHtml}}
    </div>`;
}}

function escHtml(s) {{
  return String(s)
    .replace(/&/g,"&amp;")
    .replace(/</g,"&lt;")
    .replace(/>/g,"&gt;")
    .replace(/"/g,"&quot;");
}}

// ── FETCH & REFRESH ───────────────────────────────────────────────
async function fetchData() {{
  const [evRes, sesRes] = await Promise.allSettled([
    fetch("/api/calendar_events").then(r => r.json()),
    fetch("/api/work_time_sessions").then(r => r.json()),
  ]);

  if (evRes.status === "fulfilled") {{
    const raw = evRes.value;
    const events = Array.isArray(raw) ? raw : (raw.data || raw.items || []);
    renderEvents(Array.isArray(events) ? events : Object.values(events));
  }}

  if (sesRes.status === "fulfilled") {{
    const raw = sesRes.value;
    const sessions = raw.data || raw.items || raw;
    renderWorkers(sessions);
  }}

  const now = new Date();
  els.lastRefresh.textContent = `${{String(now.getHours()).padStart(2,"0")}}:${{String(now.getMinutes()).padStart(2,"0")}}:${{String(now.getSeconds()).padStart(2,"0")}}`;
  els.loading.classList.add("hidden");
}}

// ── COUNTDOWN ────────────────────────────────────────────────────
let countdown = REFRESH_INTERVAL;
setInterval(() => {{
  countdown--;
  if (countdown <= 0) {{
    countdown = REFRESH_INTERVAL;
    fetchData();
  }}
  els.countdown.textContent = countdown;
}}, 1000);

// ── INIT ─────────────────────────────────────────────────────────
fetchData();
</script>
</body>
</html>
"""


def _dict_to_js(d: dict) -> str:
    """Convert a Python dict to a JS object literal string."""
    parts = []
    for k, v in d.items():
        parts.append(f'  "{k}": "{v}"')
    return "{\n" + ",\n".join(parts) + "\n}"
