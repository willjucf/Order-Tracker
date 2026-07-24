import { app, BrowserWindow, shell, Menu } from 'electron'
import { spawn, spawnSync, ChildProcess } from 'child_process'
import path from 'path'
import http from 'http'

const BACKEND_PORT = 8420
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null
let backendKilled = false

function startBackend(): ChildProcess | null {
  const isDev = !app.isPackaged

  if (isDev) {
    // In dev the backend is started separately by `npm run dev:backend`
    // (via concurrently). Don't spawn a second one here — it would fight for
    // port 8420. Just wait for the external one in waitForBackend().
    return null
  }

  // In production, spawn the bundled backend executable.
  const backendPath = path.join(process.resourcesPath, 'backend', 'main.exe')
  const proc = spawn(backendPath, [], { stdio: 'pipe' })
  proc.stdout?.on('data', (data) => console.log(`[backend] ${data}`))
  proc.stderr?.on('data', (data) => console.error(`[backend] ${data}`))
  return proc
}

// Kill the backend and its ENTIRE process tree. `child.kill()` alone only
// signals the direct child; the bundled main.exe spawns its own Python child
// (which runs uvicorn), so a plain kill leaves that grandchild alive and still
// holding port 8420 — the "orphaned backend" that survives the red X. On
// Windows, taskkill /T kills the whole tree, /F forces it. Synchronous so it
// completes before the app process itself exits.
function killBackend() {
  if (backendKilled) return
  backendKilled = true

  const proc = backendProcess
  backendProcess = null
  if (!proc || proc.pid == null) return

  try {
    if (process.platform === 'win32') {
      spawnSync('taskkill', ['/pid', String(proc.pid), '/T', '/F'], { stdio: 'ignore' })
    } else {
      proc.kill('SIGTERM')
    }
  } catch (e) {
    console.error('Failed to kill backend:', e)
  }
}

function waitForBackend(maxRetries = 30): Promise<void> {
  return new Promise((resolve, reject) => {
    let retries = 0

    function check() {
      const req = http.get(`${BACKEND_URL}/api/stats`, (res) => {
        if (res.statusCode === 200) {
          resolve()
        } else {
          retry()
        }
      })
      req.on('error', retry)
      req.setTimeout(1000, retry)
    }

    function retry() {
      retries++
      if (retries >= maxRetries) {
        reject(new Error('Backend failed to start'))
      } else {
        setTimeout(check, 500)
      }
    }

    check()
  })
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1500,
    height: 1000,
    minWidth: 1200,
    minHeight: 800,
    title: 'Order Tracker',
    backgroundColor: '#121212',
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // Open external links in default browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

app.whenReady().then(async () => {
  // Remove the native menu bar (File, Edit, View, etc.)
  Menu.setApplicationMenu(null)

  // Start backend
  backendProcess = startBackend()

  try {
    await waitForBackend()
  } catch (e) {
    console.error('Failed to start backend:', e)
  }

  await createWindow()
})

// Pressing the red X closes the window → window-all-closed fires. Kill the
// backend tree first, then quit.
app.on('window-all-closed', () => {
  killBackend()
  app.quit()
})

// Fires on every quit path (including app.quit() above and OS-initiated quit).
// Belt-and-suspenders so the backend never survives the app.
app.on('before-quit', killBackend)
app.on('will-quit', killBackend)

// If the main process is torn down without a normal quit (e.g. terminated),
// still make a best-effort attempt to take the backend tree down with it.
process.on('exit', killBackend)
process.on('SIGINT', () => {
  killBackend()
  process.exit(0)
})
process.on('SIGTERM', () => {
  killBackend()
  process.exit(0)
})

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow()
  }
})
