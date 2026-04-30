# WEB_TIME_QR_WORKSTATIONS_AUDIT.md
# Audit: Time Tracking, QR Workflows, Workstations, and Labor Recording
# Project: TECH_modul — ERP for furniture manufacturing workshop
# Generated: 2026-04-22
# Scope: Web frontend (frontend/) + FastAPI backend (src/api/) compared to desktop (src/)

---

## 1. Executive Summary

Time tracking in TECH_modul has the most complete real implementation of any web feature area audited.
The KioskService state machine (`src/server/kiosk_service.py`) is production-ready with correct JSON
persistence, proper break handling, and net-hour computation. The web kiosk scan page
(`time-tracking/scan/page.tsx`) calls it correctly via real API endpoints.

However, this working core is surrounded by partially or fully mocked components:
- `handoff/page.tsx` uses a hardcoded worker "JanK." and calls a missing endpoint → always 404
- `TouchTerminal.tsx` shows `alert()` on finish and saves nothing
- `/api/kiosk/state` has a method name mismatch bug (`get_worker_state` vs `get_state`) → `AttributeError`
- `production/page.tsx` reports hardcoded 45% progress regardless of actual data
- Workstations are string literals scattered across files — no database entity

The gap between the real KioskService and the mocked UI layers is the dominant risk.

---

## 2. Scope

| Area | Covered |
|---|---|
| Employee time tracking (RCP) — clock in/out/break | Yes |
| QR code scanning for workers and orders | Yes |
| Web kiosk terminal (time-tracking/scan) | Yes |
| Production terminal (production/_components) | Yes |
| Order handoff / kanban board | Yes |
| Workstation entities and assignment | Yes |
| Desktop time tracking comparison | Yes |
| Backend KioskService and persistence | Yes |
| Data server vs FastAPI dual-server issue | Yes |

Out of scope: invoice import, estimation/pricing, 3D import, material warehouse.

---

## 3. Relevant Web Structure

```
frontend/src/app/
├── time-tracking/
│   ├── page.tsx                     # Monthly work sheet editor (per worker, per day)
│   └── scan/
│       └── page.tsx                 # Web kiosk: camera QR + worker grid + action buttons
├── production/
│   ├── page.tsx                     # Production overview (progress hardcoded 45%)
│   ├── handoff/
│   │   └── page.tsx                 # Kanban order handoff — PARTIALLY MOCKED
│   └── _components/
│       └── ProductionTerminalPage.tsx  # 5-station production terminal — REAL
frontend/src/components/
└── TouchTerminal.tsx                # Touch-friendly kiosk variant — FULLY MOCKED

frontend/src/services/api.ts         # TechModulAPI typed client (lines ~850-1100 for kiosk)
```

---

## 4. Desktop Reference Structure

```
src/
├── server/
│   ├── kiosk_service.py             # KioskService state machine — REAL, 246 lines
│   ├── worker_qr.py                 # QR generation and parsing
│   ├── work_time_store.py           # WorkTimeStoreJson (monthly archive)
│   └── work_time_session_store.py   # WorkTimeSessionStoreJson (live sessions)
├── ui/
│   ├── kiosk_page.py                # Desktop PyQt6 kiosk (BarcodeDetector via WebView)
│   ├── stanowisko_page.py           # Workstation assignment UI
│   └── tab_stanowiska.py            # Workstation tab (full CRUD)
├── api/
│   ├── main_api.py                  # FastAPI — kiosk endpoints lines ~1200-1400
│   └── data_server.py               # Legacy HTTP server on port 8000 — ALSO handles kiosk
data/
├── work_time.json                   # Monthly archive (WorkTimeStoreJson)
├── work_time_sessions.json          # Live sessions (WorkTimeSessionStoreJson)
└── workers.json                     # Worker definitions with QR strings
```

---

## 5. Employee Time Tracking / RCP: Desktop vs Web

