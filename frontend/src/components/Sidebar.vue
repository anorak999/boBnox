<script setup lang="ts">
import { useOrganizerStore } from '../stores/organizer'
import { useConfigStore } from '../stores/config'

const store = useOrganizerStore()
const configStore = useConfigStore()
</script>

<template>
  <aside class="w-64 flex-shrink-0 p-3 flex flex-col gap-3">
    <div class="card">
      <h1 class="text-xl font-bold">boBnox</h1>
      <p class="text-xs mt-1" style="color: var(--muted)">v5.0.0</p>
    </div>

    <div class="card flex flex-col gap-3">
      <button class="btn w-full text-left text-sm" @click="configStore.toggleTheme">
        {{ configStore.darkMode ? '☀️ Light Mode' : '🌙 Dark Mode' }}
      </button>

      <div class="border-t pt-3" style="border-color: var(--border)">
        <p class="text-xs font-semibold mb-2" style="color: var(--muted)">Engine</p>
        <label class="flex items-center justify-between text-sm cursor-pointer">
          <span>⟲ Daemon</span>
          <input type="checkbox" v-model="store.daemonActive" @change="store.toggleDaemon"
            class="w-4 h-4 accent-green-500" />
        </label>
        <label class="flex items-center justify-between text-sm cursor-pointer mt-1">
          <span>⎔ MIME Sort</span>
          <input type="checkbox" v-model="store.useMime" class="w-4 h-4 accent-blue-500" />
        </label>
      </div>

      <div class="border-t pt-3" style="border-color: var(--border)">
        <p class="text-xs font-semibold mb-1" style="color: var(--muted)">Ledger</p>
        <p class="text-sm" style="color: var(--accent-green)">
          Pending: {{ store.pendingCount }}
        </p>
      </div>

      <div class="border-t pt-3" style="border-color: var(--border)">
        <p class="text-xs font-semibold mb-2" style="color: var(--muted)">Logging</p>
        <label class="flex items-center justify-between text-sm cursor-pointer">
          <span>Verbose output</span>
          <input type="checkbox" v-model="store.includeHidden" class="w-4 h-4" />
        </label>
      </div>
    </div>
  </aside>
</template>
