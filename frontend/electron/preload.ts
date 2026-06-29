import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('bobnox', {
  openDirectoryDialog: () => ipcRenderer.invoke('open-directory-dialog'),
  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),
})
