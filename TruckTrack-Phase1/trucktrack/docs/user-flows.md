# Screens and end-to-end flows

| Screen | User | Main controls |
|---|---|---|
|Sign in|All|Username/password, inline errors|
|My journey|Driver|Assigned truck, current stage, next punch, short delay form, recent own history|
|Operations overview|Director/Admin|Today's KPIs, current operation, timeline, exception links, all today's/carried-forward journeys, refresh|
|Trip details|Authorized users|Four-event timeline, expected/actual/variance, reason, timestamp and verification evidence, correction history|
|Trip history|All|Date range, truck, driver, status, pagination, detail navigation; driver remains scoped|
|Performance|Director/Admin|Today/week/month/custom and truck/driver filters, timing min/mean/max, reason/direction bars, trends, prior-period comparison, accountability|
|Reports|Director/Admin|Daily/weekly/monthly/custom, comparison and segment rows, CSV export|
|People & fleet|Director/Admin|Truck state, driver assignments, capacity, route timings|
|Administration|Admin|Users, drivers, trucks, routes, delay reasons; create/edit/deactivate dialogs|
|Alert settings|Admin|Five configurable time thresholds|
|Audit history|Admin|Paginated actions and old/new evidence dialog|

## Setup and scheduling
Create admin → (optional) seed demonstration → sign in → Administration → create DRIVER user → create driver linked to user → create and assign truck → create outbound route → create reverse route → Schedule journey.

## Driver operation
My journey → next action → type truck code → verify assignment → confirm event → automatic server timestamp. Repeat at destination arrival, return departure and origin arrival. On arrival the service calculates segment duration and tolerance status. A delayed segment offers a short reason/remarks dialog. Completing the fourth event closes the trip and releases the truck/driver for scheduling.

If a location permission is declined or unavailable, record without coordinates and explicitly retain that absence. Do not call the record GPS-verified. No arbitrary authoritative time input is exposed to drivers.

## Director flow
Overview → attention-required exception → related trip → inspect segment and event evidence. Performance → select date range → see directional timing and delay reasons. Reports → choose daily/weekly/monthly/custom → download CSV.

## Correction flow
Admin opens trip → Correct time on an existing event → choose time and mandatory reason → service validates chronological consistency → append revision. If driver forgot a punch entirely, Add missing next event → supply reason/time → append admin correction event. Repeat missing predecessors sequentially when necessary. Original timestamps and each correction remain visible. The model disallows an impossible causal order rather than silently rearranging events.

## Company decisions to confirm
- Exact schedules, travel expectations/tolerances for both directions.
- Significant-delay, late-start, missed-punch, dwell and long-open alert thresholds.
- Who schedules trips and which named users receive Admin/Director access.
- Whether typed/scanned truck code is sufficient evidence in V1.
- Whether in-app alerts are sufficient or a named external delivery provider is required.
- Required retention, backup frequency, hosting and access policy before production.
- Whether future native mobile, QR/camera recognition or offline punching is necessary; none is claimed in this phase.
