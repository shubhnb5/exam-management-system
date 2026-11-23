# Combine Mentor

QR-based hall ticket (admit card) generation and exam attendance system — auto-generates personalized admit cards from student data, lets each student download their own card from a student portal, and verifies entry via QR scans across multiple exam centers in real time.

## Architecture

- **Backend**: FastAPI + PostgreSQL (SQLAlchemy + Alembic). JWT auth for admins, teachers and students (student tokens carry a separate type and are rejected by admin/scanner endpoints, and vice versa).
- **Ticket generation**: `reportlab` + `qrcode` render a personalized PDF hall ticket (candidate details, exam timetable, a Marathi rules page) with a random, unguessable QR token embedded per student. No student photos — the source Excel data has none.
- **Frontend-admin**: React (Vite) — add exam centers, upload students, generate admit cards, monitor status, view registered student accounts, manage teacher accounts, live attendance stats, and a per-student attendance view (with a date picker, since the exam spans multiple dates) showing who was present/absent and who scanned them in.
- **Frontend-scanner**: React (Vite) PWA — teacher login + camera-based QR scanning (`html5-qrcode`), full-screen glanceable pass/fail feedback.
- **Frontend-student**: React (Vite), mobile-first — student sign up, login (mobile number + password), forgot password, and download of the student's own admit card.
- **Race safety**: a Postgres `UNIQUE(student_id, scan_date)` constraint on the `scans` table — not application logic — is what actually prevents the same student being checked in twice, even under concurrent scans from different devices. Verified under a real 10-way concurrent scan test: exactly 1 succeeded, 9 were rejected with a clear "already scanned at X by Y at HH:MM" message.

## Key design decisions

