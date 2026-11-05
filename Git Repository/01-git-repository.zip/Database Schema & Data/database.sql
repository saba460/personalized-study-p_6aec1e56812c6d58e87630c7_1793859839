-- Personalized Study Planner: SQLite schema and fictional demo data
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

-- Fictional local demonstration only: demo@example.com / StudyDemo!2026
-- Password is a Werkzeug-compatible PBKDF2 hash, never stored as plaintext.
-- Run schema.sql first. Re-running this seed does not duplicate demo records.
PRAGMA foreign_keys = ON;
BEGIN;
INSERT INTO users(name,email,password_hash)
VALUES ('Demo Student','demo@example.com','pbkdf2:sha256:600000$gkV0nUdetbF3RzMo$152b33690055000ba7a048663a89f15ce2330cd3b57eb12b5a67d5cb6a276aa7')
ON CONFLICT(email) DO NOTHING;
INSERT INTO subjects(user_id,name)
SELECT id,'Mathematics' FROM users WHERE email='demo@example.com'
ON CONFLICT(user_id,name) DO NOTHING;
INSERT INTO subjects(user_id,name)
SELECT id,'Python Programming' FROM users WHERE email='demo@example.com'
ON CONFLICT(user_id,name) DO NOTHING;
INSERT INTO subjects(user_id,name)
SELECT id,'Database Systems' FROM users WHERE email='demo@example.com'
ON CONFLICT(user_id,name) DO NOTHING;
WITH examples(subject,title,notes,priority,status,offset,minutes) AS (
 VALUES
 ('Mathematics','Review linear equations','Work through five practice questions.','high','pending','-1 day',45),
 ('Python Programming','Practice Python functions','Build a reusable study timer function.','high','in_progress','+1 day',60),
 ('Database Systems','Draw the study planner ER model','Identify keys and user ownership relationships.','medium','pending','+3 days',30),
 ('Mathematics','Practice probability','Review independent events and conditional probability.','low','pending','+7 days',40),
 ('Python Programming','Read the Flask quickstart','Understand routes, templates, and sessions.','medium','completed','-2 days',25)
)
INSERT INTO tasks(user_id,subject_id,title,notes,priority,status,due_date,estimated_minutes)
SELECT u.id,s.id,e.title,e.notes,e.priority,e.status,date('now','localtime',e.offset),e.minutes
FROM examples e JOIN users u ON u.email='demo@example.com'
JOIN subjects s ON s.user_id=u.id AND s.name=e.subject
WHERE NOT EXISTS(SELECT 1 FROM tasks t WHERE t.user_id=u.id AND t.title=e.title);
COMMIT;
