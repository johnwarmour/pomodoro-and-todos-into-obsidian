import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras


@contextmanager
def get_conn():
    conn = psycopg2.connect(
        os.environ["DATABASE_URL"],
        cursor_factory=psycopg2.extras.RealDictCursor,
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(vault_path: str = "", daily_notes_folder: str = "Daily"):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id          SERIAL PRIMARY KEY,
                    title       TEXT NOT NULL,
                    list        TEXT NOT NULL DEFAULT 'backlog',
                    completed   INTEGER NOT NULL DEFAULT 0,
                    created_at  TEXT NOT NULL,
                    completed_at TEXT,
                    position    INTEGER NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS pomodoros (
                    id               SERIAL PRIMARY KEY,
                    started_at       TEXT NOT NULL,
                    completed_at     TEXT,
                    duration_minutes INTEGER NOT NULL DEFAULT 25,
                    todo_id          INTEGER,
                    todo_title       TEXT,
                    notes            TEXT,
                    completed        INTEGER NOT NULL DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            defaults = {
                "work_duration": "25",
                "break_duration": "5",
                "auto_break": "true",
                "obsidian_vault_path": vault_path,
                "obsidian_daily_notes_folder": daily_notes_folder,
            }
            for k, v in defaults.items():
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s) "
                    "ON CONFLICT (key) DO NOTHING",
                    (k, v),
                )