### Desktop (PyQt6)
- `kiosk_page.py`: full PyQt6 widget embedding a browser for BarcodeDetector camera QR
- Worker QR format: `TECH_MODUL_WORKER|ID=XXX|NAME=YYY` — parsed by `worker_qr.py`
- `tab_stanowiska.py`: full CRUD for workstation entities with assignment tracking
- Desktop time sheet (`tab_czas_pracy.py`): monthly calendar grid, per-day entries, manual edit
- Full audit trail: each finish call writes `WorkTimeEntryDef` with start, end, breaks, net hours
- Note on finished entry: `"Rejestracja z kiosku web"` (hardcoded in `kiosk_service.py:189`)

### Web (Next.js)
- `time-tracking/scan/page.tsx`: real kiosk, fully functional via `KioskService`
- `time-tracking/page.tsx`: monthly sheet editor, shows existing `work_time.json` data
- No equivalent of `tab_stanowiska.py` — workstation CRUD missing from web entirely
- No worker QR generation page in web (desktop `worker_qr.py` generates printable QR labels)

### Comparison table

| Feature | Desktop | Web |
|---|---|---|
| Camera QR scan | Yes (kiosk_page.py) | Yes (scan/page.tsx) |
| Manual worker search | Yes | Yes (worker grid) |
| Clock in / break / out | Yes | Yes |
| Session state persistence | JSON (real) | JSON via same KioskService |
| Monthly time sheet view | Yes (calendar grid) | Yes (page.tsx) |
| Workstation CRUD | Yes (tab_stanowiska.py) | No |
| QR label printing | Yes (worker_qr.py) | No |
| Project linking per session | No (project_code = "") | No |

---

## 6. QR Workflows Found in the Codebase

### 6.1 Worker QR (`TECH_MODUL_WORKER|ID=XXX|NAME=YYY`)
- **Generated by:** `src/server/worker_qr.py` (desktop)
- **Parsed by:** `KioskService.resolve_scan(qr_text)` in `kiosk_service.py:77-92`
- **Web endpoint:** `POST /api/kiosk/scan` → calls `kiosk_service.resolve_scan()`
- **Web UI:** `time-tracking/scan/page.tsx` — BarcodeDetector + `resolveKioskScan(id)`
- **Status: REAL and WORKING**

### 6.2 Order QR (`PRJ-{id}`)
- **Used by:** `production/handoff/page.tsx` — `handleScan()` reads input, matches `PRJ-{id}`
- **Endpoint called:** `PUT http://localhost:8000/api/orders/{orderId}/status`
- **Status of endpoint:** DOES NOT EXIST in `data_server.py` or `main_api.py`
- **Result:** 404 always, UI does optimistic update then reverts on error
- **Status: BROKEN**

### 6.3 QR in data_server.py HTML kiosk pages
- `data_server.py` serves static HTML kiosk pages at port 8000
- These HTML pages also use `BarcodeDetector` via inline JavaScript
- Separate code path from Next.js web app
- No shared state management — session state may diverge if both active simultaneously

### Summary

| QR Type | Generated | Scanned (Web) | Scanned (Desktop) | Persisted |
|---|---|---|---|---|
| Worker QR | worker_qr.py ✓ | scan/page.tsx ✓ | kiosk_page.py ✓ | work_time.json ✓ |
| Order QR (PRJ-) | Unknown | handoff/page.tsx (broken) | Unknown | Never (endpoint missing) |
| Task/Module QR | Not implemented | Not implemented | Not implemented | N/A |

---

## 7. Workstation / Terminal Workflows

### 7.1 Workstation entities
Workstations are NOT database entities anywhere in the codebase. They exist only as hardcoded string literals:

```
"cnc" | "oklejanie" | "lakiernia" | "montaz" | "biuro"
```

These strings appear in at minimum:
- `ProductionTerminalPage.tsx` (station tab type)
- `main_api.py` production endpoints
- `stanowisko_page.py` desktop UI
- `tab_stanowiska.py` desktop CRUD (UI labels, not DB rows)
- `kiosk_service.py` — `workstation` field on `WorkTimeEntryDef` (string, not FK)

Adding or renaming a workstation requires changes in at least 5 files simultaneously.

