const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Orb control methods
  orbQuery: (text) => ipcRenderer.invoke('orb-query', text),
  orbCursorMove: (x, y) => ipcRenderer.invoke('orb:cursor-move', x, y),
  getOrbStatus: () => ipcRenderer.invoke('orb:get-status'),

  // Window control methods
  minimizeWindow: () => ipcRenderer.invoke('window:minimize'),
  closeWindow: () => ipcRenderer.invoke('window:close'),
  setIgnoreMouseEvents: (ignore, options) => ipcRenderer.invoke('window:set-ignore-mouse-events', ignore, options),

  // Settings
  openSettings: () => ipcRenderer.send('open-settings'),

  // Dashboard
  sendSettings: (settings) => ipcRenderer.send('orb:settings', settings),

  // Event listeners
  onOrbPositionUpdate: (callback) => ipcRenderer.on('orb:position-update', callback),
  onOrbStatusChange: (callback) => ipcRenderer.on('orb:status-change', callback),
  onCognitivePulse: (callback) => ipcRenderer.on('orb:cognitive-pulse', callback),
  onSpeechPulse: (callback) => ipcRenderer.on('orb:speech-pulse', callback),
  onVerbalCommand: (callback) => ipcRenderer.on('orb:verbal-command', callback),
  onSettingsUpdate: (callback) => ipcRenderer.on('update-orb-settings', callback),
  onOpenSettings: (callback) => ipcRenderer.on('open-settings', callback),
  onSpeak: (callback) => ipcRenderer.on('speak', callback)
});