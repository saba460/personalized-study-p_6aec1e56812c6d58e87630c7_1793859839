-- SQLite 3. Composite ownership foreign key prevents cross-user subject assignment.
PRAGMA foreign_keys = ON;
BEGIN;
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK(length(trim(name)) BETWEEN 1 AND 80),
    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL COLLATE NOCASE CHECK(length(trim(name)) BETWEEN 1 AND 80),
    UNIQUE(user_id, name),
    UNIQUE(id, user_id)
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    subject_id INTEGER NOT NULL,
    title TEXT NOT NULL CHECK(length(trim(title)) BETWEEN 1 AND 160),
    notes TEXT NOT NULL DEFAULT '' CHECK(length(notes) <= 2000),
    priority TEXT NOT NULL DEFAULT 'medium' CHECK(priority IN ('low','medium','high')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','in_progress','completed')),
    due_date TEXT NOT NULL CHECK(length(due_date)=10 AND due_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    estimated_minutes INTEGER NOT NULL DEFAULT 30 CHECK(typeof(estimated_minutes)='integer' AND estimated_minutes BETWEEN 1 AND 1440),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(subject_id,user_id) REFERENCES subjects(id,user_id) ON DELETE RESTRICT
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_due ON tasks(user_id,due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks(user_id,status);
CREATE INDEX IF NOT EXISTS idx_tasks_subject ON tasks(subject_id,user_id);
COMMIT;
