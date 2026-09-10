# TruckTrack — requirement map and scope
Source: Untitled document(1).pdf, all 36 pages / sections 1–30. The user's desktop-first instruction overrides the PDF's responsive/mobile delivery wording. No native mobile app in Phase 1.

## Business problem and users
Reliable Noida–Delhi–Noida operations without repeated driver calls. Driver records simple verified events and delay reasons; Director investigates exceptions and performance; Admin configures operations and performs explicitly audited corrections. Multi-truck and multi-route relational design from day one.

## Source-to-feature map
| Source sections | Phase 1 implementation / verification |
|---|---|
|1–4, 29|Modular Python FastAPI monolith, REST boundary, desktop HTML/CSS/JS UI, SQLite local / PostgreSQL-compatible SQLAlchemy|
|5, 22|Hashed passwords, database sessions, login/logout, active-user checks, driver ownership restriction, Director read-only, Admin maintenance|
|6, 13 verification step|Unique truck code validated against active assigned driver and trip; evidence stored per event. No camera/physical-presence claim|
|7–8|Users, drivers, trucks, directional routes, trips, four ordered events, delays, reasons, audit logs; support multiple trucks/routes|
|9–10|Per-direction expected duration/tolerance snapshots; server-calculated duration/delay; short reason/remarks form|
|11, 14 audit step|Server UTC timestamp, optional client timestamp/location/device evidence, explicit driver confirmation; append-only correction records with old/new/who/when/why|
|12–15|Current-operation cards, selected-trip timeline, status, started/expected arrival, travel/expected/delay, linked exception center|
|16–18|Today/week/month/custom range, outbound/return min/mean/max, on-time %, delay totals/mean/max, reason and direction breakdown; per-driver accountability|
|19|Daily/weekly/monthly/custom reports, daily detail rows, summary metrics, monthly comparisons, CSV export|
|20|Configurable significant-delay, late-start, overdue-punch, destination-dwell and long-open thresholds; in-app alerts refreshed while dashboard open|
|21|Extension boundaries for GPS/ETA/maintenance/fuel/documents; not implemented in V1|
|23–24|REST endpoints, Pydantic schemas, service/repository separation, documented API and folder layout|
|25|Requirements/design before coding, migrations, health check, incremental tests, at least 30 historical demo trips|
|26–28|Driver next-action workspace and own history; director dashboard/reports; admin management/audit; full four-event acceptance scenario|
|30|Architecture, ERD, API, flows, decisions and verification plan in docs|

## Rules and validations
- Journey: ORIGIN_DEPARTURE → DESTINATION_ARRIVAL → DESTINATION_DEPARTURE → ORIGIN_ARRIVAL. Location labels derive from routes, matching Noida/Delhi example without hardcoding these places.
- Admin schedules a truck/driver pair and two reverse directional routes. One open trip per truck AND per driver. Reject inactive entities, wrong assignment, mismatched reverse routes, duplicate/out-of-order events and future correction times.
- Driver sees and operates only own records. Director reads management information, cannot mutate. Admin alone manages master data, users, settings and corrections.
- Normal punches use authoritative server UTC time; capture optional device time as untrusted evidence. Driver cannot submit authoritative times. Corrections never destroy the original event; effective values derive from correction revisions.
- Delay is max(0, actual − expected). DELAYED only when actual > expected + tolerance. Metrics display variance even when within tolerance; report count includes only beyond-tolerance segments.
- Snapshot both route durations/tolerances and names at trip creation; later route edits cannot rewrite history.
- Referenced master records are deactivated rather than physically deleted. Preserve audit trail and restrict changes affecting an open trip.
- Password length 12–128; finite capacities and positive bounded timing fields; validated timestamps, coordinates and text lengths; SQLAlchemy bound queries, cookie CSRF checks, revoked sessions, login throttling.

## Explicit assumptions (configurable; company should confirm)
1. Local timezone Asia/Kolkata; timestamps stored UTC, displayed locally. Workday follows trip's scheduled departure date.
2. Admin creates scheduled trips; no recurring auto-scheduler was specified. Incomplete trips carry forward on operations screen.
3. Server clock is authoritative for reliability. Device timestamp is retained as evidence, resolving the PDF's device-time versus anti-manipulation tension.
4. V1 identification = unique truck code typed or entered using a keyboard scanner. This verifies database assignment, not physical location or truck authenticity.
5. Alerts are in-app, evaluated on refresh (30 seconds). Email/SMS/push provider and recipients are unspecified, so no external delivery is invented.
6. Defaults: significant delay 30 min, start grace 30 min, overdue arrival grace 30 min, destination dwell 120 min, maximum open duration 720 min. Editable by Admin.
7. Missing punch means overdue expected next event; the software cannot distinguish actual travel delay from a forgotten punch without evidence.
8. Admin inherits management read access and can record missing next events with a required reason; cannot bypass causal event ordering.
9. Cancellation is permitted only for a trip with no punches and requires reason; no deletion of operational records.
10. Completed-trip on-time denominator includes completed trips only. Delay statistics count completed travel segments over tolerance. Missing reasons remain visible as Unreported.
11. No unrequested fuel, maintenance, vehicle documents, live tracking, AI, mobile responsiveness, or camera recognition.

## Nonfunctional scope
Desktop browser at 1200px+; no build tool/CDN required for operational UI. Persistent SQL database, atomic writes, uniqueness constraints, security headers, no secrets bundled. Local single-process server is the Phase 1 target. Production deployment requires environment-specific TLS, backup/restore, monitoring and infrastructure validation; code cannot itself certify production readiness.

## Design verification before coding
Reviewed all 30 sections against the map above. Event sequence, route direction, timestamps, correction semantics, permission boundaries, metric denominators, notifications and deferred scope are internally consistent with the stated assumptions. Proceed under the user's authorization to complete Phase 1; these assumptions are not represented as company-confirmed policies.
