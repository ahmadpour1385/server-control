# Server Control

A local web panel for managing Linux and Windows servers from a single page.
It runs on your own computer and talks to the servers live over SSH and
PowerShell Remoting. No database, no job queue.

## Features

- **Servers**: add, edit and delete servers; SSH host-key pinning on first connect
- **Live monitoring**: uptime, RAM, CPU and disk usage refreshed every 3 seconds, with live
  CPU and RAM charts for the last ~5 minutes (Linux over SSH, Windows over PowerShell Remoting / WinRM)
- **Web terminal**: full interactive shell in the browser (xterm.js + WebSocket) for Linux servers
- **File manager**: browse, upload, download, create folders and delete over SFTP (Linux)
- **Project manager**: start, stop, update and read logs of processes on a remote server (Linux)
- **DNS tools**: a read-only record viewer, and a helper that connects a subdomain to a server.
  It shows the exact record to create, verifies it directly on the authoritative name servers
  and checks the server's ports. Main domain, `www`, `mail` and similar names are locked.
- **Security**: panel login, optional encrypted storage of server passwords
- **Offline frontend**: Tailwind, HTMX and xterm.js are vendored, so the panel works without internet

## How it works

- The UI is server-rendered HTML; HTMX swaps small fragments, so there is no JavaScript framework.
- SSH connections are pooled in memory, one per server.
- Terminal: browser, WebSocket (Django Channels consumer), Paramiko shell.
- Projects run detached on the server (`setsid`) with a PID file and a log file, so they survive the SSH session.
- Monitoring samples are kept in an in-memory ring buffer and drawn as server-side SVG.

## Tech stack

| Area | Technology |
|---|---|
| Backend | Python, Django (ASGI via Daphne), Channels |
| UI | HTMX, Tailwind CSS |
| Linux access | Paramiko (SSH, SFTP) |
| Windows access | pypsrp (PowerShell Remoting) |
| Terminal | xterm.js over WebSocket |
| DNS | dnspython |
| Crypto | cryptography (Fernet), PBKDF2 |
| Storage | a local JSON file (`panel_data/settings.json`) |

## Quick start (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py runserver 127.0.0.1:8765 --noreload
```

Or just double-click `run.bat`.

Open http://127.0.0.1:8765/. On the first visit you will be asked to create a panel password.

## Security model

- The panel is meant to run **only on your own machine** and listens on `127.0.0.1`. Do not expose it to a network.
- The panel password is stored as a salted PBKDF2-SHA256 hash. Login sessions are signed cookies,
  valid for 8 hours and invalidated on every restart. Five failed logins lock the login for 5 minutes.
- Server passwords are kept in memory by default. If you tick "save", they are encrypted with a key
  derived from the panel password; that key only exists in memory while the panel is running.
- SSH host keys are pinned on first connect. A changed key blocks the connection until you reset it.
- `panel_data/` (settings, hashes, encrypted secrets, Django secret key) is git-ignored. Never commit it.
- The DNS helper never changes DNS. Automatic editing was left out on purpose, because hosting
  control-panel API tokens can grant broad access to the whole account.
- WinRM is used over HTTP with NTLM, which is fine for localhost or a trusted network.
  For real servers, prefer a dedicated admin user and HTTPS.

## Project structure

```
servercontrol/
├── manage.py
├── run.bat
├── requirements.txt
├── config/            # Django settings, URLs, login middleware
├── apps/
│   ├── servers/       # server list, edit, host-key pinning
│   ├── monitor/       # live stats and charts (SSH / WinRM)
│   ├── terminal/      # web terminal (WebSocket consumer)
│   ├── files/         # SFTP file manager
│   ├── projects/      # start/stop/update remote processes
│   └── dns/           # DNS viewer and subdomain helper
├── services/          # SSH, PowerShell Remoting, auth/crypto, history, DNS checks, JSON store
├── templates/
├── static/vendor/     # Tailwind, HTMX, xterm.js (offline)
└── panel_data/        # settings and secrets (git-ignored)
```

## Limitations and roadmap

- Terminal, file manager and project manager currently support Linux servers only.
- Monitoring history lives in memory and resets when the panel restarts.
- No automated tests yet.