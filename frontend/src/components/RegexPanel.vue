<script setup lang="ts">
import { computed } from 'vue'
import { useOrganizerStore } from '../stores/organizer'

const store = useOrganizerStore()

const preview = computed(() => {
  if (!store.destPattern) return '—'
  const now = new Date()
  return store.destPattern
    .replace('${creation_date}', now.toISOString().slice(0, 10))
    .replace('${year}', now.getFullYear().toString())
    .replace('${month}', String(now.getMonth() + 1).padStart(2, '0'))
    .replace('${ext}', 'pdf')
    .replace('${filename}', 'invoice_march')
    .replace('//', '/')
})
</script>

<template>
  <div class="card flex flex-col">
    <h3 class="text-sm font-bold mb-2" style="color: var(--muted)">Regex Rename</h3>
    <div class="h-px mb-3" style="background: var(--border)"></div>

    <label class="text-xs mb-1" style="color: var(--muted)">Template</label>
    <input v-model="store.destPattern" class="input mb-2"
      placeholder="${creation_date}/${ext}/" style="font-family: monospace" />

    <p class="text-xs mb-2" style="color: var(--muted)">
      tokens: $&#123;creation_date&#125; $&#123;year&#125; $&#123;month&#125; $&#123;ext&#125; $&#123;filename&#125;
    </p>

    <div class="h-px mb-2" style="background: var(--border)"></div>
    <div class="flex items-center gap-2">
      <span class="text-xs" style="color: var(--muted)">Preview</span>
      <span class="text-xs" style="font-family: monospace">{{ preview }}</span>
    </div>
  </div>
</template>
