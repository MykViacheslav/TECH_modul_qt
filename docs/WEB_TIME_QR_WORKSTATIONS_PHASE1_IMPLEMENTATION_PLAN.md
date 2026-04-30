# WEB TIME, QR & WORKSTATIONS PHASE 1 IMPLEMENTATION PLAN

## 1. Phase 1 Goal
Phase 1 must make web time tracking and production terminal flows operationally safe for workshop daily use.  
Main pain to solve now: remove fake/dead flows, stop silent failures, and ensure worker actions are actually saved with traceable attribution.

## 2. Exact Scope
In scope:
- Fix `/api/kiosk/state` endpoint mismatch.
- Ensure handoff QR status change uses a working backend endpoint from web app.
- Remove/disable dead `TouchTerminal` from real production use.
- Add worker-to-order/project linkage in kiosk actions and saved entries.
- Add worker attribution + timestamp in production task toggles (persisted, not only UI).
- Replace hardcoded 45% production progress with real or safe truth-based fallback.
- Small UX safety fixes (error visibility, action blocking, clear success/failure).

Out of scope:
- Workstation CRUD and workstation master data rollout.
- QR label generator UI.
- Payroll reports and labor cost accounting redesign.
- Advanced analytics dashboards.
- Full auth/permissions redesign.
- Task/module QR system.
- Large UI redesign.

## 3. Target Outcome After Phase 1
After Phase 1, the operational flow should be:
1. Worker is identified by QR/manual selection in kiosk.
2. Worker starts session with explicit `work_type` and optional `project_code/order_id`.
3. Kiosk session state can always be fetched reliably (`/api/kiosk/state` works).
4. Worker performs break/finish actions; finish writes durable work-time entry with linkage fields.
5. On production terminals, task start/finish always records acting worker + timestamp + action log.
6. Handoff QR scan moves order stage through real API call (no dead localhost path, no fake success).
7. Production dashboard shows real progress metric (or explicit safe fallback derived from task states), not fixed 45%.
8. Dead touch-only terminal path is not available as a real production route.

## 4. Current Starting Point
What already exists and works:
- `KioskService` state machine is real and persists sessions/entries.
- Web kiosk scan flow (`/time-tracking/scan`) uses real endpoints.
- Production task action endpoint exists and updates route tasks.

What is broken/risky:
- `/api/kiosk/state` calls nonexistent `kiosk_service.get_worker_state(...)` (service has `get_state(...)`).
- `TouchTerminal` is mock/dead but still used by real routes (`/production/lakiernia`, `/production/montaz`).
- Handoff page uses direct hardcoded `http://localhost:8000/...` fetch and mock worker.
- Kiosk session finish writes `project_code=""` currently (no real linkage capture).
- Production dashboard progress still hardcoded to `45`.

What will be reused:
- `src/server/kiosk_service.py`
- `src/storage/work_time_store_json.py` and `src/storage/work_time_session_store_json.py`
- `src/core/operations_store.py` route task persistence
- Existing FastAPI endpoints in `src/api/main_api.py`

Codebase contradiction vs earlier audit:
- Earlier audit said handoff status endpoint is missing. Current code already has `PUT /api/orders/{order_id}/status` (and `/orders/{order_id}/status`) in `main_api.py`; issue now is frontend integration quality, not endpoint absence.

## 5. Required Backend/API Changes
1. Kiosk state endpoint fix
- Purpose: remove silent failure/`AttributeError` in state reads.
- Shape: `GET /api/kiosk/state?worker_id=...` returns `{ok, state}` or normalized kiosk result.
- Reuse vs new: reuse `KioskService.get_state`; no new service.
- Risk: low.

2. Normalize handoff status update API contract
- Purpose: make QR handoff stage move durable and observable.
- Shape: keep `PUT /api/orders/{id}/status` with body `{status, worker}`; return `{status, message?}` with proper HTTP errors on fail.
- Reuse vs new: reuse `data_manager.update_order_status`; add optional worker audit note if minimal.
- Risk: low.

3. Kiosk action linkage support
- Purpose: persist worker -> project/order linkage from kiosk flow.
- Shape: extend `POST /api/kiosk/action` payload to accept optional `project_code`, `order_id`, `workstation`, `note`; propagate to service/session.
- Reuse vs new: reuse existing endpoint/service; additive fields only.
- Risk: medium.

4. Production task action attribution hardening
- Purpose: no task toggle without clear actor/timestamp.
- Shape: `POST /api/production/task-action` requires non-empty `worker_name`; appends timestamped action log to task notes; optional structured `actor` fields in response.
- Reuse vs new: reuse existing route-task persistence.
- Risk: low/medium.

