# Combine Mentor

QR-based hall ticket generation and exam attendance system — auto-generates personalized tickets from student data, emails them out, and verifies entry via QR scans across multiple exam centers in real time.

## Architecture

- **Backend**: FastAPI + PostgreSQL (SQLAlchemy + Alembic). JWT auth for both admins and teachers.
- **Ticket generation**: `reportlab` + `qrcode` render a personalized PDF hall ticket (candidate details, exam timetable, a Marathi rules page) with a random, unguessable QR token embedded per student. No student photos — the source Excel data has none.
- **Frontend-admin**: React (Vite) — upload students, generate tickets, send emails, monitor status, manage teacher accounts, live attendance stats, and a per-student attendance view (with a date picker, since the exam spans multiple dates) showing who was present/absent and who scanned them in.
- **Frontend-scanner**: React (Vite) PWA — teacher login + camera-based QR scanning (`html5-qrcode`), full-screen glanceable pass/fail feedback.
- **Race safety**: a Postgres `UNIQUE(student_id, scan_date)` constraint on the `scans` table — not application logic — is what actually prevents the same student being checked in twice, even under concurrent scans from different devices. Verified under a real 10-way concurrent scan test: exactly 1 succeeded, 9 were rejected with a clear "already scanned at X by Y at HH:MM" message.

## Key design decisions

- **"Today" boundary**: calendar date, pinned explicitly to IST (`Asia/Kolkata`) via `app/timeutils.py` — this does not depend on the server/container's own system timezone (which typically defaults to UTC on cloud hosts), so exam-day boundaries stay correct regardless of where this gets deployed.
- **Re-upload behavior**: upserts students by **email**. Re-uploading a sheet updates existing students, adds new ones, never duplicates.
- **Exam center assignment**: chosen once per upload via a dropdown in the admin dashboard, not a column in the Excel sheet — every student in the uploaded file is assigned to whichever center you pick. Upload one sheet per center. Re-uploading a sheet under a different center selection moves those students to the new center.
- **Offline handling**: v1 is online-only — the scanner shows a clear "no connection" message and the teacher retries. No offline queue/sync (this was an explicit simplicity trade-off; revisit if centers have unreliable internet in practice).
- **Teacher accounts**: one fixed login per teacher/device, created by the admin. Revoking a lost device = deactivating that one account.
- **Roll No.** on the ticket is just the last 7 digits of the student's mobile number — computed at render time, not stored.
- **Email**: SMTP with a Google Workspace App Password (2000/day limit comfortably covers up to ~1500 students in one run).

## Repo layout

```
backend/               FastAPI app
  app/
    models.py           SQLAlchemy schema
    routers/             auth, admin, scan endpoints
    services/            excel import, PDF generation, QR, email, rules page
  alembic/               DB migrations
ticket_template/
  config.json            org name, exam title, timetable, subject code, etc. — EDIT THIS to rebrand
  logo.png               drop your logo here (falls back to a placeholder circle if absent)
  fonts/                 Noto Sans + Noto Sans Devanagari (bundled, open source, supports Marathi text)
frontend-admin/         React admin dashboard
frontend-scanner/       React scanner PWA
docker-compose.yml      Full self-hosted stack: db + backend + both frontends
```

## Setup

### 1. Configure

Copy `.env.example` to `.env` at the repo root and fill in:

- `JWT_SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `SMTP_USERNAME` / `SMTP_APP_PASSWORD` — your Google Workspace account + an [App Password](https://myaccount.google.com/apppasswords) (requires 2FA enabled on the account)
- `ADMIN_DEFAULT_PASSWORD` — change this from the default before going live

Edit `ticket_template/config.json` for your actual org name, exam title, subject code, timetable, signatory, and (optionally) website/Telegram handle. Drop your logo at `ticket_template/logo.png`.

### 2. Run everything with Docker (recommended for production/self-hosting)

```
docker compose up --build
```

Caddy is the only container exposed to the outside world (ports 80/443) and routes everything off a single domain by path, terminating real HTTPS automatically via Let's Encrypt — see `DOMAIN`, `ADMIN_BASE_PATH`, `SCANNER_BASE_PATH` in `.env.example`:

- Admin dashboard: `https://<DOMAIN>/admin/`
- Scanner PWA: `https://<DOMAIN>/scanner/`
- Backend API: `https://<DOMAIN>/api/`

Migrations run automatically on backend startup. A default admin user (`admin` / whatever you set `ADMIN_DEFAULT_PASSWORD` to) and two exam centers are seeded on first run.

### 3. Run for local development

```
docker compose up -d db          # just Postgres

cd backend
python -m venv venv && ./venv/Scripts/pip install -r requirements.txt
./venv/Scripts/alembic upgrade head
./venv/Scripts/uvicorn app.main:app --reload

cd frontend-admin && cp .env.example .env && npm install && npm run dev     # :5173
cd frontend-scanner && cp .env.example .env && npm install && npm run dev  # :5174
```

**Camera note**: mobile browsers only grant camera access over HTTPS or `localhost`. Testing the scanner from a real phone on your local network will need a reverse proxy with TLS (e.g. Caddy) or a tunnel (e.g. ngrok) — plain `http://<lan-ip>:5174` will not get camera permission on most phones.

## First-time admin workflow

1. Log into the admin dashboard with the seeded admin account.
2. Add teacher accounts (5 per center × 2 centers) under "Teacher Devices / Accounts".
3. Upload your Excel sheet: columns `Student Name`, `Email`, `Mobile Number`. Select the exam center for this sheet from the dropdown above the upload box — every student in the file is assigned to that center. Upload separately per center.
4. Click "Generate Hall Tickets", then "Send Emails".
5. Monitor per-student ticket/email status in the table; re-run "Send Emails" to retry failures (up to 3 attempts per student).

Teachers log into the scanner PWA with their own account and start scanning — no setup needed on their end beyond camera permission.

## Known limitations / things to revisit

- No database backup strategy yet — attendance records are currently only as safe as the Postgres volume.
- No HTTPS/TLS setup — required before real phones can grant camera access to the scanner PWA off `localhost`. Needs a reverse proxy (e.g. Caddy for automatic HTTPS) or a tunnel for testing.
- No self-service ticket regeneration for a single student (e.g. after a data-entry typo) — currently requires a manual script.
- No exportable final attendance record (CSV/Excel) for post-exam institutional record-keeping — the admin dashboard's Attendance view is live/on-screen only.
- `GET /admin/students` does one extra query per student for email status — fine at ~1500 rows, would want batching past a few thousand.
- No automated test suite yet — validated via live manual/scripted testing against a real Postgres instance (schema constraints, Excel upload, ticket generation, concurrent scan race-safety) and a real browser (Playwright) for both React apps.
- The dev database currently has a few sample students/teachers from testing (`asha.test@example.com` etc.) — wipe these (`docker compose down -v` on the `db` volume, or just delete the rows) before handing real student data to the system.
