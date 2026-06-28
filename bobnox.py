import os
import sys
import shutil
import subprocess
import platform
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

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

# --- Font Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GEIST_DIR = os.path.join(SCRIPT_DIR, "Geist")
GEIST_FONT = os.path.join(GEIST_DIR, "Geist-VariableFont_wght.ttf")
GEIST_BOLD = os.path.join(GEIST_DIR, "static", "Geist-Bold.ttf")
GEIST_MEDIUM = os.path.join(GEIST_DIR, "static", "Geist-Medium.ttf")
GEIST_REGULAR = os.path.join(GEIST_DIR, "static", "Geist-Regular.ttf")
GEIST_MONO = os.path.join(GEIST_DIR, "static", "Geist-Regular.ttf")

ICON_PATH = os.path.join(SCRIPT_DIR, "BoBnox-icon", "Bobnox-icon.png")
SVG_PATH = os.path.join(SCRIPT_DIR, "assets", "Sort--Streamline-Solar.svg")

# --- File Manager Integration ---
def open_in_file_manager(path: str):
    try:
        if IS_MACOS:
            subprocess.Popen(["open", path])
        elif IS_LINUX:
            subprocess.Popen(["nautilus", path])
        else:
            subprocess.Popen(["explorer", path])
    except FileNotFoundError:
        try:
            subprocess.Popen(["xdg-open", path])
        except FileNotFoundError:
            logger.warning("No file manager found")

