# Fly Dubai — Complaint Token Queue System

A lightweight IT-helpdesk style token queue system built with **plain HTML/CSS/JS** and a small
**Python** server that holds one shared queue so phones, the admin PC, and the waiting-area TV all
stay in sync over the same Wi-Fi.

## Pages

| File | Role | Open on |
|------|------|---------|
| `patient.html` | Complaint registration form | Phone / kiosk (mobile-first) |
| `admin.html`   | Staff queue control (PIN `admin123`) | Desktop / tablet |
| `display.html` | Waiting-area TV board | Fullscreen TV |

## Run locally

```bash
python3 server.py
```

Then open from any device on the same Wi-Fi (replace with your machine's LAN IP):

- Patient:  `http://<your-ip>:8753/patient.html`
- Admin:    `http://<your-ip>:8753/admin.html`
- Display:  `http://<your-ip>:8753/display.html`

## How it works

- All three pages read/write a single shared queue via the server API:
  - `GET  /api/state` — current queue
  - `POST /api/register` — register a complaint (atomic)
  - `POST /api/op` — admin actions (call-next, mark-done, skip, re-insert, mark-reviewed, set-name, reset)
- State is persisted to `state.json` and **auto-resets each new day** (tokens start at 01).
- Admin and display poll the server every 1.5s for live updates.

## Features

- Issue types: IT, Outlook Issue, Hardware Issues, Laptop Issues, Other Issues
- International / UAE-friendly phone input (no country-specific validation)
- Optional complaint details, surfaced in the admin **Complaints** tab
- Dark / light themes, mobile-optimised patient form
- CSV export, printable daily report, QR-code generator for the patient URL

## Notes

- Keep the terminal running while the system is in use (closing it stops the server).
- Allow Python through the OS firewall so other devices can connect.
- `state.json` is runtime data and is intentionally git-ignored.
