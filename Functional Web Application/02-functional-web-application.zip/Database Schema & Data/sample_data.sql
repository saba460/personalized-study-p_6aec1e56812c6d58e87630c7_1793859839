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
