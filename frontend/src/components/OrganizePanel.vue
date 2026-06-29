<script setup lang="ts">
import { useOrganizerStore } from '../stores/organizer'

const store = useOrganizerStore()
</script>

<template>
  <div class="card grid grid-cols-2 gap-3">
    <button class="btn btn-primary text-base py-4" @click="store.startOrganize"
      :disabled="store.isRunning">
      ▶ Organize
    </button>
    <button class="btn text-base py-4" @click="store.undoOperation"
      :disabled="store.isRunning || store.pendingCount === 0">
      ⟲ Undo
    </button>
    <button class="btn text-base py-4" @click="store.scanForDuplicates"
      :disabled="!store.targetPath">
      🔍 Dedup Scan
    </button>
    <button class="btn text-base py-4" @click="store.loadLedgerHistory()">
      📋 History
    </button>
  </div>
</template>
