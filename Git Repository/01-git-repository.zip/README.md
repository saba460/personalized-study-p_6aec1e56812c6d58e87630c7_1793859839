# Personalized Study Planner

A runnable Python capstone application for organizing study subjects, tasks, and
deadlines. Flask serves the web interface and JSON API; SQLite persists each
user's data. No Node build, external API, or database server is required.

## Features

- Register, sign in, sign out, and update your display name.
- Add, rename, and delete your own subjects.
- Create, view, edit, complete, reopen, and delete study tasks.
- Set task priority, due date, notes, status, and estimated study minutes.
- Filter by subject, status, priority, search text, and due date.
- Sort by recommended priority, due date, or newest task.
- View totals, completed tasks, overdue tasks, and remaining study effort.
- Server-side validation, hashed passwords, CSRF protection, and per-user access checks.

## Quick start

Requires Python 3.12 or newer. Open a terminal in the repository root.

**Windows PowerShell** (activation is optional):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r "Functional Web Application\requirements.txt"
Set-Location "Functional Web Application"
..\.venv\Scripts\python.exe -m flask --app run init-db --demo
..\.venv\Scripts\python.exe run.py
```

**macOS / Linux:**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r "Functional Web Application/requirements.txt"
cd "Functional Web Application"
../.venv/bin/python -m flask --app run init-db --demo
../.venv/bin/python run.py
```

Open **http://127.0.0.1:5000**. Use `demo@example.com` / `StudyDemo!2026`, or
create your own account. Omit `--demo` for an empty database. Stop with Ctrl+C.
Data and the local session secret are created in `Functional Web Application/instance/`
and excluded from Git. Initializing again preserves existing records.

## Run the tests

From the repository root after installing requirements:

```powershell
.\.venv\Scripts\python.exe scripts/run_tests.py
```

On macOS/Linux: `.venv/bin/python scripts/run_tests.py`.
The suite uses Python's built-in `unittest`, Flask's test client, and a fresh
temporary SQLite database per test. See [test documentation](Unit%20Tests/README.md).
GitHub Actions is configured to run the same backend tests on pushes and pull requests.
Local results do not imply that the GitHub Actions run has completed.

## Project structure and deliverables

| Deliverable | Source / documentation |
|---|---|
| 1. Git Repository | This repository, [repository guide](Git%20Repository/README.md), and meaningful implementation commits |
| 2. Functional Web Application | [Python app and web interface](Functional%20Web%20Application/) |
| 3. Database Schema & Data | [SQL scripts and ER model](Database%20Schema%20%26%20Data/) |
| 4. API Documentation | [Endpoint reference and examples](API%20Documentation/API.md) |
| 5. Unit Tests | [Backend tests and results](Unit%20Tests/) |

`submissions/` contains ready-to-upload files with numbered names matching these
five deliverables. See [submission mapping](SUBMISSION_GUIDE.md).
Regenerate them with `python scripts/package_deliverables.py` after changing source.

## Prioritization rule

The recommendation is a deterministic rule, not machine learning. Score equals
priority weight plus deadline urgency:

| Component | Points |
|---|---|
| High / medium / low priority | 30 / 20 / 10 |
| Overdue | +50 |
| Due today or tomorrow | +40 |
| Due in 2–3 days | +25 |
| Due in 4–7 days | +10 |
| Due later | +0 |

Completed tasks score zero. Recommended order uses score descending, then due date
ascending, then ID ascending. Dates use the server's local calendar date.
Estimated minutes describe study effort and do not change the score.

## Evaluation walkthrough

1. Initialize with `--demo`, start the server, and sign in to the demo account.
2. Observe three subjects and five tasks in different statuses and priorities.
3. Add a subject and create a task due tomorrow with high priority.
4. Edit its title, notes, due date, and estimated minutes.
5. Filter tasks by that subject, status, priority, search text, and due date.
6. Complete and reopen a task; verify the dashboard and recommendation change.
7. Delete a task and its empty subject. A subject with tasks reports a helpful conflict.
8. Sign out and register a second account. Confirm the demo user's data is absent.
9. Run the tests and inspect the SQL scripts and API examples.

## Scope and deployment

This submission runs locally using Flask's development server, with debug disabled.
It is not a hosted public demo. Before exposing it to the internet, use a production
WSGI server behind HTTPS, set a strong `STUDY_SECRET_KEY`, set `STUDY_HTTPS=1`,
add authentication rate limiting, remove the demo account, and configure backups.
Registration is self-service; there is no administrator, password-reset email,
notification service, or account-deletion feature in this capstone scope.

The original placeholder commits are preserved. Implementation commits describe
the actual work; history is not backdated to simulate project weeks.
