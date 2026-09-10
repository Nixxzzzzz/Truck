# TruckTrack — local desktop application

A Python implementation of the attached Truck Journey & Transport Control System specification. Driver punches, truck-code assignment verification, route-based delay calculations, Director overview/analytics/reports, Admin management and auditable corrections are implemented in separate modules.

**Verification status:** 38 rule/security/request-schema tests passed and Python/JavaScript syntax checks passed. Full FastAPI/SQLAlchemy integration, migrations, live startup and browser layout could not be verified in the build environment because dependency installation and browser localhost access were blocked. Read docs/testing.md before treating this as a verified release. No production-readiness certification is claimed.

## Technology choices
| Component | Choice | Why |
|---|---|---|
|Backend|Python 3.11 or 3.12 + FastAPI|Matches the PDF; structured REST endpoints and generated API schema|
|Validation|Pydantic 2|Bounded fields, timestamps, role/event enums, rejection of unexpected inputs|
|Data|SQLAlchemy 2 + SQLite|Persistent local operation without installing a DB server; PostgreSQL-compatible model design|
|Migrations|Alembic|Versioned initial schema and a clear path for future updates|
|UI|Local HTML, CSS, JavaScript ES modules|Desktop browser application; no Node build, external fonts or CDN required|
|Authentication|scrypt + opaque database sessions|Salted password hashes, revocation, active-role checks and cookie CSRF protection|
|Server|Uvicorn|ASGI server for FastAPI|
|Tests|unittest + pytest/HTTPX|Pure rules and full API workflow coverage|

FastAPI/Uvicorn server guidance: https://fastapi.tiangolo.com/deployment/manually/
SQLite foreign-key behavior: https://docs.sqlalchemy.org/en/20/dialects/sqlite.html

This is a local browser-based application powered by Python, not a native Windows executable. Keep the server terminal open while using it. Your laptop's browser is the Phase 1 interface. Mobile/tablet responsiveness is deferred.

## 1. Extract and open a terminal
Extract TruckTrack-Phase1.zip. Open a terminal **inside the trucktrack directory**, where requirements.txt and alembic.ini are located. Install Python 3.11 or 3.12 from python.org if needed, with Python added to PATH. You need internet for the first package install.

## 2. Windows PowerShell installation
These commands do not require virtual-environment activation, avoiding PowerShell execution-policy problems:
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app.cli init-admin
```
If Python 3.11 is installed instead, use `py -3.11 -m venv .venv` for the first command. Initialization securely prompts for admin username, display name and a password of 12–128 characters. Nothing is sent to an external service.

Optional realistic demonstration data:
```powershell
.\.venv\Scripts\python.exe -m app.cli seed-demo
```
This creates one truck, one driver account, one director account, two routes, ten delay reasons, 35 completed historical trips with a mixture of on-time and delayed segments, and one scheduled trip. It prints generated passwords for `demo.driver` and `demo.director` once. Save them securely. Truck verification code: **TT-001**. Synthetic events are explicitly marked DEMO_SEED. Running seed-demo again does not duplicate the trips.

Run locally:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open **http://127.0.0.1:8000**. Sign in using the admin account you created, or a generated demo account. Stop the server with Ctrl+C.

Run all tests in a second terminal:
```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## 3. macOS / Linux installation
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python -m alembic upgrade head
python -m app.cli init-admin
python -m app.cli seed-demo
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Run tests in a second terminal with the environment active:
```bash
python -m pytest -q
```
Demo seeding is optional; omit it when entering company data. If your Linux installation lacks venv support, install the OS package for your Python version's venv module first.

## 4. Everyday use
- **Admin:** create a DRIVER user → linked driver → assigned truck → outbound and reverse routes → Schedule journey. Configure timings and meaningful alert thresholds.
- **Driver:** My journey → next action → enter assigned truck code → verify → confirm punch. Repeat until return arrival. Enter delay reason if a segment exceeds tolerance.
- **Director:** Overview → linked exceptions → trip timeline/evidence. Performance and Reports support date/driver/truck filters and CSV export.
- **Admin corrections:** open a trip, choose Correct time (or Add missing next event), supply timestamp and a reason. Originals remain in the timeline; revisions and audit record explain the change.
- **Users and passwords:** Admin edits a user in Administration. Leave password blank to preserve it; supply a new 12–128-character password to reset it. Password or role changes revoke that user's sessions.
- **Delete:** deactivation only. Historical records are retained. Complete/cancel open trips before editing their assigned resources.

Default route seed: Noida HQ → Delhi 60 min +10 tolerance; Delhi → Noida HQ 70 min +10 tolerance. These are demonstration settings, not confirmed company expectations.

## 5. Configuration
Copy .env.example once, then edit .env locally. Do not overwrite an existing .env when upgrading.
- DATABASE_URL: default SQLite file; relative to the terminal's current directory. Always run commands from this project root.
- APP_TIMEZONE: display and trip-date timezone; default Asia/Kolkata. Stored timestamps are UTC.
- SESSION_HOURS: 1–168, default 12.
- COOKIE_SECURE: false only for local HTTP. Set true when using HTTPS in a deployed environment.
- ALLOWED_HOSTS: comma-separated hostnames accepted by the server.
- Optional ADMIN_USERNAME, ADMIN_NAME, ADMIN_PASSWORD support noninteractive initial setup. Prefer the interactive hidden password prompt; remove a setup password from .env after use.

