<script setup lang="ts">
import { useOrganizerStore } from '../stores/organizer'

const store = useOrganizerStore()
</script>

<template>
  <div class="card flex flex-col">
    <h3 class="text-sm font-bold mb-2" style="color: var(--muted)">Deduplication Engine</h3>
    <div class="h-px mb-3" style="background: var(--border)"></div>

    <label class="text-xs mb-1" style="color: var(--muted)">Collision Strategy</label>
    <select v-model="store.collisionStrategy" class="input mb-3">
      <option value="SMART_RENAME">SMART_RENAME</option>
      <option value="OVERWRITE">OVERWRITE</option>
      <option value="SKIP">SKIP</option>
    </select>

    <label class="text-xs mb-1" style="color: var(--muted)">Entropy Filter</label>
    <label class="flex items-center gap-2 text-sm cursor-pointer mb-3">
      <input type="checkbox" v-model="store.useEntropy" class="w-4 h-4 accent-blue-500" />
      Skip high-entropy files
    </label>

    <div v-if="store.duplicates.length > 0" class="mt-auto">
      <p class="text-xs font-semibold mb-1" style="color: var(--muted)">
        {{ store.duplicates.length }} duplicates found
      </p>
      <div class="max-h-32 overflow-y-auto text-xs" style="color: var(--muted)">
        <div v-for="dup in store.duplicates.slice(0, 10)" :key="dup.path" class="py-1 border-b" style="border-color: var(--border)">
          {{ dup.path.split('/').pop() }} ← {{ dup.original.split('/').pop() }}
        </div>
      </div>
    </div>
  </div>
</template>
