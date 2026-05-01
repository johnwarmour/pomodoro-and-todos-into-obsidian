from datetime import date
from pathlib import Path


TASKS_HEADER = "## Today's Tasks"
POMS_HEADER  = "## Pomodoros"


def _build_tasks_block(todos: list) -> list[str]:
    lines = [TASKS_HEADER]
    if todos:
        for todo in todos:
            check = "x" if todo["completed"] else " "
            lines.append(f"- [{check}] {todo['title']}")
    else:
        lines.append("*(No tasks added today)*")
    return lines


def _build_poms_block(pomodoros: list) -> list[str]:
    completed = [p for p in pomodoros if p["completed"]]
    lines = [f"{POMS_HEADER} ({len(completed)})"]
    if completed:
        lines.append("")
        lines.append("| Time | Duration | Task | Notes |")
        lines.append("|------|----------|------|-------|")
        for p in completed:
            time_str = p["started_at"][11:16]
            task = p["todo_title"] or "—"
            notes = (p["notes"] or "—").replace("\n", " ")
            lines.append(f"| {time_str} | {p['duration_minutes']} min | {task} | {notes} |")
    else:
        lines.append("*(No pomodoros completed today)*")
    return lines


def _replace_section(lines: list[str], new_block: list[str], header_prefix: str) -> list[str]:
    """Replace an existing ## section (identified by header_prefix) with new_block.
    If not found, append it. Preserves all other content."""
    start = None
    for i, line in enumerate(lines):
        if line.strip().startswith(header_prefix):
            start = i
            break

    if start is None:
        # Section doesn't exist yet — append with a blank line separator
        result = list(lines)
        if result and result[-1].strip():
            result.append("")
        result.extend(new_block)
        result.append("")
        return result

    # Find where this section ends (next ## header or EOF)
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    # Strip trailing blank lines inside the old block so we don't accumulate blanks
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1

    return lines[:start] + new_block + [""] + lines[end:]


def sync_to_daily_note(todos: list, pomodoros: list, vault_path: str, daily_notes_folder: str) -> str:
    today = date.today().strftime("%Y-%m-%d")
    folder = Path(vault_path)
    if daily_notes_folder:
        folder = folder / daily_notes_folder
    folder.mkdir(parents=True, exist_ok=True)
    note_path = folder / f"{today}.md"

    if note_path.exists():
        existing = note_path.read_text(encoding="utf-8").splitlines()
    else:
        existing = [f"# {today}", ""]

    lines = _replace_section(existing, _build_tasks_block(todos), TASKS_HEADER)
    lines = _replace_section(lines, _build_poms_block(pomodoros), POMS_HEADER)

    note_path.write_text("\n".join(lines), encoding="utf-8")
    return str(note_path)
