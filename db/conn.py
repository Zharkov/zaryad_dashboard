import sqlite3
from config import DB_PATH


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def db_migrate():
    with db_conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS workers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            default_start TEXT,
            default_end TEXT,
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            arrived_at TEXT NOT NULL,
            left_at TEXT,
            auto_closed INTEGER NOT NULL DEFAULT 0,
            UNIQUE(worker_id, date)
        );
        CREATE INDEX IF NOT EXISTS idx_shifts_date ON shifts(date);
        CREATE INDEX IF NOT EXISTS idx_shifts_worker ON shifts(worker_id);
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            action TEXT NOT NULL,
            shift_id INTEGER,
            details TEXT
        );
        CREATE TABLE IF NOT EXISTS objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS worker_objects (
            worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
            attached_at TEXT NOT NULL,
            PRIMARY KEY (worker_id, object_id)
        );
        CREATE INDEX IF NOT EXISTS idx_wobj_worker ON worker_objects(worker_id);
        CREATE INDEX IF NOT EXISTS idx_wobj_object ON worker_objects(object_id);
        CREATE TABLE IF NOT EXISTS worker_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_comments_worker ON worker_comments(worker_id);
        CREATE TABLE IF NOT EXISTS worker_credentials (
            worker_id INTEGER PRIMARY KEY REFERENCES workers(id) ON DELETE CASCADE,
            password_plain TEXT NOT NULL,
            blocked INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS shift_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_shift_comments_shift ON shift_comments(shift_id);
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_plain TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)
