#!/usr/bin/env python3
import logging
import sys
import threading
from http.server import ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import HOST, PORT
from db.conn import db_migrate
from db.admin_users import get_admin_count
from db.backup import backup_loop
from sessions import cleanup_sessions_loop
from handler import Handler


def _setup_access_log():
    log_dir = Path(__file__).parent / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "access.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger = logging.getLogger("zaryad.access")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)


def main():
    _setup_access_log()
    db_migrate()

    if get_admin_count() == 0:
        print(
            "ERROR: нет администраторов в БД. "
            "Добавь через: python manage_admins.py add <логин> <пароль>",
            file=sys.stderr,
        )
        sys.exit(1)

    t = threading.Thread(target=cleanup_sessions_loop, daemon=True)
    t.start()
    threading.Thread(target=backup_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    display_host = "localhost" if HOST in ("0.0.0.0", "") else HOST
    print(f"ЗАРЯД запущен · http://{display_host}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлен.")


if __name__ == "__main__":
    main()
