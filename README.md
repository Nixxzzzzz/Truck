# Truck

Truck is a FastAPI-based transport operations project for driver punches, truck-code assignment verification, route delay tracking, director reporting, admin management, and auditable corrections.

This repository contains the application in [TruckTrack-Phase1/trucktrack](TruckTrack-Phase1/trucktrack). The app is container-ready, includes CI, and has deployment guidance for Render and Oracle Cloud Always Free.

For Render, use the repository-root [Dockerfile](Dockerfile) and [render.yaml](render.yaml).

## What’s inside

- FastAPI backend with SQLite by default
- Dockerfile and startup script
- GitHub Actions CI
- Render deployment blueprint and guide
- Oracle Cloud fallback guide

## Run locally

Open the app folder first:

```powershell
cd TruckTrack-Phase1/trucktrack
```

Then create a virtual environment, install dependencies, run migrations, and start the server:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m app.cli init-admin
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Deployment

Primary cloud path: Render.

- Read [TruckTrack-Phase1/trucktrack/docs/render-deployment.md](TruckTrack-Phase1/trucktrack/docs/render-deployment.md)
- Use [TruckTrack-Phase1/trucktrack/render.yaml](TruckTrack-Phase1/trucktrack/render.yaml)

Fallback path: Oracle Cloud Always Free.

- Read [TruckTrack-Phase1/trucktrack/docs/oracle-deployment.md](TruckTrack-Phase1/trucktrack/docs/oracle-deployment.md)

## Notes

- The root README is the one GitHub displays on the repository homepage.
- The actual application code lives in the nested `TruckTrack-Phase1/trucktrack` directory.