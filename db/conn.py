import sqlite3
from config import DB_PATH


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
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
            shift_type TEXT NOT NULL DEFAULT 'day',
            arrived_at TEXT NOT NULL,
            left_at TEXT,
            auto_closed INTEGER NOT NULL DEFAULT 0,
            UNIQUE(worker_id, date, shift_type)
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
        CREATE TABLE IF NOT EXISTS object_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            object_id INTEGER NOT NULL REFERENCES objects(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_object_comments_object ON object_comments(object_id);
        CREATE TABLE IF NOT EXISTS login_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            role TEXT NOT NULL,
            worker_id INTEGER,
            login_at TEXT NOT NULL,
            logout_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_login_log_login_at ON login_log(login_at);
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            kind TEXT NOT NULL DEFAULT 'skill',
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS worker_skills (
            worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            skill_id INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            note TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (worker_id, skill_id)
        );
        CREATE INDEX IF NOT EXISTS idx_wskill_worker ON worker_skills(worker_id);
        CREATE TABLE IF NOT EXISTS worker_compat (
            from_worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            to_worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            score INTEGER NOT NULL CHECK (score BETWEEN -2 AND 2),
            note TEXT,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (from_worker_id, to_worker_id),
            CHECK (from_worker_id <> to_worker_id)
        );
        CREATE INDEX IF NOT EXISTS idx_compat_to ON worker_compat(to_worker_id);
        CREATE TABLE IF NOT EXISTS crews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            note TEXT,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS crew_workers (
            crew_id INTEGER NOT NULL REFERENCES crews(id) ON DELETE CASCADE,
            worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            added_at TEXT NOT NULL,
            PRIMARY KEY (crew_id, worker_id)
        );
        CREATE INDEX IF NOT EXISTS idx_crewwork_worker ON crew_workers(worker_id);
        CREATE TABLE IF NOT EXISTS fines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            date TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'fine',
            title TEXT NOT NULL,
            description TEXT,
            amount REAL NOT NULL,
            created_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_fines_worker ON fines(worker_id);
        CREATE INDEX IF NOT EXISTS idx_fines_date ON fines(date);
        CREATE TABLE IF NOT EXISTS fine_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fine_id INTEGER NOT NULL REFERENCES fines(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            deleted_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_fine_comments_fine ON fine_comments(fine_id);
        CREATE TABLE IF NOT EXISTS time_presets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_type TEXT NOT NULL DEFAULT 'day',
            time TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(shift_type, time)
        );
        """)
    # Incremental column migrations
    try:
        with db_conn() as c:
            c.execute("ALTER TABLE admin_users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'")
    except Exception:
        pass

    try:
        with db_conn() as c:
            c.execute("ALTER TABLE skills ADD COLUMN kind TEXT NOT NULL DEFAULT 'skill'")
    except Exception:
        pass

    # fines: 'fine' (штраф) / 'bonus' (премия) в одной таблице
    try:
        with db_conn() as c:
            c.execute("ALTER TABLE fines ADD COLUMN kind TEXT NOT NULL DEFAULT 'fine'")
    except Exception:
        pass

    # shifts: add shift_type + widen UNIQUE(worker_id, date) -> (worker_id, date, shift_type)
    # SQLite can't ALTER a UNIQUE constraint in place, so rebuild the table.
    with db_conn() as c:
        cols = [r["name"] for r in c.execute("PRAGMA table_info(shifts)")]
        if "shift_type" not in cols:
            c.execute("PRAGMA foreign_keys = OFF")
            c.executescript("""
            CREATE TABLE shifts_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
                date TEXT NOT NULL,
                shift_type TEXT NOT NULL DEFAULT 'day',
                arrived_at TEXT NOT NULL,
                left_at TEXT,
                auto_closed INTEGER NOT NULL DEFAULT 0,
                UNIQUE(worker_id, date, shift_type)
            );
            INSERT INTO shifts_new (id, worker_id, date, shift_type, arrived_at, left_at, auto_closed)
                SELECT id, worker_id, date, 'day', arrived_at, left_at, auto_closed FROM shifts;
            DROP TABLE shifts;
            ALTER TABLE shifts_new RENAME TO shifts;
            CREATE INDEX IF NOT EXISTS idx_shifts_date ON shifts(date);
            CREATE INDEX IF NOT EXISTS idx_shifts_worker ON shifts(worker_id);
            """)

    with db_conn() as c:
        count = c.execute("SELECT COUNT(*) FROM time_presets").fetchone()[0]
        if count == 0:
            import datetime as _dt
            ts = _dt.datetime.now().isoformat()
            c.executemany(
                "INSERT INTO time_presets (shift_type, time, created_at) VALUES (?, ?, ?)",
                [
                    ("day", "09:00", ts), ("day", "17:00", ts),
                    ("night", "22:00", ts), ("night", "06:00", ts),
                ],
            )
