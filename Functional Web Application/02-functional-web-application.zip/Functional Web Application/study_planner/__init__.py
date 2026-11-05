"""Personalized Study Planner: application factory and JSON API."""
import hmac
import os
import re
import secrets
import sqlite3
from datetime import date
from functools import wraps
from pathlib import Path

import click
from flask import Flask, g, jsonify, render_template, request, session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

STATUSES = ("pending", "in_progress", "completed")
PRIORITIES = ("low", "medium", "high")


def get_db():
    if "db" not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def priority_score(task, today=None):
    """Explainable priority: importance + deadline urgency, completed tasks last."""
    if task["status"] == "completed":
        return 0
    days = (date.fromisoformat(task["due_date"]) - (today or date.today())).days
    urgency = 50 if days < 0 else 40 if days <= 1 else 25 if days <= 3 else 10 if days <= 7 else 0
    return {"low": 10, "medium": 20, "high": 30}[task["priority"]] + urgency


def fail(message, status=400):
    return jsonify(error=message), status


def authenticated(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return fail("Sign in to continue.", 401)
        return fn(*args, **kwargs)
    return wrapped


def body(allowed):
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError("Provide a JSON object.")
    if set(data) - set(allowed):
        raise ValueError("Unknown fields: " + ", ".join(sorted(set(data) - set(allowed))))
    return data


def text_field(data, key, maximum):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise ValueError(f"{key} must contain 1 to {maximum} characters.")
    return value.strip()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret = os.environ.get("STUDY_SECRET_KEY")
    if not secret:
        secret_file = Path(app.instance_path) / "secret.key"
        try:
            secret_file.write_text(secrets.token_hex(32), encoding="utf-8") if not secret_file.exists() else None
            secret = secret_file.read_text(encoding="utf-8")
        except OSError:
            secret = secrets.token_hex(32)
    app.config.from_mapping(
        SECRET_KEY=secret,
        DATABASE=str(Path(app.instance_path) / "study.sqlite3"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("STUDY_HTTPS") == "1",
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if test_config:
        app.config.update(test_config)

    @app.teardown_appcontext
    def close_db(_error):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.before_request
    def protect_mutations():
        if request.path.startswith("/api/") and request.method in ("POST", "PATCH", "DELETE"):
            expected = session.get("csrf_token", "")
            supplied = request.headers.get("X-CSRF-Token", "")
            if not expected or not hmac.compare_digest(expected.encode(), supplied.encode()):
                return fail("Invalid CSRF token. Refresh your session.", 403)

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; base-uri 'self'; frame-ancestors 'none'"
        if request.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.errorhandler(ValueError)
    def validation_error(error):
        return fail(str(error))

    @app.errorhandler(HTTPException)
    def http_error(error):
        if request.path.startswith("/api/"):
            return fail(error.description, error.code)
        return error

    @app.cli.command("init-db")
    @click.option("--demo", is_flag=True, help="Also insert the fictional demo account and study data.")
    def init_db(demo):
        """Initialize an empty database without destroying existing records."""
        db = get_db()
        sql_dir = Path(__file__).resolve().parents[2] / "Database Schema & Data"
        # Release packages also include a copy beside the Python package.
        if not sql_dir.exists():
            sql_dir = Path(__file__).resolve().parents[1] / "database"
        db.executescript((sql_dir / "schema.sql").read_text(encoding="utf-8"))
        if demo:
            db.executescript((sql_dir / "sample_data.sql").read_text(encoding="utf-8"))
        click.echo("Database ready" + (" with demo data." if demo else "."))

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        get_db().execute("SELECT 1 FROM users LIMIT 1").fetchone()
        return jsonify(status="ok")

    @app.get("/api/session")
    def current_session():
        session.setdefault("csrf_token", secrets.token_urlsafe(32))
        user = get_db().execute("SELECT id, name, email FROM users WHERE id = ?", (session.get("user_id"),)).fetchone()
        return jsonify(user=dict(user) if user else None, csrf_token=session["csrf_token"])

    @app.post("/api/auth/register")
    def register():
        data = body(("name", "email", "password"))
        name = text_field(data, "name", 80)
        email = text_field(data, "email", 254).lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            raise ValueError("Enter a valid email address.")
        password = data.get("password")
        if not isinstance(password, str) or not 8 <= len(password) <= 128:
            raise ValueError("Password must contain 8 to 128 characters.")
        db = get_db()
        try:
            with db:
                user_id = db.execute("INSERT INTO users(name,email,password_hash) VALUES (?,?,?)", (name, email, generate_password_hash(password))).lastrowid
        except sqlite3.IntegrityError:
            return fail("Email already registered.", 409)
        session.clear()
        session.update(user_id=user_id, csrf_token=secrets.token_urlsafe(32))
        return jsonify(user={"id": user_id, "name": name, "email": email}, csrf_token=session["csrf_token"]), 201

    @app.post("/api/auth/login")
    def login():
        data = body(("email", "password"))
        email = text_field(data, "email", 254).lower()
        password = data.get("password")
        if not isinstance(password, str) or not 1 <= len(password) <= 128:
            raise ValueError("Password must contain 1 to 128 characters.")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            return fail("Invalid email or password.", 401)
        session.clear()
        session.update(user_id=user["id"], csrf_token=secrets.token_urlsafe(32))
        return jsonify(user={k: user[k] for k in ("id", "name", "email")}, csrf_token=session["csrf_token"])

    @app.post("/api/auth/logout")
    def logout():
        session.clear()
        return jsonify(message="Signed out.")

    @app.patch("/api/users/me")
    @authenticated
    def profile():
        data = body(("name",))
        name = text_field(data, "name", 80)
        db = get_db()
        with db:
            db.execute("UPDATE users SET name=? WHERE id=?", (name, session["user_id"]))
        return jsonify(user=dict(db.execute("SELECT id,name,email FROM users WHERE id=?", (session["user_id"],)).fetchone()))

    @app.route("/api/subjects", methods=["GET", "POST"])
    @authenticated
    def subjects():
        db, uid = get_db(), session["user_id"]
        if request.method == "GET":
            return jsonify(subjects=[dict(s) for s in db.execute("SELECT id,name FROM subjects WHERE user_id=? ORDER BY name", (uid,))])
        data = body(("name",))
        name = text_field(data, "name", 80)
        try:
            with db:
                sid = db.execute("INSERT INTO subjects(user_id,name) VALUES (?,?)", (uid, name)).lastrowid
        except sqlite3.IntegrityError:
            return fail("A subject with that name already exists.", 409)
        return jsonify(subject={"id": sid, "name": name}), 201

    @app.route("/api/subjects/<int:sid>", methods=["PATCH", "DELETE"])
    @authenticated
    def subject_detail(sid):
        db, uid = get_db(), session["user_id"]
        if not db.execute("SELECT id FROM subjects WHERE id=? AND user_id=?", (sid, uid)).fetchone():
            return fail("Subject not found.", 404)
        if request.method == "DELETE":
            if db.execute("SELECT id FROM tasks WHERE subject_id=? AND user_id=? LIMIT 1", (sid, uid)).fetchone():
                return fail("Move or delete this subject's tasks first.", 409)
            with db:
                db.execute("DELETE FROM subjects WHERE id=? AND user_id=?", (sid, uid))
            return "", 204
        name = text_field(body(("name",)), "name", 80)
        try:
            with db:
                db.execute("UPDATE subjects SET name=? WHERE id=? AND user_id=?", (name, sid, uid))
        except sqlite3.IntegrityError:
            return fail("A subject with that name already exists.", 409)
        return jsonify(subject={"id": sid, "name": name})

    def validate_task(data):
        data["title"] = text_field(data, "title", 160)
        notes = data.get("notes", "")
        if not isinstance(notes, str) or len(notes) > 2000:
            raise ValueError("notes must be text up to 2000 characters.")
        data["notes"] = notes.strip()
        if data.get("priority") not in PRIORITIES or data.get("status") not in STATUSES:
            raise ValueError("Invalid priority or status.")
        due = data.get("due_date")
        if not isinstance(due, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
            raise ValueError("due_date must be a valid YYYY-MM-DD date.")
        date.fromisoformat(due)
        minutes = data.get("estimated_minutes", 30)
        if type(minutes) is not int or not 1 <= minutes <= 1440:
            raise ValueError("estimated_minutes must be an integer from 1 to 1440.")
        data["estimated_minutes"] = minutes
        sid = data.get("subject_id")
        if type(sid) is not int or not 1 <= sid <= 9223372036854775807 or not get_db().execute("SELECT id FROM subjects WHERE id=? AND user_id=?", (sid, session["user_id"])).fetchone():
            raise ValueError("Choose one of your subjects.")
        return data

    def task_json(row):
        task = dict(row)
        task["priority_score"] = priority_score(task)
        return task

    def find_task(tid):
        return get_db().execute("SELECT t.*, s.name AS subject_name FROM tasks t JOIN subjects s ON s.id=t.subject_id WHERE t.id=? AND t.user_id=?", (tid, session["user_id"])).fetchone()

    fields = ("title", "notes", "subject_id", "priority", "status", "due_date", "estimated_minutes")

    @app.route("/api/tasks", methods=["GET", "POST"])
    @authenticated
    def tasks():
        db, uid = get_db(), session["user_id"]
        if request.method == "POST":
            data = body(fields)
            data.setdefault("priority", "medium")
            data.setdefault("status", "pending")
            data = validate_task(data)
            with db:
                tid = db.execute("INSERT INTO tasks(user_id,title,notes,subject_id,priority,status,due_date,estimated_minutes) VALUES (?,?,?,?,?,?,?,?)", (uid, *(data[f] for f in fields))).lastrowid
            return jsonify(task=task_json(find_task(tid))), 201
        allowed = {"subject_id", "status", "priority", "q", "due_before", "sort"}
        if set(request.args) - allowed:
            raise ValueError("Unknown task filter.")
        clauses, args = ["t.user_id=?"], [uid]
        for key, choices in (("status", STATUSES), ("priority", PRIORITIES)):
            if key in request.args:
                if request.args[key] not in choices:
                    raise ValueError(f"Invalid {key} filter.")
                clauses.append(f"t.{key}=?")
                args.append(request.args[key])
        if "subject_id" in request.args:
            if not request.args["subject_id"].isascii() or not request.args["subject_id"].isdigit() or len(request.args["subject_id"]) > 18:
                raise ValueError("subject_id must be an integer.")
            clauses.append("t.subject_id=?")
            args.append(int(request.args["subject_id"]))
        if "q" in request.args:
            if len(request.args["q"]) > 160:
                raise ValueError("Search is limited to 160 characters.")
            query = request.args["q"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("(t.title LIKE ? ESCAPE '\\' OR t.notes LIKE ? ESCAPE '\\')")
            args.extend([f"%{query}%"] * 2)
        if "due_before" in request.args:
            due = request.args["due_before"]
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", due):
                raise ValueError("due_before must be YYYY-MM-DD.")
            date.fromisoformat(due)
            clauses.append("t.due_date<=?")
            args.append(due)
        sort = request.args.get("sort", "recommended")
        if sort not in ("recommended", "due_date", "newest"):
            raise ValueError("Invalid sort. Choose recommended, due_date, or newest.")
        rows = db.execute("SELECT t.*, s.name AS subject_name FROM tasks t JOIN subjects s ON s.id=t.subject_id WHERE " + " AND ".join(clauses), args)
        result = [task_json(row) for row in rows]
        keys = {
            "recommended": lambda t: (-t["priority_score"], t["due_date"], t["id"]),
            "due_date": lambda t: (t["due_date"], t["id"]),
            "newest": lambda t: -t["id"],
        }
        result.sort(key=keys[sort])
        return jsonify(tasks=result, count=len(result))

    @app.route("/api/tasks/<int:tid>", methods=["GET", "PATCH", "DELETE"])
    @authenticated
    def task_detail(tid):
        row = find_task(tid)
        if row is None:
            return fail("Task not found.", 404)
        if request.method == "GET":
            return jsonify(task=task_json(row))
        db = get_db()
        if request.method == "DELETE":
            with db:
                db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (tid, session["user_id"]))
            return "", 204
        changes = body(fields)
        if not changes:
            raise ValueError("Provide at least one task field.")
        data = validate_task({**{f: row[f] for f in fields}, **changes})
        with db:
            db.execute("UPDATE tasks SET title=?,notes=?,subject_id=?,priority=?,status=?,due_date=?,estimated_minutes=?,updated_at=CURRENT_TIMESTAMP WHERE id=? AND user_id=?", (*(data[f] for f in fields), tid, session["user_id"]))
        return jsonify(task=task_json(find_task(tid)))

    @app.get("/api/dashboard")
    @authenticated
    def dashboard():
        rows = get_db().execute("SELECT * FROM tasks WHERE user_id=?", (session["user_id"],)).fetchall()
        pending = [r for r in rows if r["status"] != "completed"]
        return jsonify(total=len(rows), completed=len(rows)-len(pending),
                       overdue=sum(r["due_date"] < date.today().isoformat() for r in pending),
                       remaining_minutes=sum(r["estimated_minutes"] for r in pending))

    return app
