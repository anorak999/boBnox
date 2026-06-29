const BASE_URL = 'http://127.0.0.1:8420'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json()
}

export function useApi() {
  return {
    getVersion: () => request<{ version: string }>('/api/version'),

    getConfig: () => request<import('../types').Config>('/api/config'),

    updateConfig: (config: Partial<import('../types').Config>) =>
      request<{ status: string }>('/api/config', {
        method: 'PUT',
        body: JSON.stringify(config),
      }),

    startOrganize: (req: import('../types').OrganizeRequest) =>
      request<import('../types').OrganizeResponse>('/api/organize', {
        method: 'POST',
        body: JSON.stringify(req),
      }),

    getJobStatus: (jobId: string) =>
      request<import('../types').JobStatus>(`/api/organize/${jobId}`),

    undo: (limit: number = 10) =>
      request<import('../types').UndoResponse>('/api/undo', {
        method: 'POST',
        body: JSON.stringify({ limit }),
      }),

    scanDuplicates: (path: string) =>
      request<import('../types').DedupScanResponse>('/api/dedup/scan', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),

    getLedgerHistory: (limit = 200, filter = '') =>
      request<import('../types').LedgerHistoryResponse>(
        `/api/ledger/history?limit=${limit}&filter=${encodeURIComponent(filter)}`
      ),

    getLedgerCount: () =>
      request<{ count: number }>('/api/ledger/count'),

    startDaemon: (path: string) =>
      request<{ status: string; path: string }>('/api/daemon/start', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),

    stopDaemon: (path: string) =>
      request<{ status: string }>('/api/daemon/stop', {
        method: 'POST',
        body: JSON.stringify({ path }),
      }),

    listDirectory: (path: string = '/') =>
      request<import('../types').DirectoryResponse>(`/api/directory/list?path=${encodeURIComponent(path)}`),
  }
}
