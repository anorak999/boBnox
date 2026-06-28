import os
import sys
import shutil
import subprocess
import platform
import json
import re
import hashlib
import sqlite3
import time
import stat
import math
import struct
import collections
import logging
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import font as tkfont
import customtkinter as ctk

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

try:
    from inotify_simple import INotify, flags as inotify_flags
    HAS_INOTIFY = True
except ImportError:
    HAS_INOTIFY = False

IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# Fix rendering artifacts on Linux by forcing circle shapes
if IS_LINUX:
    try:
        ctk.CTkDrawEngine.preferred_drawing_method = "circle_shapes"
    except Exception:
        pass

# ======================================================================
# DESIGN TOKENS - Unified Bento styling constants
# ======================================================================
APP_RADIUS = 16
CARD_RADIUS = 12
BTN_RADIUS = 8
INPUT_RADIUS = 6

BG_DARK = "#161618"
BG_LIGHT = "#F5F5F7"
CARD_DARK = "#242426"
CARD_LIGHT = "#FFFFFF"

TEXT_DARK = "#F5F5F7"
TEXT_LIGHT = "#1D1D1F"
MUTED_DARK = "#98989D"
MUTED_LIGHT = "#6E6E73"
BORDER_DARK = "#2C2C2E"
BORDER_LIGHT = "#E5E5EA"
ENTRY_DARK = "#2C2C2E"
ENTRY_LIGHT = "#F2F2F7"
BTN_DARK = "#2C2C2E"
BTN_LIGHT = "#F2F2F7"
BTN_HOVER_DARK = "#3A3A3C"
BTN_HOVER_LIGHT = "#E5E5EA"

ACCENT_BLUE = "#007AFF"
ACCENT_GREEN = "#34C759"
ACCENT_CORAL = "#FF3B30"
ACCENT_ORANGE = "#FF9500"

# --- Logging ---
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("bobnox")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger

logger = setup_logging()

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEIST_STATIC = os.path.join(SCRIPT_DIR, "Geist", "static")
ICON_SOURCE = os.path.join(SCRIPT_DIR, "BoBnox-icon", "Bobnox-icon.png")
ICON_APP = os.path.expanduser("~/.local/share/bobnox/icon.png")
ICON_SYSTEM = os.path.expanduser("~/.local/share/icons/bobnox.png")
SVG_PATH = os.path.join(SCRIPT_DIR, "assets", "Sort--Streamline-Solar.svg")

FONT_FILES = {
    "Geist": os.path.join(GEIST_STATIC, "Geist-Regular.ttf"),
    "Geist-Medium": os.path.join(GEIST_STATIC, "Geist-Medium.ttf"),
    "Geist-Bold": os.path.join(GEIST_STATIC, "Geist-Bold.ttf"),
    "Geist-SemiBold": os.path.join(GEIST_STATIC, "Geist-SemiBold.ttf"),
}

def install_geist_fonts():
    installed = 0
    local_dir = Path.home() / ".local" / "share" / "fonts" / "Geist"
    local_dir.mkdir(parents=True, exist_ok=True)
    for name, path in FONT_FILES.items():
        if os.path.exists(path):
            dest = local_dir / os.path.basename(path)
            if not dest.exists():
                try:
                    shutil.copy2(path, dest)
                    installed += 1
                except Exception:
                    pass
    if installed > 0:
        try:
            subprocess.run(["fc-cache", "-f"], capture_output=True, timeout=15)
        except Exception:
            pass
    return installed > 0

def geist_available():
    try:
        f = tkfont.Font(family="Geist", size=12)
        return "geist" in f.actual("family").lower()
    except Exception:
        return False

def ensure_icons_installed():
    for dest_path in [ICON_APP, ICON_SYSTEM]:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(ICON_SOURCE) and not dest.exists():
            try:
                shutil.copy2(ICON_SOURCE, dest)
            except Exception:
                pass
    try:
        subprocess.run(["gtk-update-icon-cache", "-f", os.path.expanduser("~/.local/share/icons/")], capture_output=True, timeout=10)
        subprocess.run(["update-desktop-database", os.path.expanduser("~/.local/share/applications/")], capture_output=True, timeout=10)
    except Exception:
        pass

# --- File Manager ---
def open_in_nautilus(path: str):
    try:
        subprocess.Popen(["nautilus", path])
    except FileNotFoundError:
        try:
            subprocess.Popen(["xdg-open", path])
        except FileNotFoundError:
            pass


# ======================================================================
# FEATURE 1: Async I/O File Processing Engine
# ======================================================================
class AsyncFileProcessor:
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def _blocking_move(self, src: str, dest: str) -> bool:
        try:
            shutil.move(src, dest)
            return True
        except Exception as e:
            logger.error(f"Move failed: {src} -> {e}")
            return False

    async def process_transfer(self, src: str, dest: str) -> bool:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self.executor, self._blocking_move, src, dest)

    async def bulk_move(self, file_mapping: dict) -> list:
        tasks = [self.process_transfer(src, dest) for src, dest in file_mapping.items()]
        return await asyncio.gather(*tasks)


# ======================================================================
# FEATURE 2: Magic-Number MIME Content Verification
# ======================================================================
class MimeValidator:
    def __init__(self):
        self.mime_analyzer = magic.Magic(mime=True) if HAS_MAGIC else None

    def resolve_true_type(self, file_path: str) -> Optional[str]:
        if not self.mime_analyzer or not os.path.exists(file_path):
            return None
        try:
            return self.mime_analyzer.from_file(file_path)
        except Exception:
            return None

    def route_by_mime(self, file_path: str) -> str:
        mime_type = self.resolve_true_type(file_path)
        if not mime_type:
            return "Other Files"
        main_type = mime_type.split('/')[0]
        sub_type = mime_type.split('/')[-1] if '/' in mime_type else ""

        # Specific MIME type overrides
        if sub_type in ("zip", "x-zip-compressed", "x-7z-compressed", "x-rar-compressed", "x-tar", "x-gzip", "x-bzip2"):
            return "Archives"
        if sub_type in ("pdf",):
            return "Documents"
        if sub_type in ("vnd.openxmlformats-officedocument.wordprocessingml.document", "msword"):
            return "Documents"

        category_map = {
            "image": "Images", "video": "Videos", "audio": "Audio",
            "text": "Text Documents",
        }
        return category_map.get(main_type, "Other Files")