### 7.2 ProductionTerminalPage.tsx — REAL
- 5 station tabs: CNC, Oklejanie, Lakiernia, Montaż, Biuro
- `getProductionTasks(station)` → `GET /api/production/tasks?station=X`
- `toggleProductionTask(taskId)` → `POST /api/production/tasks/{id}/toggle`
- 10-second polling for live updates
- `findMaterialForTask()` — score-based fuzzy material matching
- `detectSheetFormat()`, `detectGlueType()`, `detectBatchTag()` — text parsing helpers
- **Status: REAL, calls real API, but no actual persistence of "who did what" per task**

### 7.3 TouchTerminal.tsx — FULLY MOCKED
- Touch-optimized kiosk variant for tablet use
- `handleFinish()` calls `alert("Praca zakończona!")` — nothing saved
- Tasks are hardcoded local array, not fetched from API
- Worker state not persisted
- **Status: DEAD — do not rely on this component for any real functionality**

### 7.4 handoff/page.tsx — PARTIALLY MOCKED
- 6-stage kanban: Rysunek → Materiały → Produkcja → Montaż → Poprawki → Zakończone
- `activeWorker` hardcoded to `"JanK."` (comment: `// Mock worker logged in`)
- QR scan input `handleScan()` parses `PRJ-{id}` and calls `moveOrder()`
- `moveOrder()` → `PUT http://localhost:8000/api/orders/{orderId}/status` — endpoint MISSING
- **Status: BROKEN — kanban stage change always fails silently**

### 7.5 production/page.tsx
- Shows production overview per order
- Progress displayed as hardcoded `45%` regardless of actual task completion
- Fetches order list from real API, but progress calculation is faked
- **Status: PARTIALLY REAL — data fetched, progress mocked**

---

## 8. Current Web Labor/Event Flow

### Working flow (time-tracking/scan):
```
Worker presents QR card
  → BarcodeDetector reads TECH_MODUL_WORKER|ID=XXX|NAME=YYY
  → POST /api/kiosk/scan → KioskService.resolve_scan()
  → Returns worker_id + current session state
  → UI shows start / break_start / break_end / finish buttons
  → Button press → POST /api/kiosk/action {worker_id, action}
  → KioskService._handle_action() runs state machine
  → On finish: _finish_session() writes WorkTimeEntryDef to work_time.json
  → Live session deleted from work_time_sessions.json
```

### Broken flow (handoff QR):
```
User scans order QR PRJ-{id}
  → handleScan() parses id
  → moveOrder(id, nextStage) called
  → PUT http://localhost:8000/api/orders/{id}/status
  → 404 Not Found
  → Optimistic UI update reverts
  → No state change persisted
```

### Dead flow (TouchTerminal):
```
Worker taps "Zakończ"
  → handleFinish()
  → alert("Praca zakończona!")
  → [nothing]
```

---

## 9. Worker / Task / Station / Project Linking

### What KioskService stores per session:
```python
class WorkTimeEntryDef:
    worker_id: str
    worker_name: str
    date: str
    start_time: str
    end_time: str
    break_minutes: int
    net_hours: float
    workstation: str   # hardcoded string, not FK
    project_code: str  # ALWAYS "" — never set
    note: str          # ALWAYS "Rejestracja z kiosku web"
```

### What is missing from every session:
- `project_code` is hardcoded to `""` in `kiosk_service.py:183`
- No task reference — cannot answer "what did this worker produce today?"
- No order reference — cannot answer "which order's labor hours are these?"
- No module reference — cannot compute per-module labor cost
- `note` is always the same string — no custom notes per session

### ProductionTerminalPage task linking:
- Tasks are fetched per station: `GET /api/production/tasks?station=X`
- `toggleProductionTask(taskId)` marks task done/undone
- Task completion is stored, but NOT linked to which worker toggled it
- No timestamp on individual task completion (only order-level status)

---

## 10. Persistence and Audit Trail

### Real persistence (KioskService path):
| Store | File | Written by | When |
|---|---|---|---|
| Live sessions | `data/work_time_sessions.json` | `WorkTimeSessionStoreJson` | start / break / action |
| Monthly archive | `data/work_time.json` | `WorkTimeStoreJson.upsert_day_entry()` | finish only |
| Worker list | `data/workers.json` | Desktop worker CRUD | manual |

