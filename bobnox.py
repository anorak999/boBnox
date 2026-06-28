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

# ======================================================================
# DESIGN TOKENS - Unified Bento styling constants
# ======================================================================
APP_RADIUS = 16
CARD_RADIUS = 12
BTN_RADIUS = 8
INPUT_RADIUS = 8

BG_DARK = "#0D0D0D"
CARD_DARK = "#1A1A1A"
BG_LIGHT = "#F2F2F7"
CARD_LIGHT = "#FFFFFF"

TEXT_DARK = "#FFFFFF"
TEXT_LIGHT = "#000000"
MUTED_DARK = "#8E8E93"
MUTED_LIGHT = "#636366"
BORDER_DARK = "#2C2C2E"
BORDER_LIGHT = "#D1D1D6"
ENTRY_DARK = "#0D0D0D"
ENTRY_LIGHT = "#E5E5EA"
BTN_DARK = "#2C2C2E"
BTN_LIGHT = "#E5E5EA"
BTN_HOVER_DARK = "#3A3A3C"
BTN_HOVER_LIGHT = "#D1D1D6"

ACCENT_BLUE = "#005CE6"
ACCENT_GREEN = "#22C85A"
ACCENT_CORAL = "#FF4F31"

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
            return "Uncategorized"
        main_type = mime_type.split('/')[0]
        category_map = {
            "image": "Images", "video": "Videos", "audio": "Audio",
            "application": "Documents", "text": "Text Documents",
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
        for fp in Path(target_dir).rglob('*'):
            if fp.is_file():
                file_hash = self.compute_sha256(str(fp))
                if file_hash in self.hash_registry:
                    duplicates.append({"path": str(fp), "original": self.hash_registry[file_hash], "hash": file_hash})
                else:
                    self.hash_registry[file_hash] = str(fp)
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
    def validate_file(file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        file_stat = os.lstat(file_path)
        if stat.S_ISLNK(file_stat.st_mode):
            logger.warning(f"Quarantined symlink: {file_path}")
            return False
        if file_stat.st_uid == 0:
            logger.warning(f"Quarantined root-owned: {file_path}")
            return False
        if os.path.basename(file_path).startswith('.'):
            return False
        if not os.access(file_path, os.W_OK):
            logger.warning(f"Write denied: {file_path}")
            return False
        return True


# ======================================================================
# FEATURE 8: GTK File-Conflict Portal
# ======================================================================
class GtkConflictResolver:
    @staticmethod
    def prompt_resolution(target_path: str) -> str:
        filename = os.path.basename(target_path)
        cmd = [
            "zenity", "--list", "--title=boBnox Collision Alert",
            "--text", f"File collision: {filename}\nDestination exists. Choose action:",
            "--radiolist", "--column=Select", "--column=Action",
            "TRUE", "Smart Rename", "FALSE", "Overwrite", "FALSE", "Skip"
        ]
        try:
            result = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
            return result
        except subprocess.CalledProcessError:
            return "Skip"

    def handle_collision(self, src: str, dest: str) -> Optional[str]:
        if not os.path.exists(dest):
            return dest
        action = self.prompt_resolution(dest)
        if action == "Overwrite":
            return dest
        elif action == "Smart Rename":
            base, ext = os.path.splitext(dest)
            counter = 1
            new_dest = f"{base}_{counter}{ext}"
            while os.path.exists(new_dest):
                counter += 1
                new_dest = f"{base}_{counter}{ext}"
            return new_dest
        return None


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
        '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives', '.tar': 'Archives', '.gz': 'Archives',
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
        self.token_parser = TokenParser()
        self.dest_pattern = None
        self.conflict_resolver = GtkConflictResolver()
        self.guard = PosixGuard()

    def organize_directory(self, directory_path: str, status_callback, dry_run: bool = False,
                           use_mime: bool = False, dedup_scan: bool = False) -> int:
        if not os.path.isdir(directory_path):
            raise FileNotFoundError("Invalid directory.")

        directory = Path(directory_path)

        if dedup_scan:
            duplicates = self.dedup_engine.scan_directory(directory_path)
            if duplicates:
                status_callback(f"Found {len(duplicates)} duplicates.", 0.0)
                self.dedup_engine.reset()

        if self.organize_subdirectories:
            files_to_move = [f for f in directory.rglob('*') if f.is_file() and f.name != os.path.basename(__file__)]
        else:
            files_to_move = [f for f in directory.iterdir() if f.is_file() and f.name != os.path.basename(__file__)]

        files_to_move = [f for f in files_to_move if self.guard.validate_file(str(f))]
        total = len(files_to_move)
        moved = 0
        if total == 0:
            status_callback("No files to organize.", 1.0)
            return 0

        self._move_history.clear()

        for i, fp in enumerate(files_to_move):
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
                    self._move_history.append((dest_path, fp))
                    moved += 1
                except Exception as ex:
                    logger.error(f"Failed: {fp.name}: {ex}")
                    continue
            else:
                moved += 1

            status_callback(f"{'Would move' if dry_run else 'Moving'} ({i+1}/{total}): {fp.relative_to(directory)} -> {folder_name}", (i+1)/total)

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
# SETTINGS DIALOG
# ======================================================================
class SettingsDialog(ctk.CTkToplevel):
    def __init__(self, parent, config: dict, on_save_callback):
        super().__init__(parent)
        self.config = config.copy()
        self.on_save = on_save_callback
        self.title("Settings")
        self.geometry("520x620")
        self.resizable(False, False)
        self.grab_set()

        # Determine current theme
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg = BG_DARK if is_dark else BG_LIGHT
        card = CARD_DARK if is_dark else CARD_LIGHT
        text = TEXT_DARK if is_dark else TEXT_LIGHT
        muted = MUTED_DARK if is_dark else MUTED_LIGHT
        border = BORDER_DARK if is_dark else BORDER_LIGHT
        entry_bg = ENTRY_DARK if is_dark else ENTRY_LIGHT

        self.configure(fg_color=bg)

        # Main BentoCard container
        main_card = ctk.CTkFrame(self, fg_color=card, corner_radius=APP_RADIUS)
        main_card.pack(fill="both", expand=True, padx=12, pady=12)

        # Header
        ctk.CTkLabel(main_card, text="⚙ Settings", font=("Geist", 18, "bold"), text_color=text).pack(anchor="w", padx=20, pady=(20, 8))
        ctk.CTkFrame(main_card, height=1, fg_color=border).pack(fill="x", padx=20, pady=(0, 12))

        # Scrollable extension list
        self.scroll_frame = ctk.CTkScrollableFrame(main_card, fg_color=card, corner_radius=CARD_RADIUS, border_color=border, border_width=1)
        self.scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        # Buttons
        btn_frame = ctk.CTkFrame(main_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(btn_frame, text="💾 Save", font=("Geist", 13, "bold"), fg_color=ACCENT_BLUE, hover_color="#004BB3", height=36, corner_radius=BTN_RADIUS, command=self._save).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="Cancel", font=("Geist", 13), fg_color=BTN_DARK if is_dark else BTN_LIGHT, hover_color=BTN_HOVER_DARK if is_dark else BTN_HOVER_LIGHT, text_color=text, height=36, corner_radius=BTN_RADIUS, command=self.destroy).pack(side="left")

        self.extension_entries = {}
        self.after(30, self._render_mappings)

    def _render_mappings(self):
        is_dark = ctk.get_appearance_mode() == "Dark"
        text = TEXT_DARK if is_dark else TEXT_LIGHT
        muted = MUTED_DARK if is_dark else MUTED_LIGHT
        entry_bg = ENTRY_DARK if is_dark else ENTRY_LIGHT
        border = BORDER_DARK if is_dark else BORDER_LIGHT
        card = CARD_DARK if is_dark else CARD_LIGHT

        for ext, folder in sorted(self.config.get("extension_map", {}).items()):
            row = ctk.CTkFrame(self.scroll_frame, fg_color=card, corner_radius=CARD_RADIUS)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=ext, font=("Geist", 13, "bold"), text_color=muted, width=80).pack(side="left", padx=(12, 8), pady=8)
            entry = ctk.CTkEntry(row, font=("Geist", 13), fg_color=entry_bg, border_color=border, text_color=text, corner_radius=INPUT_RADIUS, height=32)
            entry.insert(0, folder)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)
            self.extension_entries[ext] = entry

    def _save(self):
        for ext, entry in self.extension_entries.items():
            self.config["extension_map"][ext] = entry.get()
        self.on_save(self.config)
        self.destroy()


