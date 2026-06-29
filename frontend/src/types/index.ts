export interface OrganizeRequest {
  path: string
  dry_run: boolean
  recursive: boolean
  use_mime: boolean
  dedup_scan: boolean
  use_entropy: boolean
  include_hidden: boolean
  collision_strategy: string
  dest_pattern: string | null
}

export interface OrganizeResponse {
  job_id: string
  status: string
}

export interface JobStatus {
  job_id: string
  status: string
  moved?: number
}

export interface UndoResponse {
  restored: number
}

export interface DuplicateItem {
  path: string
  original: string
  hash: string
  size: number | null
}

export interface DedupScanResponse {
  duplicates: DuplicateItem[]
  count: number
}

export interface Config {
  extension_map: Record<string, string>
  organize_subdirectories: boolean
  create_log_file: boolean
  dark_mode: boolean
}

export interface LedgerEntry {
  id: number
  source: string
  dest: string
  timestamp: number
  status: string
}

export interface LedgerHistoryResponse {
  entries: LedgerEntry[]
  total: number
}

export interface StatusUpdate {
  type: string
  message: string
  progress: number
}

export interface DirectoryListing {
  path: string
  name: string
  is_dir: boolean
  size: number | null
}

export interface DirectoryResponse {
  path: string
  entries: DirectoryListing[]
}