- **"Today" boundary**: calendar date, pinned explicitly to IST (`Asia/Kolkata`) via `app/timeutils.py` — this does not depend on the server/container's own system timezone (which typically defaults to UTC on cloud hosts), so exam-day boundaries stay correct regardless of where this gets deployed.
- **Re-upload behavior**: upserts students by **email**. Re-uploading a sheet updates existing students, adds new ones, never duplicates. If a re-upload changes the name, mobile or center of a student who already has an admit card, the card is regenerated automatically (same QR token, so printed copies keep scanning) and the upload result lists every changed card.
- **One mobile number = one student**: mobile numbers are stored normalized to 10 digits. Upload rows whose mobile number is invalid or already used by another student are skipped and listed in the upload result; student portal accounts are unique per mobile number too.
- **Student portal ↔ uploaded data**: a student account is linked to the uploaded student with the same mobile number. The admit card lookup always starts from the logged-in account, never from an ID sent by the browser, so a student can only ever get their own card. Cards are visible as soon as the admin generates them.
- **OTP**: signup requires verifying the mobile number with an OTP (the server creates the account only with a short-lived proof token), and forgot password is mobile → OTP → new password. Three providers, chosen with `OTP_PROVIDER`:
  - `firebase` — **Google Firebase Phone Authentication** sends the SMS from Google's own approved senders (no DLT registration of your own). The backend still does the checks first (number valid, already registered / has an account) and then verifies Google's signed ID token (signature against Google's public keys, project, issuer, freshness ≤ 15 min, phone provider, +91 number matching the one being verified). Needs `FIREBASE_PROJECT_ID`, `FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, a Firebase project on the Blaze plan with Phone sign-in enabled, the site's domain in Authorized domains and India allowed in the SMS region policy.
  - `msg91` — own MSG91 account with a DLT-approved template (`MSG91_AUTH_KEY`, `MSG91_TEMPLATE_ID`). Server-generated codes: 5-minute expiry, single use, 5 wrong tries, 60 s resend, 5 per number per hour, per-IP cap, stored only as a keyed hash.
  - `console` — **test mode**, no SMS (code in the backend log, and on screen with `OTP_DEV_ECHO=true`).
  Accounts created before OTP existed keep working and become verified after an OTP password reset. Login is throttled (5 failures per 15 minutes per mobile number). If someone registers with a wrong number, the admin deletes that account under "Student Accounts".
- **Aadhaar** (optional at signup): validated (12 digits + Verhoeff checksum), unique per account, stored encrypted (`FIELD_ENCRYPTION_KEY`), and only ever shown masked (`XXXX-XXXX-1234`) to the admin.
- **Exam center assignment**: chosen once per upload via a dropdown in the admin dashboard, not a column in the Excel sheet — every student in the uploaded file is assigned to whichever center you pick. Upload one sheet per center. Re-uploading a sheet under a different center selection moves those students to the new center.
- **Offline handling**: v1 is online-only — the scanner shows a clear "no connection" message and the teacher retries. No offline queue/sync (this was an explicit simplicity trade-off; revisit if centers have unreliable internet in practice).
- **Teacher accounts**: one fixed login per teacher/device, created by the admin. Revoking a lost device = deactivating that one account.
- **Roll No.** on the ticket is just the last 7 digits of the student's mobile number — computed at render time, not stored.
- **No email sending**: the student email from the uploaded sheet is kept for reference/records only. Students download admit cards from the student portal.

## Production notes (sized for ~5000 students)

- **Uploads run in the background**: the upload request returns immediately and the dashboard polls for the result, so large files never hit the proxy timeout. Measured for 5000 rows: CSV ~2s, Excel ~4s, Word ~7s, PDF ~50s (PDF table extraction is slow). Only one upload is processed at a time.
- **Admit card generation**: ~0.25s per card (~20 min for 5000) in the background; the API stays responsive meanwhile. Each card is ~380 KB (~1.9 GB for 5000). PDFs on disk are only a cache — a missing or outdated file is regenerated (atomically) on the next download.
- **Load-tested**: 300 students signing up, logging in and downloading concurrently (50 at a time) with zero errors, including with all PDFs wiped from disk.
- **nginx**: `client_max_body_size 20m` on `/api/` (see `deploy/nginx-standalone.conf`) — nginx's 1 MB default rejects larger student lists with "413".
- **Run a single uvicorn process** (as the Dockerfile does): upload/generation job status and login throttling are kept in memory.
- **Startup warnings**: the backend logs a `SECURITY:` warning if `JWT_SECRET_KEY` is a placeholder, `FIELD_ENCRYPTION_KEY` is unset, or the default admin password is weak. `docker-compose.yml` currently loads `.env.example` (placeholder `JWT_SECRET_KEY=changeme`) — use real secrets in production.
- **Student downloads** use a 2-minute single-student download link opened as a normal link, so they also work inside WhatsApp/Instagram/Gmail in-app browsers. The student portal is built for browsers back to ~2020 (iOS 14+, Chrome 87+).

## Design system — "Seal & Signal"

All three frontends share one visual language, drawn from the examination itself (admit cards, invigilator seals, perforated ticket stubs, security-printed certificates):

- **Palette**: ink-indigo (`#12163a`) for navigation and hero surfaces, warm parchment (`#f4efe4`) workspace, one marigold accent (`#f2a93b`) for focus/active states; status colours verdigris (success), vermilion (danger), turmeric (warning). Tokens are CSS custom properties at the top of each app's `src/index.css`.
- **Type**: Fraunces (display), Manrope (UI), JetBrains Mono (numbers, times, section numbers) — self-hosted via `@fontsource-variable/*` (no external font CDN). Devanagari falls back to the system's Noto Sans Devanagari / Nirmala UI / Kohinoor.
- **Motifs**: CSS-only guilloché texture on ink surfaces (`.guilloche`), perforated ticket edge for the admit card, stamp-style status badges, the circular `BrandSeal` mark, a single line-icon set (`components/Icon.jsx`, no emoji).
- **Responsive (mobile-first)**:
  - Admin — phones: top bar + bottom tab bar + "More" sheet; 768–1439px: compact navigation rail; ≥1440px: full sidebar. Tables become labelled cards below 1280px (every column and action kept) and real tables above.
  - Student portal — phones: hero band with an overlapping card; ≥1024px: split story panel + form, two-column home.
  - Scanner — full-screen night console; result screens with a countdown bar for the 3-second auto-resume.

## Repo layout

```
backend/               FastAPI app
  app/
    models.py           SQLAlchemy schema
    routers/             auth, admin, scan, student endpoints
    services/            excel import, PDF generation, QR, admit card lookup, rules page
  alembic/               DB migrations
ticket_template/
  config.json            org name, exam title, timetable, subject code, etc. — EDIT THIS to rebrand
  logo.png               drop your logo here (falls back to a placeholder circle if absent)
  fonts/                 Noto Sans + Noto Sans Devanagari (bundled, open source, supports Marathi text)
frontend-admin/         React admin dashboard
frontend-scanner/       React scanner PWA
frontend-student/       React student portal
docker-compose.yml      Full self-hosted stack: db + backend + all three frontends
```

## Setup

### 1. Configure

Copy `.env.example` to `.env` at the repo root and fill in:

- `JWT_SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `FIELD_ENCRYPTION_KEY` — generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Set it once and never change it (changing it makes stored Aadhaar numbers unreadable).
- `ADMIN_DEFAULT_PASSWORD` — change this from the default before going live

Edit `ticket_template/config.json` for your actual org name, exam title, subject code, timetable, signatory, and (optionally) website/Telegram handle. Drop your logo at `ticket_template/logo.png`.

### 2. Run everything with Docker (recommended for production/self-hosting)

```
docker compose up --build
```

Caddy is the only container exposed to the outside world (ports 80/443) and routes everything off a single domain by path, terminating real HTTPS automatically via Let's Encrypt — see `DOMAIN`, `ADMIN_BASE_PATH`, `SCANNER_BASE_PATH` in `.env.example`:

- Admin dashboard: `https://<DOMAIN>/admin/`
- Scanner PWA: `https://<DOMAIN>/scanner/`
- Student portal: `https://<DOMAIN>/student/`
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
cd frontend-student && cp .env.example .env && npm install && npm run dev  # :5175
```

**Camera note**: mobile browsers only grant camera access over HTTPS or `localhost`. Testing the scanner from a real phone on your local network will need a reverse proxy with TLS (e.g. Caddy) or a tunnel (e.g. ngrok) — plain `http://<lan-ip>:5174` will not get camera permission on most phones.

## First-time admin workflow

1. Log into the admin dashboard with the seeded admin account.
2. Manage exam centers under "Exam Centers" (also "+ Add Exam Center" next to the dropdown under "Upload Students"). Renaming a center updates its admit cards automatically (same QR codes). A center can only be deleted while no students, teachers or attendance records use it; with attendance history it can be renamed but not deleted.
3. Add teacher accounts under "Teacher Devices / Accounts".
4. Upload your Excel sheet: columns `Student Name`, `Email`, `Mobile Number`. Select the exam center for this sheet from the dropdown above the upload box — every student in the file is assigned to that center. Upload separately per center. Fix and re-upload any rows listed as skipped.
5. Click "Generate Admit Cards".
   - Missed a student in the sheet? Students → "+ Add Student" (with "Generate admit card now" ticked) adds them and makes their card in one step.
   - Typo in a student's details? Students → "Edit". If they already have an admit card it's updated automatically (same QR code).
6. Students sign up on the student portal with the same mobile number that is in the sheet, log in, and download their admit card. Registered students are listed under "Student Accounts".

Teachers log into the scanner PWA with their own account and start scanning — no setup needed on their end beyond camera permission.

## Known limitations / things to revisit

- No database backup strategy yet — attendance records are currently only as safe as the Postgres volume.
- No HTTPS/TLS setup — required before real phones can grant camera access to the scanner PWA off `localhost`. Needs a reverse proxy (e.g. Caddy for automatic HTTPS) or a tunnel for testing.
- OTP SMS needs a live MSG91 account with DLT registration; until then the backend runs in OTP test mode (`OTP_PROVIDER=console`), where no SMS is sent.
- Login/forgot-password throttling is in-memory, i.e. per backend process and reset on restart.
- No exportable final attendance record (CSV/Excel) for post-exam institutional record-keeping — the admin dashboard's Attendance view is live/on-screen only.
- No automated test suite yet — validated via live manual/scripted testing against a real Postgres instance (schema constraints, Excel upload, ticket generation, concurrent scan race-safety) and a real browser (Playwright) for both React apps.
- The dev database currently has a few sample students/teachers from testing (`asha.test@example.com` etc.) — wipe these (`docker compose down -v` on the `db` volume, or just delete the rows) before handing real student data to the system.