# ======================================================================
# FEATURE 3: SHA-256 Hash De-duplication Layer
# ======================================================================
class DeduplicationEngine:
    def __init__(self, chunk_size: int = 65536):
        self.chunk_size = chunk_size
        self.hash_registry = {}

    def compute_sha256(self, file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(self.chunk_size):
                sha256.update(chunk)
        return sha256.hexdigest()

    def scan_directory(self, target_dir: str) -> list:
        duplicates = []
        seen_hashes = {}
        for fp in Path(target_dir).rglob('*'):
            if fp.is_file() and not fp.is_symlink():
                try:
                    file_hash = self.compute_sha256(str(fp))
                    if file_hash in seen_hashes:
                        duplicates.append({"path": str(fp), "original": seen_hashes[file_hash], "hash": file_hash})
                    else:
                        seen_hashes[file_hash] = str(fp)
                except (IOError, OSError):
                    pass
        return duplicates

    def reset(self):
        self.hash_registry.clear()


# ======================================================================
# FEATURE 4: Kernel-Level File System Watcher (inotify)
# ======================================================================
class DirectoryWatcher:
    def __init__(self, target_dir: str, callback):
        self.target_dir = target_dir
        self.callback = callback
        self._running = False
        self._thread = None

    def _watch_loop(self):
        if not HAS_INOTIFY:
            logger.warning("inotify not available")
            return
        inotify = INotify()
        watch_flags = inotify_flags.CREATE | inotify_flags.MOVED_TO
        inotify.add_watch(self.target_dir, watch_flags)
        self._running = True
        while self._running:
            events = inotify.read(timeout=500)
            for event in events:
                full_path = os.path.join(self.target_dir, event.name)
                if os.path.isfile(full_path):
                    self.callback(full_path)

    def start(self):
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False


# ======================================================================
# FEATURE 5: Transactional Rollback Ledger (SQLite)
# ======================================================================
class TransactionLedger:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = str(CONFIG_DIR / "bobnox_ledger.db")
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS file_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_path TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    file_hash TEXT,
                    timestamp REAL NOT NULL,
                    status TEXT NOT NULL DEFAULT 'COMPLETED'
                )
            """)

    def log_move(self, src: str, dest: str, file_hash: str = ""):
        with self.conn:
            self.conn.execute(
                "INSERT INTO file_operations (source_path, target_path, file_hash, timestamp, status) VALUES (?, ?, ?, ?, ?)",
                (src, dest, file_hash, time.time(), "COMPLETED")
            )

    def rollback_latest(self, limit: int = 10) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, source_path, target_path FROM file_operations WHERE status='COMPLETED' ORDER BY timestamp DESC LIMIT ?", (limit,))
        records = cursor.fetchall()
        restored = 0
        for record_id, src, dest in records:
            try:
                if os.path.exists(dest):
                    Path(src).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(dest, src)
                    restored += 1
                self.conn.execute("UPDATE file_operations SET status='ROLLED_BACK' WHERE id=?", (record_id,))
            except Exception as e:
                logger.error(f"Rollback failed: {e}")
        self.conn.commit()
        return restored

    def get_pending_count(self) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM file_operations WHERE status='COMPLETED'")
        return cursor.fetchone()[0]


# ======================================================================
# FEATURE 6: RegEx Pattern Parsing and Variable Tokenization
# ======================================================================
class TokenParser:
    def __init__(self):
        self.token_regex = re.compile(r'\$\{([^}]+)\}')

    def _resolve_token(self, token: str, file_path: str) -> str:
        if token == "creation_date":
            stat_info = os.stat(file_path)
            return datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d")
        elif token == "ext":
            return os.path.splitext(file_path)[1].lstrip('.')
        elif token == "filename":
            return os.path.splitext(os.path.basename(file_path))[0]
        elif token == "year":
            return datetime.fromtimestamp(os.stat(file_path).st_ctime).strftime("%Y")
        elif token == "month":
            return datetime.fromtimestamp(os.stat(file_path).st_ctime).strftime("%m")
        return "unknown"

    def parse_destination(self, schema: str, file_path: str) -> str:
        return self.token_regex.sub(lambda m: self._resolve_token(m.group(1), file_path), schema)


# ======================================================================
# FEATURE 7: POSIX Permission Guard
# ======================================================================
class PosixGuard:
    @staticmethod
    def validate_file(file_path: str, include_hidden: bool = False) -> bool:
        if not os.path.exists(file_path):
            return False
        file_stat = os.lstat(file_path)
        if stat.S_ISLNK(file_stat.st_mode):
            logger.warning(f"Quarantined symlink: {file_path}")
            return False
        if file_stat.st_uid == 0:
            logger.warning(f"Quarantined root-owned: {file_path}")
            return False
        if not include_hidden and os.path.basename(file_path).startswith('.'):
            return False
        if not os.access(file_path, os.W_OK):
            logger.warning(f"Write denied: {file_path}")
            return False
        return True


# ======================================================================
# FEATURE 8: GTK File-Conflict Portal
# ======================================================================
class GtkConflictResolver:
    def __init__(self, default_strategy: str = "PROMPT"):
        self.default_strategy = default_strategy

    def prompt_resolution(self, target_path: str) -> str:
        if self.default_strategy != "PROMPT":
            return self.default_strategy
        filename = os.path.basename(target_path)
        cmd = [
            "zenity", "--list", "--title=boBnox Collision Alert",
            "--text", f"File collision: {filename}\nDestination exists. Choose action:",
            "--radiolist", "--column=Select", "--column=Action",
            "TRUE", "SMART_RENAME", "FALSE", "OVERWRITE", "FALSE", "SKIP"
        ]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            return result
        except subprocess.CalledProcessError:
            return "SKIP"

    def handle_collision(self, src: str, dest: str) -> Optional[str]:
        if not os.path.exists(dest):
            return dest
        action = self.prompt_resolution(dest)
        if action == "OVERWRITE":
            return dest
        elif action == "SMART_RENAME":
            base, ext = os.path.splitext(dest)
            counter = 1
            new_dest = f"{base}_{counter}{ext}"
            while os.path.exists(new_dest):
                counter += 1
                new_dest = f"{base}_{counter}{ext}"
            return new_dest
        return None


# ======================================================================
# FEATURE 11: Cryptographic Chunk-Level Deduplication & Reflink Engine
# ======================================================================
class ReflinkDeduplicator:
    FICLONE = 0x40049409

    def __init__(self, chunk_size: int = 65536):
        self.chunk_size = chunk_size
        self._libc = None
        try:
            import ctypes
            self._libc = ctypes.CDLL(None)
        except Exception:
            pass

    def calculate_signature(self, file_path: str) -> str:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(self.chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    def deduplicate(self, src: str, dest: str, try_reflink: bool = True) -> str:
        if not os.path.exists(src):
            raise FileNotFoundError(f"Source missing: {src}")

        if try_reflink and self._libc:
            try:
                with open(src, "rb") as src_f, open(dest, "wb+") as dest_f:
                    import fcntl
                    fcntl.ioctl(dest_f.fileno(), self.FICLONE, src_f.fileno())
                return "COW_REFLINK"
            except (IOError, OSError):
                if os.path.exists(dest):
                    os.remove(dest)

        os.link(src, dest)
        return "HARDLINK"


# ======================================================================
# FEATURE 12: Structural Integrity Validation (Magic Byte Sniffing)
# ======================================================================
class StructuralIntegrityValidator:
    def __init__(self):
        self.signature_matrix = {
            ".pdf": b"\x25\x50\x44\x46", ".zip": b"\x50\x4B\x03\x04",
            ".jar": b"\x50\x4B\x03\x04", ".png": b"\x89\x50\x4E\x47",
            ".elf": b"\x7F\x45\x4C\x46", ".jpg": b"\xFF\xD8\xFF",
            ".gif": b"\x47\x49\x46\x38", ".mp3": b"\x49\x44\x33",
            ".mp4": b"\x00\x00\x00\x18", ".py": None,
        }
        self.max_read = 16

    def analyze_file(self, file_path: str) -> dict:
        _, ext = os.path.splitext(file_path.lower())
        if ext not in self.signature_matrix:
            return {"status": "SKIPPED", "reason": "Unknown extension"}
        expected = self.signature_matrix[ext]
        if expected is None:
            return {"status": "VALIDATED", "type": "TEXT"}
        try:
            with open(file_path, "rb") as f:
                header = f.read(self.max_read)
        except IOError:
            return {"status": "ERROR", "reason": "Unreadable"}
        if header.startswith(expected):
            return {"status": "VALIDATED", "type": ext}
        return {"status": "ANOMALY", "action": "QUARANTINE", "ext": ext}


# ======================================================================
# FEATURE 13: Shannon Entropy Analytics
# ======================================================================
class ShannonEntropyAnalyzer:
    def calculate_entropy(self, file_path: str) -> float:
        if not os.path.exists(file_path) or os.path.islink(file_path):
            return 0.0
        size = os.path.getsize(file_path)
        if size == 0 or size > 100_000_000:  # Skip files > 100MB
            return 0.0
        try:
            with open(file_path, "rb") as f:
                data = f.read(min(size, 10_000_000))  # Cap at 10MB
        except (IOError, OSError):
            return 0.0
        counts = collections.Counter(data)
        entropy = 0.0
        for count in counts.values():
            p = count / size
            entropy -= p * math.log2(p)
        return round(entropy, 4)

    def classify(self, file_path: str) -> dict:
        e = self.calculate_entropy(file_path)
        _, ext = os.path.splitext(file_path.lower())
        # Archive/compressed files naturally have high entropy - don't quarantine them
        archive_exts = {'.zip', '.7z', '.rar', '.tar', '.gz', '.bz2', '.xz', '.zst', '.torrent'}
        if ext in archive_exts:
            tier, action = "COMPRESSED", "STANDARD_SORT"
        elif e < 4.5:
            tier, action = "STRUCTURED", "STANDARD_SORT"
        elif e <= 6.8:
            tier, action = "COMPILED_BINARY", "VERIFY_METADATA"
        else:
            tier, action = "ENCRYPTED_RANDOM", "QUARANTINE"
        return {"file": file_path, "entropy": e, "tier": tier, "action": action}


# ======================================================================
# FEATURE 14: POSIX Extended Attributes (xattr) Metadata Layering
# ======================================================================
class InodeMetadataLayer:
    def __init__(self):
        self._has_xattr = hasattr(os, "setxattr")

    def write_states(self, file_path: str, metadata: dict) -> bool:
        if not self._has_xattr:
            return False
        try:
            for key, val in metadata.items():
                os.setxattr(file_path, f"user.bobnox.{key}", val.encode("utf-8"))
            return True
        except OSError:
            return False

    def read_states(self, file_path: str, keys: list) -> dict:
        result = {}
        if not self._has_xattr:
            return {k: None for k in keys}
        for key in keys:
            try:
                result[key] = os.getxattr(file_path, f"user.bobnox.{key}").decode("utf-8")
            except OSError:
                result[key] = None
        return result


# ======================================================================
# FEATURE 15: Kernel-Driven Inotify Daemon (ctypes native)
# ======================================================================
class KernelInotifyDaemon:
    IN_CLOSE_WRITE = 0x00000008
    IN_MOVED_TO = 0x00000080
    EVENT_FMT = "iIII"
    EVENT_SIZE = struct.calcsize(EVENT_FMT)

    def __init__(self, watch_dir: str, callback):
        self.watch_dir = watch_dir
        self.callback = callback
        self._running = False
        self._fd = -1
        self._wd = -1
        self._thread = None
        if not IS_LINUX:
            logger.warning("KernelInotifyDaemon is Linux-only")
            return
        try:
            import ctypes
            self._libc = ctypes.CDLL(None)
            self._fd = self._libc.inotify_init()
        except Exception:
            self._fd = -1

    def start(self):
        if self._fd < 0:
            return
        mask = self.IN_CLOSE_WRITE | self.IN_MOVED_TO
        self._wd = self._libc.inotify_add_watch(self._fd, self.watch_dir.encode(), mask)
        if self._wd < 0:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def _poll(self):
        import select
        while self._running:
            r, _, _ = select.select([self._fd], [], [], 1.0)
            if not r:
                continue
            try:
                buf = os.read(self._fd, 4096)
            except OSError:
                break
            offset = 0
            while offset < len(buf):
                if len(buf) - offset < self.EVENT_SIZE:
                    break
                wd, mask, cookie, nlen = struct.unpack_from(self.EVENT_FMT, buf, offset)
                offset += self.EVENT_SIZE
                if nlen > 0:
                    name = buf[offset:offset + nlen].decode().rstrip("\x00")
                    offset += nlen
                    self.callback(os.path.join(self.watch_dir, name))

    def stop(self):
        self._running = False
        if self._wd >= 0 and self._fd >= 0:
            self._libc.inotify_rm_watch(self._fd, self._wd)
        if self._fd >= 0:
            os.close(self._fd)


# ======================================================================
# FEATURE 9: Headless CLI Control Architecture
# ======================================================================
class BobnoxCLI:
    def __init__(self):
        self.parser = None
        self._build_args()

    def _build_args(self):
        import argparse
        self.parser = argparse.ArgumentParser(description="boBnox Sorting Engine", prog="bobnox")
        sub = self.parser.add_subparsers(dest="command")

        org = sub.add_parser("organize", help="Organize a directory")
        org.add_argument("source", help="Target directory")
        org.add_argument("--dry-run", action="store_true")
        org.add_argument("--recursive", "-r", action="store_true")
        org.add_argument("--verbose", "-v", action="store_true")
        org.add_argument("--config", help="Path to config JSON")
        org.add_argument("--daemon", action="store_true", help="Run inotify watcher daemon")
        org.add_argument("--use-mime", action="store_true", help="Use MIME-based sorting")
        org.add_argument("--dedup", action="store_true", help="Scan for duplicates first")
        org.add_argument("--pattern", help="Regex destination pattern, e.g. '${creation_date}/${ext}/'")

        sub.add_parser("undo", help="Undo last operation")
        sub.add_parser("dedup", help="Scan for duplicate files")

        cfg = sub.add_parser("config", help="View/modify config")
        cfg.add_argument("--show", action="store_true")
        cfg.add_argument("--list-extensions", action="store_true")

    def execute(self, args_list=None):
        if args_list is None:
            args_list = sys.argv[1:]
        args = self.parser.parse_args(args_list)

        if not args.command:
            self.parser.print_help()
            return

        config = load_config()
        if hasattr(args, 'config') and args.config:
            if not os.path.exists(args.config):
                print(f"Error: Config file not found: {args.config}")
                sys.exit(1)
            with open(args.config) as f:
                config.update(json.load(f))

        if args.command == "organize":
            self._run_organize(args, config)
        elif args.command == "undo":
            ledger = TransactionLedger()
            restored = ledger.rollback_latest()
            print(f"Restored {restored} files.")
        elif args.command == "dedup":
            dedup = DeduplicationEngine()
            dups = dedup.scan_directory(args.source if hasattr(args, 'source') else ".")
            for d in dups:
                print(f"DUPLICATE: {d['path']} (copy of {d['original']})")
            print(f"Found {len(dups)} duplicates.")
        elif args.command == "config":
            if args.show:
                print(json.dumps(config, indent=2))
            elif args.list_extensions:
                for ext, folder in sorted(config.get("extension_map", {}).items()):
                    print(f"  {ext:10} -> {folder}")

    def _run_organize(self, args, config):
        organizer = FileOrganizer(config)
        if args.use_mime:
            organizer.mime_validator = MimeValidator()
        if args.pattern:
            organizer.token_parser = TokenParser()
            organizer.dest_pattern = args.pattern

        if args.daemon and HAS_INOTIFY:
            print(f"[DAEMON] Watching {args.source} for new files...")
            watcher = DirectoryWatcher(args.source, lambda p: organizer.organize_single_file(p, args.source, dry_run=args.dry_run))
            watcher.start()
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                watcher.stop()
        else:
            def cb(msg, pct):
                print(msg)
            moved = organizer.organize_directory(args.source, cb, dry_run=args.dry_run)
            print(f"Done. Moved {moved} files.")


# ======================================================================
# CONFIGURATION
# ======================================================================
DEFAULT_CONFIG = {
    "extension_map": {
        '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
        '.bmp': 'Images', '.svg': 'Images', '.tiff': 'Images', '.webp': 'Images', '.heic': 'Images',
        '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
        '.txt': 'Text Documents', '.rtf': 'Documents', '.odt': 'Documents', '.md': 'Text Documents',
        '.xls': 'Spreadsheets', '.xlsx': 'Spreadsheets', '.csv': 'Spreadsheets',
        '.ppt': 'Presentations', '.pptx': 'Presentations',
        '.mp3': 'Audio', '.wav': 'Audio', '.aac': 'Audio', '.flac': 'Audio', '.ogg': 'Audio', '.m4a': 'Audio',
        '.mp4': 'Videos', '.mov': 'Videos', '.avi': 'Videos', '.mkv': 'Videos', '.wmv': 'Videos', '.flv': 'Videos',
        '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives', '.tar': 'Archives',
        '.gz': 'Archives', '.torrent': 'Archives',
        '.py': 'Scripts', '.js': 'Scripts', '.html': 'Web Files', '.css': 'Web Files',
        '.java': 'Code', '.cpp': 'Code', '.c': 'Code', '.sh': 'Scripts',
        '.exe': 'Executables', '.msi': 'Installers', '.dmg': 'Installers',
    },
    "organize_subdirectories": False,
    "create_log_file": True,
    "dark_mode": True,
}

CONFIG_DIR = Path.home() / ".config" / "bobnox"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "undo_history.json"

def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                user_config = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(config: dict) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception:
        return False


# ======================================================================
# FILE ORGANIZER CORE (with all features integrated)
# ======================================================================
class FileOrganizer:
    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_config()
        self.extension_map = self.config.get("extension_map", DEFAULT_CONFIG["extension_map"])
        self.organize_subdirectories = self.config.get("organize_subdirectories", False)
        self.create_log_file = self.config.get("create_log_file", True)
        self._move_history: List[Tuple[Path, Path]] = []
        self.ledger = TransactionLedger()
        self.mime_validator = MimeValidator() if HAS_MAGIC else None
        self.dedup_engine = DeduplicationEngine()
        self.reflink_dedup = ReflinkDeduplicator()
        self.struct_validator = StructuralIntegrityValidator()
        self.entropy_analyzer = ShannonEntropyAnalyzer()
        self.xattr_layer = InodeMetadataLayer()
        self.token_parser = TokenParser()
        self.dest_pattern = None
        self.conflict_resolver = GtkConflictResolver()
        self.guard = PosixGuard()

    def organize_directory(self, directory_path: str, status_callback, dry_run: bool = False,
                           use_mime: bool = False, dedup_scan: bool = False,
                           use_entropy: bool = False, include_hidden: bool = False) -> int:
        if not os.path.isdir(directory_path):
            raise FileNotFoundError("Invalid directory.")

        directory = Path(directory_path)
        skipped_entropy = 0
        skipped_guard = 0

        if dedup_scan:
            duplicates = self.dedup_engine.scan_directory(directory_path)
            if duplicates:
                status_callback(f"Found {len(duplicates)} duplicates.", 0.0)
            self.dedup_engine.reset()

        if self.organize_subdirectories:
            files_to_move = [f for f in directory.rglob('*') if f.is_file() and f.name != os.path.basename(__file__)]
        else:
            files_to_move = [f for f in directory.iterdir() if f.is_file() and f.name != os.path.basename(__file__)]

        valid = []
        for f in files_to_move:
            if self.guard.validate_file(str(f), include_hidden=include_hidden):
                valid.append(f)
            else:
                skipped_guard += 1
        files_to_move = valid

        if use_entropy:
            filtered = []
            for f in files_to_move:
                result = self.entropy_analyzer.classify(str(f))
                if result["action"] == "STANDARD_SORT":
                    filtered.append(f)
                else:
                    skipped_entropy += 1
                    status_callback(f"[ENTROPY] Skipped {f.name} — {result['tier']}", 0.0)
            files_to_move = filtered

        total = len(files_to_move)
        moved = 0
        if total == 0:
            status_callback(f"No files to organize. Skipped: {skipped_guard} (guard) + {skipped_entropy} (entropy)", 1.0)
            return 0

        self._move_history.clear()

        for i, fp in enumerate(files_to_move):
            integrity = self.struct_validator.analyze_file(str(fp))
            if integrity.get("status") == "ANOMALY":
                status_callback(f"[ANOMALY] {fp.name} — magic byte mismatch, quarantined", (i + 1) / total)
                continue

            ext = fp.suffix.lower()
            if use_mime and self.mime_validator:
                folder_name = self.mime_validator.route_by_mime(str(fp))
            else:
                folder_name = self.extension_map.get(ext, f"{ext[1:].upper()} Files" if ext else "Other Files")

            if self.dest_pattern:
                folder_name = self.token_parser.parse_destination(self.dest_pattern, str(fp))
                dest = directory / folder_name
            else:
                dest = directory / folder_name

            if not dry_run and not dest.exists():
                dest.mkdir(parents=True, exist_ok=True)

            base, e = os.path.splitext(fp.name)
            counter = 1
            dest_path = dest / fp.name
            while dest_path.exists():
                resolved = self.conflict_resolver.handle_collision(str(fp), str(dest_path))
                if resolved is None:
                    break
                dest_path = Path(resolved)
                if resolved == str(dest / fp.name):
                    counter += 1
                    dest_path = dest / f"{base}_{counter}{e}"

            if not dry_run:
                try:
                    file_hash = self.dedup_engine.compute_sha256(str(fp))
                    shutil.move(str(fp), str(dest_path))
                    self.ledger.log_move(str(fp), str(dest_path), file_hash)
                    self.xattr_layer.write_states(str(dest_path), {"moved_at": str(time.time()), "original_path": str(fp)})
                    self._move_history.append((dest_path, fp))
                    moved += 1
                except Exception as ex:
                    logger.error(f"Failed: {fp.name}: {ex}")
                    continue
            else:
                moved += 1

            status_callback(f"{'Would move' if dry_run else 'Moving'} ({i+1}/{total}): {fp.relative_to(directory)} → {folder_name}", (i + 1) / total)

        status_callback(f"Done. Moved: {moved}  Skipped (guard): {skipped_guard}  Skipped (entropy): {skipped_entropy}", 1.0)
        return moved

    def organize_single_file(self, file_path: str, watch_dir: str, dry_run: bool = False):
        fp = Path(file_path)
        if not fp.is_file() or not self.guard.validate_file(str(fp)):
            return
        ext = fp.suffix.lower()
        folder_name = self.extension_map.get(ext, f"{ext[1:].upper()} Files" if ext else "Other Files")
        dest = Path(watch_dir) / folder_name
        if not dry_run:
            dest.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(fp), str(dest / fp.name))
                self.ledger.log_move(str(fp), str(dest / fp.name))
            except Exception as e:
                logger.error(f"Watch move failed: {e}")

    def undo_last_organization(self, status_callback) -> int:
        restored = self.ledger.rollback_latest()
        self._move_history.clear()
        return restored


# ======================================================================
# LEDGER HISTORY DIALOG
# ======================================================================
class LedgerHistoryDialog(ctk.CTkToplevel):
    """Browse the full SQLite operation log."""

    def __init__(self, parent, ledger):
        super().__init__(parent)
        self.ledger = ledger
        self.title("Operation History")
        self.geometry("720x480")
        self.resizable(True, True)
        self.grab_set()

        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = CARD_DARK if is_dark else CARD_LIGHT
        text = TEXT_DARK if is_dark else TEXT_LIGHT
        muted = MUTED_DARK if is_dark else MUTED_LIGHT
        entry = ENTRY_DARK if is_dark else ENTRY_LIGHT
        border = BORDER_DARK if is_dark else BORDER_LIGHT

        self.configure(fg_color=bg)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=20, pady=(16, 0))
        ctk.CTkLabel(hdr, text="Operation History", font=("Geist", 16, "bold"), text_color=text).pack(side="left")

        filter_row = ctk.CTkFrame(self, fg_color="transparent")
        filter_row.pack(fill="x", padx=20, pady=(8, 4))
        filter_row.columnconfigure(0, weight=1)

        self._filter_var = tk.StringVar()
        ctk.CTkEntry(filter_row, textvariable=self._filter_var, placeholder_text="Filter by filename...", font=("Geist", 11), fg_color=entry, border_color=border, text_color=text, corner_radius=INPUT_RADIUS, height=28).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(filter_row, text="Refresh", font=("Geist", 11), fg_color=BTN_DARK if is_dark else BTN_LIGHT, hover_color=BTN_HOVER_DARK if is_dark else BTN_HOVER_LIGHT, text_color=text, height=28, corner_radius=BTN_RADIUS, command=self._load).grid(row=0, column=1)
        self._filter_var.trace_add("write", lambda *_: self._load())

        col_hdr = ctk.CTkFrame(self, fg_color=entry, corner_radius=0)
        col_hdr.pack(fill="x", padx=20, pady=(4, 0))
        for label, w in [("Timestamp", 140), ("Source", 220), ("Destination", 220), ("Status", 80)]:
            ctk.CTkLabel(col_hdr, text=label, font=("Geist", 10), text_color=muted, width=w, anchor="w").pack(side="left", padx=8, pady=4)

        self._scroll = ctk.CTkScrollableFrame(self, fg_color=bg, corner_radius=0, border_width=1, border_color=border)
        self._scroll.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        self._stats_label = ctk.CTkLabel(self, text="", font=("Geist", 10), text_color=muted)
        self._stats_label.pack(anchor="w", padx=20, pady=(0, 12))

        self._load()
        self.after(50, lambda: self._center(parent))

    def _load(self):
        for w in self._scroll.winfo_children():
            w.destroy()

        is_dark = ctk.get_appearance_mode() == "Dark"
        text = TEXT_DARK if is_dark else TEXT_LIGHT
        muted = MUTED_DARK if is_dark else MUTED_LIGHT
        border = BORDER_DARK if is_dark else BORDER_LIGHT
        filt = self._filter_var.get().lower()

        cursor = self.ledger.conn.cursor()
        cursor.execute("SELECT timestamp, source_path, target_path, status FROM file_operations ORDER BY timestamp DESC LIMIT 500")
        rows = cursor.fetchall()

        shown = 0
        for ts, src, dest, status in rows:
            src_name = os.path.basename(src)
            if filt and filt not in src_name.lower() and filt not in src.lower():
                continue
            row_frame = ctk.CTkFrame(self._scroll, fg_color="transparent", corner_radius=0)
            row_frame.pack(fill="x", pady=1)
            ctk.CTkFrame(row_frame, height=1, fg_color=border).pack(fill="x")
            content = ctk.CTkFrame(row_frame, fg_color="transparent")
            content.pack(fill="x", padx=4, pady=3)
            ts_str = datetime.fromtimestamp(ts).strftime("%m-%d %H:%M:%S")
            ctk.CTkLabel(content, text=ts_str, font=("Courier", 10), text_color=muted, width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(content, text=src_name, font=("Geist", 10), text_color=text, width=220, anchor="w").pack(side="left")
            ctk.CTkLabel(content, text=os.path.basename(dest), font=("Geist", 10), text_color=muted, width=220, anchor="w").pack(side="left")
            sc = ACCENT_GREEN if status == "COMPLETED" else ACCENT_CORAL
            ctk.CTkLabel(content, text=status, font=("Geist", 9), text_color=sc, width=80, anchor="w").pack(side="left")
            shown += 1

        self._stats_label.configure(text=f"Showing {shown} of {len(rows)} operations")

    def _center(self, parent):
        self.update_idletasks()
        w, h = 720, 480
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{max(0,x)}+{max(0,y)}")


# ======================================================================
# SETTINGS DIALOG
# ======================================================================
class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog - opens as a separate modal window."""
    
    def __init__(self, parent, config: dict, on_save_callback):
        super().__init__(parent)
        self.config = config.copy()
        self.on_save = on_save_callback

        self.title("Settings")
        self.geometry("520x620")
        self.resizable(False, False)

        # Anchor modal to parent window
        self.transient(parent)
        self.grab_set()

        # Theme colors
        is_dark = ctk.get_appearance_mode() == "Dark"
        card = CARD_DARK if is_dark else CARD_LIGHT
        text = TEXT_DARK if is_dark else TEXT_LIGHT
        muted = MUTED_DARK if is_dark else MUTED_LIGHT
        border = BORDER_DARK if is_dark else BORDER_LIGHT
        entry_bg = ENTRY_DARK if is_dark else ENTRY_LIGHT
        btn_dark = BTN_DARK if is_dark else BTN_LIGHT
        btn_hover = BTN_HOVER_DARK if is_dark else BTN_HOVER_LIGHT

        # Force parent to calculate actual dimensions before centering
        parent.update_idletasks()

        # Center on parent using actual coordinates
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + (pw // 2) - 260
        y = py + (ph // 2) - 310
        self.geometry(f"520x620+{max(0, x)}+{max(0, y)}")

        # Fix bg_color on Toplevel
        self.configure(fg_color=card, bg_color=card)

        # Main container with explicit bg_color chain
        main_container = ctk.CTkFrame(self, fg_color=card, bg_color=card, corner_radius=APP_RADIUS)
        main_container.pack(fill="both", expand=True, padx=0, pady=0)

        # Content wrapper
        content = ctk.CTkFrame(main_container, fg_color=card, bg_color=card, corner_radius=0)
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # Header
        gf = "Geist" if geist_available() else ("Helvetica" if IS_MACOS else "Sans")
        ctk.CTkLabel(content, text="⚙ Settings", font=(gf, 18, "bold"), text_color=text).pack(anchor="w", pady=(0, 8))
        ctk.CTkFrame(content, height=1, fg_color=border, bg_color=card).pack(fill="x", pady=(0, 12))

        # Scrollable extension list with explicit bg chain
        self.scroll_frame = ctk.CTkScrollableFrame(content, fg_color=card, bg_color=card, corner_radius=CARD_RADIUS, border_color=border, border_width=1)
        self.scroll_frame.pack(fill="both", expand=True, pady=(0, 12))

        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color=card, bg_color=card)
        btn_frame.pack(fill="x", pady=(0, 4))
        ctk.CTkButton(btn_frame, text="💾 Save", font=(gf, 13, "bold"), fg_color=ACCENT_BLUE, hover_color="#004BB3", height=36, corner_radius=BTN_RADIUS, command=self._save).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="Cancel", font=(gf, 13), fg_color=btn_dark, hover_color=btn_hover, text_color=text, height=36, corner_radius=BTN_RADIUS, command=self.destroy).pack(side="left")

        self.extension_entries = {}
        self.after(30, self._render_mappings)

    def _render_mappings(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        text = TEXT_DARK if is_dark else TEXT_LIGHT
        muted = MUTED_DARK if is_dark else MUTED_LIGHT
        entry_bg = ENTRY_DARK if is_dark else ENTRY_LIGHT
        border = BORDER_DARK if is_dark else BORDER_LIGHT
        card = CARD_DARK if is_dark else CARD_LIGHT
        gf = "Geist" if geist_available() else ("Helvetica" if IS_MACOS else "Sans")

        for ext, folder in sorted(self.config.get("extension_map", {}).items()):
            row = ctk.CTkFrame(self.scroll_frame, fg_color=card, bg_color=card, corner_radius=CARD_RADIUS)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=ext, font=(gf, 13, "bold"), text_color=muted, width=80).pack(side="left", padx=(12, 8), pady=8)
            entry = ctk.CTkEntry(row, font=(gf, 13), fg_color=entry_bg, border_color=border, text_color=text, corner_radius=INPUT_RADIUS, height=32)
            entry.insert(0, folder)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)
            self.extension_entries[ext] = entry

    def _save(self):
        for ext, entry in self.extension_entries.items():
            self.config["extension_map"][ext] = entry.get()
        self.on_save(self.config)
        self.destroy()


