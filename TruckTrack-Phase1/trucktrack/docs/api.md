# REST API
Base URL: http://127.0.0.1:8000/api
All request bodies are JSON. Extra input keys are rejected. Interactive OpenAPI is at `/docs`; raw schema is `/openapi.json`. The operational UI is fully local; Swagger's documentation assets may need internet.

## Authentication
`POST /auth/login` accepts `{ "username": "your-user", "password": "your-password" }`. Returns user (never password hash), timezone, csrf, access_token, token_type. Browser receives HttpOnly SameSite=Strict cookie. Browser mutations must send `X-CSRF-Token` returned by login or `/auth/me`. API/mobile clients can send `Authorization: Bearer <access_token>` instead. Do not persist bearer tokens in frontend localStorage. `GET /auth/me` refreshes user/CSRF context. `POST /auth/logout` revokes the session.

## Endpoint map
| Method | Path (under /api) | Role | Behavior |
|---|---|---|---|
|GET|/users, /users/{id}|Admin|Safe account metadata|
|GET|/drivers, /drivers/{id}|All|Driver restricted to own driver record|
|GET|/trucks, /trucks/{id}|All|Driver restricted to assigned trucks|
|GET|/routes, /routes/{id}|All|Drivers see active routes|
|GET|/delay-reasons, /delay-reasons/{id}|All|Drivers see active reasons|
|POST|/users, /drivers, /trucks, /routes, /delay-reasons|Admin|Create validated record|
|PUT|Each above /{id}|Admin|Replace editable fields; blank user password preserves hash|
|DELETE|Each above /{id}|Admin|Deactivate, retain history; open-trip constraints apply|
|GET, PUT|/settings|Management read / Admin write|Configurable alert thresholds|
|GET|/audit?offset=0&limit=100&entity_id=...|Admin|Newest-first audit records; limit <=500|
|POST|/trips|Admin|Schedule truck/driver/outbound/return routes|
|GET|/trips|All|Driver-own scope; date/truck/driver/status filters; offset/limit <=500|
|GET|/trips/{id}|All|Authorized full trip, derived timing, timeline, corrections, exceptions|
|POST|/trips/{id}/identify|Driver/Admin|Validate truck code, active assignment and trip ownership|
|POST|/trips/{id}/events|Driver|Record next driver-confirmed event with server timestamp|
|POST|/trips/{id}/events/missing|Admin|Append missing next event with correction reason and effective time|
|POST|/trips/{id}/events/{event_id}/corrections|Admin|Append timestamp revision; original unchanged|
|POST|/trips/{id}/delay|Driver/Admin|Create/update segment reason and remarks; changes audited|
|POST|/trips/{id}/cancel|Admin|Cancel only unstarted SCHEDULED trip; reason required|
|GET|/dashboard/today|Director/Admin|Today's and carried-forward open trips, KPIs and exception center|
|GET|/dashboard/analytics|Director/Admin|Date/driver/truck filters, timing/delay patterns, accountability, previous equal-length comparison|
|GET|/reports/daily, /reports/weekly, /reports/monthly, /reports/custom|Director/Admin|JSON detail and summary; `format=csv` for export|

Unauthenticated health check: `GET /health` verifies database connection and schema availability.

## Request examples
Create trip:
```json
{"truck_id":1,"driver_id":1,"route_id":1,"return_route_id":2,"scheduled_departure":"2026-09-09T09:00:00+05:30"}
```
Normal event:
```json
{"event_type":"ORIGIN_DEPARTURE","truck_code":"TT-001","device_id":"dispatch desktop","device_time":"2026-09-09T09:00:00+05:30"}
```
Optional event coordinates: latitude/longitude must appear together, within valid bounds. Device time must include timezone. Device evidence is not trusted location attestation.

Correction:
```json
{"event_time":"2026-09-09T10:25:00+05:30","reason":"Dispatch register confirms arrival at 10:25"}
```
A missing-event request also includes `event_type` and must name the next missing event.

Delay:
```json
{"route_segment":"OUTBOUND","reason_id":1,"remarks":"Traffic near destination"}
```

Analytics example: `/dashboard/analytics?period=custom&start=2026-09-01&end=2026-09-30&truck_id=1`
Periods: today, week, month, custom. Dates are inclusive and based on scheduled departure in APP_TIMEZONE. Noncustom ranges ignore explicit dates; reports with both start/end use that custom range. A single report boundary is rejected. Previous period means an equal number of preceding calendar days, not automatically the entire previous calendar month.

## Errors and transactions
400/422 invalid payload/range; 401 invalid or expired login; 403 role/CSRF failure; 404 unknown or inaccessible record; 409 assignment, duplicate, state or integrity conflict; 429 repeated failed login; 503 database unavailable/busy. Transactions commit before response using function-scoped FastAPI dependencies; failures roll back all associated data/audit mutations. User-facing responses never include database connection secrets or SQL statements.
