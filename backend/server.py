import os
import sys
import json
import uuid
import asyncio
import threading
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobnox import (
    FileOrganizer, TransactionLedger, DeduplicationEngine,
    KernelInotifyDaemon, load_config, save_config, __version__,
    DEFAULT_CONFIG, CONFIG_DIR
)
from backend.models import (
    OrganizeRequest, OrganizeResponse,
    UndoRequest, UndoResponse,
    DedupScanRequest, DedupScanResponse, DuplicateItem,
    ConfigResponse, ConfigUpdateRequest,
    LedgerHistoryResponse, LedgerEntry,
    StatusUpdate,
    DaemonRequest, DaemonResponse,
    DirectoryListing,
)

app = FastAPI(title="boBnox API", version=__version__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

organizer = FileOrganizer()
active_jobs: dict[str, dict] = {}
active_watchers: dict[str, KernelInotifyDaemon] = {}
connected_clients: list[WebSocket] = []


async def broadcast(message: dict):
    dead = []
    for ws in connected_clients:
        try:
            await ws.send_json(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)


def sync_broadcast(message: dict):
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(broadcast(message))
    except RuntimeError:
        asyncio.run(broadcast(message))


@app.get("/api/version")
async def get_version():
    return {"version": __version__}


@app.get("/api/config", response_model=ConfigResponse)
async def get_config():
    config = load_config()
    return ConfigResponse(
        extension_map=config.get("extension_map", DEFAULT_CONFIG["extension_map"]),
        organize_subdirectories=config.get("organize_subdirectories", False),
        create_log_file=config.get("create_log_file", True),
        dark_mode=config.get("dark_mode", True),
    )


@app.put("/api/config")
async def update_config(req: ConfigUpdateRequest):
    config = load_config()
    if req.extension_map is not None:
        config["extension_map"] = req.extension_map
    if req.organize_subdirectories is not None:
        config["organize_subdirectories"] = req.organize_subdirectories
    if req.create_log_file is not None:
        config["create_log_file"] = req.create_log_file
    if req.dark_mode is not None:
        config["dark_mode"] = req.dark_mode
    save_config(config)
    organizer.config = config
    organizer.extension_map = config.get("extension_map", DEFAULT_CONFIG["extension_map"])
    organizer.organize_subdirectories = config.get("organize_subdirectories", False)
    return {"status": "ok"}


@app.post("/api/organize", response_model=OrganizeResponse)
async def start_organize(req: OrganizeRequest):
    if not os.path.isdir(req.path):
        return OrganizeResponse(job_id="", status="error: invalid directory")

    job_id = str(uuid.uuid4())[:8]
    active_jobs[job_id] = {"status": "running", "moved": 0}

    organizer.conflict_resolver.__class__.__init__(
        organizer.conflict_resolver, default_strategy=req.collision_strategy
    )
    organizer.dest_pattern = req.dest_pattern if req.dest_pattern else None
    organizer.organize_subdirectories = req.recursive

    def run_job():
        try:
            def status_cb(msg, pct):
                sync_broadcast({"type": "progress", "message": msg, "progress": pct})
            moved = organizer.organize_directory(
                req.path, status_cb, dry_run=req.dry_run,
                use_mime=req.use_mime, dedup_scan=req.dedup_scan,
                use_entropy=req.use_entropy, include_hidden=req.include_hidden,
            )
            active_jobs[job_id]["status"] = "completed"
            active_jobs[job_id]["moved"] = moved
            sync_broadcast({"type": "complete", "job_id": job_id, "moved": moved})
        except Exception as e:
            active_jobs[job_id]["status"] = f"error: {str(e)}"
            sync_broadcast({"type": "error", "job_id": job_id, "message": str(e)})

    threading.Thread(target=run_job, daemon=True).start()
    return OrganizeResponse(job_id=job_id, status="started")


@app.get("/api/organize/{job_id}")
async def get_job_status(job_id: str):
    job = active_jobs.get(job_id)
    if not job:
        return {"status": "not_found"}
    return {"job_id": job_id, **job}


@app.post("/api/undo", response_model=UndoResponse)
async def undo_operation(req: UndoRequest):
    restored = organizer.ledger.rollback_latest(limit=req.limit)
    return UndoResponse(restored=restored)


@app.post("/api/dedup/scan", response_model=DedupScanResponse)
async def scan_duplicates(req: DedupScanRequest):
    dedup = DeduplicationEngine()
    dups = dedup.scan_directory(req.path)
    items = []
    for d in dups:
        try:
            size = os.path.getsize(d["path"])
        except OSError:
            size = None
        items.append(DuplicateItem(path=d["path"], original=d["original"], hash=d["hash"], size=size))
    return DedupScanResponse(duplicates=items, count=len(items))


@app.get("/api/ledger/history", response_model=LedgerHistoryResponse)
async def get_ledger_history(limit: int = 200, filter: str = ""):
    entries = organizer.ledger.get_history(limit=limit, filter_str=filter)
    return LedgerHistoryResponse(
        entries=[LedgerEntry(**e) for e in entries],
        total=len(entries),
    )


@app.get("/api/ledger/count")
async def get_ledger_count():
    return {"count": organizer.ledger.get_pending_count()}


@app.post("/api/daemon/start", response_model=DaemonResponse)
async def start_daemon(req: DaemonRequest):
    if not os.path.isdir(req.path):
        return DaemonResponse(status="error: invalid path")

    if req.path in active_watchers:
        active_watchers[req.path].stop()

    def on_file(file_path):
        try:
            organizer.organize_single_file(file_path, req.path)
            sync_broadcast({"type": "daemon_event", "message": f"Processed: {os.path.basename(file_path)}"})
        except Exception as e:
            sync_broadcast({"type": "error", "message": f"Daemon error: {str(e)}"})

    watcher = KernelInotifyDaemon(req.path, on_file)
    watcher.start()
    active_watchers[req.path] = watcher
    return DaemonResponse(status="started", path=req.path)


@app.post("/api/daemon/stop")
async def stop_daemon(req: DaemonRequest):
    watcher = active_watchers.pop(req.path, None)
    if watcher:
        watcher.stop()
        return DaemonResponse(status="stopped", path=req.path)
    return DaemonResponse(status="not_found", path=req.path)


@app.get("/api/directory/list")
async def list_directory(path: str = "/"):
    entries = []
    try:
        for item in sorted(Path(path).iterdir()):
            try:
                is_dir = item.is_dir()
                size = None if is_dir else item.stat().st_size
                entries.append(DirectoryListing(
                    path=str(item),
                    name=item.name,
                    is_dir=is_dir,
                    size=size,
                ))
            except (PermissionError, OSError):
                continue
    except (PermissionError, OSError):
        pass
    return {"path": path, "entries": entries}


@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    await websocket.accept()
    connected_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    except Exception:
        if websocket in connected_clients:
            connected_clients.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8420)
