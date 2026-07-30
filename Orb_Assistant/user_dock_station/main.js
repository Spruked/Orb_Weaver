const { app, BrowserWindow, ipcMain, Menu, Tray, nativeImage, safeStorage, shell } = require('electron');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { ConfigStore, PROVIDER_TYPES, sanitizeConfig, buildRuntimeProfile } = require('./config');
const { OrbDockControlPlane } = require('./control-plane');

const CONTROL_PLANE_HOST = '127.0.0.1';
const CONTROL_PLANE_PORT = Number(process.env.ORB_DOCK_PORT || 17420);

let mainWindow = null;
let tray = null;
let configStore = null;
let currentConfig = null;
let controlPlane = null;
let controlPlaneAddress = null;
let credentialFile = null;

function createDockIcon() {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
      <defs><radialGradient id="g"><stop offset="0" stop-color="#ffffff"/><stop offset="0.4" stop-color="#9be7ff"/><stop offset="1" stop-color="#6b46ff"/></radialGradient></defs>
      <circle cx="16" cy="16" r="12" fill="url(#g)"/>
      <circle cx="16" cy="16" r="14" fill="none" stroke="#ffffff" stroke-opacity="0.5"/>
    </svg>`;
  return nativeImage.createFromDataURL(`data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`).resize({ width: 16, height: 16 });
}

function ensureToken(tokenPath) {
  try {
    const existing = fs.readFileSync(tokenPath, 'utf8').trim();
    if (existing.length >= 32) return existing;
  } catch {}
  const token = crypto.randomBytes(32).toString('base64url');
  fs.mkdirSync(path.dirname(tokenPath), { recursive: true });
  fs.writeFileSync(tokenPath, `${token}\n`, { encoding: 'utf8', mode: 0o600 });
  return token;
}

function readCredentials() {
  try {
    const parsed = JSON.parse(fs.readFileSync(credentialFile, 'utf8'));
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeCredentials(credentials) {
  fs.mkdirSync(path.dirname(credentialFile), { recursive: true });
  const temporary = `${credentialFile}.tmp`;
  fs.writeFileSync(temporary, `${JSON.stringify(credentials, null, 2)}\n`, { encoding: 'utf8', mode: 0o600 });
  fs.renameSync(temporary, credentialFile);
}

function credentialKey(profileId, slot) {
  return `${profileId}:${slot}`;
}

function storeCredential(profileId, slot, apiKey) {
  if (!['primary', 'fallback'].includes(slot)) throw new Error('Invalid credential slot');
  const value = String(apiKey || '').trim();
  if (!value) throw new Error('API key is required');
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error('Operating-system credential encryption is not available. The API key was not saved.');
  }
  const credentials = readCredentials();
  credentials[credentialKey(profileId, slot)] = safeStorage.encryptString(value).toString('base64');
  writeCredentials(credentials);
}

function clearCredential(profileId, slot) {
  const credentials = readCredentials();
  delete credentials[credentialKey(profileId, slot)];
  writeCredentials(credentials);
}

function credentialStored(profileId, slot) {
  const credentials = readCredentials();
  return Boolean(credentials[credentialKey(profileId, slot)]);
}

function getCredential(profileId, slot) {
  const credentials = readCredentials();
  const encrypted = credentials[credentialKey(profileId, slot)];
  if (!encrypted || !safeStorage.isEncryptionAvailable()) return null;
  try {
    return safeStorage.decryptString(Buffer.from(encrypted, 'base64'));
  } catch {
    return null;
  }
}

function withCredentialFlags(config) {
  const safe = sanitizeConfig(config);
  const profile = safe.profiles[safe.activeProfileId];
  profile.llm.primary.apiKeyStored = credentialStored(safe.activeProfileId, 'primary');
  profile.llm.fallback.apiKeyStored = credentialStored(safe.activeProfileId, 'fallback');
  return safe;
}

function persistConfig(nextConfig) {
  currentConfig = configStore.save(withCredentialFlags(nextConfig));
  currentConfig = withCredentialFlags(currentConfig);
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('dock:config-changed', buildRuntimeProfile(currentConfig));
  }
  refreshTrayMenu();
  return currentConfig;
}

function patchActiveProfile(patch) {
  const safe = withCredentialFlags(currentConfig);
  const profileId = safe.activeProfileId;
  safe.profiles[profileId] = {
    ...safe.profiles[profileId],
    ...patch
  };
  return persistConfig(safe);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1180,
    height: 790,
    minWidth: 980,
    minHeight: 680,
    show: false,
    backgroundColor: '#090b14',
    title: 'ORB Dock Station',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.once('ready-to-show', () => mainWindow.show());
  mainWindow.on('close', (event) => {
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide();
    }
  });
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https://')) shell.openExternal(url);
    return { action: 'deny' };
  });
}

function showWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) createWindow();
  mainWindow.show();
  mainWindow.focus();
}

function refreshTrayMenu() {
  if (!tray || !currentConfig) return;
  const profile = currentConfig.profiles[currentConfig.activeProfileId];
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Open ORB Dock Station', click: showWindow },
    { type: 'separator' },
    {
      label: profile.voice.enabled ? 'Mute every assigned ORB' : 'Unmute every assigned ORB',
      click: () => patchActiveProfile({ voice: { ...profile.voice, enabled: !profile.voice.enabled } })
    },
    {
      label: profile.motion.sleepEnabled ? 'Disable ORB sleep' : 'Enable ORB sleep',
      click: () => patchActiveProfile({ motion: { ...profile.motion, sleepEnabled: !profile.motion.sleepEnabled } })
    },
    { type: 'separator' },
    {
      label: 'Quit Dock Station',
      click: () => {
        app.isQuitting = true;
        app.quit();
      }
    }
  ]));
}

function createTray() {
  tray = new Tray(createDockIcon());
  tray.setToolTip('ORB Dock Station');
  tray.on('double-click', showWindow);
  refreshTrayMenu();
}

function getState() {
  currentConfig = withCredentialFlags(currentConfig);
  return {
    config: currentConfig,
    runtimeProfile: buildRuntimeProfile(currentConfig),
    providers: PROVIDER_TYPES,
    connectedOrbs: controlPlane ? controlPlane.listOrbs() : [],
    controlPlane: controlPlaneAddress,
    encryptionAvailable: safeStorage.isEncryptionAvailable()
  };
}

function registerIpc() {
  ipcMain.handle('dock:get-state', () => getState());

  ipcMain.handle('dock:save-config', (_event, payload) => {
    return { ok: true, state: { ...getState(), config: persistConfig(payload), runtimeProfile: buildRuntimeProfile(currentConfig) } };
  });

  ipcMain.handle('dock:save-credential', (_event, payload) => {
    const profileId = String(payload?.profileId || currentConfig.activeProfileId);
    const slot = String(payload?.slot || 'primary');
    storeCredential(profileId, slot, payload?.apiKey);
    currentConfig = persistConfig(currentConfig);
    return { ok: true, stored: true, state: getState() };
  });

  ipcMain.handle('dock:clear-credential', (_event, payload) => {
    const profileId = String(payload?.profileId || currentConfig.activeProfileId);
    const slot = String(payload?.slot || 'primary');
    clearCredential(profileId, slot);
    currentConfig = persistConfig(currentConfig);
    return { ok: true, stored: false, state: getState() };
  });

  ipcMain.handle('dock:get-runtime-credential', (_event, payload) => {
    const profileId = String(payload?.profileId || currentConfig.activeProfileId);
    const slot = String(payload?.slot || 'primary');
    return { apiKey: getCredential(profileId, slot) };
  });

  ipcMain.handle('dock:refresh-orbs', () => ({ orbs: controlPlane ? controlPlane.listOrbs() : [] }));
  ipcMain.handle('dock:hide', () => mainWindow?.hide());
}

async function startApplication() {
  const userData = app.getPath('userData');
  configStore = new ConfigStore(path.join(userData, 'orb-dock-config.json'));
  credentialFile = path.join(userData, 'orb-dock-credentials.json');
  currentConfig = withCredentialFlags(configStore.load());

  const tokenPath = path.join(userData, 'orb-dock-runtime.token');
  const token = ensureToken(tokenPath);
  controlPlane = new OrbDockControlPlane({
    host: CONTROL_PLANE_HOST,
    port: CONTROL_PLANE_PORT,
    token,
    getRuntimeProfile: () => buildRuntimeProfile(withCredentialFlags(currentConfig)),
    getRuntimeCredential: (slot) => getCredential(currentConfig.activeProfileId, slot)
  });
  controlPlaneAddress = await controlPlane.start();

  registerIpc();
  createWindow();
  createTray();
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', showWindow);
  app.whenReady().then(startApplication).catch((error) => {
    console.error('ORB Dock Station failed to start:', error);
    app.quit();
  });
}

app.on('before-quit', () => {
  app.isQuitting = true;
});

app.on('window-all-closed', () => {
  // The Dock Station remains available from the system tray.
});

app.on('quit', () => {
  controlPlane?.stop().catch(() => {});
});
