import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path("productivity.db")


def init_db(vault_path: str = "", daily_notes_folder: str = "Daily"):
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                list TEXT NOT NULL DEFAULT 'backlog',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                completed_at TEXT,
                position INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS pomodoros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                duration_minutes INTEGER NOT NULL DEFAULT 25,
                todo_id INTEGER,
                todo_title TEXT,
                notes TEXT,
                completed INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        defaults = {
            "work_duration": "25",
            "break_duration": "5",
            "auto_break": "true",
            "obsidian_vault_path": vault_path,
            "obsidian_daily_notes_folder": daily_notes_folder,
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
