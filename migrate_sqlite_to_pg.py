"""One-time migration: copies todos, pomodoros, and settings from productivity.db into Postgres."""
import os
import sqlite3
from pathlib import Path

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

SQLITE_PATH = Path("productivity.db")

if not SQLITE_PATH.exists():
    print("productivity.db not found — nothing to migrate.")
    exit(0)

sqlite_conn = sqlite3.connect(SQLITE_PATH)
sqlite_conn.row_factory = sqlite3.Row

todos     = sqlite_conn.execute("SELECT * FROM todos ORDER BY id").fetchall()
pomodoros = sqlite_conn.execute("SELECT * FROM pomodoros ORDER BY id").fetchall()
settings  = sqlite_conn.execute("SELECT * FROM settings").fetchall()
sqlite_conn.close()

pg_conn = psycopg2.connect(os.environ["DATABASE_URL"], cursor_factory=psycopg2.extras.RealDictCursor)

with pg_conn:
    with pg_conn.cursor() as cur:
        for row in todos:
            cur.execute("""
                INSERT INTO todos (id, title, list, completed, created_at, completed_at, position)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    title        = EXCLUDED.title,
                    list         = EXCLUDED.list,
                    completed    = EXCLUDED.completed,
                    created_at   = EXCLUDED.created_at,
                    completed_at = EXCLUDED.completed_at,
                    position     = EXCLUDED.position
            """, (row["id"], row["title"], row["list"], row["completed"],
                  row["created_at"], row["completed_at"], row["position"]))

        for row in pomodoros:
            cur.execute("""
                INSERT INTO pomodoros (id, started_at, completed_at, duration_minutes, todo_id, todo_title, notes, completed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    started_at       = EXCLUDED.started_at,
                    completed_at     = EXCLUDED.completed_at,
                    duration_minutes = EXCLUDED.duration_minutes,
                    todo_id          = EXCLUDED.todo_id,
                    todo_title       = EXCLUDED.todo_title,
                    notes            = EXCLUDED.notes,
                    completed        = EXCLUDED.completed
            """, (row["id"], row["started_at"], row["completed_at"], row["duration_minutes"],
                  row["todo_id"], row["todo_title"], row["notes"], row["completed"]))

        for row in settings:
            cur.execute("""
                INSERT INTO settings (key, value) VALUES (%s, %s)
                ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """, (row["key"], row["value"]))

        # Re-sync SERIAL sequences so new inserts don't conflict with migrated IDs
        cur.execute("SELECT setval('todos_id_seq', (SELECT MAX(id) FROM todos))")
        cur.execute("SELECT setval('pomodoros_id_seq', (SELECT MAX(id) FROM pomodoros))")

print(f"Migrated {len(todos)} todo(s), {len(pomodoros)} pomodoro(s), {len(settings)} setting(s).")
pg_conn.close()
