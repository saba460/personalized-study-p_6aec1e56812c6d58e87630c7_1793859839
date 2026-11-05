# Running the web application

Use the quick-start commands in the repository root README. Python 3.12+ is required.

If you already have an activated Python environment, run from this directory:

```sh
python -m pip install -r requirements.txt
python -m flask --app run init-db --demo
python run.py
```

Open http://127.0.0.1:5000 and sign in with
`demo@example.com` / `StudyDemo!2026`, or register a new account.
The server binds only to your local machine and debug is disabled.

The application factory is `study_planner.create_app`. `run.py` exports its WSGI
application as `app`. `study_planner/templates` contains the page;
`study_planner/static` contains the stylesheet and JavaScript. There is no frontend
build step. SQL scripts live in the repository's `Database Schema & Data` folder.

The instance database is initialized explicitly, persists across restarts, and is
excluded from source control. The demo initializer preserves existing data.
If port 5000 is occupied, run `python -m flask --app run run --port 5001` instead.
