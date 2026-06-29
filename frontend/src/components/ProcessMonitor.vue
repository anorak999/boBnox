<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useOrganizerStore } from '../stores/organizer'

const store = useOrganizerStore()
const consoleEl = ref<HTMLElement>()

watch(() => store.logMessages.length, async () => {
  await nextTick()
  if (consoleEl.value) {
    consoleEl.value.scrollTop = consoleEl.value.scrollHeight
  }
})
</script>

<template>
  <div class="card flex flex-col">
    <h3 class="text-sm font-bold mb-2" style="color: var(--muted)">Process Monitor</h3>

    <div class="flex items-center justify-between mb-2">
      <span class="text-sm" :style="{ color: store.isRunning ? '#FFD60A' : 'var(--accent-green)' }">
        {{ store.status }}
      </span>
      <span class="text-sm" style="color: var(--muted)">{{ Math.round(store.progress * 100) }}%</span>
    </div>

    <div class="progress-bar mb-3">
      <div class="progress-bar-fill" :style="{ width: `${store.progress * 100}%` }"></div>
    </div>

    <div ref="consoleEl" class="console flex-1">
      <div v-for="(msg, i) in store.logMessages" :key="i">{{ msg }}</div>
    </div>
  </div>
</template>
