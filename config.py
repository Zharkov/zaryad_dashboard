import os
import sys
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

_users_raw = os.environ.get("WEB_USERS", "").strip()
USERS: dict[str, str] = {}
if _users_raw:
    for _pair in _users_raw.split(","):
        _pair = _pair.strip()
        if ":" not in _pair:
            continue
        _u, _p = _pair.split(":", 1)
        USERS[_u.strip()] = _p.strip()
else:
    _legacy_user = os.environ.get("WEB_USER", "").strip()
    _legacy_pass = os.environ.get("WEB_PASS", "").strip()
    if _legacy_user and _legacy_pass:
        USERS[_legacy_user] = _legacy_pass

if not USERS:
    print("ERROR: no users configured. Set WEB_USERS=admin:pass1,boss:pass2 in .env",
          file=sys.stderr)
    sys.exit(1)

PORT = int(os.environ.get("WEB_PORT", "9090"))
HOST = os.environ.get("WEB_HOST", "0.0.0.0")
SESSION_TTL_DAYS = 30

TZ = dt.timezone(dt.timedelta(hours=3))
