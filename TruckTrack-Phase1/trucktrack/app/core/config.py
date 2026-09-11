"""Environment configuration. No application secret is needed for opaque DB sessions."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./trucktrack.db')
TIMEZONE = os.getenv('APP_TIMEZONE', 'Asia/Kolkata')
ZoneInfo(TIMEZONE)
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
SESSION_HOURS = int(os.getenv('SESSION_HOURS', '12'))
if not 1 <= SESSION_HOURS <= 168:
    raise ValueError('SESSION_HOURS must be 1–168')
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,testserver,*.onrender.com').split(',') if host.strip()]
render_hostname = os.getenv('RENDER_EXTERNAL_HOSTNAME')
if render_hostname and render_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_hostname)
if '*.onrender.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*.onrender.com')
if 'truck-x98i.onrender.com' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('truck-x98i.onrender.com')