# ======================================================================
# MAIN APPLICATION (Bento UI v2.3.0)
# ======================================================================
# MAIN APPLICATION (Bento UI v3.0.0 - Stability Fixed)
# ======================================================================
class BoBnoxApp(ctk.CTk):

    def __init__(self):
        super().__init__(className="bobnox")

        self.app_config = load_config()
        self.organizer = FileOrganizer(self.app_config)
        self.log_messages = []
        self.running = False

        self.title("BoBnox v4.1.0")
        self.geometry("1200x820")
        self.minsize(960, 680)

        if not geist_available():
            install_geist_fonts()
        ensure_icons_installed()

        self._icon_ref = None
        icon_path = ICON_SYSTEM if os.path.exists(ICON_SYSTEM) else ICON_APP if os.path.exists(ICON_APP) else ICON_SOURCE
        if os.path.exists(icon_path):
            try:
                self._icon_ref = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, self._icon_ref)
            except Exception:
                pass

        self.C_BG = (BG_LIGHT, BG_DARK)
        self.C_CARD = (CARD_LIGHT, CARD_DARK)
        self.C_TEXT = (TEXT_LIGHT, TEXT_DARK)
        self.C_MUTED = (MUTED_LIGHT, MUTED_DARK)
        self.C_ENTRY = (ENTRY_LIGHT, ENTRY_DARK)
        self.C_BORDER = (BORDER_LIGHT, BORDER_DARK)
        self.C_BTN = (BTN_LIGHT, BTN_DARK)
        self.C_BTN_HOVER = (BTN_HOVER_LIGHT, BTN_HOVER_DARK)

        gf = "Geist" if geist_available() else ("Helvetica" if IS_MACOS else "Sans")
        self.F_TITLE = (gf, 26, "bold")
        self.F_SUB = (gf, 12)
        self.F_LABEL = (gf, 13)
        self.F_BTN = (gf, 13, "bold")
        self.F_CONSOLE = ("Courier", 11)

        self.path_var = tk.StringVar()
        self.dry_run_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=self.app_config.get("organize_subdirectories", False))
        self.mime_sort_var = tk.BooleanVar(value=False)
        self.log_file_var = tk.BooleanVar(value=self.app_config.get("create_log_file", True))
        self.hidden_var = tk.BooleanVar(value=False)
        self.verbose_var = tk.BooleanVar(value=False)
        self.entropy_var = tk.BooleanVar(value=False)
        self.undo_limit_var = tk.StringVar(value="10")
        self.collision_var = tk.StringVar(value="SMART_RENAME")
        self.template_var = tk.StringVar()
        self._watcher = None

        self.grid_columnconfigure(0, weight=0, minsize=250)
        self.grid_columnconfigure(1, weight=1, minsize=420)
        self.grid_columnconfigure(2, weight=1, minsize=420)
        self.grid_rowconfigure(0, weight=1, minsize=140)
        self.grid_rowconfigure(1, weight=0, minsize=70)
        self.grid_rowconfigure(2, weight=2, minsize=240)
        self.grid_rowconfigure(3, weight=2, minsize=220)

        ctk.set_appearance_mode("Dark" if self.app_config.get("dark_mode", True) else "Light")

        self._create_widgets()

    # --- Patch helpers ---
    def _build_sidebar_extras(self, sidebar, gf):
        is_dark = ctk.get_appearance_mode() == "Dark"
        text = self.C_TEXT
        muted = self.C_MUTED
        border = self.C_BORDER

        ctk.CTkFrame(sidebar, height=1, fg_color=border).pack(fill="x", padx=14, pady=(8, 0))
        ctk.CTkLabel(sidebar, text="Logging", font=(gf, 9), text_color=muted).pack(anchor="w", padx=14, pady=(8, 4))

        def _sw(parent, label, var):
            r = ctk.CTkFrame(parent, fg_color="transparent")
            r.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(r, text=label, font=(gf, 11), text_color=text).pack(side="left")
            ctk.CTkSwitch(r, variable=var, text="", width=36, height=18, progress_color=ACCENT_GREEN, fg_color=("#AEAEB2", "#48484A"), button_color="#FFFFFF").pack(side="right")

        _sw(sidebar, "Create log file", self.log_file_var)
        _sw(sidebar, "Verbose output", self.verbose_var)

        ctk.CTkFrame(sidebar, height=1, fg_color=border).pack(fill="x", padx=14, pady=(8, 0))
        ctk.CTkLabel(sidebar, text="Guard", font=(gf, 9), text_color=muted).pack(anchor="w", padx=14, pady=(8, 4))
        _sw(sidebar, "Include hidden files", self.hidden_var)

    def _build_collision_row(self, parent, gf):
        muted = self.C_MUTED
        entry = self.C_ENTRY
        border = self.C_BORDER

        ctk.CTkLabel(parent, text="Collision Strategy", font=(gf, 10), text_color=muted).pack(anchor="w", padx=14, pady=(10, 2))
        ctk.CTkOptionMenu(parent, variable=self.collision_var, values=["SMART_RENAME", "OVERWRITE", "SKIP", "PROMPT"], font=(gf, 11), fg_color=entry, button_color=ACCENT_BLUE, text_color=self.C_TEXT, corner_radius=INPUT_RADIUS, height=30).pack(fill="x", padx=14)

    def _build_undo_row(self, parent, gf):
        muted = self.C_MUTED
        entry = self.C_ENTRY
        border = self.C_BORDER
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(4, 0))
        ctk.CTkLabel(row, text="Undo depth", font=(gf, 10), text_color=muted).pack(side="left")
        ctk.CTkEntry(row, textvariable=self.undo_limit_var, font=(gf, 11), width=48, height=24, fg_color=entry, border_color=border, text_color=self.C_TEXT, corner_radius=INPUT_RADIUS, justify="center").pack(side="right")

    def _build_regex_card_extras(self, parent, gf):
        muted = self.C_MUTED
        border = self.C_BORDER
        ctk.CTkLabel(parent, text="tokens: ${creation_date}  ${year}  ${month}  ${ext}  ${filename}", font=(gf, 9), text_color=muted, anchor="w").pack(anchor="w", padx=14, pady=(4, 0))
        ctk.CTkFrame(parent, height=1, fg_color=border).pack(fill="x", padx=14, pady=(8, 0))
        preview_row = ctk.CTkFrame(parent, fg_color="transparent")
        preview_row.pack(fill="x", padx=14, pady=(6, 12))
        ctk.CTkLabel(preview_row, text="Preview", font=(gf, 9), text_color=muted).pack(side="left", padx=(0, 8))
        self._preview_label = ctk.CTkLabel(preview_row, text="—", font=("Courier", 10), text_color=muted, anchor="w")
        self._preview_label.pack(side="left", fill="x", expand=True)
        self.template_var.trace_add("write", self._update_template_preview)

    def _update_template_preview(self, *_):
        raw = self.template_var.get()
        if not raw:
            self._preview_label.configure(text="—")
            return
        now = datetime.now()
        resolved = raw.replace("${creation_date}", now.strftime("%Y-%m-%d")).replace("${year}", now.strftime("%Y")).replace("${month}", now.strftime("%m")).replace("${ext}", "pdf").replace("${filename}", "invoice_march")
        resolved = resolved.replace("//", "/")
        self._preview_label.configure(text=resolved)

    def _open_ledger_history(self):
        LedgerHistoryDialog(self, self.organizer.ledger).focus()

    def _show_dedup_results(self, duplicates):
        if not duplicates:
            self._log("Dedup scan: no duplicates found.")
            return
        self._log(f"Dedup scan: {len(duplicates)} duplicate(s) found:")
        for item in duplicates[:50]:
            path = item.get("path", "")
            original = item.get("original", "")
            try:
                size = os.path.getsize(path)
                size_str = f"{size // 1024} KB"
            except OSError:
                size_str = "?"
            self._log(f"  DUP {os.path.basename(path)} ({size_str}) <- {os.path.basename(original)}")
        if len(duplicates) > 50:
            self._log(f"  ... and {len(duplicates) - 50} more")

    def _log(self, msg: str):
        """Thread-safe bounded console log (max 500 lines)."""
        self.log_messages.append(msg)
        self.after(0, lambda: self._do_log(msg))

    def _do_log(self, msg: str):
        self.console.configure(state="normal")
        self.console.insert("end", msg + "\n")
        # Cap at 500 lines to prevent unbounded growth
        content = self.console.get("1.0", "end")
        lines = content.split("\n")
        if len(lines) > 500:
            self.console.delete("1.0", f"{len(lines) - 500}.0")
        self.console.see("end")
        self.console.configure(state="disabled")

    def _create_widgets(self):
        gf = "Geist" if geist_available() else ("Helvetica" if IS_MACOS else "Sans")

        # SIDEBAR (flat corners - no notch artifact)
        sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=self.C_CARD, bg_color=self.C_BG)
        sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew", padx=12, pady=12)

        ctk.CTkLabel(sidebar, text="boBnox", font=self.F_TITLE, text_color=self.C_TEXT).pack(anchor="w", padx=20, pady=(24, 4))
        ctk.CTkLabel(sidebar, text="v4.0.0", font=(gf, 11), text_color=self.C_MUTED).pack(anchor="w", padx=20, pady=(0, 16))
        ctk.CTkFrame(sidebar, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=8)

        self.theme_switch = ctk.CTkSwitch(sidebar, text="Dark Mode", command=self._toggle_theme, font=(gf, 11), text_color=self.C_TEXT, progress_color=ACCENT_BLUE, fg_color=("#AEAEB2", "#48484A"), button_color="#FFFFFF", button_hover_color=("#F0F0F0", "#E0E0E0"))
        self.theme_switch.pack(anchor="w", padx=20, pady=8)
        if self.app_config.get("dark_mode", True):
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
            self.theme_switch.configure(text="Light Mode")

        ctk.CTkFrame(sidebar, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(sidebar, text="Engine", font=self.F_SUB, text_color=self.C_MUTED).pack(anchor="w", padx=20, pady=(8, 4))
        self.daemon_switch = ctk.CTkSwitch(sidebar, text="⟲ Daemon", font=(gf, 11), text_color=self.C_TEXT, progress_color=ACCENT_GREEN, fg_color=("#AEAEB2", "#48484A"), button_color="#FFFFFF", button_hover_color=("#F0F0F0", "#E0E0E0"), command=self._toggle_daemon)
        self.daemon_switch.pack(anchor="w", padx=20, pady=4)
        self.mime_switch = ctk.CTkSwitch(sidebar, text="⎔ MIME Sort", font=(gf, 11), text_color=self.C_TEXT, progress_color=ACCENT_BLUE, fg_color=("#AEAEB2", "#48484A"), button_color="#FFFFFF", button_hover_color=("#F0F0F0", "#E0E0E0"))
        self.mime_switch.pack(anchor="w", padx=20, pady=4)
        ctk.CTkFrame(sidebar, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(sidebar, text="Ledger", font=self.F_SUB, text_color=self.C_MUTED).pack(anchor="w", padx=20, pady=(8, 4))
        self.ledger_status = ctk.CTkLabel(sidebar, text=f"Pending: {self.organizer.ledger.get_pending_count()}", font=(gf, 11), text_color=ACCENT_GREEN)
        self.ledger_status.pack(anchor="w", padx=20, pady=4)
        self._build_sidebar_extras(sidebar, gf)

        # CONTENT GRID
        content = ctk.CTkFrame(self, fg_color="transparent", bg_color=self.C_BG, corner_radius=0)
        content.grid(row=0, column=1, columnspan=2, rowspan=4, padx=4, pady=12, sticky="nsew")
        content.grid_columnconfigure(0, weight=1, minsize=420)
        content.grid_columnconfigure(1, weight=1, minsize=420)
        content.grid_rowconfigure(0, weight=0)
        content.grid_rowconfigure(1, weight=1)
        content.grid_rowconfigure(2, weight=1)

        # HERO CARD (brand + options inline)
        hero = ctk.CTkFrame(content, fg_color=self.C_CARD, bg_color=self.C_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=self.C_BORDER)
        hero.grid(row=0, column=0, columnspan=2, padx=6, pady=(6, 6), sticky="ew")
        hero.columnconfigure(0, weight=1)
        hero.columnconfigure(2, weight=0)

        # Left: title + path
        left = ctk.CTkFrame(hero, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=14)

        ctk.CTkLabel(left, text="boBnox", font=(gf, 20, "bold"), text_color=self.C_TEXT).pack(anchor="w")
        ctk.CTkLabel(left, text="File Organization Engine", font=(gf, 11), text_color=self.C_MUTED).pack(anchor="w", pady=(2, 0))
        pending = self.organizer.ledger.get_pending_count()
        ctk.CTkLabel(left, text=f"● SQLite Ledger  ·  Pending: {pending}", font=(gf, 10), text_color=ACCENT_GREEN).pack(anchor="w", pady=(4, 10))

        path_row = ctk.CTkFrame(left, fg_color="transparent")
        path_row.pack(fill="x")
        path_row.columnconfigure(0, weight=1)
        self.path_entry = ctk.CTkEntry(path_row, textvariable=self.path_var, font=(gf, 11), placeholder_text="Select a folder...", fg_color=self.C_ENTRY, border_color=self.C_BORDER, text_color=self.C_TEXT, corner_radius=INPUT_RADIUS, height=30)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.browse_btn = ctk.CTkButton(path_row, text="Browse", font=(gf, 11, "bold"), fg_color=ACCENT_BLUE, hover_color="#005FCC", height=30, corner_radius=BTN_RADIUS, command=self._select_directory)
        self.browse_btn.grid(row=0, column=1)

        # Divider
        divider = ctk.CTkFrame(hero, width=1, fg_color=self.C_BORDER)
        divider.grid(row=0, column=1, sticky="ns", padx=0, pady=12)

        # Right: options
        opts = ctk.CTkFrame(hero, fg_color="transparent", width=180)
        opts.grid(row=0, column=2, sticky="ns", padx=(12, 16), pady=14)
        opts.pack_propagate(False)

        ctk.CTkLabel(opts, text="Global Options", font=(gf, 10), text_color=self.C_MUTED).pack(anchor="w", pady=(0, 8))

        def _opt_row(parent, label, dot_color, var):
            r = ctk.CTkFrame(parent, fg_color="transparent")
            r.pack(fill="x", pady=3)
            ctk.CTkFrame(r, width=8, height=8, corner_radius=4, fg_color=dot_color).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(r, text=label, font=(gf, 11), text_color=self.C_TEXT).pack(side="left")
            ctk.CTkSwitch(r, variable=var, text="", width=36, height=18, progress_color=ACCENT_GREEN, fg_color=("#AEAEB2", "#48484A"), button_color="#FFFFFF", button_hover_color=("#F0F0F0", "#E0E0E0")).pack(side="right")

        _opt_row(opts, "Dry Run", ACCENT_BLUE, self.dry_run_var)
        _opt_row(opts, "Recursive", ACCENT_ORANGE, self.recursive_var)
        dedup_var = tk.BooleanVar(value=False)
        _opt_row(opts, "Dedup Scan", ACCENT_CORAL, dedup_var)
        self.sw_dedup_var = dedup_var

        # MIDDLE ROW: Dedup + Rename (fill both, expand)
        dedup_card = ctk.CTkFrame(content, fg_color=self.C_CARD, bg_color=self.C_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=self.C_BORDER)
        dedup_card.grid(row=1, column=0, padx=(6, 3), pady=3, sticky="nsew")
        ctk.CTkLabel(dedup_card, text="Deduplication Engine", text_color=self.C_MUTED, font=(gf, 12, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkFrame(dedup_card, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(dedup_card, text="Purge Mode", text_color=self.C_MUTED, font=(gf, 10)).pack(anchor="w", padx=16, pady=(4, 2))
        self.opt_link_mode = ctk.CTkOptionMenu(dedup_card, values=["SMART_LINK", "HARDLINK", "DELETE"], fg_color=self.C_BTN, button_color=ACCENT_BLUE, text_color=self.C_TEXT, font=(gf, 11))
        self.opt_link_mode.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(dedup_card, text="Entropy Filter", text_color=self.C_MUTED, font=(gf, 10)).pack(anchor="w", padx=16, pady=(4, 2))
        ctk.CTkCheckBox(dedup_card, text="Skip high-entropy files", variable=self.entropy_var, fg_color=ACCENT_BLUE, text_color=self.C_TEXT, font=(gf, 11)).pack(anchor="w", padx=16, pady=(0, 8))
        self._build_collision_row(dedup_card, gf)
        ctk.CTkFrame(dedup_card, fg_color="transparent").pack(fill="both", expand=True)

        rename_card = ctk.CTkFrame(content, fg_color=self.C_CARD, bg_color=self.C_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=self.C_BORDER)
        rename_card.grid(row=1, column=1, padx=(3, 6), pady=3, sticky="nsew")
        ctk.CTkLabel(rename_card, text="Regex Rename", text_color=self.C_MUTED, font=(gf, 12, "bold")).pack(anchor="w", padx=16, pady=(12, 4))
        ctk.CTkFrame(rename_card, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(rename_card, text="Pattern", text_color=self.C_MUTED, font=(gf, 10)).pack(anchor="w", padx=16, pady=(4, 2))
        self.txt_regex = ctk.CTkEntry(rename_card, placeholder_text=r"^.*$", fg_color=self.C_ENTRY, border_color=self.C_BORDER, text_color=self.C_TEXT, font=("Courier", 11), corner_radius=INPUT_RADIUS, height=30)
        self.txt_regex.pack(fill="x", padx=16, pady=(0, 4))
        ctk.CTkLabel(rename_card, text="Template", text_color=self.C_MUTED, font=(gf, 10)).pack(anchor="w", padx=16, pady=(8, 2))
        self.txt_template = ctk.CTkEntry(rename_card, textvariable=self.template_var, placeholder_text="${creation_date}/${ext}/", fg_color=self.C_ENTRY, border_color=self.C_BORDER, text_color=self.C_TEXT, font=("Courier", 11), corner_radius=INPUT_RADIUS, height=30)
        self.txt_template.pack(fill="x", padx=16, pady=(0, 4))
        self._build_regex_card_extras(rename_card, gf)
        ctk.CTkFrame(rename_card, fg_color="transparent").pack(fill="both", expand=True)

        # BOTTOM ROW: Actions + Monitor (fill both, expand)
        actions_card = ctk.CTkFrame(content, fg_color=self.C_CARD, bg_color=self.C_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=self.C_BORDER)
        actions_card.grid(row=2, column=0, padx=(6, 3), pady=(3, 6), sticky="nsew")
        actions_card.grid_columnconfigure((0, 1), weight=1)
        actions_card.grid_rowconfigure((0, 1), weight=1)

        self.organize_btn = ctk.CTkButton(actions_card, text="▶  Organize", font=(gf, 11, "bold"), fg_color=ACCENT_GREEN, hover_color="#2DB84D", text_color="#FFFFFF", corner_radius=BTN_RADIUS, height=48, command=self._start_organizing)
        self.organize_btn.grid(row=0, column=0, padx=6, pady=6, sticky="nsew")

        self.undo_btn = ctk.CTkButton(actions_card, text="⟲  Undo", font=(gf, 11, "bold"), fg_color=self.C_BTN, hover_color=self.C_BTN_HOVER, text_color=self.C_TEXT, corner_radius=BTN_RADIUS, height=48, command=self._undo_action, state="disabled")
        self.undo_btn.grid(row=0, column=1, padx=6, pady=6, sticky="nsew")

        self.open_folder_btn = ctk.CTkButton(actions_card, text="📁  Open Folder", font=(gf, 11, "bold"), fg_color=self.C_BTN, hover_color=self.C_BTN_HOVER, text_color=self.C_TEXT, corner_radius=BTN_RADIUS, height=48, command=self._open_folder)
        self.open_folder_btn.grid(row=1, column=0, padx=6, pady=6, sticky="nsew")

        self.settings_btn = ctk.CTkButton(actions_card, text="⚙  Settings", font=(gf, 11, "bold"), fg_color=self.C_BTN, hover_color=self.C_BTN_HOVER, text_color=self.C_TEXT, corner_radius=BTN_RADIUS, height=48, command=self._open_settings)
        self.settings_btn.grid(row=1, column=1, padx=6, pady=6, sticky="nsew")

        monitor = ctk.CTkFrame(content, fg_color=self.C_CARD, bg_color=self.C_BG, corner_radius=CARD_RADIUS, border_width=1, border_color=self.C_BORDER)
        monitor.grid(row=2, column=1, padx=(3, 6), pady=(3, 6), sticky="nsew")
        monitor.grid_rowconfigure(2, weight=1)
        monitor.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(monitor, text="Process Monitor", text_color=self.C_MUTED, font=(gf, 12, "bold")).grid(row=0, column=0, sticky="w", padx=16, pady=(12, 4))
        status_frame = ctk.CTkFrame(monitor, fg_color="transparent", bg_color=self.C_CARD)
        status_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))

        self.status_label = ctk.CTkLabel(status_frame, text="System Ready", text_color=ACCENT_GREEN, font=(gf, 11), width=350, anchor="w")
        self.status_label.pack(side="left")
        self.progress_label = ctk.CTkLabel(status_frame, text="0%", text_color=self.C_MUTED, font=(gf, 11), width=50, anchor="e")
        self.progress_label.pack(side="right")
        self.progress_bar = ctk.CTkProgressBar(status_frame, height=6, fg_color=self.C_BORDER, progress_color=ACCENT_BLUE)
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(12, 8))
        self.progress_bar.set(0.0)

        self.console = ctk.CTkTextbox(monitor, fg_color=("#F8F8FA", "#1C1C1E"), text_color=self.C_TEXT, font=self.F_CONSOLE, corner_radius=INPUT_RADIUS, border_color=self.C_BORDER, border_width=1)
        self.console.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        self.console.insert("end", ">> boBnox v4.0.0 initialized.\n>> Awaiting target directory...\n")
        self.console.configure(state="disabled")

    def _toggle_theme(self):
        if self.theme_switch.get() == 1:
            ctk.set_appearance_mode("Dark")
            self.theme_switch.configure(text="Dark Mode")
            self.app_config["dark_mode"] = True
        else:
            ctk.set_appearance_mode("Light")
            self.theme_switch.configure(text="Light Mode")
            self.app_config["dark_mode"] = False
        save_config(self.app_config)

    def _toggle_daemon(self):
        path = self.path_var.get()
        if self.daemon_switch.get() == 1:
            if not path or not os.path.isdir(path):
                self._log("[WARN] Select a valid directory first.")
                self.after(0, lambda: self.daemon_switch.deselect())
                return
            self._watcher = KernelInotifyDaemon(path, lambda p: self.after(0, lambda: self._handle_watched_file(p, path)))
            self._watcher.start()
            self._log(f"[DAEMON] Watching: {path}")
        else:
            if self._watcher:
                self._watcher.stop()
                self._watcher = None
                self._log("[DAEMON] Stopped.")

    def _handle_watched_file(self, file_path: str, watch_dir: str):
        try:
            self.organizer.organize_single_file(file_path, watch_dir)
            self._log(f"[DAEMON] Processed: {os.path.basename(file_path)}")
        except Exception as e:
            self._log(f"[DAEMON] Error: {str(e)}")

    def _select_directory(self):
        try:
            target = subprocess.check_output(
                ["zenity", "--file-selection", "--directory", "--title=Select Target Directory"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            if target:
                self.path_var.set(target)
                self._log(f"[INFO] Directory: {target}")
        except subprocess.CalledProcessError:
            pass

    def _on_recursive_toggle(self):
        self.app_config["organize_subdirectories"] = self.recursive_var.get()
        self.organizer.organize_subdirectories = self.recursive_var.get()
        save_config(self.app_config)

    def _open_folder(self):
        path = self.path_var.get()
        if path and os.path.isdir(path):
            open_in_nautilus(path)

    def _open_settings(self):
        if hasattr(self, '_settings_win') and self._settings_win is not None:
            try:
                if self._settings_win.winfo_exists():
                    self._settings_win.focus()
                    return
            except Exception:
                pass
        self._settings_win = SettingsDialog(self, self.app_config, self._on_settings_save)

    def _on_settings_save(self, new_config: dict):
        self.app_config = new_config
        self.organizer.config = new_config
        self.organizer.extension_map = new_config.get("extension_map", DEFAULT_CONFIG["extension_map"])
        save_config(new_config)
        self._log("[INFO] Settings saved.")

    def _set_ui_state(self, disabled: bool):
        state = "disabled" if disabled else "normal"
        for btn in [self.organize_btn, self.undo_btn, self.open_folder_btn, self.settings_btn, self.browse_btn]:
            btn.configure(state=state)
        self.path_entry.configure(state=state)

    def _start_organizing(self):
        path = self.path_var.get().strip()
        if not path or not os.path.isdir(path):
            self._log("[WARN] Select a valid directory first.")
            return
        if self.running:
            return

        dry_run = self.dry_run_var.get()
        recursive = self.recursive_var.get()
        dedup = self.sw_dedup_var.get()
        use_mime = self.mime_sort_var.get()
        hidden = self.hidden_var.get()

        use_entropy = self.entropy_var.get()

        self.organizer.conflict_resolver = GtkConflictResolver(default_strategy=self.collision_var.get())
        template = self.template_var.get().strip()
        self.organizer.dest_pattern = template if template else None
        self.organizer.organize_subdirectories = recursive
        self.app_config["create_log_file"] = self.log_file_var.get()

        self.running = True
        self.resizable(False, False)
        self._set_ui_state(True)
        self.after(0, lambda: self.status_label.configure(text="Processing...", text_color="#FFD60A"))
        self.after(0, lambda: self.progress_bar.set(0.0))
        self.after(0, lambda: self.progress_label.configure(text="0%"))
        self._log(f"[INFO] Organizing: {path}")
        threading.Thread(target=self._organize_thread, args=(path, dry_run, use_mime, dedup, use_entropy, hidden), daemon=True).start()

    def _organize_thread(self, path, dry_run, use_mime, dedup, use_entropy, hidden):
        try:
            moved = self.organizer.organize_directory(
                path, self._update_status, dry_run=dry_run,
                use_mime=use_mime, dedup_scan=dedup,
                use_entropy=use_entropy, include_hidden=hidden
            )
            msg = f"Preview: {moved} files." if dry_run and moved else f"Done! Moved {moved} files." if moved else "No files to move."
            self.after(0, lambda: self._log(f"\n[DONE] {msg}"))
            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=ACCENT_GREEN))
            self.after(0, lambda: self.progress_label.configure(text="100%"))
            self.after(0, lambda: self.undo_btn.configure(state="normal" if moved > 0 and not dry_run else "disabled"))
            self.after(0, lambda: self.ledger_status.configure(text=f"Pending: {self.organizer.ledger.get_pending_count()}"))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self._log(f"[ERROR] {err}"))
            self.after(0, lambda: self.status_label.configure(text="Error", text_color=ACCENT_CORAL))
        finally:
            self.running = False
            self.after(0, lambda: self.resizable(True, True))
            self.after(0, lambda: self._set_ui_state(False))

    def _update_status(self, message: str, progress: float):
        self.after(0, lambda: self._do_update_status(message, progress))

    def _do_update_status(self, message: str, progress: float):
        # Truncate long messages to prevent label reflow
        display = message[:50] + "..." if len(message) > 50 else message
        self.status_label.configure(text=display, text_color=self.C_TEXT)
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"{int(progress * 100)}%")
        self._log(f"  {message}")

    def _undo_action(self):
        if self.running:
            return
        self.running = True
        self.resizable(False, False)
        self._set_ui_state(True)
        self.after(0, lambda: self.status_label.configure(text="Undoing...", text_color="#FFD60A"))
        threading.Thread(target=self._undo_thread, daemon=True).start()

    def _undo_thread(self):
        try:
            try:
                limit = int(self.undo_limit_var.get())
                limit = max(1, min(limit, 500))
            except ValueError:
                limit = 10
            restored = self.organizer.ledger.rollback_latest(limit=limit)
            self.after(0, lambda: self._log(f"\n[DONE] Restored {restored} files (limit: {limit})."))
            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=ACCENT_GREEN))
            self.after(0, lambda: self.ledger_status.configure(text=f"Pending: {self.organizer.ledger.get_pending_count()}"))
            self.after(0, lambda: self.undo_btn.configure(state="disabled"))
        except Exception as e:
            err = str(e)
            self.after(0, lambda: self._log(f"[ERROR] Undo failed: {err}"))
        finally:
            self.running = False
            self.after(0, lambda: self.resizable(True, True))
            self.after(0, lambda: self._set_ui_state(False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("organize", "undo", "dedup", "config"):
        BobnoxCLI().execute()
    else:
        app = BoBnoxApp()
        app.mainloop()
