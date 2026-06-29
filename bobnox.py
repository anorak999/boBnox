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

__version__ = "5.0.0"

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
CONFIG_DIR = Path.home() / ".config" / "bobnox"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_FILE = CONFIG_DIR / "undo_history.json"

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
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

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

    def get_history(self, limit: int = 200, filter_str: str = "") -> list:
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, source_path, target_path, timestamp, status FROM file_operations ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        if filter_str:
            filt = filter_str.lower()
            rows = [(r_id, src, dest, ts, st) for r_id, src, dest, ts, st in rows
                    if filt in os.path.basename(src).lower() or filt in os.path.basename(dest).lower()]
        return [{"id": r_id, "source": src, "dest": dest, "timestamp": ts, "status": st}
                for r_id, src, dest, ts, st in rows]


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
# FEATURE 8: Conflict Resolution
# ======================================================================
class GtkConflictResolver:
    def __init__(self, default_strategy: str = "SMART_RENAME"):
        self.default_strategy = default_strategy

    def handle_collision(self, src: str, dest: str) -> Optional[str]:
        if not os.path.exists(dest):
            return dest
        action = self.default_strategy
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
        elif action == "SKIP":
            return None
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
            ".pdf": b"\x25\x50\x44\x46",
            ".zip": b"\x50\x4B\x03\x04", ".jar": b"\x50\x4B\x03\x04",
            ".rar": b"\x52\x61\x72\x21", ".7z": b"\x37\x7A\xBC\xAF",
            ".gz": b"\x1F\x8B", ".bz2": b"\x42\x5A\x68",
            ".tar": None,
            ".png": b"\x89\x50\x4E\x47", ".jpg": b"\xFF\xD8\xFF",
            ".gif": b"\x47\x49\x46\x38", ".bmp": b"\x42\x4D",
            ".tiff": b"\x49\x49\x2A\x00", ".tif": b"\x49\x49\x2A\x00",
            ".webp": b"\x52\x49\x46\x46", ".ico": b"\x00\x00\x01\x00",
            ".heic": b"\x66\x74\x79\x70", ".heif": b"\x66\x74\x79\x70",
            ".mp3": b"\x49\x44\x33", ".wav": b"\x52\x49\x46\x46",
            ".flac": b"\x66\x4C\x61\x43", ".ogg": b"\x4F\x67\x67\x53",
            ".aac": b"\xFF\xF1", ".m4a": b"\x66\x74\x79\x70",
            ".mp4": b"\x00\x00\x00\x18", ".mov": b"\x66\x74\x79\x70",
            ".avi": b"\x52\x49\x46\x46", ".mkv": b"\x1A\x45\xDF\xA3",
            ".webm": b"\x1A\x45\xDF\xA3", ".flv": b"\x46\x4C\x56\x01",
            ".wmv": b"\x30\x26\xB2\x75",
            ".exe": b"\x4D\x5A", ".msi": b"\xD0\xCF\x11\xE0",
            ".dll": b"\x4D\x5A", ".so": b"\x7F\x45\x4C\x46",
            ".elf": b"\x7F\x45\x4C\x46",
            ".ttf": b"\x00\x01\x00\x00", ".otf": b"\x4F\x54\x54\x4F",
            ".woff": b"\x77\x4F\x46\x46", ".woff2": b"\x77\x4F\x46\x32",
            ".py": None, ".js": None, ".html": None, ".css": None,
            ".java": None, ".cpp": None, ".c": None, ".h": None,
            ".sh": None, ".bash": None, ".zsh": None, ".fish": None,
            ".rb": None, ".php": None, ".pl": None, ".pm": None,
            ".go": None, ".rs": None, ".cs": None, ".ts": None,
            ".jsx": None, ".tsx": None, ".vue": None, ".svelte": None,
            ".json": None, ".xml": None, ".yaml": None, ".yml": None,
            ".toml": None, ".ini": None, ".cfg": None, ".conf": None,
            ".md": None, ".txt": None, ".log": None, ".rtf": None,
            ".csv": None, ".tsv": None, ".sql": None,
            ".scss": None, ".sass": None, ".less": None,
            ".lock": None, ".theme": None,
            ".makefile": None, ".cmake": None, ".gradle": None,
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
        return {"status": "MISMATCH", "action": "WARN", "ext": ext}