def select_folder_native() -> Optional[str]:
    if IS_LINUX:
        try:
            result = subprocess.run(
                ["zenity", "--file-selection", "--directory", "--title=Select Folder"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            pass
    if IS_MACOS:
        try:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Finder" to set p to POSIX path of (choose folder)'],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            pass
    return None

# --- Configuration ---
DEFAULT_CONFIG = {
    "extension_map": {
        '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
        '.bmp': 'Images', '.svg': 'Images', '.tiff': 'Images', '.webp': 'Images',
        '.heic': 'Images',
        '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
        '.txt': 'Text Documents', '.rtf': 'Documents', '.odt': 'Documents',
        '.md': 'Text Documents',
        '.xls': 'Spreadsheets', '.xlsx': 'Spreadsheets', '.csv': 'Spreadsheets',
        '.ppt': 'Presentations', '.pptx': 'Presentations',
        '.mp3': 'Audio', '.wav': 'Audio', '.aac': 'Audio', '.flac': 'Audio',
        '.ogg': 'Audio', '.m4a': 'Audio',
        '.mp4': 'Videos', '.mov': 'Videos', '.avi': 'Videos', '.mkv': 'Videos',
        '.wmv': 'Videos', '.flv': 'Videos',
        '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives', '.tar': 'Archives',
        '.gz': 'Archives',
        '.py': 'Scripts', '.js': 'Scripts', '.html': 'Web Files', '.css': 'Web Files',
        '.java': 'Code', '.cpp': 'Code', '.c': 'Code', '.sh': 'Scripts',
        '.exe': 'Executables', '.msi': 'Installers', '.dmg': 'Installers',
    },
    "organize_subdirectories": False,
    "create_log_file": True,
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
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


def load_undo_history() -> list:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_undo_history(history: list) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        return True
    except Exception:
        return False


# --- File Organizer Core ---
class FileOrganizer:

    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_config()
        self.extension_map = self.config.get("extension_map", DEFAULT_CONFIG["extension_map"])
        self.organize_subdirectories = self.config.get("organize_subdirectories", False)
        self.create_log_file = self.config.get("create_log_file", True)
        self._move_history: List[Tuple[Path, Path]] = []
        self._load_persistent_history()

    def _load_persistent_history(self):
        history = load_undo_history()
        self._move_history = [(Path(h["current"]), Path(h["original"])) for h in history]

    def _save_persistent_history(self):
        history = [{"current": str(c), "original": str(o)} for c, o in self._move_history]
        save_undo_history(history)

    def organize_directory(self, directory_path: str, status_callback, dry_run: bool = False) -> int:
        if not os.path.isdir(directory_path):
            raise FileNotFoundError("The selected path is not a valid directory.")

        directory = Path(directory_path)
        logger.info(f"Organizing: {directory_path} (dry_run={dry_run})")

        if self.organize_subdirectories:
            files_to_move = [f for f in directory.rglob('*') if f.is_file() and f.name != os.path.basename(__file__)]
        else:
            files_to_move = [f for f in directory.iterdir() if f.is_file() and f.name != os.path.basename(__file__)]

        total = len(files_to_move)
        moved = 0

        if total == 0:
            status_callback("No files to organize.", 1.0)
            return 0

        self._move_history.clear()

        for i, fp in enumerate(files_to_move):
            rel = fp.relative_to(directory)
            ext = fp.suffix.lower()
            folder_name = self.extension_map.get(ext, f"{ext[1:].upper()} Files" if ext else "Other Files")
            dest = directory / folder_name

            if not dry_run and not dest.exists():
                dest.mkdir(parents=True, exist_ok=True)

            base, e = os.path.splitext(fp.name)
            counter = 1
            dest_path = dest / fp.name
            while dest_path.exists():
                dest_path = dest / f"{base} ({counter}){e}"
                counter += 1

            if not dry_run:
                try:
                    shutil.move(str(fp), str(dest_path))
                    self._move_history.append((dest_path, fp))
                    moved += 1
                except Exception as ex:
                    logger.error(f"Failed to move {fp.name}: {ex}")
                    continue
            else:
                moved += 1

            pct = (i + 1) / total
            action = "Would move" if dry_run else "Moving"
            status_callback(f"{action} ({i + 1}/{total}): {rel} -> {folder_name}", pct)

        if not dry_run and self._move_history:
            self._save_persistent_history()

        return moved

    def undo_last_organization(self, status_callback) -> int:
        if not self._move_history:
            status_callback("Nothing to undo.", 1.0)
            return 0

        total = len(self._move_history)
        restored = 0

        for i, (cur, orig) in enumerate(self._move_history):
            if cur.exists():
                orig.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(cur), str(orig))
                    restored += 1
                except Exception as ex:
                    logger.error(f"Failed to restore {cur.name}: {ex}")
            status_callback(f"Restoring ({i + 1}/{total}): {cur.name}", (i + 1) / total)

        self._move_history.clear()
        self._save_persistent_history()
        return restored


# --- Settings Dialog ---
class SettingsDialog(ctk.CTkToplevel):

    def __init__(self, parent, config: dict, on_save_callback):
        super().__init__(parent)
        self.config = config.copy()
        self.on_save = on_save_callback
        self.title("Settings")
        self.geometry("520x620")
        self.configure(fg_color="#0D0D0D")
        self.resizable(False, False)
        self.grab_set()

        self.FONT_LABEL = ("Geist", 13)
        self.FONT_TITLE = ("Geist", 18, "bold")
        self.BG_CARD = "#1A1A1A"
        self.TEXT_MAIN = "#FFFFFF"
        self.TEXT_MUTED = "#8E8E93"
        self.ACCENT = "#005CE6"

        self.extension_entries = {}
        self._create_widgets()

    def _create_widgets(self):
        header = ctk.CTkLabel(self, text="Extension Mappings", font=self.FONT_TITLE, text_color=self.TEXT_MAIN)
        header.pack(anchor="w", padx=20, pady=(20, 10))

        scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#0D0D0D", corner_radius=0)
        scroll_frame.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        for ext, folder in sorted(self.config.get("extension_map", {}).items()):
            row = ctk.CTkFrame(scroll_frame, fg_color=self.BG_CARD, corner_radius=8)
            row.pack(fill="x", pady=3)

            ctk.CTkLabel(row, text=ext, font=self.FONT_LABEL, text_color=self.TEXT_MUTED, width=80).pack(side="left", padx=(12, 8), pady=8)
            entry = ctk.CTkEntry(row, font=self.FONT_LABEL, fg_color="#0D0D0D", border_color="#2C2C2E", text_color=self.TEXT_MAIN, corner_radius=6, height=32)
            entry.insert(0, folder)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)
            self.extension_entries[ext] = entry

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))

        ctk.CTkButton(btn_frame, text="Save", font=("Geist", 13, "bold"), fg_color=self.ACCENT, hover_color="#004BB3", height=38, corner_radius=8, command=self._save).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="Cancel", font=("Geist", 13), fg_color="#2C2C2E", hover_color="#3A3A3C", text_color=self.TEXT_MAIN, height=38, corner_radius=8, command=self.destroy).pack(side="left")

    def _save(self):
        for ext, entry in self.extension_entries.items():
            self.config["extension_map"][ext] = entry.get()
        self.on_save(self.config)
        self.destroy()


