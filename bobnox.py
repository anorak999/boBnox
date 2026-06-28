import os
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
from tkinter import font as tkfont
import customtkinter as ctk

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
    """Install icons to standard freedesktop paths for GNOME shell."""
    for dest_path in [ICON_APP, ICON_SYSTEM]:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(ICON_SOURCE) and not dest.exists():
            try:
                shutil.copy2(ICON_SOURCE, dest)
                logger.info(f"Icon installed: {dest}")
            except Exception as e:
                logger.warning(f"Icon install failed: {e}")
    # Refresh icon cache
    try:
        subprocess.run(["gtk-update-icon-cache", "-f", os.path.expanduser("~/.local/share/icons/")],
                       capture_output=True, timeout=10)
        subprocess.run(["update-desktop-database", os.path.expanduser("~/.local/share/applications/")],
                       capture_output=True, timeout=10)
    except Exception:
        pass

# --- File Manager (open in Nautilus only) ---
def open_in_nautilus(path: str):
    """Open a folder in Nautilus file manager."""
    try:
        subprocess.Popen(["nautilus", path])
    except FileNotFoundError:
        try:
            subprocess.Popen(["xdg-open", path])
        except FileNotFoundError:
            pass

# --- Configuration ---
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
            status_callback(f"{'Would move' if dry_run else 'Moving'} ({i + 1}/{total}): {rel} -> {folder_name}", (i + 1) / total)
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
        self.resizable(False, False)
        self.grab_set()
        self.extension_entries = {}
        self._create_widgets()

    def _create_widgets(self):
        ctk.CTkLabel(self, text="Extension Mappings", font=("Geist", 18, "bold")).pack(anchor="w", padx=24, pady=(20, 10))

        scroll = ctk.CTkScrollableFrame(self, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=(0, 10))

        for ext, folder in sorted(self.config.get("extension_map", {}).items()):
            row = ctk.CTkFrame(scroll, corner_radius=8)
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=ext, font=("Geist", 13), width=80).pack(side="left", padx=(12, 8), pady=8)
            entry = ctk.CTkEntry(row, font=("Geist", 13), corner_radius=6, height=32)
            entry.insert(0, folder)
            entry.pack(side="left", fill="x", expand=True, padx=(0, 12), pady=8)
            self.extension_entries[ext] = entry

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 16))
        ctk.CTkButton(btn_frame, text="Save", font=("Geist", 13, "bold"), fg_color="#005CE6", hover_color="#004BB3", height=36, corner_radius=8, command=self._save).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="Cancel", font=("Geist", 13), height=36, corner_radius=8, command=self.destroy).pack(side="left")

    def _save(self):
        for ext, entry in self.extension_entries.items():
            self.config["extension_map"][ext] = entry.get()
        self.on_save(self.config)
        self.destroy()


