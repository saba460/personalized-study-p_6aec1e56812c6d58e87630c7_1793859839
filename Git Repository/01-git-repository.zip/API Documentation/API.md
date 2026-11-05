# Study Planner JSON API

Base URL for the local app: `http://127.0.0.1:5000/api`.
All bodies and responses use JSON except successful `DELETE`, which returns an
empty body. State is persisted in SQLite. IDs are integers; dates are `YYYY-MM-DD`.

## Authentication and CSRF

The API uses a signed, HTTP-only session cookie (`SameSite=Lax`), not a bearer token.
First call `GET /session`, retain its cookie, and read `csrf_token`. Every `POST`,
`PATCH`, and `DELETE` requires that value in the `X-CSRF-Token` header.
Set `Content-Type: application/json` when supplying a body.
Register/login automatically sign in and rotate the session and CSRF token;
replace the saved token with the token returned in their responses. Logout clears
the session. Call `/session` again to obtain a new token before the next login.
Browser JavaScript handles this automatically.

Protected routes return `401` when signed out. Foreign users' task and subject IDs
return `404` to avoid disclosing their existence. Invalid/missing CSRF returns `403`.

## Endpoints

| Method | Path | Authentication | Request / response |
|---|---|---|---|
| GET | `/health` | Public | `{"status":"ok"}`; requires initialized DB |
| GET | `/session` | Public | `{"user":null,"csrf_token":"..."}` or current user |
| POST | `/auth/register` | Public + CSRF | `name`, `email`, `password`; returns user + new token, `201` |
| POST | `/auth/login` | Public + CSRF | `email`, `password`; returns user + new token, `200` |
| POST | `/auth/logout` | CSRF | Clears session; returns message, `200` |
| PATCH | `/users/me` | Required | `name`; returns updated `user`, `200` |
| GET | `/subjects` | Required | Returns `{"subjects":[{"id":1,"name":"Mathematics"}]}` |
| POST | `/subjects` | Required | `name`; returns `subject`, `201` |
| PATCH | `/subjects/{id}` | Required | `name`; returns `subject`, `200` |
| DELETE | `/subjects/{id}` | Required | `204`; `409` if subject has tasks |
| GET | `/tasks` | Required | Returns `{"tasks":[...],"count":1}`; supports filters below |
| POST | `/tasks` | Required | Task fields below; returns `task`, `201` |
| GET | `/tasks/{id}` | Required | Returns `task`, `200` |
| PATCH | `/tasks/{id}` | Required | One or more task fields; returns updated `task`, `200` |
| DELETE | `/tasks/{id}` | Required | `204` |
| GET | `/dashboard` | Required | `total`, `completed`, `overdue`, `remaining_minutes` |

User objects contain `id`, `name`, and `email`. Password hashes are never returned.

## Task fields

| Field | Rules |
|---|---|
| `title` | Required on create; 1–160 characters after trimming |
| `subject_id` | Required on create; ID of one of the current user's subjects |
| `due_date` | Required on create; real calendar date in `YYYY-MM-DD` format |
| `notes` | Optional text, at most 2,000 characters; defaults to empty string |
| `priority` | `low`, `medium`, or `high`; defaults to `medium` |
| `status` | `pending`, `in_progress`, or `completed`; defaults to `pending` |
| `estimated_minutes` | Integer 1–1440; defaults to 30 |

Task responses additionally contain `id`, `user_id`, `subject_name`, `created_at`,
`updated_at`, and `priority_score`. Timestamps are SQLite UTC timestamps.
The calculated score is refreshed at read time using the server's local date;
see the root README for the scoring formula. There is no writable score field.
Unknown request fields are rejected. Task PATCH preserves unspecified fields.

Subject and display names must contain 1–80 trimmed characters. Email is normalized
to lowercase and must have a basic valid email shape, up to 254 characters.
Registration passwords must contain 8–128 characters and are stored as hashes.

## Task filtering and sorting

All filters can be combined with AND:

| Query parameter | Values / behavior |
|---|---|
| `subject_id` | Integer subject ID |
| `status` | `pending`, `in_progress`, `completed` |
| `priority` | `low`, `medium`, `high` |
| `q` | Substring search in title or notes; up to 160 characters; `%` and `_` are literal |
| `due_before` | Inclusive date upper bound in `YYYY-MM-DD` |
| `sort` | `recommended` (default), `due_date`, or `newest` |

Example: `/tasks?subject_id=1&status=pending&priority=high&sort=due_date`.
Dashboard totals always describe all of the signed-in user's tasks, regardless
of the task-list filters. Overdue excludes completed tasks and tasks due today.
Remaining minutes sum only unfinished tasks. This small capstone API returns all
matching tasks without pagination.

## Complete PowerShell example

Run the app first, then paste this into PowerShell. It uses the fictional demo login.
`$subjectId` is read from the API rather than assuming fixed IDs.

```powershell
$baseUrl = 'http://127.0.0.1:5000/api'
$sessionInfo = Invoke-RestMethod "$baseUrl/session" -SessionVariable webSession
$headers = @{ 'X-CSRF-Token' = $sessionInfo.csrf_token }
$loginBody = @{ email='demo@example.com'; password='StudyDemo!2026' } | ConvertTo-Json
$login = Invoke-RestMethod "$baseUrl/auth/login" -Method Post -WebSession $webSession -Headers $headers -ContentType 'application/json' -Body $loginBody
$headers['X-CSRF-Token'] = $login.csrf_token
$subjects = Invoke-RestMethod "$baseUrl/subjects" -WebSession $webSession
$subjectId = $subjects.subjects[0].id
$taskBody = @{ title='Review chapter 3'; subject_id=$subjectId; due_date=(Get-Date).AddDays(1).ToString('yyyy-MM-dd'); priority='high'; estimated_minutes=45 } | ConvertTo-Json
$created = Invoke-RestMethod "$baseUrl/tasks" -Method Post -WebSession $webSession -Headers $headers -ContentType 'application/json' -Body $taskBody
Invoke-RestMethod "$baseUrl/tasks?priority=high&sort=recommended" -WebSession $webSession
$taskId = $created.task.id
Invoke-RestMethod "$baseUrl/tasks/$taskId" -Method Patch -WebSession $webSession -Headers $headers -ContentType 'application/json' -Body '{"status":"completed"}'
Invoke-RestMethod "$baseUrl/dashboard" -WebSession $webSession
```

Example task response:

```json
{
  "task": {
    "id": 6,
    "user_id": 1,
    "subject_id": 1,
    "subject_name": "Mathematics",
    "title": "Review chapter 3",
    "notes": "",
    "priority": "high",
    "status": "pending",
    "due_date": "2026-11-06",
    "estimated_minutes": 45,
    "created_at": "2026-11-05 10:00:00",
    "updated_at": "2026-11-05 10:00:00",
    "priority_score": 70
  }
}
```

IDs, timestamps, and scores depend on your data and the current server date.

## Errors

Error shape: `{"error":"Choose one of your subjects."}`.

| Status | Meaning |
|---|---|
| 400 | Invalid field, malformed JSON, invalid date, or unknown filter |
| 401 | Not signed in, or incorrect login credentials |
| 403 | Missing/invalid CSRF token |
| 404 | Record/endpoint not found or not owned by current user |
| 409 | Duplicate email/subject, or attempted deletion of a nonempty subject |
| 413 | Request exceeds 64 KiB |
| 415 | Non-JSON body sent to an endpoint that requires JSON |

Use HTTPS and production hosting configuration before public deployment.
