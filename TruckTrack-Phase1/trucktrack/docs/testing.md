# Verification record and test instructions

## Executed in the build environment
- Read all 36 PDF pages / all 30 numbered sections as extracted text; inspected first-page rendering.
- `python -m unittest tests.test_rules tests.test_schemas -v`: **38 tests passed**.
- `python -m compileall -q app tests migrations`: passed.
- `node --check` on every JavaScript module: passed.
- Unit coverage: exact expected time, tolerance boundary, delayed variance, early arrival, missing start, overnight/timezone arithmetic, correct and invalid sequence, duplicate/fifth events, reverse time, ordered/future corrections, original list preservation, salted password verification, token digests, request lengths/types, coordinates, server-time override rejection, timezone requirements, roles and password whitespace.

## Environment-blocked verification — not claimed as passed
The dependency install could not complete because network approval was cancelled by this environment. FastAPI, SQLAlchemy, Alembic, HTTPX and pytest were not available locally. The full API integration suite, migration execution, seeded database, PostgreSQL path and live server were therefore **not executed here**. The cloud browser also rejected access to the local visual preview with `ERR_BLOCKED_BY_CLIENT`; no visual/end-to-end browser verification is claimed.

This is a complete source implementation with a verification limitation, not a certified production release. Do not infer a passing integration test from a passing Python syntax check.

## Run after installing requirements
From the extracted trucktrack directory with the virtual environment active:
```bash
python -m pytest -q
```
The API suite creates a separate temporary SQLite file and seeds test accounts. It does not use trucktrack.db. API tests cover authentication, CSRF, bearer sessions/logout, role boundaries, driver ownership, truck identity, all four events, duplicate/order rejection, driver timestamp rejection, master-data constraints, snapshots, admin corrections, delays, reports, exception detection, cancellation, input/injection cases, settings and deactivated sessions.

Run dependency-light tests separately:
```bash
python -m unittest tests.test_rules tests.test_schemas -v
```

## Manual desktop acceptance
1. Migrate, initialize admin and run seed-demo. Save the generated demo passwords. Start Uvicorn.
2. Open http://127.0.0.1:8000; sign in as admin. Confirm Overview, People & fleet, Administration, Performance, Reports and Audit load. Select This month or a custom 35-day range for history.
3. Sign out; sign in as demo.driver. My journey must show UP16AB1234 and an appropriate next action. Try an incorrect truck code; it must be rejected. Use TT-001, then confirm the first event.
4. Repeat the next actions in order until return arrival. With rapid test clicks these are near-zero-duration demo journeys; they are not realistic transport-time evidence.
5. Sign out; sign in as demo.director. Confirm completed status, four timestamps and verification evidence. Verify admin mutations cannot be performed via the API using this session.
6. Admin: schedule a new trip for the now-free truck/driver. Confirm attempting another open trip for either resource fails.
7. To exercise delays without waiting, use Admin's Add missing next event on an unstarted test trip. Record departure four hours ago and destination arrival 78 minutes later. Record remaining next events in chronological order, all in the past. Expected 60 + tolerance 10 must yield DELAYED, variance 18.
8. Driver: open that trip and record Traffic plus remarks for outbound. Director: confirm reason, report row and analytics.
9. Admin: correct destination arrival to 80 minutes after departure. Confirm original timestamp remains, revision includes reason/actor/time, derived delay becomes 20, and the previous reported-delay snapshot is retained in API data/audit.
10. Try a correction before departure and one in the future. Both must fail without changes.
11. Admin: schedule a new trip with departure sufficiently in the past. Check late-start warning. Add a missing departure over 90 minutes ago; check significant-delay and overdue-arrival warnings. Destination arrival over 120 minutes ago without return departure produces return-not-started.
12. Export daily, weekly and monthly CSVs; confirm totals, filters, UTF-8 place/driver names, reasons and prior-period values. CSV cells beginning with formula markers are escaped.
13. Restart the server and confirm data persists. Sign out and confirm the old session no longer grants access.
14. Inspect at 1280×800 and 1440×900: navigation, tables with horizontal scrolling, modal forms, error messages, next-action buttons and timeline. Mobile layout is intentionally deferred.
15. Before a PostgreSQL deployment: run migration, API suite configured for an isolated PostgreSQL test DB, simultaneous punch/create/correction tests, backup/restore and TLS/session checks. The supplied automated suite specifically uses SQLite; adapting its test DB fixture is needed for a separate PostgreSQL deployment test, not for Phase 1 local operation.
