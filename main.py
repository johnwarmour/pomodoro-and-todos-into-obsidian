import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from db import get_conn, init_db
from obsidian import sync_to_daily_note

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(
        vault_path=os.getenv("OBSIDIAN_VAULT_PATH", ""),
        daily_notes_folder=os.getenv("OBSIDIAN_DAILY_NOTES_FOLDER", "Daily"),
    )
    yield


app = FastAPI(title="Focus", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def root():
    return FileResponse("frontend/index.html")


# ── Todos ──────────────────────────────────────────────────────────────────────

class TodoCreate(BaseModel):
    title: str
    list: str = "backlog"


class TodoUpdate(BaseModel):
    title: Optional[str] = None
    list: Optional[str] = None
    completed: Optional[bool] = None
    position: Optional[int] = None


@app.get("/api/todos")
def get_todos():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM todos ORDER BY list, position, id").fetchall()
        return [dict(r) for r in rows]


@app.post("/api/todos")
def create_todo(todo: TodoCreate):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO todos (title, list, created_at) VALUES (?, ?, ?)",
            (todo.title, todo.list, now),
        )
        return {"id": cur.lastrowid, "title": todo.title, "list": todo.list,
                "completed": 0, "created_at": now, "completed_at": None, "position": 0}


@app.put("/api/todos/{todo_id}")
def update_todo(todo_id: int, todo: TodoUpdate):
    with get_conn() as conn:
        if not conn.execute("SELECT 1 FROM todos WHERE id = ?", (todo_id,)).fetchone():
            raise HTTPException(404, "Todo not found")
        updates: dict = {}
        if todo.title is not None:
            updates["title"] = todo.title
        if todo.list is not None:
            updates["list"] = todo.list
        if todo.completed is not None:
            updates["completed"] = 1 if todo.completed else 0
            updates["completed_at"] = datetime.now().isoformat() if todo.completed else None
        if todo.position is not None:
            updates["position"] = todo.position
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE todos SET {set_clause} WHERE id = ?",
                [*updates.values(), todo_id],
            )
        return dict(conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone())


@app.delete("/api/todos/{todo_id}")
def delete_todo(todo_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    return {"ok": True}


# ── Pomodoros ──────────────────────────────────────────────────────────────────

class PomodoroStart(BaseModel):
    todo_id: Optional[int] = None
    todo_title: Optional[str] = None
    duration_minutes: int = 25


class PomodoroComplete(BaseModel):
    notes: Optional[str] = None


@app.get("/api/pomodoros/today")
def get_today_pomodoros():
    today = date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM pomodoros WHERE DATE(started_at) = ? ORDER BY started_at",
            (today,),
        ).fetchall()
        return [dict(r) for r in rows]


@app.get("/api/pomodoros/active")
def get_active_pomodoro():
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM pomodoros WHERE completed_at IS NULL ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        return dict(row) if row else None


@app.post("/api/pomodoros/start")
def start_pomodoro(pom: PomodoroStart):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        # Abandon any lingering active pomodoro
        conn.execute(
            "UPDATE pomodoros SET completed = 0, completed_at = ? WHERE completed_at IS NULL",
            (now,),
        )
        cur = conn.execute(
            "INSERT INTO pomodoros (started_at, duration_minutes, todo_id, todo_title, completed) "
            "VALUES (?, ?, ?, ?, 0)",
            (now, pom.duration_minutes, pom.todo_id, pom.todo_title),
        )
        return dict(conn.execute("SELECT * FROM pomodoros WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.put("/api/pomodoros/{pom_id}/complete")
def complete_pomodoro(pom_id: int, data: PomodoroComplete):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE pomodoros SET completed = 1, completed_at = ?, notes = ? WHERE id = ?",
            (now, data.notes, pom_id),
        )
        return dict(conn.execute("SELECT * FROM pomodoros WHERE id = ?", (pom_id,)).fetchone())


@app.put("/api/pomodoros/{pom_id}/abandon")
def abandon_pomodoro(pom_id: int):
    now = datetime.now().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE pomodoros SET completed = 0, completed_at = ? WHERE id = ?",
            (now, pom_id),
        )
    return {"ok": True}


# ── Settings ───────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def get_settings():
    with get_conn() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


@app.put("/api/settings")
def update_settings(settings: dict):
    with get_conn() as conn:
        for k, v in settings.items():
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (k, str(v)),
            )
    return {"ok": True}


# ── Obsidian ───────────────────────────────────────────────────────────────────

@app.post("/api/obsidian/sync")
def obsidian_sync():
    with get_conn() as conn:
        settings = {r["key"]: r["value"] for r in
                    conn.execute("SELECT key, value FROM settings").fetchall()}
        vault_path = settings.get("obsidian_vault_path", "")
        folder = settings.get("obsidian_daily_notes_folder", "Daily")
        if not vault_path:
            raise HTTPException(400, "Obsidian vault path not set. Open Settings to configure it.")
        today = date.today().isoformat()
        todos = [dict(r) for r in conn.execute(
            "SELECT * FROM todos WHERE list = 'today' ORDER BY position, id"
        ).fetchall()]
        pomodoros = [dict(r) for r in conn.execute(
            "SELECT * FROM pomodoros WHERE DATE(started_at) = ? ORDER BY started_at", (today,)
        ).fetchall()]
    try:
        path = sync_to_daily_note(todos, pomodoros, vault_path, folder)
        return {"ok": True, "path": path}
    except Exception as e:
        raise HTTPException(500, f"Sync failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
