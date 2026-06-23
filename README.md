# Fly Dubai — Complaint Token Queue System

A lightweight IT-helpdesk **complaint registration & token queue** system. Plain HTML/CSS/JS
frontends plus a small **Python** backend that holds one shared queue, so the complaint form,
admin panel, and waiting-area display all stay in sync.

## Structure

```
form/index.html         → Complaint registration form (mobile-first)
admin-app/index.html    → Staff queue control (PIN: admin123)
display-app/index.html  → Waiting-area TV display
server.py               → Shared-queue backend API
render.yaml             → Render deploy config (backend)
requirements.txt        → (stdlib only — marks this as a Python service)
```

## Run locally

```bash
python3 server.py
```

Open from any device on the same Wi-Fi (replace with your machine's LAN IP):

- Form:    `http://<your-ip>:8753/form/`
- Admin:   `http://<your-ip>:8753/admin-app/`
- Display: `http://<your-ip>:8753/display-app/`

When served locally, the pages auto-detect localhost/LAN and talk to the same-origin backend.

## Deploy to production (Vercel × 3 + Render × 1)

The 3 pages are static (host on Vercel); the queue backend must run somewhere always-on (Render).

### 1. Backend → Render
1. Go to [render.com](https://render.com) → **New → Web Service** → connect this repo.
2. Render reads `render.yaml` automatically (runtime: Python, start: `python server.py`).
3. Deploy → copy the URL, e.g. `https://flydubai-complaint-queue.onrender.com`.

### 2. Point the frontends at the backend
In each of `form/index.html`, `admin-app/index.html`, `display-app/index.html`, set the
`API_BASE` constant's production URL to your Render URL (replace `REPLACE-WITH-YOUR-RENDER-URL`).

### 3. Frontends → Vercel (3 separate projects, same repo)
For each project, set **Root Directory** and deploy:

| Vercel project | Root Directory | Result |
|----------------|----------------|--------|
| complaint form | `form` | `flydubai-complaint.vercel.app` |
| admin panel | `admin-app` | `flydubai-admin.vercel.app` |
| TV display | `display-app` | `flydubai-display.vercel.app` |

## API

- `GET  /api/state` — current queue
- `POST /api/register` — register a complaint (atomic)
- `POST /api/op` — admin actions (call-next, mark-done, skip, re-insert, mark-reviewed, set-name, reset)

State persists to `state.json` and **auto-resets each new day** (tokens start at 01).

## Features

- Issue types: IT, Outlook Issue, Hardware Issues, Laptop Issues, Other Issues (dropdown)
- International / UAE-friendly phone input (no country-specific validation)
- Optional complaint details → admin **Complaints** tab
- Dark / light themes, mobile-optimised form, CSV export, printable report, QR-code generator
- Live cross-device sync (admin & display poll the backend every 1.5s)

## Notes

- `state.json` is runtime data and is git-ignored.
- Render free tier sleeps after ~15 min idle, but the always-open TV display polling keeps it awake during the day.