### No audit trail for:
- Task completion toggles (who, when, which task)
- Kanban stage changes (would have been written by missing endpoint)
- Production progress (hardcoded, never written)
- Break reasons (break is tracked in minutes, no reason field)

### Retention concern:
`work_time_sessions.json` is deleted (entry removed) on session finish. If the server crashes
between `start` and `finish`, the live session is lost. There is no recovery mechanism or
session orphan detection.

---

## 11. What Is Already Done in Web

| Feature | File | Notes |
|---|---|---|
| Worker QR scan via camera | time-tracking/scan/page.tsx | BarcodeDetector, real |
| Manual worker search | time-tracking/scan/page.tsx | Worker grid with search |
| Clock in / break / clock out | time-tracking/scan/page.tsx | All 4 actions real |
| Session state display | time-tracking/scan/page.tsx | Start time, elapsed |
| Monthly time sheet view | time-tracking/page.tsx | Reads work_time.json |
| 5-station production terminal | ProductionTerminalPage.tsx | 10-sec polling, real |
| Task toggle per station | ProductionTerminalPage.tsx | Persisted via API |
| Material matching for tasks | ProductionTerminalPage.tsx | Fuzzy score match |

---

## 12. What Is Partially Done in Web

| Feature | File | Gap |
|---|---|---|
| Order kanban | handoff/page.tsx | PUT endpoint missing → always 404 |
| Worker identity in handoff | handoff/page.tsx | Hardcoded "JanK.", no real auth |
| Production progress | production/page.tsx | Data fetched but progress hardcoded 45% |
| Kiosk state query | main_api.py | `/api/kiosk/state` calls wrong method name |
| Task authorship | ProductionTerminalPage.tsx | Toggled but not attributed to worker |

---

## 13. What Is Missing in Web Compared to Desktop

| Missing Feature | Desktop Has It In | Effort to Add |
|---|---|---|
| Workstation CRUD (add/rename/delete) | tab_stanowiska.py | Medium — needs DB table first |
| Worker QR label printing | worker_qr.py | Small — generate PNG/PDF with qrcode lib |
| Project code linkage per session | Not in desktop either | Medium — requires session form change |
| Task attribution per toggle | Not in desktop either | Small — add worker_id to toggle payload |
| Session orphan recovery | Not anywhere | Medium |
| Break reason field | Not anywhere | Small |
| Per-task labor cost allocation | Not anywhere | Large |
| Real production progress calculation | Not anywhere | Medium |

---

## 14. UX / Product Gaps

1. **No confirmation screen after clock-out.** Worker scans, presses Finish, sees nothing except
   the page returning to idle. No "You worked 7h 32m today, goodbye" message.

2. **TouchTerminal is dead but installed.** If routed to this component (e.g., tablet kiosk),
   workers think they are clocking out but nothing is saved. Silent data loss.

3. **Handoff kanban appears to work.** The optimistic update shows the order moving to next stage,
   then reverts silently after the 404. Workers may assume the move happened.

4. **Worker name search is case-sensitive.** `workers.filter(w => w.name.includes(query))` —
   typing "jan" won't find "Jan".

5. **No per-worker summary in kiosk.** After clock-in, there is no "You have worked 3 days this
   week" context visible to the worker.

6. **Production terminal has no "assigned to me" filter.** All workers see all tasks for their
   station. Useful for small teams, problematic as headcount grows.

---

## 15. Risks / Technical Debt

### Critical (data loss or silent failure)

| Risk | Location | Impact |
|---|---|---|
| `get_worker_state` AttributeError | `main_api.py` `/api/kiosk/state` | Endpoint always crashes; kiosk state cannot be queried via FastAPI |
| TouchTerminal saves nothing | `TouchTerminal.tsx` | If routed to tablet kiosk, all clock-outs are lost |
| Order QR endpoint missing | `handoff/page.tsx` + missing route | All kanban moves via QR silently fail |
| Session lost on server crash | `KioskService._sessions` dict | No persistence between start and finish if server restarts |
| Two servers handling kiosk | `data_server.py` + `main_api.py` | Sessions from port 8000 not visible to FastAPI and vice versa |