# ======================================================================
# FEATURE 13: Shannon Entropy Analytics
# ======================================================================
class ShannonEntropyAnalyzer:
    def calculate_entropy(self, file_path: str) -> float:
        if not os.path.exists(file_path) or os.path.islink(file_path):
            return 0.0
        size = os.path.getsize(file_path)
        if size == 0 or size > 100_000_000:
            return 0.0
        try:
            with open(file_path, "rb") as f:
                data = f.read(min(size, 1_000_000))
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
        known_media_exts = {
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif', '.ico',
            '.tiff', '.tif', '.raw', '.cr2', '.nef', '.arw', '.psd', '.svg',
            '.mp3', '.wav', '.aac', '.flac', '.ogg', '.m4a', '.wma', '.opus', '.aiff', '.mid', '.midi',
            '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.vob',
            '.zip', '.7z', '.rar', '.tar', '.gz', '.bz2', '.xz', '.zst', '.tgz',
            '.torrent', '.iso', '.img', '.deb', '.rpm',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.ttf', '.otf', '.woff', '.woff2', '.eot',
            '.stl', '.obj', '.fbx', '.blend',
        }
        if ext in known_media_exts:
            tier, action = "KNOWN_MEDIA", "STANDARD_SORT"
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
# CONFIGURATION
# ======================================================================
DEFAULT_CONFIG = {
    "extension_map": {
        '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
        '.bmp': 'Images', '.svg': 'Images', '.tiff': 'Images', '.tif': 'Images',
        '.webp': 'Images', '.heic': 'Images', '.heif': 'Images', '.ico': 'Images',
        '.raw': 'Images', '.cr2': 'Images', '.nef': 'Images', '.arw': 'Images',
        '.psd': 'Images', '.ai': 'Images', '.eps': 'Images', '.indd': 'Images',
        '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
        '.rtf': 'Documents', '.odt': 'Documents', '.pages': 'Documents',
        '.epub': 'Documents', '.mobi': 'Documents',
        '.txt': 'Text Documents', '.md': 'Text Documents', '.markdown': 'Text Documents',
        '.log': 'Text Documents', '.ini': 'Text Documents', '.cfg': 'Text Documents',
        '.conf': 'Text Documents', '.env': 'Text Documents', '.properties': 'Text Documents',
        '.xls': 'Spreadsheets', '.xlsx': 'Spreadsheets', '.csv': 'Spreadsheets',
        '.tsv': 'Spreadsheets', '.ods': 'Spreadsheets', '.numbers': 'Spreadsheets',
        '.ppt': 'Presentations', '.pptx': 'Presentations', '.key': 'Presentations',
        '.odp': 'Presentations',
        '.mp3': 'Audio', '.wav': 'Audio', '.aac': 'Audio', '.flac': 'Audio',
        '.ogg': 'Audio', '.m4a': 'Audio', '.wma': 'Audio', '.opus': 'Audio',
        '.aiff': 'Audio', '.mid': 'Audio', '.midi': 'Audio',
        '.mp4': 'Videos', '.mov': 'Videos', '.avi': 'Videos', '.mkv': 'Videos',
        '.wmv': 'Videos', '.flv': 'Videos', '.webm': 'Videos', '.m4v': 'Videos',
        '.mpg': 'Videos', '.mpeg': 'Videos', '.3gp': 'Videos', '.vob': 'Videos',
        '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives', '.tar': 'Archives',
        '.gz': 'Archives', '.bz2': 'Archives', '.xz': 'Archives', '.zst': 'Archives',
        '.tar.gz': 'Archives', '.tgz': 'Archives', '.tar.bz2': 'Archives',
        '.tar.xz': 'Archives', '.deb': 'Archives', '.rpm': 'Archives',
        '.torrent': 'Archives', '.iso': 'Archives', '.img': 'Archives',
        '.html': 'Web Files', '.htm': 'Web Files', '.css': 'Web Files',
        '.scss': 'Code', '.sass': 'Code', '.less': 'Code',
        '.js': 'Scripts', '.jsx': 'Code', '.ts': 'Code', '.tsx': 'Code',
        '.vue': 'Code', '.svelte': 'Code',
        '.py': 'Scripts', '.pyw': 'Scripts', '.sh': 'Scripts', '.bash': 'Scripts',
        '.zsh': 'Scripts', '.fish': 'Scripts', '.ps1': 'Scripts', '.bat': 'Scripts', '.cmd': 'Scripts',
        '.rb': 'Code', '.php': 'Code', '.pl': 'Code', '.pm': 'Code',
        '.java': 'Code', '.kt': 'Code', '.scala': 'Code', '.groovy': 'Code',
        '.go': 'Code', '.rs': 'Code', '.c': 'Code', '.h': 'Code',
        '.cpp': 'Code', '.hpp': 'Code', '.cc': 'Code', '.cxx': 'Code',
        '.cs': 'Code', '.fs': 'Code', '.vb': 'Code',
        '.json': 'Code', '.xml': 'Code', '.yaml': 'Code', '.yml': 'Code',
        '.toml': 'Code', '.ini': 'Code', '.cfg': 'Code', '.conf': 'Code',
        '.lock': 'Code', '.theme': 'Code',
        '.makefile': 'Code', '.cmake': 'Code', '.gradle': 'Code',
        '.sbt': 'Code', '.maven': 'Code',
        '.exe': 'Executables', '.msi': 'Installers', '.dmg': 'Installers',
        '.app': 'Executables', '.apk': 'Installers', '.ipa': 'Installers',
        '.appimage': 'Executables', '.snap': 'Installers', '.flatpak': 'Installers',
        '.ttf': 'Fonts', '.otf': 'Fonts', '.woff': 'Fonts', '.woff2': 'Fonts', '.eot': 'Fonts',
        '.stl': '3D Files', '.obj': '3D Files', '.fbx': '3D Files', '.blend': '3D Files',
        '.dwg': '3D Files', '.dxf': '3D Files', '.step': '3D Files', '.iges': '3D Files',
        '.db': 'Databases', '.sqlite': 'Databases', '.sql': 'Databases',
        '.mdb': 'Databases', '.accdb': 'Databases',
    },
    "organize_subdirectories": False,
    "create_log_file": True,
    "dark_mode": True,
}

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
# FILE ORGANIZER CORE
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
        self.async_processor = AsyncFileProcessor(max_workers=4)

    def _validate_and_route(self, file_path: str, directory: str,
                            use_mime: bool = False, include_hidden: bool = False) -> Optional[Path]:
        fp = Path(file_path)
        if not fp.is_file() or not self.guard.validate_file(str(fp), include_hidden=include_hidden):
            return None
        integrity = self.struct_validator.analyze_file(str(fp))
        if integrity.get("status") == "ANOMALY":
            return None
        ext = fp.suffix.lower()
        if use_mime and self.mime_validator:
            folder_name = self.mime_validator.route_by_mime(str(fp))
        else:
            folder_name = self.extension_map.get(ext, f"{ext[1:].upper()} Files" if ext else "Other Files")
        return Path(directory) / folder_name / fp.name

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

        move_map = {}
        skip_anomaly = set()
        for i, fp in enumerate(files_to_move):
            integrity = self.struct_validator.analyze_file(str(fp))
            if integrity.get("status") == "ANOMALY":
                status_callback(f"[ANOMALY] {fp.name} — magic byte mismatch, quarantined", (i + 1) / total)
                skip_anomaly.add(str(fp))
                continue
            if integrity.get("status") == "MISMATCH":
                status_callback(f"[WARN] {fp.name} — magic bytes don't match {integrity.get('ext', '?')}, sorting by extension", (i + 1) / total)

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

            move_map[str(fp)] = str(dest_path)
            status_callback(f"{'Would move' if dry_run else 'Queued'} ({i+1}/{total}): {fp.relative_to(directory)} → {folder_name}", (i + 1) / total)

        if dry_run:
            moved = len(move_map)
        else:
            results = asyncio.run(self.async_processor.bulk_move(move_map))
            for (src, dest_p), success in zip(move_map.items(), results):
                if success:
                    self.ledger.log_move(src, dest_p)
                    self.xattr_layer.write_states(dest_p, {"moved_at": str(time.time()), "original_path": src})
                    self._move_history.append((Path(dest_p), Path(src)))
                    moved += 1
                else:
                    logger.error(f"Async move failed: {src}")

        status_callback(f"Done. Moved: {moved}  Skipped (guard): {skipped_guard}  Skipped (entropy): {skipped_entropy}", 1.0)
        return moved

    def organize_single_file(self, file_path: str, watch_dir: str, dry_run: bool = False):
        dest_path = self._validate_and_route(file_path, watch_dir)
        if dest_path is None:
            return
        if not dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(file_path), str(dest_path))
                self.ledger.log_move(str(file_path), str(dest_path))
                self.xattr_layer.write_states(str(dest_path), {"moved_at": str(time.time()), "original_path": str(file_path)})
            except Exception as e:
                logger.error(f"Watch move failed: {e}")

    def undo_last_organization(self, status_callback=None) -> int:
        restored = self.ledger.rollback_latest()
        self._move_history.clear()
        return restored


# ======================================================================
# CLI
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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("organize", "undo", "dedup", "config"):
        BobnoxCLI().execute()
    else:
        print(f"boBnox v{__version__} — backend server mode")
        print("CLI usage: python3 bobnox.py organize <path> | undo | dedup | config --show")
        print("API server: python3 -m backend.server")
