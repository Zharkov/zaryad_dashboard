import os
import datetime as dt
from pathlib import Path


def _load_dotenv():
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv()

DB_PATH = os.environ.get("WORKTIME_DB", str(Path(__file__).parent / "worktime.db"))

PORT = int(os.environ.get("WEB_PORT", "9090"))
HOST = os.environ.get("WEB_HOST", "0.0.0.0")
SESSION_TTL_DAYS = 30

TZ = dt.timezone(dt.timedelta(hours=3))