### Method name mismatch — detailed:
```python
# main_api.py (FastAPI endpoint)
state = kiosk_service.get_worker_state(worker_id)  # AttributeError!

# kiosk_service.py (actual method name)
def get_state(self, worker_id: str) -> Optional[dict]:
    ...

# data_server.py (correct call)
state = kiosk_service.get_state(worker_id)  # Works
```

### High (correctness)

| Risk | Location | Impact |
|---|---|---|
| Workstations as string literals | 5+ files | Adding a station requires code changes, not config |
| `project_code = ""` always | `kiosk_service.py:183` | Labor hours never linked to any order |
| Hardcoded progress 45% | `production/page.tsx` | Misleads any capacity planning view |
| Hardcoded worker "JanK." | `handoff/page.tsx` | Audit trail says the same person moved every order |

---

## 16. Recommended Target Flow

The target flow, once all components are connected, should be:

```
1. WORKER ARRIVAL
   Worker scans QR card at web kiosk
   → System identifies worker, shows current state
   → Worker selects workstation from dropdown (not hardcoded string)
   → Optionally selects active order/project
   → Presses START → KioskService records session

2. DURING SHIFT
   Worker opens production terminal on same station
   → Sees tasks assigned to their station AND their active order
   → Toggles tasks complete → attribution saved with worker_id + timestamp
   → If moving order to next kanban stage: scans order QR
   → PUT /api/orders/{id}/status persists stage + worker who moved it

3. END OF SHIFT
   Worker scans QR again at kiosk
   → Shows: "You worked X hours today on [order], completed Y tasks"
   → Presses FINISH → KioskService writes entry with project_code populated
   → Monthly work_time.json updated, session deleted

4. MANAGER VIEW (next day)
   Opens time-tracking/page.tsx → sees all workers, hours, per-order breakdown
   Opens production/page.tsx → sees real % completion (from task toggles, not hardcoded)
```

---

## 17. Recommended Build Order (Priority 1/2/3)

### Priority 1 — Fix silent failures (no new features, just correctness)

1. **Fix `get_worker_state` → `get_state` in `main_api.py`**
   - File: `src/api/main_api.py`
   - One-line rename, eliminates `AttributeError` on `/api/kiosk/state`

2. **Add `PUT /api/orders/{id}/status` endpoint**
   - File: `src/api/main_api.py`
   - Reads `data/zamowienia.json`, updates stage field, writes back
   - Unblocks handoff QR and kanban board entirely

3. **Remove or disable `TouchTerminal.tsx`**
   - Either remove routing to it or add a warning banner
   - Prevents silent clock-out data loss on tablet kiosks

### Priority 2 — Connect existing real components

4. **Wire `project_code` in kiosk session**
   - Add order selector to `time-tracking/scan/page.tsx` after worker resolves
   - Pass `project_code` to `POST /api/kiosk/action` payload
   - `KioskService` stores it in `WorkTimeEntryDef`

5. **Add `worker_id` to task toggle**
   - `ProductionTerminalPage.tsx`: include `activeWorker` in `toggleProductionTask()` call
   - Backend: add `toggled_by: str` to task record
   - Enables real task attribution

6. **Replace hardcoded 45% with real calculation**
   - `production/page.tsx`: compute `completed_tasks / total_tasks` per order
   - Data already available from `GET /api/production/tasks?station=X`

### Priority 3 — New structure (medium effort)

7. **Create `workstations` table in SQLite**
   - Schema: `id, name, display_name, active`
   - Seed with 5 current hardcoded stations
   - Replace string literals with FK lookups across all files

8. **Add workstation selector in kiosk scan page**
   - After worker resolves, show workstation dropdown
   - Pass to `KioskService` → stored on `WorkTimeEntryDef`

9. **Build workstation CRUD page in web**
   - Equivalent of desktop `tab_stanowiska.py`
   - Required before workstations can be managed without code changes

---

## 18. Suggested Target Web Structure

