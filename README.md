# Fly Dubai — Complaint Token Queue System

An IT-helpdesk **complaint registration & token queue**. Three static pages backed by a free
**Firebase Realtime Database** — no server to run, always-on, instant real-time sync worldwide.

## Structure

```
form/index.html         → Complaint registration form (mobile-first)
admin-app/index.html    → Staff queue control (PIN: Amal123)
display-app/index.html  → Waiting-area TV display
server.py               → optional: serves the folders for local testing
```

All three talk directly to one Firebase Realtime Database, so phones, the admin PC, and the TV
all share the same live queue.

## Hosting (production)

- **Frontend:** 3 separate Vercel projects from this one repo (Root Directory = `form`,
  `admin-app`, `display-app`; Framework Preset = **Other**).
- **Data:** Firebase Realtime Database (free Spark plan — never sleeps).

No backend server is deployed; the pages load the Firebase SDK from a CDN and connect directly.

## Firebase setup

The database URL is set in each page as `FIREBASE_DB_URL`. To point at a different Firebase
project, create a Realtime Database, set its rules to:

```json
{ "rules": { ".read": true, ".write": true } }
```

…then replace `FIREBASE_DB_URL` in `form/index.html`, `admin-app/index.html`,
`display-app/index.html` with your database URL.

## Data model

A single `state` node holds the day's queue:

```
state = { date, nextId, tokens[], queue[], pending[], currentToken, servedCount, hospitalName }
```

- Registrations and admin actions are **atomic Firebase transactions** (no lost writes).
- Times are stamped in **Dubai time** (Asia/Dubai, UTC+4).
- The queue **auto-resets each new day** (tokens start at 01).

## Local testing

```bash
python3 server.py      # serves the folders on http://localhost:8753
```
Open `/form/`, `/admin-app/`, `/display-app/`. (Local pages still use the live Firebase DB.)

## Features

- Issue types: IT, Outlook Issue, Hardware Issues, Laptop Issues, Other Issues (dropdown)
- International / UAE-friendly phone input
- Optional complaint details → admin **Complaints** tab
- Light theme default; admin always light; TV display always dark
- CSV export, printable report, QR-code generator
- Instant real-time sync (Firebase live listeners)

## Note on security

The Firebase rules are open (`read`/`write` = true) for simplicity. Anyone with the database URL
could read/modify data. Fine for an internal tool; tighten the rules if the data is sensitive.
