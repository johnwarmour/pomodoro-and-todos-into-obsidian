from datetime import date
from pathlib import Path


def sync_to_daily_note(todos: list, pomodoros: list, vault_path: str, daily_notes_folder: str) -> str:
    today = date.today().strftime("%Y-%m-%d")
    folder = Path(vault_path)
    if daily_notes_folder:
        folder = folder / daily_notes_folder
    folder.mkdir(parents=True, exist_ok=True)
    note_path = folder / f"{today}.md"

    lines = [f"# {today}", ""]

    lines.append("## Today's Tasks")
    if todos:
        for todo in todos:
            check = "x" if todo["completed"] else " "
            lines.append(f"- [{check}] {todo['title']}")
    else:
        lines.append("*(No tasks added today)*")
    lines.append("")

    completed_poms = [p for p in pomodoros if p["completed"]]
    lines.append(f"## Pomodoros ({len(completed_poms)})")
    if completed_poms:
        lines.append("")
        lines.append("| Time | Duration | Task | Notes |")
        lines.append("|------|----------|------|-------|")
        for p in completed_poms:
            time_str = p["started_at"][11:16]
            task = p["todo_title"] or "—"
            notes = (p["notes"] or "—").replace("\n", " ")
            lines.append(f"| {time_str} | {p['duration_minutes']} min | {task} | {notes} |")
    else:
        lines.append("*(No pomodoros completed today)*")
    lines.append("")

    note_path.write_text("\n".join(lines), encoding="utf-8")
    return str(note_path)
