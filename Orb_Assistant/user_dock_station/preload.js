const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('orbDock', {
  getState: () => ipcRenderer.invoke('dock:get-state'),
  saveConfig: (config) => ipcRenderer.invoke('dock:save-config', config),
  saveCredential: (payload) => ipcRenderer.invoke('dock:save-credential', payload),
  clearCredential: (payload) => ipcRenderer.invoke('dock:clear-credential', payload),
  refreshOrbs: () => ipcRenderer.invoke('dock:refresh-orbs'),
  hide: () => ipcRenderer.invoke('dock:hide'),
  onConfigChanged: (handler) => {
    if (typeof handler !== 'function') return () => {};
    const listener = (_event, profile) => handler(profile);
    ipcRenderer.on('dock:config-changed', listener);
    return () => ipcRenderer.removeListener('dock:config-changed', listener);
  }
});
