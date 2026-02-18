import { app, BrowserWindow, shell, Menu } from 'electron'
import { spawn, ChildProcess } from 'child_process'
import path from 'path'
import http from 'http'

const BACKEND_PORT = 8420
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null

function startBackend(): ChildProcess {
  const isDev = !app.isPackaged

  if (isDev) {
    // In dev, assume backend is started separately via `npm run dev:backend`
    // or start it here
    const backendDir = path.join(__dirname, '../../backend')
    const proc = spawn('python', ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)], {
      cwd: backendDir,
      stdio: 'pipe',
    })
    proc.stdout?.on('data', (data) => console.log(`[backend] ${data}`))
    proc.stderr?.on('data', (data) => console.error(`[backend] ${data}`))
    return proc
  } else {
    // In production, spawn the bundled backend executable
    const backendPath = path.join(process.resourcesPath, 'backend', 'main.exe')
    const proc = spawn(backendPath, [], { stdio: 'pipe' })
    proc.stdout?.on('data', (data) => console.log(`[backend] ${data}`))
    proc.stderr?.on('data', (data) => console.error(`[backend] ${data}`))
    return proc
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

app.on('window-all-closed', () => {
  // Kill backend process
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
  app.quit()
})

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow()
  }
})
