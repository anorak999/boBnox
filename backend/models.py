from pydantic import BaseModel
from typing import Optional


class OrganizeRequest(BaseModel):
    path: str
    dry_run: bool = False
    recursive: bool = False
    use_mime: bool = False
    dedup_scan: bool = False
    use_entropy: bool = False
    include_hidden: bool = False
    collision_strategy: str = "SMART_RENAME"
    dest_pattern: Optional[str] = None


class OrganizeResponse(BaseModel):
    job_id: str
    status: str


class UndoRequest(BaseModel):
    limit: int = 10


class UndoResponse(BaseModel):
    restored: int


class DedupScanRequest(BaseModel):
    path: str


class DuplicateItem(BaseModel):
    path: str
    original: str
    hash: str
    size: Optional[int] = None


class DedupScanResponse(BaseModel):
    duplicates: list[DuplicateItem]
    count: int


class ConfigResponse(BaseModel):
    extension_map: dict[str, str]
    organize_subdirectories: bool
    create_log_file: bool
    dark_mode: bool


class ConfigUpdateRequest(BaseModel):
    extension_map: Optional[dict[str, str]] = None
    organize_subdirectories: Optional[bool] = None
    create_log_file: Optional[bool] = None
    dark_mode: Optional[bool] = None


class LedgerEntry(BaseModel):
    id: int
    source: str
    dest: str
    timestamp: float
    status: str


class LedgerHistoryResponse(BaseModel):
    entries: list[LedgerEntry]
    total: int


class StatusUpdate(BaseModel):
    type: str
    message: str
    progress: float = 0.0


class DaemonRequest(BaseModel):
    path: str


class DaemonResponse(BaseModel):
    status: str
    path: Optional[str] = None


class DirectoryListing(BaseModel):
    path: str
    name: str
    is_dir: bool
    size: Optional[int] = None
