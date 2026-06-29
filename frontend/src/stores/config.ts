import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '../composables/useApi'
import type { Config } from '../types'

export const useConfigStore = defineStore('config', () => {
  const api = useApi()
  const config = ref<Config | null>(null)
  const darkMode = ref(true)

  async function loadConfig() {
    try {
      config.value = await api.getConfig()
      darkMode.value = config.value.dark_mode
      applyTheme()
    } catch { /* ignore */ }
  }

  async function saveConfig(updates: Partial<Config>) {
    try {
      await api.updateConfig(updates)
      if (updates.dark_mode !== undefined) {
        darkMode.value = updates.dark_mode
        applyTheme()
      }
      await loadConfig()
    } catch { /* ignore */ }
  }

  function toggleTheme() {
    const newMode = !darkMode.value
    saveConfig({ dark_mode: newMode })
  }

  function applyTheme() {
    document.documentElement.classList.toggle('dark', darkMode.value)
  }

  return { config, darkMode, loadConfig, saveConfig, toggleTheme }
})
