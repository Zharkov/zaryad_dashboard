#!/usr/bin/env python3
import threading
from http.server import ThreadingHTTPServer

from config import HOST, PORT
from db.conn import db_migrate
from sessions import cleanup_sessions_loop
from handler import Handler


def main():
    db_migrate()
    t = threading.Thread(target=cleanup_sessions_loop, daemon=True)
    t.start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    display_host = "localhost" if HOST in ("0.0.0.0", "") else HOST
    print(f"ЗАРЯД запущен · http://{display_host}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nОстановлен.")


if __name__ == "__main__":
    main()