```
frontend/src/app/
├── time-tracking/
│   ├── page.tsx                     # Monthly sheet — exists, keep
│   ├── scan/
│   │   └── page.tsx                 # Web kiosk — exists, extend with order selector
│   └── admin/
│       └── page.tsx                 # NEW: manager view, hours by order, export
├── production/
│   ├── page.tsx                     # Fix hardcoded 45%
│   ├── terminal/
│   │   └── page.tsx                 # Rename from _components/ProductionTerminalPage
│   ├── handoff/
│   │   └── page.tsx                 # Fix endpoint, fix hardcoded worker
│   └── tasks/
│       └── page.tsx                 # NEW: task list with worker attribution
├── workstations/
│   ├── page.tsx                     # NEW: workstation CRUD (replaces tab_stanowiska.py)
│   └── [id]/
│       └── page.tsx                 # NEW: per-station task view + active workers
└── workers/
    └── qr/
        └── page.tsx                 # NEW: QR label generator + print (replaces worker_qr.py)
```

---

## 19. Open Questions

1. **Should sessions survive server restart?**
   Currently `WorkTimeSessionStoreJson` is a dict in memory backed by JSON — but loaded fresh
   on startup. If `work_time_sessions.json` is written on every action, sessions DO survive
   restart. Confirm that `_save()` is called on every state change (it is, in `kiosk_service.py`).
   Risk is if the server process is killed mid-write (file corruption).

2. **Which server should own the kiosk endpoints long-term?**
   Both `data_server.py` (port 8000) and `main_api.py` (FastAPI) currently call the same
   `KioskService` instance. If they run as separate processes, sessions will diverge.
   Decision needed: consolidate all kiosk traffic to FastAPI and retire `data_server.py`.

3. **How should workstation assignment work?**
   Option A: Worker selects workstation at each clock-in (flexible, extra tap per day).
   Option B: Worker has a default workstation set in `workers.json` (fast, less flexible).
   Option C: System auto-detects workstation from which terminal scanned the QR.

4. **Who generates worker QR codes in production?**
   Currently only desktop `worker_qr.py` can generate them. If a new worker is added via web,
   they cannot get a QR card without also having the desktop app available.

5. **Should production task completion drive labor cost in wycena?**
   If task toggles include `worker_id` and timestamp, it becomes possible to compute actual
   labor cost per order. This would be a significant improvement over the current hardcoded
   rates in `ProductionService`. Is this in scope for next quarter?

---

## 20. Plain-language Summary for Owner

**What works right now in your web app for time tracking:**
- Workers can scan their QR cards at the web kiosk page and clock in, take breaks, and clock
  out. This is fully real — hours are saved to the JSON file and can be viewed in the monthly
  sheet. The 5 production station terminals (CNC, Oklejanie, Lakiernia, Montaż, Biuro) are
  also real — workers can see and check off tasks.

**What looks like it works but doesn't:**
- The order handoff kanban board (where you scan an order QR to move it to the next stage)
  appears to move the order, then silently resets — because the API endpoint it needs doesn't
  exist yet. This needs one new API route to fix.
- There is a second kiosk component (TouchTerminal) that may be shown on tablets — it shows
  `alert("Praca zakończona!")` and saves nothing. Workers think they clocked out but they didn't.

**The biggest missing piece:**
- When a worker clocks in, their hours are saved but there is no link to which order they were
  working on. So you can see "Jan worked 8 hours on Tuesday" but not "Jan worked 4 hours on
  order #42 and 4 hours on order #57." Adding an order selector to the clock-in screen would
  fix this and make labor cost allocation possible.

**The quickest wins (each under 1 hour of developer time):**
1. Fix one typo in `main_api.py` (`get_worker_state` → `get_state`) — stops a crash
2. Add the missing `PUT /api/orders/{id}/status` endpoint — fixes kanban QR scanning
3. Remove `TouchTerminal.tsx` from any tablet kiosk routing — stops silent data loss

**The medium-term goal:**
Turn workstations from hardcoded text strings into proper database records so you can add or
rename a station without touching code. This is a 1-2 day task but unlocks clean workstation
management, proper assignment tracking, and real reporting by station.

---

*End of audit. Document covers time tracking, QR workflows, workstations, and labor recording.*
*Related audits: WEB_SERVICES_ESTIMATION_AUDIT.md, WEB_MATERIALS_DATABASE_AUDIT.md, WEB_MATERIALS_INVOICE_AUDIT.md*
