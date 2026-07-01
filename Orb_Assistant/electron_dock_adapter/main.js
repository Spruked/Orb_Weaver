const { app, BrowserWindow, ipcMain, screen, Menu, MenuItem } = require('electron');
const path = require('path');
const { OrbBridge } = require('./orb-bridge');

// CPU-only mode: Disable GPU acceleration since no dedicated GPU is available.
app.disableHardwareAcceleration();

// Fix cache location permissions on Windows
// Note: In sandboxed environments, writing to the user profile can be denied.
// Keep Electron's userData/cache under the app directory (workspace-writable).
const userDataPath = path.resolve(__dirname, '..', '.orb-assistant');
app.setPath('userData', userDataPath);
app.setPath('cache', path.join(userDataPath, 'Cache'));

app.commandLine.appendSwitch('user-data-dir', userDataPath);
app.commandLine.appendSwitch('disk-cache-dir', path.join(userDataPath, 'Cache'));

app.commandLine.appendSwitch('no-sandbox');
app.commandLine.appendSwitch('disable-gpu');
app.commandLine.appendSwitch('disable-gpu-compositing');
app.commandLine.appendSwitch('disable-software-rasterizer');
app.commandLine.appendSwitch('in-process-gpu');
// In restricted Windows environments, Chromium's network service sandbox may fail
// to apply directory ACLs and crash at startup.
app.commandLine.appendSwitch('disable-features', 'NetworkServiceSandbox,WinSbox');

let orbBridge;
let mainWindow;
let settingsWindow = null;

async function createWindow() {
  const disablePythonBridge = process.env.ORB_DISABLE_PYTHON_BRIDGE === '1';

  if (!disablePythonBridge) {
    orbBridge = new OrbBridge();
    try {
      await orbBridge.start();
      console.log('✓ Orb started via Electron');
    } catch (err) {
      console.error('Failed to start orb:', err);
      app.quit();
      return;
    }
  } else {
    orbBridge = null;
    console.log('ℹ Python bridge disabled (ORB_DISABLE_PYTHON_BRIDGE=1)');
  }

  const displays = screen.getAllDisplays();
  const bounds = displays.map((display) => display.bounds);
  const minX = Math.min(...bounds.map((b) => b.x));
  const minY = Math.min(...bounds.map((b) => b.y));
  const maxX = Math.max(...bounds.map((b) => b.x + b.width));
  const maxY = Math.max(...bounds.map((b) => b.y + b.height));
  const width = maxX - minX;
  const height = maxY - minY;

  mainWindow = new BrowserWindow({
    width: width,
    height: height,
    x: minX,
    y: minY,
    frame: false,
    show: true,
    transparent: true,
    backgroundColor: '#00000000', // IMPORTANT: Force transparency
    alwaysOnTop: true,
    skipTaskbar: true,
    focusable: true, // Allow interaction for now
    resizable: false,
    movable: false,
    level: 'screen-saver', // Higher priority for staying on top
    hasShadow: false, // Ensure no shadow on transparent window
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Context menu for orb adjustments
  mainWindow.webContents.on('context-menu', (event, params) => {
    const menu = new Menu();
    menu.append(new MenuItem({
      label: 'Open Settings',
      click: () => ipcMain.emit('open-settings')
    }));
    menu.append(new MenuItem({
      label: 'Speak Status',
      click: () => mainWindow.webContents.send('speak-status')
    }));
    menu.popup();
  });

  ipcMain.handle('window:set-ignore-mouse-events', (event, ignore, options) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    win.setIgnoreMouseEvents(ignore, options);
  });

  // Settings window
  ipcMain.on('open-settings', () => {
    if (settingsWindow) {
      settingsWindow.focus();
      return;
    }

    settingsWindow = new BrowserWindow({
      width: 400,
      height: 350,
      parent: mainWindow,
      modal: true,
      show: false,
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false
      }
    });

    settingsWindow.loadFile(path.join(__dirname, '..', 'src', 'settings.html'));

    settingsWindow.once('ready-to-show', () => {
      settingsWindow.show();
    });

    settingsWindow.on('closed', () => {
      settingsWindow = null;
    });
  });

  ipcMain.on('apply-settings', (event, settings) => {
    // Send settings to main window
    mainWindow.webContents.send('update-orb-settings', settings);
  });

  // Context menu for orb adjustments
  mainWindow.webContents.on('context-menu', (event, params) => {
    const menu = new Menu();
    menu.append(new MenuItem({ label: 'Open Dashboard', click: () => openDashboard() }));
    menu.append(new MenuItem({ label: 'Speak Status', click: () => speakStatus() }));
    menu.popup();
  });

  if (orbBridge) {
    orbBridge.onMessage((message) => {
      if (message.type === 'cognitive_pulse') {
        mainWindow.webContents.send('orb:cognitive-pulse', message.data);
      } else if (message.type === 'speech_pulse') {
        mainWindow.webContents.send('orb:speech-pulse', message.data, message.transcription);
      } else if (message.type === 'verbal_command') {
        mainWindow.webContents.send('orb:verbal-command', message.command, message.color || null);
      }
    });
  }

  ipcMain.handle('orb:cursor-move', async (_event, x, y) => {
    if (!orbBridge) return;
    orbBridge.sendMessage({ type: 'cursor_move', x, y });
  });

  ipcMain.handle('orb:get-status', async () => {
    if (!orbBridge) {
      return { running: false, controller_status: 'disabled' };
    }
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('Status timeout')), 5000);

      const handler = (response) => {
        if (response && response.type === 'status_response') {
          clearTimeout(timeout);
          orbBridge.removeMessageHandler(handler);
          resolve(response.data);
        }
      };

      orbBridge.onMessage(handler);
      orbBridge.sendMessage({ type: 'get_status' });
    });
  });

  mainWindow.on('closed', () => {
    if (orbBridge) {
      orbBridge.stop();
    }
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'src', 'index.html'));

  // Ensure window stays on top
  setInterval(() => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.setAlwaysOnTop(true);
    }
  }, 1000);
}

function openDashboard() {
  const dashboardWindow = new BrowserWindow({
    width: 400,
    height: 300,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });
  dashboardWindow.loadFile(path.join(__dirname, 'src', 'dashboard.html'));
  dashboardWindow.once('ready-to-show', () => {
    dashboardWindow.show();
  });
}

function speakStatus() {
  mainWindow.webContents.send('speak', 'Orb status: Active and tracking.');
}

ipcMain.on('orb:settings', (event, settings) => {
  mainWindow.webContents.send('orb:settings', settings);
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (orbBridge) {
    orbBridge.stop();
  }
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