No signing secret is necessary: sessions use cryptographically random tokens whose hashes are stored in the database. Do not add an unused SECRET_KEY merely as a placeholder.

## 6. Database and migrations
SQLite setup is the Alembic command above. Database file: trucktrack.db. Tables and ERD: docs/database.md. Do not manually create tables or copy individual SQLite tables.
```bash
python -m alembic current
python -m alembic upgrade head
```
Future development migration workflow (after changing models):
```bash
python -m alembic revision --autogenerate -m "describe schema change"
python -m alembic upgrade head
```
Review generated migrations before applying them. The initial migration is frozen; changing application models will not rewrite it.

Optional PostgreSQL: create an empty database with your PostgreSQL administration tools, set DATABASE_URL to `postgresql+psycopg://USER:PASSWORD@localhost:5432/trucktrack` using your actual local credentials, then run the same migration/init commands. URL-encode special password characters. Switching this URL does not migrate existing SQLite data. PostgreSQL deployment is not required for Phase 1 and has not been executed in the build environment.

## 7. API and documentation
- Operational UI: http://127.0.0.1:8000
- Health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs
- Machine-readable schema: http://127.0.0.1:8000/openapi.json

Read in this order:
1. docs/requirements.md — all specification sections mapped, scope and assumptions.
2. docs/architecture.md — stack, responsibilities, data/auth flow and staged plan.
3. docs/database.md — schema, ERD, constraints and backup notes.
4. docs/api.md — endpoints, payloads and permission rules.
5. docs/user-flows.md — screens and user workflows.
6. docs/testing.md — executed results, blocked checks, full acceptance walkthrough.

## 8. Troubleshooting
| Symptom | Fix |
|---|---|
|`py` or `python` not found|Install Python 3.11/3.12 and reopen the terminal; on Windows use the Python launcher `py`.|
|`No module named fastapi/sqlalchemy/alembic`|Install requirements using the same `.venv` Python used to run the app.|
|Package install fails / proxy / certificate error|Use your organization's approved package index/network configuration. Do not disable TLS verification. Initial package download requires internet.|
|`Depends() got an unexpected keyword argument 'scope'`|FastAPI must be >=0.121; reinstall using this requirements.txt in the selected virtual environment.|
|`no such table` or database unavailable|Run `python -m alembic upgrade head` from the project root, then init-admin. Confirm DATABASE_URL.|
|Cannot open database|Use a writable extracted project folder. Do not run directly inside a ZIP or read-only folder.|
|Port 8000 in use|Use `--port 8001`, then open http://127.0.0.1:8001.|
|Invalid host header|Use 127.0.0.1/localhost, or add the intended hostname to ALLOWED_HOSTS and restart.|
|Sign-in succeeds but next request is unauthenticated|For localhost HTTP, COOKIE_SECURE must be false. Use the same host throughout, not alternating localhost and 127.0.0.1.|
|CSRF error|Refresh or sign in again; the browser restores the session-bound token via /auth/me.|
|Lost generated demo password|Sign in as Admin and reset that user in Administration → Users.|
|Cannot edit truck/driver/route|An open trip references it. Complete it, or cancel it if unstarted.|
|Cannot create a trip|Check active driver user, active assigned truck, matching reverse routes and no existing open trip for either resource.|
|Invalid punch sequence|Record the displayed next action. Admin can add a genuinely missing predecessor with a reason.|
|No delay-reason button|The segment must exceed expected duration plus tolerance. A positive variance alone is not delayed status.|
|No historical data|Run seed-demo or select a range that includes real journeys; analytics use completed segments.|
|Device location unavailable|Optional location needs browser permission and a supported secure context. Punches still work without it.|
|Wrong time displayed|Check APP_TIMEZONE and computer clock. Admin datetime input uses the computer timezone, explicitly labeled; display uses APP_TIMEZONE.|
|ZoneInfo timezone error on Windows|Ensure tzdata from requirements.txt is installed.|
|Browser cannot load `/docs` offline|Swagger documentation assets can require internet; the main application does not. Use docs/api.md and /openapi.json offline.|

## 9. Practical limits and next phase
Truck-code identification verifies assignment, not camera recognition, location or physical truck presence. In-app alerts recalculate every 30 seconds while an operations screen is open; the app does not send email/SMS/push. Route timings are snapshotted, normal event timestamps are server-generated, and optional client evidence is explicitly untrusted.

Before real production deployment, validate the full test suite and actual desktop workflow, define company timing/evidence policies, and configure TLS, database permissions, backup/restore and monitoring for that environment. Dependency versions are bounded, not an executed lockfile; freeze the successfully tested laptop environment with `python -m pip freeze > requirements.lock.txt` for repeatable deployment.

Phase 2 is mobile/tablet responsiveness. Live GPS, camera recognition, route deviation, maintenance, fuel and vehicle documents remain future modules per the PDF and are not presented as V1 features.
