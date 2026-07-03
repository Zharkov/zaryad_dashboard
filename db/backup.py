import datetime as dt
import sqlite3
import time
from pathlib import Path

from config import DB_PATH

BACKUP_DIR = Path(__file__).parent.parent / "backups"
BACKUP_INTERVAL_DAYS = 3
BACKUP_RETENTION_DAYS = 12
CHECK_INTERVAL_SECONDS = 3600


def _backup_filename() -> str:
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"worktime_{ts}.db"


def make_backup() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dest_path = BACKUP_DIR / _backup_filename()
    src = sqlite3.connect(DB_PATH)
    try:
        dest = sqlite3.connect(dest_path)
        try:
            src.backup(dest)
        finally:
            dest.close()
    finally:
        src.close()
    return dest_path


def cleanup_old_backups(retention_days: int = BACKUP_RETENTION_DAYS) -> None:
    if not BACKUP_DIR.exists():
        return
    cutoff = time.time() - retention_days * 86400
    for f in BACKUP_DIR.glob("worktime_*.db"):
        if f.stat().st_mtime < cutoff:
            f.unlink(missing_ok=True)


def _last_backup_time() -> float | None:
    if not BACKUP_DIR.exists():
        return None
    files = list(BACKUP_DIR.glob("worktime_*.db"))
    if not files:
        return None
    return max(f.stat().st_mtime for f in files)


def backup_loop():
    while True:
        try:
            last = _last_backup_time()
            due = last is None or (time.time() - last) >= BACKUP_INTERVAL_DAYS * 86400
            if due:
                make_backup()
            cleanup_old_backups()
        except Exception:
            pass
        time.sleep(CHECK_INTERVAL_SECONDS)
