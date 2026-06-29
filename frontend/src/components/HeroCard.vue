<script setup lang="ts">
import { useOrganizerStore } from '../stores/organizer'

const store = useOrganizerStore()

async function browseDirectory() {
  // In Electron, this would use the native dialog
  // For browser, we use a simple prompt
  const path = prompt('Enter directory path:', store.targetPath || '/home')
  if (path) store.targetPath = path
}
</script>

<template>
  <div class="card flex items-center gap-6">
    <div class="flex-1">
      <h2 class="text-lg font-bold">boBnox</h2>
      <p class="text-xs mb-3" style="color: var(--muted)">File Organization Engine</p>
      <p class="text-xs mb-2" style="color: var(--accent-green)">
        ● SQLite Ledger · Pending: {{ store.pendingCount }}
      </p>
      <div class="flex gap-2">
        <input v-model="store.targetPath" class="input flex-1" placeholder="Select a folder..." />
        <button class="btn btn-blue" @click="browseDirectory">Browse</button>
      </div>
    </div>

    <div class="w-px h-16" style="background: var(--border)"></div>

    <div class="flex flex-col gap-2 text-sm" style="min-width: 160px">
      <p class="text-xs font-semibold" style="color: var(--muted)">Global Options</p>
      <label class="flex items-center justify-between cursor-pointer">
        <span class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" style="background: var(--accent-blue)"></span>
          Dry Run
        </span>
        <input type="checkbox" v-model="store.dryRun" class="w-4 h-4 accent-blue-500" />
      </label>
      <label class="flex items-center justify-between cursor-pointer">
        <span class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" style="background: var(--accent-orange)"></span>
          Recursive
        </span>
        <input type="checkbox" v-model="store.recursive" class="w-4 h-4 accent-orange-500" />
      </label>
      <label class="flex items-center justify-between cursor-pointer">
        <span class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" style="background: var(--accent-coral)"></span>
          Dedup Scan
        </span>
        <input type="checkbox" v-model="store.dedupScan" class="w-4 h-4 accent-red-500" />
      </label>
    </div>
  </div>
</template>
