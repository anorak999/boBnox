const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')

let mainWindow = null
let backendProcess = null
const BACKEND_PORT = 8420
const BOBNOX_DIR = path.resolve(__dirname, '..')
const FRONTEND_DIR = path.join(BOBNOX_DIR, 'dist')

function startBackend() {
  backendProcess = spawn('python3', ['-m', 'backend.server'], {
    cwd: BOBNOX_DIR,
    stdio: 'pipe',
    env: { ...process.env, PYTHONPATH: BOBNOX_DIR },
  })

  backendProcess.stdout.on('data', (d) => console.log(`[backend] ${d.toString().trim()}`))
  backendProcess.stderr.on('data', (d) => console.error(`[backend] ${d.toString().trim()}`))
  backendProcess.on('close', (code) => console.log(`[backend] exited ${code}`))
}

function waitForBackend(callback, retries = 20) {
  http.get(`http://127.0.0.1:${BACKEND_PORT}/api/version`, (res) => {
    callback()
  }).on('error', () => {
    if (retries > 0) {
      setTimeout(() => waitForBackend(callback, retries - 1), 500)
    } else {
      callback()
    }
  })
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 820,
    minWidth: 960,
    minHeight: 680,
    title: 'BoBnox',
    icon: path.join(BOBNOX_DIR, 'BoBnox-icon', 'Bobnox-icon.png'),
    backgroundColor: '#161618',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  const indexPath = path.join(FRONTEND_DIR, 'index.html')
  mainWindow.loadFile(indexPath)

  mainWindow.on('closed', () => { mainWindow = null })
}

ipcMain.handle('open-directory-dialog', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Select Target Directory',
  })
  return result.canceled ? null : result.filePaths[0]
})

ipcMain.handle('get-backend-port', () => BACKEND_PORT)

app.whenReady().then(() => {
  startBackend()
  waitForBackend(createWindow)
})

app.on('window-all-closed', () => {
  if (backendProcess) backendProcess.kill()
  app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})
