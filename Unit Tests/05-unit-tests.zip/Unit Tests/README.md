# Backend unit and integration tests

Run `python scripts/run_tests.py` from the root with the project environment active.
Alternatively: `python -m unittest discover -s "Unit Tests" -p "test_*.py" -v`.
Only Flask and its dependencies are needed; unittest ships with Python.

There are 27 test methods, including parameterized subtests. They cover:

- Priority weights, deadline boundary cases, and completed-task ranking.
- Registration, password hashing, duplicate emails, login/logout, and profile updates.
- Session rotation, CSRF checks, authentication, and separation of users' records.
- Subject CRUD, duplicate names, and deletion conflicts for subjects with tasks.
- Task CRUD, completion, validation, and rejected updates preserving existing data.
- Combined filters, wildcard-safe search, SQL injection input, and sort options.
- Dashboard counts, overdue tasks, and unfinished study effort.
- SQLite foreign keys, ownership constraints, repeated schema/seed initialization.
- Demo login, HTML/static routes, health, security headers, and JSON errors.

Every backend test gets a temporary database; tests do not modify the application's
instance database. The unit tests for scoring use a fixed date. API tests use
relative dates so they remain valid on later days.

See `test-results.txt` for the recorded local run. This is backend verification;
it does not claim browser UI automation, coverage percentage, load testing, or
production security certification. The GitHub Actions workflow runs the same suite.