# --- Main Application ---
class BoBnoxApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.organizer = FileOrganizer(self.config)
        self.log_messages = []

        self.title("boBnox")
        self.geometry("900x750")
        self.configure(fg_color="#0D0D0D")

        # Set window icon
        if os.path.exists(ICON_PATH):
            try:
                self.after(100, lambda: self.iconphoto(False, tk.PhotoImage(file=ICON_PATH)))
            except Exception:
                pass

        # Colors
        self.BG_CARD = "#1A1A1A"
        self.TEXT_MAIN = "#FFFFFF"
        self.TEXT_MUTED = "#8E8E93"
        self.ACCENT_BLUE = "#005CE6"
        self.ACCENT_GREEN = "#22C85A"
        self.ACCENT_CORAL = "#FF4F31"

        # Fonts
        self.FONT_TITLE = ("Geist", 28, "bold")
        self.FONT_SUBTITLE = ("Geist", 13)
        self.FONT_LABEL = ("Geist", 14)
        self.FONT_BUTTON = ("Geist", 13, "bold")
        self.FONT_CONSOLE = ("Geist", 12)

        # Variables
        self.path_var = tk.StringVar()
        self.dry_run_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=self.config.get("organize_subdirectories", False))

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(3, weight=1)

        self._create_widgets()

    def _create_widgets(self):
        # --- CARD 1: Branding ---
        brand_card = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=16)
        brand_card.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        ctk.CTkLabel(brand_card, text="boBnox", text_color=self.TEXT_MAIN, font=self.FONT_TITLE).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(brand_card, text="Organize your files into categorized folders", text_color=self.TEXT_MUTED, font=self.FONT_SUBTITLE).pack(anchor="w", padx=20, pady=(0, 16))

        # --- CARD 2: Options ---
        config_card = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=16)
        config_card.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")

        ctk.CTkLabel(config_card, text="Options", text_color=self.TEXT_MUTED, font=self.FONT_SUBTITLE).pack(anchor="w", padx=20, pady=(16, 8))

        self.dry_run_check = ctk.CTkCheckBox(config_card, text="Dry Run (Preview only)", variable=self.dry_run_var, font=self.FONT_LABEL, text_color=self.TEXT_MAIN, hover_color=self.ACCENT_BLUE, fg_color=self.ACCENT_BLUE)
        self.dry_run_check.pack(anchor="w", padx=20, pady=6)

        self.recursive_check = ctk.CTkCheckBox(config_card, text="Include Subdirectories", variable=self.recursive_var, font=self.FONT_LABEL, text_color=self.TEXT_MAIN, hover_color=self.ACCENT_BLUE, fg_color=self.ACCENT_BLUE, command=self._on_recursive_toggle)
        self.recursive_check.pack(anchor="w", padx=20, pady=6)

        # --- CARD 3: Path Selection ---
        path_card = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=16)
        path_card.grid(row=1, column=0, columnspan=2, padx=12, pady=12, sticky="nsew")

        ctk.CTkLabel(path_card, text="Target Directory", text_color=self.TEXT_MUTED, font=self.FONT_SUBTITLE).pack(anchor="w", padx=20, pady=(12, 4))

        path_frame = ctk.CTkFrame(path_card, fg_color="transparent")
        path_frame.pack(fill="x", padx=16, pady=(0, 16))

        self.path_entry = ctk.CTkEntry(path_frame, placeholder_text="Select a directory to begin...", fg_color="#0D0D0D", border_color="#2C2C2E", text_color=self.TEXT_MAIN, font=self.FONT_CONSOLE, height=40, corner_radius=8, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Browse button with icon
        if os.path.exists(ICON_PATH):
            try:
                self._browse_icon = ctk.CTkImage(light_image=None, dark_image=None, size=(20, 20))
                from PIL import Image
                img = Image.open(ICON_PATH).resize((20, 20), Image.Resampling.LANCZOS)
                self._browse_icon = ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))
                self.browse_btn = ctk.CTkButton(path_frame, text=" Browse", image=self._browse_icon, font=self.FONT_BUTTON, fg_color=self.ACCENT_BLUE, hover_color="#004BB3", height=40, width=110, corner_radius=8, command=self._select_directory)
            except Exception:
                self.browse_btn = ctk.CTkButton(path_frame, text="Browse", font=self.FONT_BUTTON, fg_color=self.ACCENT_BLUE, hover_color="#004BB3", height=40, width=100, corner_radius=8, command=self._select_directory)
        else:
            self.browse_btn = ctk.CTkButton(path_frame, text="Browse", font=self.FONT_BUTTON, fg_color=self.ACCENT_BLUE, hover_color="#004BB3", height=40, width=100, corner_radius=8, command=self._select_directory)
        self.browse_btn.pack(side="left")

        # --- CARD 4: Actions ---
        actions_card = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=16)
        actions_card.grid(row=2, column=0, columnspan=2, padx=12, pady=12, sticky="nsew")

        actions_inner = ctk.CTkFrame(actions_card, fg_color="transparent")
        actions_inner.pack(pady=12, padx=16, fill="x")

        # Organize button with SVG icon
        self.organize_img = None
        if os.path.exists(SVG_PATH):
            try:
                import cairosvg
                from PIL import Image as PILImage
                png_data = cairosvg.svg2png(url=SVG_PATH, output_width=24, output_height=24)
                img = PILImage.open(__import__('io').BytesIO(png_data)).convert('RGBA')
                self.organize_img = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))
            except Exception:
                pass

        organize_kwargs = dict(
            text=" Organize" if self.organize_img else "Organize",
            font=self.FONT_BUTTON,
            fg_color=self.ACCENT_GREEN,
            hover_color="#1AAE4D",
            text_color="#FFFFFF",
            height=40,
            corner_radius=10,
            command=self._start_organizing
        )
        if self.organize_img:
            organize_kwargs["image"] = self.organize_img
        self.organize_btn = ctk.CTkButton(actions_inner, **organize_kwargs)
        self.organize_btn.pack(side="left", padx=(0, 10))

        self.undo_btn = ctk.CTkButton(actions_inner, text="Undo", font=self.FONT_BUTTON, fg_color="#2C2C2E", hover_color="#3A3A3C", text_color=self.TEXT_MAIN, height=40, corner_radius=8, command=self._undo_action, state="disabled")
        self.undo_btn.pack(side="left", padx=(0, 10))

        self.settings_btn = ctk.CTkButton(actions_inner, text="Settings", font=self.FONT_BUTTON, fg_color="#2C2C2E", hover_color="#3A3A3C", text_color=self.TEXT_MAIN, height=40, corner_radius=8, command=self._open_settings)
        self.settings_btn.pack(side="left", padx=(0, 10))

        self.open_folder_btn = ctk.CTkButton(actions_inner, text="Open Folder", font=self.FONT_BUTTON, fg_color="#2C2C2E", hover_color="#3A3A3C", text_color=self.TEXT_MAIN, height=40, corner_radius=8, command=self._open_folder)
        self.open_folder_btn.pack(side="left", padx=(0, 10))

        self.clear_btn = ctk.CTkButton(actions_inner, text="Clear Console", font=self.FONT_BUTTON, fg_color="transparent", hover_color="#2C2C2E", text_color=self.ACCENT_CORAL, border_color=self.ACCENT_CORAL, border_width=1, height=40, corner_radius=8, command=self._clear_log)
        self.clear_btn.pack(side="right")

        # --- CARD 5: Terminal & Status ---
        terminal_card = ctk.CTkFrame(self, fg_color=self.BG_CARD, corner_radius=16)
        terminal_card.grid(row=3, column=0, columnspan=2, padx=12, pady=(12, 20), sticky="nsew")
        terminal_card.grid_rowconfigure(2, weight=1)
        terminal_card.grid_columnconfigure(0, weight=1)

        status_frame = ctk.CTkFrame(terminal_card, fg_color="transparent")
        status_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))

        self.status_label = ctk.CTkLabel(status_frame, text="System Ready", text_color=self.ACCENT_GREEN, font=self.FONT_SUBTITLE)
        self.status_label.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(terminal_card, height=4, fg_color="#2C2C2E", progress_color=self.ACCENT_BLUE, corner_radius=2)
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        self.progress_bar.set(0.0)

        self.console = ctk.CTkTextbox(terminal_card, fg_color="#0D0D0D", text_color="#A9A9B2", font=self.FONT_CONSOLE, corner_radius=8, border_color="#2C2C2E", border_width=1)
        self.console.grid(row=2, column=0, sticky="nsew", padx=16, pady=(10, 16))
        self.console.insert("end", "[INFO] Application initialized.\n[INFO] Awaiting target directory selection...\n")
        self.console.configure(state="disabled")

    # --- Actions ---
    def _log(self, msg: str):
        self.log_messages.append(msg)
        self.console.configure(state="normal")
        self.console.insert("end", msg + "\n")
        self.console.see("end")
        self.console.configure(state="disabled")

    def _clear_log(self):
        self.log_messages.clear()
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.insert("end", "[INFO] Console cleared.\n")
        self.console.configure(state="disabled")

    def _select_directory(self):
        path = select_folder_native()
        if not path:
            try:
                path = filedialog.askdirectory()
            except Exception:
                pass
        if path:
            self.path_var.set(path)
            self._log(f"[INFO] Directory selected: {path}")

    def _on_recursive_toggle(self):
        self.config["organize_subdirectories"] = self.recursive_var.get()
        self.organizer.organize_subdirectories = self.recursive_var.get()
        save_config(self.config)

    def _open_folder(self):
        path = self.path_var.get()
        if path and os.path.isdir(path):
            open_in_file_manager(path)
        else:
            self._log("[WARN] Select a valid folder first.")

    def _open_settings(self):
        SettingsDialog(self, self.config, self._on_settings_save)

    def _on_settings_save(self, new_config: dict):
        self.config = new_config
        self.organizer.config = new_config
        self.organizer.extension_map = new_config.get("extension_map", DEFAULT_CONFIG["extension_map"])
        self.organizer.organize_subdirectories = new_config.get("organize_subdirectories", False)
        self.organizer.create_log_file = new_config.get("create_log_file", True)
        self.recursive_var.set(self.organizer.organize_subdirectories)
        save_config(new_config)
        self._log("[INFO] Settings saved successfully.")

    def _set_ui_state(self, disabled: bool):
        state = "disabled" if disabled else "normal"
        self.organize_btn.configure(state=state)
        self.undo_btn.configure(state=state)
        self.settings_btn.configure(state=state)
        self.open_folder_btn.configure(state=state)
        self.browse_btn.configure(state=state)
        self.dry_run_check.configure(state=state)
        self.recursive_check.configure(state=state)
        self.path_entry.configure(state=state)

    def _start_organizing(self):
        path = self.path_var.get()
        if not path or not os.path.isdir(path):
            self._log("[ERROR] Please select a valid directory first.")
            return

        self._set_ui_state(True)
        self.status_label.configure(text="Processing...", text_color="#FFD60A")
        self.progress_bar.set(0.0)
        self._clear_log()
        self._log(f"[INFO] Starting organization: {path}")
        self._log(f"[INFO] Mode: {'Dry Run' if self.dry_run_var.get() else 'Live'}")
        self._log(f"[INFO] Recursive: {self.recursive_var.get()}")

        threading.Thread(target=self._organize_thread, args=(path, self.dry_run_var.get()), daemon=True).start()

    def _organize_thread(self, path: str, dry_run: bool):
        try:
            self.organizer.organize_subdirectories = self.recursive_var.get()
            moved = self.organizer.organize_directory(path, self._update_status, dry_run=dry_run)

            if dry_run:
                msg = f"Preview complete! {moved} files would be moved." if moved else "No files to move."
            else:
                msg = f"Organization complete! Moved {moved} files." if moved else "No files to move."

            self._log(f"\n[DONE] {msg}")

            if not dry_run and self.organizer.create_log_file:
                self._save_log_file(path)

            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=self.ACCENT_GREEN))
            self.after(0, lambda: self.undo_btn.configure(state="normal" if moved > 0 and not dry_run else "disabled"))
            self.after(0, lambda: self._set_ui_state(False))

        except Exception as e:
            self._log(f"[ERROR] {e}")
            self.after(0, lambda: self.status_label.configure(text="Error", text_color=self.ACCENT_CORAL))
            self.after(0, lambda: self._set_ui_state(False))

    def _update_status(self, message: str, progress: float):
        self.after(0, lambda: self._do_update_status(message, progress))

    def _do_update_status(self, message: str, progress: float):
        self.status_label.configure(text=message, text_color=self.TEXT_MAIN)
        self.progress_bar.set(progress)
        self._log(f"  {message}")

    def _undo_action(self):
        if not self.organizer._move_history:
            self._log("[INFO] Nothing to undo.")
            return

        self._set_ui_state(True)
        self.status_label.configure(text="Undoing...", text_color="#FFD60A")
        threading.Thread(target=self._undo_thread, daemon=True).start()

    def _undo_thread(self):
        try:
            restored = self.organizer.undo_last_organization(self._update_status)
            self._log(f"\n[DONE] Undo complete! Restored {restored} files.")
            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=self.ACCENT_GREEN))
            self.after(0, lambda: self._set_ui_state(False))
            self.after(0, lambda: self.undo_btn.configure(state="disabled"))
        except Exception as e:
            self._log(f"[ERROR] Undo failed: {e}")
            self.after(0, lambda: self._set_ui_state(False))

    def _save_log_file(self, directory_path):
        try:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            log_path = os.path.join(directory_path, f"bobnox-log-{ts}.txt")
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.log_messages))
            self._log(f"[INFO] Log saved: {log_path}")
        except Exception as e:
            logger.error(f"Failed to save log: {e}")


if __name__ == "__main__":
    app = BoBnoxApp()
    app.mainloop()
