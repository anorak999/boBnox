<script setup lang="ts">
import { onMounted } from 'vue'
import { useOrganizerStore } from './stores/organizer'
import { useConfigStore } from './stores/config'
import { useWebSocket } from './composables/useWebSocket'

import Sidebar from './components/Sidebar.vue'
import HeroCard from './components/HeroCard.vue'
import DedupPanel from './components/DedupPanel.vue'
import RegexPanel from './components/RegexPanel.vue'
import OrganizePanel from './components/OrganizePanel.vue'
import ProcessMonitor from './components/ProcessMonitor.vue'
import LedgerHistory from './components/LedgerHistory.vue'

const store = useOrganizerStore()
const configStore = useConfigStore()

const { connect } = useWebSocket((msg) => {
  store.handleStatusUpdate(msg)
})

onMounted(async () => {
  await configStore.loadConfig()
  await store.refreshLedgerCount()
  connect()
})
</script>

<template>
  <div class="flex h-screen" style="background: var(--bg)">
    <Sidebar />

    <main class="flex-1 p-3 flex flex-col gap-3 overflow-auto">
      <HeroCard />

      <div class="grid grid-cols-2 gap-3 flex-1">
        <DedupPanel />
        <RegexPanel />
      </div>

      <div class="grid grid-cols-2 gap-3">
        <OrganizePanel />
        <ProcessMonitor />
      </div>
    </main>

    <LedgerHistory />
  </div>
</template>
