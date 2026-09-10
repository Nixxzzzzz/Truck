# Complete project structure

```text
trucktrack/
├── app/
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── catalog.py
│   │   ├── dashboard.py
│   │   ├── dependencies.py
│   │   ├── reports.py
│   │   └── trips.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── entities.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── records.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── requests.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── audit.py
│   │   ├── catalog.py
│   │   ├── time_engine.py
│   │   └── trips.py
│   ├── static/
│   │   ├── admin.js
│   │   ├── api.js
│   │   ├── app.js
│   │   ├── icon.svg
│   │   ├── styles.css
│   │   └── ui.js
│   ├── templates/
│   │   └── index.html
│   ├── __init__.py
│   ├── cli.py
│   └── main.py
├── docs/
│   ├── api.md
│   ├── architecture.md
│   ├── database.md
│   ├── project-structure.md
│   ├── requirements.md
│   ├── source-specification.pdf
│   ├── testing.md
│   └── user-flows.md
├── migrations/
│   ├── versions/
│   │   └── 0001_initial.py
│   ├── env.py
│   └── script.py.mako
├── scripts/
│   └── verify_project.py
├── tests/
│   ├── __init__.py
│   ├── test_api.py
│   ├── test_rules.py
│   └── test_schemas.py
├── .env.example
├── .gitignore
├── README.md
├── alembic.ini
├── pyproject.toml
└── requirements.txt
```

No generated database, real credentials, virtual environment or temporary visual fixtures are bundled.
