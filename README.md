# Focus

Pomodoro timer + todo list with Obsidian daily note sync.

## Features

- **Today / Backlog** todo lists — move tasks between lists, mark complete
- **Pomodoro timer** — 25/5 by default, configurable; SVG ring countdown
- **Auto-break** — optionally auto-start break after work session; skip break button
- **Stop midstream** — stopping a pomodoro earns no credit
- **Notes on completion** — log what you worked on after each session
- **Obsidian sync** — writes today's tasks + pomodoro log to your daily note

## Setup

```bash
pip install fastapi "uvicorn[standard]" python-dotenv pydantic
```

Copy `.env.example` to `.env`:

```
OBSIDIAN_VAULT_PATH=/Your/Vault/Path
OBSIDIAN_DAILY_NOTES_FOLDER=Daily
```

## Usage

```bash
python main.py
```

Open [http://localhost:8000](http://localhost:8000).

## Obsidian Daily Note Format

```markdown
# 2026-04-26

##  Today's Tasks
- [x] Write unit tests
- [ ] Review PRs

## Pomodoros (3)

| Time | Duration | Task | Notes |
|------|----------|------|-------|
| 09:15 | 25 min | Write unit tests | Finished auth module |
```
