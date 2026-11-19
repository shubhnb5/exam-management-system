-- Combine Mentor database schema (PostgreSQL)
-- Generated from backend/app/models.py and backend/alembic/versions/5afe184335ba_initial_schema.py
-- Reflects the state as of migration 5afe184335ba ("initial schema").

BEGIN;

-- ---------------------------------------------------------------------------
-- exam_centers
-- ---------------------------------------------------------------------------
CREATE TABLE exam_centers (
    id   SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    code VARCHAR NOT NULL,
    CONSTRAINT exam_centers_code_key UNIQUE (code)
);

-- ---------------------------------------------------------------------------
-- students
-- ---------------------------------------------------------------------------
CREATE TABLE students (
    id              SERIAL PRIMARY KEY,
    full_name       VARCHAR NOT NULL,
    email           VARCHAR NOT NULL,
    mobile_number   VARCHAR NOT NULL,
    exam_center_id  INTEGER NOT NULL REFERENCES exam_centers (id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT students_email_key UNIQUE (email)
);

CREATE UNIQUE INDEX ix_students_email ON students (email);

-- ---------------------------------------------------------------------------
-- users  (unified login for admin + teachers)
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    username        VARCHAR NOT NULL,
    password_hash   VARCHAR NOT NULL,
    full_name       VARCHAR NOT NULL,
    role            VARCHAR NOT NULL,
    exam_center_id  INTEGER REFERENCES exam_centers (id),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_username_key UNIQUE (username),
    CONSTRAINT ck_users_role CHECK (role IN ('admin', 'teacher'))
);

-- ---------------------------------------------------------------------------
-- email_log
-- ---------------------------------------------------------------------------
CREATE TABLE email_log (
    id             SERIAL PRIMARY KEY,
    student_id     INTEGER NOT NULL REFERENCES students (id),
    status         VARCHAR NOT NULL DEFAULT 'pending',
    error_message  TEXT,
    attempt_count  INTEGER NOT NULL DEFAULT 0,
    sent_at        TIMESTAMPTZ,
    CONSTRAINT ck_email_log_status CHECK (status IN ('pending', 'sent', 'failed'))
);

-- ---------------------------------------------------------------------------
-- hall_tickets
-- ---------------------------------------------------------------------------
CREATE TABLE hall_tickets (
    id            SERIAL PRIMARY KEY,
    student_id    INTEGER NOT NULL REFERENCES students (id),
    qr_token      VARCHAR NOT NULL,
    pdf_path      VARCHAR NOT NULL,
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT hall_tickets_student_id_key UNIQUE (student_id),
    CONSTRAINT hall_tickets_qr_token_key UNIQUE (qr_token)
);

CREATE UNIQUE INDEX ix_hall_tickets_qr_token ON hall_tickets (qr_token);

-- ---------------------------------------------------------------------------
-- scans
-- Uniqueness on (student_id, scan_date) enforces "one scan per student per
-- day" at the database level, safe under concurrent inserts.
-- ---------------------------------------------------------------------------
CREATE TABLE scans (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students (id),
    teacher_id      INTEGER NOT NULL REFERENCES users (id),
    exam_center_id  INTEGER NOT NULL REFERENCES exam_centers (id),
    scan_date       DATE NOT NULL DEFAULT CURRENT_DATE,
    scanned_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_scans_student_day UNIQUE (student_id, scan_date)
);

-- ---------------------------------------------------------------------------
-- uploads  (audit trail for each Excel import)
-- ---------------------------------------------------------------------------
CREATE TABLE uploads (
    id               SERIAL PRIMARY KEY,
    filename         VARCHAR NOT NULL,
    uploaded_by      INTEGER NOT NULL REFERENCES users (id),
    row_count        INTEGER NOT NULL,
    new_students     INTEGER NOT NULL,
    updated_students INTEGER NOT NULL,
    error_count      INTEGER NOT NULL DEFAULT 0,
    uploaded_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