# ======================================================================
# MAIN APPLICATION (Bento UI)
# ======================================================================
class BoBnoxApp(ctk.CTk):

    def __init__(self):
        super().__init__(className="bobnox")

        self.app_config = load_config()
        self.organizer = FileOrganizer(self.app_config)
        self.log_messages = []

        self.title("BoBnox v2.0.4")
        self.geometry("1100x800")
        self.minsize(900, 650)

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

        # Color tuples using design tokens: ("light", "dark")
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
        self.F_CONSOLE = ("Courier", 12)

        self.path_var = tk.StringVar()
        self.dry_run_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=self.app_config.get("organize_subdirectories", False))
        self.daemon_var = tk.BooleanVar(value=False)
        self.use_mime_var = tk.BooleanVar(value=False)
        self.dedup_var = tk.BooleanVar(value=False)

        self._watcher = None

        self.grid_columnconfigure(0, weight=0, minsize=220)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        ctk.set_appearance_mode("Dark" if self.app_config.get("dark_mode", True) else "Light")

        self._create_widgets()

    def _create_widgets(self):
        # --- SIDEBAR ---
        sidebar = ctk.CTkFrame(self, width=220, fg_color=self.C_CARD, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)

        ctk.CTkLabel(sidebar, text="boBnox", font=self.F_TITLE, text_color=self.C_TEXT).pack(pady=(24, 4), padx=20, anchor="w")
        ctk.CTkLabel(sidebar, text="v2.0.4", font=self.F_SUB, text_color=self.C_MUTED).pack(padx=20, anchor="w")

        ctk.CTkFrame(sidebar, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=16)

        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(sidebar, text="Dark Mode", command=self._toggle_theme, font=self.F_LABEL, text_color=self.C_TEXT, progress_color=ACCENT_BLUE, fg_color=self.C_BORDER)
        self.theme_switch.pack(anchor="w", padx=20, pady=8)
        if self.app_config.get("dark_mode", True):
            self.theme_switch.select()
        else:
            self.theme_switch.deselect()
            self.theme_switch.configure(text="Light Mode")

        ctk.CTkFrame(sidebar, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(sidebar, text="Engine", font=self.F_SUB, text_color=self.C_MUTED).pack(anchor="w", padx=20, pady=(8, 4))
        self.daemon_switch = ctk.CTkSwitch(sidebar, text="Daemon (inotify)", font=self.F_LABEL, text_color=self.C_TEXT, progress_color=ACCENT_GREEN, fg_color=self.C_BORDER, command=self._toggle_daemon)
        self.daemon_switch.pack(anchor="w", padx=20, pady=4)
        self.mime_switch = ctk.CTkSwitch(sidebar, text="MIME Sorting", font=self.F_LABEL, text_color=self.C_TEXT, progress_color=ACCENT_BLUE, fg_color=self.C_BORDER)
        self.mime_switch.pack(anchor="w", padx=20, pady=4)

        ctk.CTkFrame(sidebar, height=1, fg_color=self.C_BORDER).pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(sidebar, text="Ledger", font=self.F_SUB, text_color=self.C_MUTED).pack(anchor="w", padx=20, pady=(8, 4))
        self.ledger_status = ctk.CTkLabel(sidebar, text=f"Pending: {self.organizer.ledger.get_pending_count()}", font=self.F_LABEL, text_color=ACCENT_GREEN)
        self.ledger_status.pack(anchor="w", padx=20, pady=4)

        # --- MAIN CONTENT ---
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=0, column=1, padx=16, pady=16, sticky="nsew")
        content.grid_columnconfigure(0, weight=3)
        content.grid_columnconfigure(1, weight=2)
        content.grid_rowconfigure(2, weight=1)

        # Row 0: Branding + Options
        brand = ctk.CTkFrame(content, fg_color=self.C_CARD, corner_radius=APP_RADIUS)
        brand.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(brand, text="boBnox", text_color=self.C_TEXT, font=self.F_TITLE).pack(anchor="w", padx=24, pady=(20, 4))
        ctk.CTkLabel(brand, text="Organize your files into categorized folders", text_color=self.C_MUTED, font=self.F_LABEL).pack(anchor="w", padx=24, pady=(0, 16))

        opts = ctk.CTkFrame(content, fg_color=self.C_CARD, corner_radius=APP_RADIUS)
        opts.grid(row=0, column=1, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(opts, text="Options", text_color=self.C_MUTED, font=self.F_SUB).pack(anchor="w", padx=24, pady=(16, 8))
        self.sw_dry = ctk.CTkSwitch(opts, text="⏀ Dry Run", variable=self.dry_run_var, font=self.F_LABEL, text_color=self.C_TEXT, progress_color=ACCENT_BLUE, fg_color=self.C_BORDER)
        self.sw_dry.pack(anchor="w", padx=24, pady=6)
        self.sw_rec = ctk.CTkSwitch(opts, text="⟲ Recursive", variable=self.recursive_var, font=self.F_LABEL, text_color=self.C_TEXT, progress_color=ACCENT_BLUE, fg_color=self.C_BORDER, command=self._on_recursive_toggle)
        self.sw_rec.pack(anchor="w", padx=24, pady=6)
        self.sw_dedup = ctk.CTkSwitch(opts, text="⎔ Dedup Scan", variable=self.dedup_var, font=self.F_LABEL, text_color=self.C_TEXT, progress_color=ACCENT_BLUE, fg_color=self.C_BORDER)
        self.sw_dedup.pack(anchor="w", padx=24, pady=(6, 16))

        # Row 1: Path
        path_card = ctk.CTkFrame(content, fg_color=self.C_CARD, corner_radius=APP_RADIUS)
        path_card.grid(row=1, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        ctk.CTkLabel(path_card, text="Target Directory", text_color=self.C_MUTED, font=self.F_SUB).pack(anchor="w", padx=24, pady=(14, 6))
        pf = ctk.CTkFrame(path_card, fg_color="transparent")
        pf.pack(fill="x", padx=20, pady=(0, 18))
        self.path_entry = ctk.CTkEntry(pf, placeholder_text="Select directory...", fg_color=self.C_ENTRY, border_color=self.C_BORDER, text_color=self.C_TEXT, font=self.F_CONSOLE, height=38, corner_radius=BTN_RADIUS, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.browse_btn = ctk.CTkButton(pf, text="Browse", font=self.F_BTN, fg_color=ACCENT_BLUE, hover_color="#004BB3", height=38, width=110, corner_radius=BTN_RADIUS, command=self._select_directory)
        self.browse_btn.pack(side="left")

        # Row 2: Command Center (Buttons + Status + Console)
        cmd_center = ctk.CTkFrame(content, fg_color=self.C_CARD, corner_radius=APP_RADIUS)
        cmd_center.grid(row=2, column=0, columnspan=2, padx=8, pady=8, sticky="nsew")
        cmd_center.grid_rowconfigure(2, weight=1)
        cmd_center.grid_columnconfigure(0, weight=1)

        # Button row
        btn_row = ctk.CTkFrame(cmd_center, fg_color="transparent")
        btn_row.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 12))

        self.organize_img = None
        if os.path.exists(SVG_PATH):
            try:
                import cairosvg, io
                from PIL import Image as PILImage
                png_data = cairosvg.svg2png(url=SVG_PATH, output_width=18, output_height=18)
                img = PILImage.open(io.BytesIO(png_data)).convert('RGBA')
                self.organize_img = ctk.CTkImage(light_image=img, dark_image=img, size=(18, 18))
            except Exception:
                pass

        org_kw = dict(text="▶ Organize", font=self.F_BTN, fg_color=ACCENT_GREEN, hover_color="#1B9E46", text_color="#000000", height=40, corner_radius=BTN_RADIUS, command=self._start_organizing)
        if self.organize_img:
            org_kw["image"] = self.organize_img
            org_kw["compound"] = "left"
        self.organize_btn = ctk.CTkButton(btn_row, **org_kw)
        self.organize_btn.pack(side="left", fill="x", expand=True, padx=4)

        self.undo_btn = ctk.CTkButton(btn_row, text="⟲ Undo", font=self.F_BTN, fg_color=self.C_BTN, hover_color=self.C_BTN_HOVER, text_color=self.C_TEXT, height=40, corner_radius=BTN_RADIUS, command=self._undo_action, state="disabled")
        self.undo_btn.pack(side="left", fill="x", expand=True, padx=4)

        self.open_folder_btn = ctk.CTkButton(btn_row, text="📁 Open", font=self.F_BTN, fg_color=self.C_BTN, hover_color=self.C_BTN_HOVER, text_color=self.C_TEXT, height=40, corner_radius=BTN_RADIUS, command=self._open_folder)
        self.open_folder_btn.pack(side="left", fill="x", expand=True, padx=4)

        self.settings_btn = ctk.CTkButton(btn_row, text="⚙ Settings", font=self.F_BTN, fg_color=self.C_BTN, hover_color=self.C_BTN_HOVER, text_color=self.C_TEXT, height=40, corner_radius=BTN_RADIUS, command=self._open_settings)
        self.settings_btn.pack(side="left", fill="x", expand=True, padx=4)

        # Status header (anchored inside command block, same padx as console)
        status_header = ctk.CTkFrame(cmd_center, fg_color="transparent")
        status_header.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 6))

        self.status_label = ctk.CTkLabel(status_header, text="System Ready", text_color=ACCENT_GREEN, font=self.F_SUB)
        self.status_label.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(status_header, height=6, fg_color=self.C_BORDER, progress_color=ACCENT_BLUE)
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=(16, 0))
        self.progress_bar.set(0.0)

        # Console (same padx as status header for alignment)
        self.console = ctk.CTkTextbox(cmd_center, fg_color=self.C_ENTRY, text_color=self.C_TEXT, font=self.F_CONSOLE, corner_radius=BTN_RADIUS, border_color=self.C_BORDER, border_width=1)
        self.console.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.console.insert("end", ">> boBnox v2.0.3 initialized.\n>> Awaiting target directory...\n")
        self.console.configure(state="disabled")

    # --- Theme ---
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

    # --- Daemon ---
    def _toggle_daemon(self):
        path = self.path_var.get()
        if self.daemon_var.get() or self.daemon_switch.get() == 1:
            if not path or not os.path.isdir(path):
                self._log("[WARN] Select a valid directory first.")
                self.daemon_switch.deselect()
                return
            self._watcher = DirectoryWatcher(path, lambda p: self.organizer.organize_single_file(p, path))
            self._watcher.start()
            self._log(f"[DAEMON] Watching: {path}")
        else:
            if self._watcher:
                self._watcher.stop()
                self._watcher = None
                self._log("[DAEMON] Stopped.")

    # --- Actions ---
    def _log(self, msg: str):
        self.log_messages.append(msg)
        self.console.configure(state="normal")
        self.console.insert("end", msg + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

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
        SettingsDialog(self, self.app_config, self._on_settings_save)

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
        self.sw_dry.configure(state=state)
        self.sw_rec.configure(state=state)
        self.sw_dedup.configure(state=state)
        self.path_entry.configure(state=state)

    def _start_organizing(self):
        path = self.path_var.get()
        if not path or not os.path.isdir(path):
            self._log("[ERROR] Select a valid directory.")
            return
        self._set_ui_state(True)
        self.status_label.configure(text="Processing...", text_color="#FFD60A")
        self.progress_bar.set(0.0)
        self._log(f"[INFO] Organizing: {path}")
        threading.Thread(target=self._organize_thread, args=(path, self.dry_run_var.get()), daemon=True).start()

    def _organize_thread(self, path: str, dry_run: bool):
        try:
            self.organizer.organize_subdirectories = self.recursive_var.get()
            moved = self.organizer.organize_directory(
                path, self._update_status, dry_run=dry_run,
                use_mime=self.mime_switch.get() == 1,
                dedup_scan=self.dedup_var.get()
            )
            msg = f"Preview: {moved} files." if dry_run and moved else f"Done! Moved {moved} files." if moved else "No files to move."
            self._log(f"\n[DONE] {msg}")
            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=ACCENT_GREEN))
            self.after(0, lambda: self.undo_btn.configure(state="normal" if moved > 0 and not dry_run else "disabled"))
            self.after(0, lambda: self.ledger_status.configure(text=f"Pending: {self.organizer.ledger.get_pending_count()}"))
            self.after(0, lambda: self._set_ui_state(False))
        except Exception as e:
            self._log(f"[ERROR] {e}")
            self.after(0, lambda: self.status_label.configure(text="Error", text_color=ACCENT_CORAL))
            self.after(0, lambda: self._set_ui_state(False))

    def _update_status(self, message: str, progress: float):
        self.after(0, lambda: self._do_update_status(message, progress))

    def _do_update_status(self, message: str, progress: float):
        self.status_label.configure(text=message, text_color=self.C_TEXT)
        self.progress_bar.set(progress)
        self._log(f"  {message}")

    def _undo_action(self):
        self._set_ui_state(True)
        self.status_label.configure(text="Undoing...", text_color="#FFD60A")
        threading.Thread(target=self._undo_thread, daemon=True).start()

    def _undo_thread(self):
        try:
            restored = self.organizer.undo_last_organization(self._update_status)
            self._log(f"\n[DONE] Restored {restored} files.")
            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=ACCENT_GREEN))
            self.after(0, lambda: self._set_ui_state(False))
            self.after(0, lambda: self.ledger_status.configure(text=f"Pending: {self.organizer.ledger.get_pending_count()}"))
            self.after(0, lambda: self.undo_btn.configure(state="disabled"))
        except Exception as e:
            self._log(f"[ERROR] Undo failed: {e}")
            self.after(0, lambda: self._set_ui_state(False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("organize", "undo", "dedup", "config"):
        BobnoxCLI().execute()
    else:
        app = BoBnoxApp()
        app.mainloop()
