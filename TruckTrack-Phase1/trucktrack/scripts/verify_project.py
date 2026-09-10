"""Dependency-light source verification; run from the project root."""
from pathlib import Path
import ast
import json
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
files=list(root.rglob('*.py'))
files=[p for p in files if '.venv' not in p.parts and '__pycache__' not in p.parts]
for path in files:
    ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
print(f'Python syntax valid: {len(files)} files')
result=subprocess.run([sys.executable,'-m','unittest','tests.test_rules','tests.test_schemas','-v'],cwd=root)
raise SystemExit(result.returncode)