5. Production status progress calculation
- Purpose: remove fake progress.
- Shape: `GET /api/production/status` computes progress per station from real task state counts (e.g., done / total or in-progress weighted formula); when no data, return explicit `0`.
- Reuse vs new: reuse `OperationsStore.list_routes()`.
- Risk: low.

## 6. Required Data/Persistence Changes
1. Extend `work_time_sessions.json` structure (additive)
- Needed fields: optional `project_code`, `order_id`, `workstation`.
- Why: carry linkage from start to finish.
- Additive/breaking: additive.
- Migration risk: low (default empty values).

2. Extend final work-time entry mapping
- `work_time.json` already has `project_code`; ensure service fills it from session/action payload.
- Optional in `note`: include `order_id/workstation` tag for Phase 1 traceability if no dedicated field.
- Additive/breaking: additive.
- Migration risk: low.

3. Route task attribution persistence
- Existing fields (`crew`, `notes`, `updated_at`) are enough for Phase 1 if enforced consistently.
- No mandatory schema change required for Phase 1.
- Additive/breaking: code activation/validation.
- Migration risk: low.

4. Order status persistence
- Existing `orders.status` update exists.
- Optional Phase 1 additive: write worker stamp in order note/history only if lightweight and already supported.
- Additive/breaking: additive optional.
- Migration risk: low.

## 7. Required Frontend/Web Changes
1. Kiosk scan page safety updates
- Area: `frontend/src/app/time-tracking/scan/page.tsx`
- Purpose: pass linkage fields when starting/finishing session and show backend errors explicitly.
- Size: medium.

2. Handoff QR flow fix
- Area: `frontend/src/app/production/handoff/page.tsx`
- Purpose: replace hardcoded localhost fetch with `TechModulAPI` call; remove mock-only worker behavior; show real failure/success.
- Size: medium.

3. Disable dead TouchTerminal in real routes
- Area: `frontend/src/app/production/lakiernia/page.tsx`, `frontend/src/app/production/montaz/page.tsx`
- Purpose: prevent non-persistent fake flow.
- Size: small.

4. Production dashboard truth-based progress
- Area: `frontend/src/app/production/page.tsx`
- Purpose: display backend-derived progress and stop fake presentation.
- Size: small.

5. API client additions/cleanup
- Area: `frontend/src/services/api.ts`
- Purpose: typed method for order status update and optional kiosk state fetch; unify error handling.
- Size: small.

## 8. File-Level Change Plan
Backend:
- `src/api/main_api.py`
  - Why: kiosk endpoints, handoff order status endpoint contract, production status calculation, task-action validation.
  - Change type: modify existing endpoints; remove duplicate/ambiguous kiosk route definitions; tighten responses.
  - Modify existing.
- `src/server/kiosk_service.py`
  - Why: accept and persist linkage fields through session lifecycle; fill project code on finish.
  - Change type: additive parameters and mapping.
  - Modify existing.
- `src/core/operations_store.py` (optional small touch)
  - Why: if minimal structured action history helper is needed.
  - Change type: small additive helper only.
  - Modify existing (optional).

Persistence:
- `src/storage/work_time_session_store_json.py`
  - Why: session fields for linkage.
  - Change type: dataclass + serialization additive fields.
  - Modify existing.
- `src/domain/work_time_models.py` (optional)
  - Why: if adding explicit order/workstation fields to entry for Phase 1; otherwise keep `project_code` + note tags.
  - Change type: additive only.
  - Modify existing only if needed.
- `src/storage/work_time_store_json.py`
  - Why: ensure merge/upsert keeps linkage fields.
  - Change type: small additive handling.
  - Modify existing.

Frontend:
- `frontend/src/services/api.ts`
  - Why: typed APIs for order status and kiosk state/linkage payloads.
  - Change type: method additions and type updates.
  - Modify existing.
- `frontend/src/app/production/handoff/page.tsx`
  - Why: fix broken QR status move path and mock worker behavior.
  - Change type: switch to API client + better error state.
  - Modify existing.
- `frontend/src/app/production/lakiernia/page.tsx`
  - Why: dead terminal currently active route.
  - Change type: route to real terminal component.
  - Modify existing.
- `frontend/src/app/production/montaz/page.tsx`
  - Why: dead terminal currently active route.
  - Change type: route to real terminal component.
  - Modify existing.
- `frontend/src/app/production/page.tsx`
  - Why: show real progress from backend.
  - Change type: small display update.
  - Modify existing.
- `frontend/src/components/TouchTerminal.tsx`
  - Why: prevent accidental production use.
  - Change type: deprecate banner/guard or keep for sandbox-only.
  - Modify existing.
- `frontend/src/app/time-tracking/scan/page.tsx`
  - Why: capture and submit linkage fields.
  - Change type: small form + payload wiring.
  - Modify existing.

Tests:
- `tests/test_api_time_qr_workstations_phase1.py` (new)
  - Why: focused Phase 1 acceptance tests.
  - Change type: new backend/API tests.
  - Create new file.

