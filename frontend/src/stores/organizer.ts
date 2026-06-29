import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useApi } from '../composables/useApi'
import type { DuplicateItem, LedgerEntry } from '../types'

export const useOrganizerStore = defineStore('organizer', () => {
  const api = useApi()

  const targetPath = ref('')
  const isRunning = ref(false)
  const dryRun = ref(false)
  const recursive = ref(false)
  const useMime = ref(false)
  const dedupScan = ref(false)
  const useEntropy = ref(false)
  const includeHidden = ref(false)
  const collisionStrategy = ref('SMART_RENAME')
  const destPattern = ref('')

  const status = ref('System Ready')
  const progress = ref(0)
  const logMessages = ref<string[]>([])
  const pendingCount = ref(0)

  const duplicates = ref<DuplicateItem[]>([])
  const ledgerEntries = ref<LedgerEntry[]>([])

  const daemonActive = ref(false)
  const daemonPath = ref('')

  function addLog(msg: string) {
    logMessages.value.push(msg)
    if (logMessages.value.length > 500) {
      logMessages.value = logMessages.value.slice(-500)
    }
  }

  async function startOrganize() {
    if (!targetPath.value || isRunning.value) return
    isRunning.value = true
    status.value = 'Processing...'
    progress.value = 0

    try {
      const res = await api.startOrganize({
        path: targetPath.value,
        dry_run: dryRun.value,
        recursive: recursive.value,
        use_mime: useMime.value,
        dedup_scan: dedupScan.value,
        use_entropy: useEntropy.value,
        include_hidden: includeHidden.value,
        collision_strategy: collisionStrategy.value,
        dest_pattern: destPattern.value || null,
      })
      addLog(`[INFO] Job started: ${res.job_id}`)
    } catch (e: any) {
      addLog(`[ERROR] ${e.message}`)
      status.value = 'Error'
    }
  }

  function handleStatusUpdate(msg: any) {
    if (msg.type === 'progress') {
      status.value = msg.message
      progress.value = msg.progress
      addLog(`  ${msg.message}`)
    } else if (msg.type === 'complete') {
      status.value = `Done! Moved ${msg.moved} files.`
      progress.value = 1
      isRunning.value = false
      addLog(`\n[DONE] Moved ${msg.moved} files.`)
      refreshLedgerCount()
    } else if (msg.type === 'error') {
      status.value = 'Error'
      isRunning.value = false
      addLog(`[ERROR] ${msg.message}`)
    } else if (msg.type === 'daemon_event') {
      addLog(`[DAEMON] ${msg.message}`)
    }
  }

  async function undoOperation() {
    if (isRunning.value) return
    isRunning.value = true
    status.value = 'Undoing...'
    try {
      const res = await api.undo()
      addLog(`\n[DONE] Restored ${res.restored} files.`)
      status.value = 'System Ready'
      await refreshLedgerCount()
    } catch (e: any) {
      addLog(`[ERROR] Undo failed: ${e.message}`)
    } finally {
      isRunning.value = false
    }
  }

  async function scanForDuplicates() {
    if (!targetPath.value) return
    try {
      const res = await api.scanDuplicates(targetPath.value)
      duplicates.value = res.duplicates
      addLog(`[DEDUP] Found ${res.count} duplicates.`)
    } catch (e: any) {
      addLog(`[ERROR] Dedup scan failed: ${e.message}`)
    }
  }

  async function refreshLedgerCount() {
    try {
      const res = await api.getLedgerCount()
      pendingCount.value = res.count
    } catch { /* ignore */ }
  }

  async function loadLedgerHistory(filter = '') {
    try {
      const res = await api.getLedgerHistory(200, filter)
      ledgerEntries.value = res.entries
    } catch { /* ignore */ }
  }

  async function toggleDaemon() {
    if (!targetPath.value) return
    try {
      if (daemonActive.value) {
        await api.stopDaemon(targetPath.value)
        daemonActive.value = false
        addLog('[DAEMON] Stopped.')
      } else {
        await api.startDaemon(targetPath.value)
        daemonActive.value = true
        daemonPath.value = targetPath.value
        addLog(`[DAEMON] Watching: ${targetPath.value}`)
      }
    } catch (e: any) {
      addLog(`[ERROR] Daemon: ${e.message}`)
    }
  }

  return {
    targetPath, isRunning, dryRun, recursive, useMime, dedupScan,
    useEntropy, includeHidden, collisionStrategy, destPattern,
    status, progress, logMessages, pendingCount,
    duplicates, ledgerEntries,
    daemonActive, daemonPath,
    addLog, startOrganize, handleStatusUpdate, undoOperation,
    scanForDuplicates, refreshLedgerCount, loadLedgerHistory, toggleDaemon,
  }
})
