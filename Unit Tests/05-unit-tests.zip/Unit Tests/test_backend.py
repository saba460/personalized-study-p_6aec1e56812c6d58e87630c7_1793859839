"""Backend regression tests using temporary SQLite databases and Flask's client."""
import sqlite3
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Functional Web Application"))
from study_planner import create_app, get_db, priority_score
from werkzeug.security import check_password_hash


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = create_app({"TESTING": True, "SECRET_KEY": "test-only", "DATABASE": str(Path(self.temp.name) / "test.sqlite3")})
        result = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.client = self.app.test_client()
        self.register()
        result = self.call("POST", "/api/subjects", {"name": "Mathematics"})
        self.sid = result.json["subject"]["id"]

    def call(self, method, path, data=None, client=None):
        client = client or self.client
        token = client.get("/api/session").json["csrf_token"]
        return client.open(path, method=method, json=data, headers={"X-CSRF-Token": token})

    def register(self, client=None, email="student@example.com", password="Testing!2026"):
        result = self.call("POST", "/api/auth/register", {"name": "Student", "email": email, "password": password}, client)
        self.assertEqual(result.status_code, 201, result.json)
        return result

    def task(self, **changes):
        data = {"title": "Practice equations", "subject_id": self.sid, "due_date": date.today().isoformat()}
        data.update(changes)
        result = self.call("POST", "/api/tasks", data)
        self.assertEqual(result.status_code, 201, result.json)
        return result.json["task"]

    def test_registration_hashes_password_and_hides_hash(self):
        with self.app.app_context():
            row = get_db().execute("SELECT * FROM users").fetchone()
            self.assertNotEqual(row["password_hash"], "Testing!2026")
            self.assertTrue(check_password_hash(row["password_hash"], "Testing!2026"))
        self.assertNotIn("password_hash", self.client.get("/api/session").json["user"])

    def test_duplicate_email_is_case_insensitive(self):
        result = self.call("POST", "/api/auth/register", {"name": "Other", "email": "STUDENT@example.com", "password": "Testing!2026"})
        self.assertEqual(result.status_code, 409)

    def test_invalid_registration_is_rejected(self):
        for changes in ({"email": "broken"}, {"password": "short"}, {"name": " "}, {"admin": True}):
            with self.subTest(changes=changes):
                data = {"name": "Valid", "email": "new@example.com", "password": "Testing!2026", **changes}
                self.assertEqual(self.call("POST", "/api/auth/register", data).status_code, 400)

    def test_login_logout_and_session_rotation(self):
        old = self.client.get("/api/session").json["csrf_token"]
        self.assertEqual(self.call("POST", "/api/auth/logout").status_code, 200)
        self.assertEqual(self.client.get("/api/tasks").status_code, 401)
        result = self.call("POST", "/api/auth/login", {"email": "STUDENT@example.com", "password": "Testing!2026"})
        self.assertEqual(result.status_code, 200)
        self.assertNotEqual(old, result.json["csrf_token"])
        self.assertEqual(self.client.post("/api/auth/logout", headers={"X-CSRF-Token": old}).status_code, 403)

    def test_password_whitespace_is_preserved(self):
        client = self.app.test_client()
        self.register(client, "spaces@example.com", "  padded password  ")
        self.call("POST", "/api/auth/logout", client=client)
        result = self.call("POST", "/api/auth/login", {"email": "spaces@example.com", "password": "  padded password  "}, client)
        self.assertEqual(result.status_code, 200)

    def test_invalid_login(self):
        for email, password in (("student@example.com", "wrong"), ("missing@example.com", "Testing!2026")):
            self.assertEqual(self.call("POST", "/api/auth/login", {"email": email, "password": password}).status_code, 401)

    def test_mutations_require_csrf_token(self):
        self.assertEqual(self.client.post("/api/subjects", json={"name": "Unauthorized"}).status_code, 403)
        self.assertEqual(self.client.get("/api/subjects").json["subjects"], [{"id": self.sid, "name": "Mathematics"}])

    def test_protected_routes_require_authentication(self):
        client = self.app.test_client()
        for path in ("/api/tasks", "/api/subjects", "/api/dashboard", "/api/tasks/1"):
            self.assertEqual(client.get(path).status_code, 401)
        self.assertEqual(self.call("POST", "/api/subjects", {"name": "No"}, client).status_code, 401)

    def test_profile_update(self):
        result = self.call("PATCH", "/api/users/me", {"name": "New Name"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get("/api/session").json["user"]["name"], "New Name")
        self.assertEqual(self.call("PATCH", "/api/users/me", {"name": " "}).status_code, 400)

    def test_subject_crud_and_duplicate_validation(self):
        self.assertEqual(self.call("POST", "/api/subjects", {"name": "mathematics"}).status_code, 409)
        result = self.call("PATCH", f"/api/subjects/{self.sid}", {"name": "Algebra"})
        self.assertEqual(result.json["subject"]["name"], "Algebra")
        self.assertEqual(self.call("DELETE", f"/api/subjects/{self.sid}").status_code, 204)
        self.assertEqual(self.client.get("/api/subjects").json["subjects"], [])

    def test_subject_with_tasks_cannot_be_deleted(self):
        task = self.task()
        self.assertEqual(self.call("DELETE", f"/api/subjects/{self.sid}").status_code, 409)
        self.call("DELETE", f"/api/tasks/{task['id']}")
        self.assertEqual(self.call("DELETE", f"/api/subjects/{self.sid}").status_code, 204)

    def test_task_crud_and_completion(self):
        task = self.task(notes="Study chapter 2", priority="high")
        path = f"/api/tasks/{task['id']}"
        self.assertEqual(self.client.get(path).json["task"]["notes"], "Study chapter 2")
        result = self.call("PATCH", path, {"title": "Revised task", "status": "completed"})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["task"]["priority_score"], 0)
        self.assertEqual(result.json["task"]["title"], "Revised task")
        self.assertEqual(self.call("DELETE", path).status_code, 204)
        self.assertEqual(self.client.get(path).status_code, 404)

    def test_invalid_task_fields_are_rejected(self):
        invalid = ({"title": " "}, {"priority": "urgent"}, {"status": "unknown"}, {"due_date": "2026-02-30"},
                   {"due_date": "20260101"}, {"estimated_minutes": 0}, {"estimated_minutes": True},
                   {"estimated_minutes": 1.5}, {"subject_id": 10**30}, {"subject_id": True},
                   {"notes": None}, {"notes": "x"*2001}, {"user_id": 999})
        for changes in invalid:
            with self.subTest(changes=list(changes)):
                data = {"title": "Valid", "subject_id": self.sid, "due_date": date.today().isoformat(), **changes}
                self.assertEqual(self.call("POST", "/api/tasks", data).status_code, 400)
        self.assertEqual(self.client.get("/api/tasks").json["count"], 0)

    def test_invalid_patch_does_not_change_record(self):
        task = self.task()
        path = f"/api/tasks/{task['id']}"
        self.assertEqual(self.call("PATCH", path, {"title": "Changed", "estimated_minutes": -1}).status_code, 400)
        self.assertEqual(self.client.get(path).json["task"]["title"], task["title"])
        self.assertEqual(self.call("PATCH", path, {}).status_code, 400)

    def test_users_cannot_read_or_mutate_each_others_records(self):
        task = self.task()
        other = self.app.test_client()
        self.register(other, "other@example.com")
        self.assertEqual(other.get("/api/tasks").json["tasks"], [])
        self.assertEqual(other.get("/api/subjects").json["subjects"], [])
        for method in ("GET", "PATCH", "DELETE"):
            result = self.call(method, f"/api/tasks/{task['id']}", {"title": "Hijacked"} if method == "PATCH" else None, other)
            self.assertEqual(result.status_code, 404)
        for method in ("PATCH", "DELETE"):
            result = self.call(method, f"/api/subjects/{self.sid}", {"name": "Hijacked"} if method == "PATCH" else None, other)
            self.assertEqual(result.status_code, 404)
        result = self.call("POST", "/api/tasks", {"title": "Hijack", "subject_id": self.sid, "due_date": "2026-12-01"}, other)
        self.assertEqual(result.status_code, 400)

    def test_filters_can_be_combined(self):
        self.task(title="Alpha equations", priority="high", status="in_progress", notes="Exam prep")
        self.task(title="Beta", priority="low")
        result = self.client.get(f"/api/tasks?subject_id={self.sid}&priority=high&status=in_progress&q=Exam&due_before={date.today().isoformat()}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual([t["title"] for t in result.json["tasks"]], ["Alpha equations"])

    def test_search_escapes_wildcards_and_sql_injection(self):
        self.task(title="Read 100% of notes")
        self.task(title="Ordinary task")
        self.assertEqual(self.client.get("/api/tasks", query_string={"q": "%"}).json["count"], 1)
        self.assertEqual(self.client.get("/api/tasks", query_string={"q": "' OR 1=1 --"}).json["count"], 0)

    def test_invalid_filters(self):
        for args in ({"status": "bad"}, {"priority": "bad"}, {"sort": "bad"}, {"due_before": "2026-02-30"},
                     {"subject_id": "nan"}, {"subject_id": "9"*30}, {"arbitrary": "bad"}):
            self.assertEqual(self.client.get("/api/tasks", query_string=args).status_code, 400)

    def test_recommended_due_and_newest_sorting(self):
        today = date.today()
        low = self.task(title="Later", priority="low", due_date=(today+timedelta(days=20)).isoformat())
        urgent = self.task(title="Overdue", priority="high", due_date=(today-timedelta(days=1)).isoformat())
        done = self.task(title="Completed", priority="high", status="completed")
        self.assertEqual([t["id"] for t in self.client.get("/api/tasks").json["tasks"]], [urgent["id"], low["id"], done["id"]])
        self.assertEqual([t["id"] for t in self.client.get("/api/tasks?sort=due_date").json["tasks"]], [urgent["id"], done["id"], low["id"]])
        self.assertEqual(self.client.get("/api/tasks?sort=newest").json["tasks"][0]["id"], done["id"])

    def test_dashboard_counts_only_unfinished_effort_and_overdue(self):
        self.task(due_date=(date.today()-timedelta(days=1)).isoformat(), estimated_minutes=45)
        self.task(status="completed", estimated_minutes=30)
        self.assertEqual(self.client.get("/api/dashboard").json, {"total": 2, "completed": 1, "overdue": 1, "remaining_minutes": 45})

    def test_schema_prevents_cross_user_foreign_key(self):
        other = self.app.test_client()
        self.register(other, "other@example.com")
        uid = other.get("/api/session").json["user"]["id"]
        with self.app.app_context():
            db = get_db()
            with self.assertRaises(sqlite3.IntegrityError):
                with db:
                    db.execute("INSERT INTO tasks(user_id,subject_id,title,due_date) VALUES (?,?,?,?)", (uid, self.sid, "Invalid owner", "2026-12-01"))

    def test_schema_rejects_invalid_status_and_missing_subject(self):
        with self.app.app_context():
            db = get_db()
            uid = db.execute("SELECT id FROM users LIMIT 1").fetchone()[0]
            for sid, status in ((self.sid, "broken"), (99999, "pending")):
                with self.assertRaises(sqlite3.IntegrityError):
                    with db:
                        db.execute("INSERT INTO tasks(user_id,subject_id,title,due_date,status) VALUES (?,?,?,?,?)", (uid, sid, "Invalid", "2026-12-01", status))

    def test_schema_and_seed_are_repeatable_and_demo_login_works(self):
        runner = self.app.test_cli_runner()
        for _ in range(2):
            result = runner.invoke(args=["init-db", "--demo"])
            self.assertEqual(result.exit_code, 0, result.output)
        other = self.app.test_client()
        result = self.call("POST", "/api/auth/login", {"email": "demo@example.com", "password": "StudyDemo!2026"}, other)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(other.get("/api/tasks").json["count"], 5)
        self.assertEqual(len(other.get("/api/subjects").json["subjects"]), 3)
        self.assertEqual(self.client.get("/api/tasks").json["count"], 0)

    def test_html_static_assets_health_and_security_headers(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Study Planner", page.data)
        self.assertEqual(page.headers["X-Frame-Options"], "DENY")
        self.assertIn("script-src 'self'", page.headers["Content-Security-Policy"])
        for path in ("/static/style.css", "/static/app.js", "/api/health"):
            self.assertEqual(self.client.get(path).status_code, 200)
        self.assertEqual(self.client.get("/api/session").headers["Cache-Control"], "no-store")

    def test_api_errors_are_json(self):
        token = self.client.get("/api/session").json["csrf_token"]
        result = self.client.post("/api/subjects", data="{bad", content_type="application/json", headers={"X-CSRF-Token": token})
        self.assertEqual(result.status_code, 400)
        self.assertIn("error", result.json)
        self.assertEqual(self.client.get("/api/missing").status_code, 404)
        self.assertEqual(self.call("POST", "/api/subjects", []).status_code, 400)


class PriorityTests(unittest.TestCase):
    def test_deadline_boundaries_and_importance(self):
        today = date(2026, 11, 5)
        for days, expected in ((-1, 80), (0, 70), (1, 70), (2, 55), (3, 55), (4, 40), (7, 40), (8, 30)):
            with self.subTest(days=days):
                task = {"priority": "high", "status": "pending", "due_date": (today+timedelta(days=days)).isoformat()}
                self.assertEqual(priority_score(task, today), expected)
        for priority, expected in (("low", 10), ("medium", 20), ("high", 30)):
            self.assertEqual(priority_score({"priority": priority, "status": "pending", "due_date": "2026-12-01"}, today), expected)

    def test_completed_task_always_scores_zero(self):
        self.assertEqual(priority_score({"priority": "high", "status": "completed", "due_date": "2020-01-01"}, date(2026, 11, 5)), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
