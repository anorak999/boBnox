<script setup lang="ts">
import { ref } from 'vue'
import { useOrganizerStore } from '../stores/organizer'

const store = useOrganizerStore()
const filter = ref('')
const show = ref(false)

function load() {
  store.loadLedgerHistory(filter.value)
}

function formatTime(ts: number) {
  return new Date(ts * 1000).toLocaleString()
}
</script>

<template>
  <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center" style="background: rgba(0,0,0,0.5)">
    <div class="card w-[700px] max-h-[500px] flex flex-col">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-bold">Operation History</h3>
        <button class="btn text-xs" @click="show = false">Close</button>
      </div>

      <div class="flex gap-2 mb-3">
        <input v-model="filter" class="input flex-1" placeholder="Filter by filename..." @input="load" />
        <button class="btn btn-blue text-xs" @click="load">Refresh</button>
      </div>

      <div class="flex-1 overflow-y-auto">
        <table class="w-full text-xs">
          <thead>
            <tr style="color: var(--muted)">
              <th class="text-left py-1">Timestamp</th>
              <th class="text-left py-1">Source</th>
              <th class="text-left py-1">Destination</th>
              <th class="text-left py-1">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="entry in store.ledgerEntries" :key="entry.id" class="border-t" style="border-color: var(--border)">
              <td class="py-1">{{ formatTime(entry.timestamp) }}</td>
              <td class="py-1">{{ entry.source.split('/').pop() }}</td>
              <td class="py-1">{{ entry.dest.split('/').pop() }}</td>
              <td class="py-1" :style="{ color: entry.status === 'COMPLETED' ? 'var(--accent-green)' : 'var(--accent-orange)' }">
                {{ entry.status }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <button v-if="!show" class="hidden" @click="show = true; load()"></button>
</template>