## 9. Recommended Operational Flow
worker QR  
→ worker identified in kiosk (`resolve_scan`)  
→ worker sees current session state (`kiosk state`)  
→ start work with selected work type and optional project/order linkage  
→ session persisted in `work_time_sessions.json`  
→ production terminal task start/finish requires worker attribution and logs timestamped action  
→ handoff QR scans order code and updates order stage via real `/api/orders/{id}/status`  
→ finish work in kiosk writes final entry to `work_time.json` with project linkage  
→ dashboard progress reflects real task states.

## 10. Minimal Safe Rules for Phase 1
- No fake success UI when backend request fails.
- No production route may use `TouchTerminal` as real path.
- No task toggle accepted with empty worker attribution.
- No hardcoded worker identity in operational screens.
- No hardcoded progress values.
- Kiosk finish must not discard linkage fields captured at start.
- QR handoff must validate order existence and allowed stage transition before success message.

## 11. Test Plan
Backend tests:
- `GET /api/kiosk/state` returns valid state and no method mismatch error.
- `POST /api/kiosk/action` persists linkage fields through finish.
- `POST /api/production/task-action` rejects empty worker and logs actor/timestamp for start+finish.
- `GET /api/production/status` returns computed progress (not constant placeholder).
- `PUT /api/orders/{id}/status` updates order status and returns failure on invalid order.

Endpoint integration tests:
- Handoff QR style update path using real endpoint contract.
- Kiosk start/break/finish with linkage fields.

Persistence tests:
- `work_time_sessions.json` stores additive linkage fields.
- `work_time.json` final entry carries expected project linkage.

Frontend smoke tests:
- `/time-tracking/scan`: worker can start/finish and see explicit error if API fails.
- `/production/handoff`: QR/ID input updates order stage via API client.
- `/production/lakiernia` and `/production/montaz`: no dead mock terminal behavior.

## 12. Rollout Order
1. Fix backend kiosk state endpoint mismatch.
2. Clean duplicate kiosk endpoint definitions and keep one canonical route set.
3. Add/verify order status endpoint contract used by handoff web flow.
4. Add kiosk linkage fields (session + finish entry mapping).
5. Enforce production task-action worker attribution rules.
6. Replace hardcoded progress logic in production status endpoint.
7. Switch lakiernia/montaz routes away from `TouchTerminal`.
8. Update handoff page to use API client endpoint and real error handling.
9. Add targeted backend/API tests.
10. Run manual workshop smoke pass on kiosk + handoff + terminal toggles.

## 13. Main Risks in Phase 1
1. Duplicate route definitions in `main_api.py`
- Why: can cause confusing behavior and regressions.
- Mitigation: consolidate to one canonical kiosk route block; add endpoint tests.

2. Frontend still calling hardcoded localhost URL
- Why: environment mismatch and silent fail risk.
- Mitigation: all calls through `TechModulAPI` base URL.

3. Linkage fields added but not propagated to final entry
- Why: partial implementation gives false confidence.
- Mitigation: end-to-end test from start action to finished entry assertions.

4. Disabling TouchTerminal may affect expected UI on tablets
- Why: operators may be used to old screen.
- Mitigation: route tablets to `ProductionTerminalPage` first, keep visual labels clear.

5. Progress formula disagreement
- Why: “real progress” definition can vary by station.
- Mitigation: Phase 1 use simple transparent formula (task-state based) and expose logic in code comments.

## 14. Definition of Done
Phase 1 is complete only when all are true:
- `/api/kiosk/state` works without runtime error and returns valid worker/session state.
- Handoff QR status move succeeds through web API client and persists `orders.status`.
- `TouchTerminal` is not used in operational production routes.
- Kiosk finish writes linked project/order context (at minimum `project_code`) to saved time entry.
- Production task actions always persist actor attribution and timestamped log.
- Production progress is computed from real data, not hardcoded.
- Targeted backend/API tests pass.
- Manual smoke test in workshop flow (QR scan -> start -> task action -> handoff -> finish) passes.

## 15. What Must Wait for Phase 2
- Workstation CRUD and workstation entity model.
- QR label generator UI.
- Full task/module QR workflow.
- Payroll reporting and labor-cost allocation.
- Advanced analytics and dashboards.
- Larger architecture cleanup and permissions redesign.

## 16. Plain-Language Summary for Owner
In this phase we are not adding new big modules.  
We are making the current web time and QR flow safe and truthful: no fake terminal, no fake progress, no hidden failures, and real worker attribution on actions.

After Phase 1, operators can reliably scan, start, move status, and finish work with saved records.  
What still waits: advanced workstation management, reporting, and analytics.  
This is the right first step because it reduces operational risk immediately without destabilizing the system.
