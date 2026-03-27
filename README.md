# Order Tracker v1.2.2

Desktop app that scans your email for Walmart and Target orders and tracks status, spending, and item stick rates.

## Requirements

- [Node.js](https://nodejs.org) 18+
- [Python](https://python.org) 3.10+

## Run in Dev Mode

```
npm install
pip install -r backend/requirements.txt
npm run dev
```

## Build the Installer

Double-click **`build.bat`** — it handles everything automatically and produces:

```
release/Order Tracker Setup 1.2.2.exe
```

Or run it from the terminal:

```
build.bat
```

## What the Installer Does

The setup `.exe` is a standard Windows installer. When you run it:

1. Asks where to install (defaults to `C:\Users\YourName\AppData\Local\Programs\Order Tracker`)
2. Installs all app files — no Python or Node.js needed on the target machine
3. Creates a **Start Menu shortcut** and optionally a **Desktop shortcut**
4. Adds an entry to **Add/Remove Programs** so you can uninstall it normally

The app is fully self-contained — everything is bundled inside the installer. Users just run the setup, open Order Tracker, and go.

## Troubleshooting

| Error | Fix |
|-------|-----|
| "python is not recognized" | Reinstall Python and check **"Add Python to PATH"** during install |
| Windows blocks the downloaded file | Right-click the file > Properties > check **Unblock** at the bottom > OK |
| Port 8420 already in use | Close other Order Tracker instances or run `taskkill /F /IM main.exe` |
| "running scripts is disabled on this system" | Run once in PowerShell: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| App opens but shows blank screen | Backend is still starting — wait a few seconds |
| "Cannot create symbolic link" during build | Enable Developer Mode: Settings > System > For Developers > ON |

## Data Storage

All data stored in `%APPDATA%/WalmartOrderTracker/` (database, settings, backgrounds).
