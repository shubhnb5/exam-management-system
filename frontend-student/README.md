# Combine Mentor — Student Portal

Mobile-first React (Vite) app where students:

- **Sign up** — first name, middle name (optional), last name, gender, mobile number, Gmail ID, Aadhaar (optional), password.
- **Log in** — with mobile number + password.
- **Forgot password** — verify the registered mobile number + Gmail ID, then set a new password.
- **Home** — profile, admit card status, and a **Download Admit Card** button once the admin has generated it.

A student's account is linked to the admin-uploaded student with the same mobile number.

## Run locally

```
cp .env.example .env
npm install
npm run dev   # http://localhost:5175 — /api is proxied to the backend on :8000
```

## Build

`VITE_BASE_PATH` (default `/`) is the path the app is served under in production (`/student/`), and
`VITE_API_URL` (default `/api`) is the backend URL. Both are read at build time.