# --- Main Application ---
class BoBnoxApp(ctk.CTk):

    def __init__(self):
        super().__init__(className="bobnox")

        self.app_config = load_config()
        self.organizer = FileOrganizer(self.app_config)
        self.log_messages = []

        self.title("BoBnox")
        self.geometry("920x760")
        self.minsize(700, 560)

        # Install fonts and icons
        if not geist_available():
            install_geist_fonts()
        ensure_icons_installed()

        # Set window icon for titlebar + dock
        self._icon_ref = None
        icon_path = ICON_SYSTEM if os.path.exists(ICON_SYSTEM) else ICON_APP if os.path.exists(ICON_APP) else ICON_SOURCE
        if os.path.exists(icon_path):
            try:
                self._icon_ref = tk.PhotoImage(file=icon_path)
                self.iconphoto(True, self._icon_ref)
            except Exception as e:
                logger.warning(f"Icon failed: {e}")

        # --- Color Tuples: ("light", "dark") ---
        self.C_BG = ("#F2F2F7", "#0D0D0D")
        self.C_CARD = ("#FFFFFF", "#1A1A1A")
        self.C_TEXT = ("#000000", "#FFFFFF")
        self.C_MUTED = ("#636366", "#8E8E93")
        self.C_ENTRY = ("#E5E5EA", "#0D0D0D")
        self.C_BORDER = ("#D1D1D6", "#2C2C2E")
        self.C_BTN = ("#E5E5EA", "#2C2C2E")
        self.C_BTN_HOVER = ("#D1D1D6", "#3A3A3C")

        # Static accents
        self.BLUE = "#005CE6"
        self.GREEN = "#22C85A"
        self.CORAL = "#FF4F31"

        # Fonts
        gf = "Geist" if geist_available() else ("Helvetica" if IS_MACOS else "Sans")
        self.F_TITLE = (gf, 26, "bold")
        self.F_SUB = (gf, 12)
        self.F_LABEL = (gf, 13)
        self.F_BTN = (gf, 13, "bold")
        self.F_CONSOLE = ("Courier", 12)

        # Variables
        self.path_var = tk.StringVar()
        self.dry_run_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=self.app_config.get("organize_subdirectories", False))

        # Grid
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(3, weight=1)

        # Set initial mode
        is_dark = self.app_config.get("dark_mode", True)
        ctk.set_appearance_mode("Dark" if is_dark else "Light")

        self._create_widgets()

    def _create_widgets(self):
        p = self  # self has all color tuples

        # CARD 1: Branding
        brand = ctk.CTkFrame(self, fg_color=p.C_CARD, corner_radius=16)
        brand.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")

        # Theme toggle
        self.theme_switch = ctk.CTkSwitch(
            brand, text="Dark Mode", command=self._toggle_theme,
            font=p.F_LABEL, text_color=p.C_TEXT,
            progress_color=self.BLUE, fg_color=p.C_BORDER
        )
        self.theme_switch.pack(anchor="w", padx=24, pady=(16, 8))
        if self.app_config.get("dark_mode", True):
            self.theme_switch.select()
            self.theme_switch.configure(text="Dark Mode")
        else:
            self.theme_switch.deselect()
            self.theme_switch.configure(text="Light Mode")

        ctk.CTkLabel(brand, text="boBnox", text_color=p.C_TEXT, font=p.F_TITLE).pack(anchor="w", padx=24, pady=(0, 4))
        ctk.CTkLabel(brand, text="Organize your files into categorized folders", text_color=p.C_MUTED, font=p.F_LABEL).pack(anchor="w", padx=24, pady=(0, 20))

        # CARD 2: Options
        opts = ctk.CTkFrame(self, fg_color=p.C_CARD, corner_radius=16)
        opts.grid(row=0, column=1, padx=12, pady=12, sticky="nsew")
        ctk.CTkLabel(opts, text="Options", text_color=p.C_MUTED, font=p.F_SUB).pack(anchor="w", padx=24, pady=(16, 8))

        self.dry_run_check = ctk.CTkCheckBox(opts, text="Dry Run (Preview only)", variable=self.dry_run_var, font=p.F_LABEL, text_color=p.C_TEXT, hover_color=self.BLUE, fg_color=self.BLUE, checkbox_width=18, checkbox_height=18)
        self.dry_run_check.pack(anchor="w", padx=24, pady=6)

        self.recursive_check = ctk.CTkCheckBox(opts, text="Include Subdirectories", variable=self.recursive_var, font=p.F_LABEL, text_color=p.C_TEXT, hover_color=self.BLUE, fg_color=self.BLUE, command=self._on_recursive_toggle, checkbox_width=18, checkbox_height=18)
        self.recursive_check.pack(anchor="w", padx=24, pady=(6, 16))

        # CARD 3: Path
        path_card = ctk.CTkFrame(self, fg_color=p.C_CARD, corner_radius=16)
        path_card.grid(row=1, column=0, columnspan=2, padx=12, pady=12, sticky="nsew")
        ctk.CTkLabel(path_card, text="Target Directory", text_color=p.C_MUTED, font=p.F_SUB).pack(anchor="w", padx=24, pady=(14, 6))

        path_frame = ctk.CTkFrame(path_card, fg_color="transparent")
        path_frame.pack(fill="x", padx=20, pady=(0, 18))

        self.path_entry = ctk.CTkEntry(path_frame, placeholder_text="Select a directory path...", fg_color=p.C_ENTRY, border_color=p.C_BORDER, text_color=p.C_TEXT, font=p.F_CONSOLE, height=38, corner_radius=8, textvariable=self.path_var)
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))

        self.browse_btn = ctk.CTkButton(path_frame, text="Browse", font=p.F_BTN, fg_color=self.BLUE, hover_color="#004BB3", height=38, width=110, corner_radius=8, command=self._select_directory)
        self.browse_btn.pack(side="left")

        # CARD 4: Actions
        actions = ctk.CTkFrame(self, fg_color=p.C_CARD, corner_radius=16)
        actions.grid(row=2, column=0, columnspan=2, padx=12, pady=12, sticky="nsew")
        actions.grid_columnconfigure((0, 1, 2, 3), weight=1, uniform="buttons")
        actions.grid_columnconfigure(4, weight=1, uniform="buttons")

        self.organize_img = None
        if os.path.exists(SVG_PATH):
            try:
                import cairosvg, io
                from PIL import Image as PILImage
                png_data = cairosvg.svg2png(url=SVG_PATH, output_width=20, output_height=20)
                img = PILImage.open(io.BytesIO(png_data)).convert('RGBA')
                self.organize_img = ctk.CTkImage(light_image=img, dark_image=img, size=(20, 20))
            except Exception:
                pass

        org_kw = dict(text="Organize", font=p.F_BTN, fg_color=self.GREEN, hover_color="#1B9E46", text_color="#000000", height=36, corner_radius=8, command=self._start_organizing)
        if self.organize_img:
            org_kw["image"] = self.organize_img
            org_kw["compound"] = "left"
        self.organize_btn = ctk.CTkButton(actions, **org_kw)
        self.organize_btn.grid(row=0, column=0, padx=(16, 6), pady=14, sticky="ew")

        self.undo_btn = ctk.CTkButton(actions, text="Undo", font=p.F_BTN, fg_color=p.C_BTN, hover_color=p.C_BTN_HOVER, text_color=p.C_TEXT, height=36, corner_radius=8, command=self._undo_action, state="disabled")
        self.undo_btn.grid(row=0, column=1, padx=6, pady=14, sticky="ew")

        self.settings_btn = ctk.CTkButton(actions, text="Settings", font=p.F_BTN, fg_color=p.C_BTN, hover_color=p.C_BTN_HOVER, text_color=p.C_TEXT, height=36, corner_radius=8, command=self._open_settings)
        self.settings_btn.grid(row=0, column=2, padx=6, pady=14, sticky="ew")

        self.open_folder_btn = ctk.CTkButton(actions, text="Open Folder", font=p.F_BTN, fg_color=p.C_BTN, hover_color=p.C_BTN_HOVER, text_color=p.C_TEXT, height=36, corner_radius=8, command=self._open_folder)
        self.open_folder_btn.grid(row=0, column=3, padx=6, pady=14, sticky="ew")

        self.clear_btn = ctk.CTkButton(actions, text="Clear Console", font=p.F_BTN, fg_color="transparent", hover_color=p.C_BTN_HOVER, text_color=self.CORAL, border_color=self.CORAL, border_width=1, height=36, corner_radius=8, command=self._clear_log)
        self.clear_btn.grid(row=0, column=4, padx=(6, 16), pady=14, sticky="ew")

        # CARD 5: Terminal
        terminal = ctk.CTkFrame(self, fg_color=p.C_CARD, corner_radius=16)
        terminal.grid(row=3, column=0, columnspan=2, padx=12, pady=(12, 20), sticky="nsew")

        status_frame = ctk.CTkFrame(terminal, fg_color="transparent")
        status_frame.pack(fill="x", padx=24, pady=(16, 6))
        self.status_label = ctk.CTkLabel(status_frame, text="System Ready", text_color=self.GREEN, font=p.F_SUB)
        self.status_label.pack(side="left")

        self.progress_bar = ctk.CTkProgressBar(terminal, height=4, fg_color=p.C_BORDER, progress_color=self.BLUE)
        self.progress_bar.pack(fill="x", padx=24, pady=4)
        self.progress_bar.set(0.0)

        self.console = ctk.CTkTextbox(terminal, fg_color=p.C_ENTRY, text_color=p.C_TEXT, font=p.F_CONSOLE, corner_radius=8, border_color=p.C_BORDER, border_width=1)
        self.console.pack(fill="both", expand=True, padx=20, pady=(12, 20))
        self.console.insert("end", "[INFO] Application initialized.\n[INFO] Awaiting target directory selection...\n")
        self.console.configure(state="disabled")

    # --- Theme Toggle ---
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
        """Native GNOME/GTK file chooser via Zenity."""
        try:
            target = subprocess.check_output(
                ["zenity", "--file-selection", "--directory", "--title=Select Target Directory"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
            if target:
                self.path_var.set(target)
                self._log(f"[INFO] Directory selected: {target}")
        except subprocess.CalledProcessError:
            self._log("[WARN] Directory selection canceled.")

    def _on_recursive_toggle(self):
        self.app_config["organize_subdirectories"] = self.recursive_var.get()
        self.organizer.organize_subdirectories = self.recursive_var.get()
        save_config(self.app_config)

    def _open_folder(self):
        path = self.path_var.get()
        if path and os.path.isdir(path):
            open_in_nautilus(path)
        else:
            self._log("[WARN] Select a valid folder first.")

    def _open_settings(self):
        SettingsDialog(self, self.app_config, self._on_settings_save)

    def _on_settings_save(self, new_config: dict):
        self.app_config = new_config
        self.organizer.config = new_config
        self.organizer.extension_map = new_config.get("extension_map", DEFAULT_CONFIG["extension_map"])
        self.organizer.organize_subdirectories = new_config.get("organize_subdirectories", False)
        self.organizer.create_log_file = new_config.get("create_log_file", True)
        self.recursive_var.set(self.organizer.organize_subdirectories)
        save_config(new_config)
        self._log("[INFO] Settings saved.")

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
            msg = f"Preview complete! {moved} files would be moved." if dry_run and moved else f"Organization complete! Moved {moved} files." if moved else "No files to move."
            self._log(f"\n[DONE] {msg}")
            if not dry_run and self.organizer.create_log_file:
                self._save_log_file(path)
            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=self.GREEN))
            self.after(0, lambda: self.undo_btn.configure(state="normal" if moved > 0 and not dry_run else "disabled"))
            self.after(0, lambda: self._set_ui_state(False))
        except Exception as e:
            self._log(f"[ERROR] {e}")
            self.after(0, lambda: self.status_label.configure(text="Error", text_color=self.CORAL))
            self.after(0, lambda: self._set_ui_state(False))

    def _update_status(self, message: str, progress: float):
        self.after(0, lambda: self._do_update_status(message, progress))

    def _do_update_status(self, message: str, progress: float):
        self.status_label.configure(text=message, text_color=self.C_TEXT)
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
            self.after(0, lambda: self.status_label.configure(text="System Ready", text_color=self.GREEN))
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
