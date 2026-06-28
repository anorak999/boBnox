import os
import sys
import shutil
import subprocess
import platform
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import io
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# --- Logging Configuration ---
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

IS_MACOS = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

# --- Nautilus / File Manager Integration ---
def open_in_file_manager(path: str):
    """Open a folder in the system file manager (Nautilus on Linux, Finder on macOS)."""
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
            logger.warning("No file manager found to open path")

def select_folder_via_nautilus() -> Optional[str]:
    """Use Nautilus (Linux) or Finder (macOS) to select a folder via portal dialog."""
    if IS_LINUX:
        try:
            result = subprocess.run(
                ["zenity", "--file-selection", "--directory", "--title=Select Folder to Organize"],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except FileNotFoundError:
            pass
    if IS_MACOS:
        try:
            result = subprocess.run(
                ["osascript", "-e", 'tell application "Finder" to set folderPath to POSIX path of (choose folder)'],
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
        logger.info("Configuration saved successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        return False


def load_undo_history() -> list:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load undo history: {e}")
    return []


def save_undo_history(history: list) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save undo history: {e}")
        return False


HAS_SVG_SUPPORT = False
try:
    import cairosvg
    from PIL import Image, ImageTk
    HAS_SVG_SUPPORT = True
except Exception:
    HAS_SVG_SUPPORT = False


# --- 1. CORE LOGIC CLASS ---
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
        logger.info(f"Organizing directory: {directory_path} (dry_run={dry_run})")

        if self.organize_subdirectories:
            files_to_move = [
                f for f in directory.rglob('*')
                if f.is_file() and f.name != os.path.basename(__file__)
            ]
        else:
            files_to_move = [
                f for f in directory.iterdir()
                if f.is_file() and f.name != os.path.basename(__file__)
            ]

        total_files = len(files_to_move)
        files_moved = 0

        if total_files == 0:
            status_callback("No files to organize.", 1.0)
            return 0

        self._move_history.clear()

        for i, file_path in enumerate(files_to_move):
            relative_path = file_path.relative_to(directory)
            file_extension = file_path.suffix.lower()

            if file_extension in self.extension_map:
                folder_name = self.extension_map[file_extension]
            else:
                folder_name = f"{file_extension[1:].upper()} Files" if file_extension else "Other Files"

            dest_folder_path = directory / folder_name

            if not dry_run and not dest_folder_path.exists():
                dest_folder_path.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created directory: {dest_folder_path}")

            original_name = file_path.name
            base_name, ext = os.path.splitext(original_name)
            counter = 1
            destination_path = dest_folder_path / original_name

            while destination_path.exists():
                new_name = f"{base_name} ({counter}){ext}"
                destination_path = dest_folder_path / new_name
                counter += 1

            if not dry_run:
                try:
                    shutil.move(str(file_path), str(destination_path))
                    self._move_history.append((destination_path, file_path))
                    files_moved += 1
                    logger.info(f"Moved: {relative_path} -> {folder_name}")
                except Exception as e:
                    logger.error(f"Failed to move {original_name}: {e}")
                    status_callback(f"Failed to move {original_name}: {e}", (i + 1) / total_files)
                    continue
            else:
                files_moved += 1
                logger.info(f"[DRY RUN] Would move: {relative_path} -> {folder_name}")

            progress_percent = (i + 1) / total_files
            action = "Would move" if dry_run else "Moving"
            status_message = f"{action} ({i + 1}/{total_files}): {relative_path} -> {folder_name}"
            status_callback(status_message, progress_percent)

        if not dry_run and self._move_history:
            self._save_persistent_history()

        return files_moved

    def undo_last_organization(self, status_callback) -> int:
        if not self._move_history:
            status_callback("Nothing to undo.", 1.0)
            return 0

        logger.info(f"Undoing last organization ({len(self._move_history)} files)")
        total = len(self._move_history)
        restored = 0

        for i, (current_path, original_path) in enumerate(self._move_history):
            if current_path.exists():
                original_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.move(str(current_path), str(original_path))
                    restored += 1
                    logger.info(f"Restored: {current_path.name} -> {original_path.parent}")
                except Exception as e:
                    logger.error(f"Failed to restore {current_path.name}: {e}")
                    status_callback(f"Failed to restore {current_path.name}: {e}", (i + 1) / total)
            progress = (i + 1) / total
            status_callback(f"Restoring ({i + 1}/{total}): {current_path.name}", progress)

        self._move_history.clear()
        self._save_persistent_history()
        return restored


# --- 2. SETTINGS DIALOG ---
class SettingsDialog(tk.Toplevel):

    def __init__(self, parent, config: dict, on_save_callback, theme_is_aqua: bool = False):
        super().__init__(parent)
        self.config = config.copy()
        self.on_save = on_save_callback
        self.theme_is_aqua = theme_is_aqua
        self.title("Settings")
        self.geometry("500x600")
        self.resizable(False, False)
        self.grab_set()

        if not theme_is_aqua:
            self.configure(bg="#1E1E1E")

        self.extension_entries = {}
        self._create_widgets()

    def _create_widgets(self):
        if not self.theme_is_aqua:
            style = ttk.Style(self)
            style.configure("Dialog.TFrame", background="#1E1E1E")
            style.configure("Dialog.TLabel", background="#1E1E1E", foreground="#FFFFFF", font=("Inter", 11))
            main_frame = ttk.Frame(self, padding="15", style="Dialog.TFrame")
            main_frame.pack(fill=tk.BOTH, expand=True)
            header_fg = "#0078D4"
            canvas_bg = "#1E1E1E"
        else:
            main_frame = ttk.Frame(self, padding="15")
            main_frame.pack(fill=tk.BOTH, expand=True)
            header_fg = "#007AFF"
            canvas_bg = "#FFFFFF"

        ttk.Label(main_frame, text="Extension Mappings", font=("Inter", 14, "bold"),
                  foreground=header_fg).pack(pady=(0, 10))

        canvas = tk.Canvas(main_frame, bg=canvas_bg, highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        row = 0
        for ext, folder in sorted(self.config.get("extension_map", {}).items()):
            ttk.Label(scrollable_frame, text=ext, font=("Inter", 11)).grid(
                row=row, column=0, sticky="w", padx=(0, 10), pady=2)
            entry = ttk.Entry(scrollable_frame, width=20)
            entry.insert(0, folder)
            entry.grid(row=row, column=1, sticky="ew", pady=2)
            self.extension_entries[ext] = entry
            row += 1

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(15, 0))
        ttk.Button(button_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

    def _save(self):
        for ext, entry in self.extension_entries.items():
            self.config["extension_map"][ext] = entry.get()
        self.on_save(self.config)
        self.destroy()


# --- 3. GUI APPLICATION CLASS ---
class FileOrganizerApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.organizer = FileOrganizer(self.config)
        self.title("boBnox")
        self.geometry("560x520")
        self.minsize(480, 440)
        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready. Select a folder to begin.")
        self.dry_run_var = tk.BooleanVar(value=False)
        self.recursive_var = tk.BooleanVar(value=self.config.get("organize_subdirectories", False))
        self.log_messages = []
        self.theme_is_aqua = False

        self._setup_theme()
        self.create_widgets()

    def _setup_theme(self):
        style = ttk.Style(self)

        if IS_MACOS:
            try:
                style.theme_use('aqua')
                self.theme_is_aqua = True
                self.BG_DARK = "#ECECEC"
                self.BG_MID = "#D4D4D4"
                self.FG_LIGHT = "#1D1D1F"
                self.ACCENT_COLOR = "#007AFF"
            except Exception:
                self.theme_is_aqua = False

        if not self.theme_is_aqua:
            try:
                style.theme_use('clam')
            except Exception:
                pass
            self.BG_DARK = "#1E1E1E"
            self.BG_MID = "#2D2D30"
            self.FG_LIGHT = "#FFFFFF"
            self.ACCENT_COLOR = "#0078D4"
            self.configure(bg=self.BG_DARK)

        style.configure("TFrame", background=self.BG_DARK)
        style.configure("TLabel", background=self.BG_DARK, foreground=self.FG_LIGHT, font=("Inter", 12))
        style.configure("Status.TLabel", background=self.BG_DARK, foreground="#888888", font=("Inter", 10, "italic"))
        style.configure("TEntry", font=("Inter", 11))
        style.configure("TButton", font=("Inter", 11, "bold"), padding=[12, 6])
        style.configure("TProgressbar", troughcolor=self.BG_MID, background=self.ACCENT_COLOR)
        style.configure("TCheckbutton", background=self.BG_DARK, foreground=self.FG_LIGHT, font=("Inter", 10))

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(expand=True, fill=tk.BOTH)
        main_frame.grid_columnconfigure(0, weight=1)

        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        path_frame.grid_columnconfigure(0, weight=1)

        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, font=("Inter", 11))
        self.path_entry.grid(row=0, column=0, sticky="ew")

        browse_frame = ttk.Frame(path_frame)
        browse_frame.grid(row=0, column=1, padx=(8, 0))

        browse_button = ttk.Button(browse_frame, text="Browse...", command=self.select_directory)
        browse_button.pack(side="left")

        nautilus_button = ttk.Button(browse_frame, text="Nautilus", command=self.select_via_nautilus)
        nautilus_button.pack(side="left", padx=(4, 0))

        options_frame = ttk.Frame(main_frame)
        options_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        options_frame.grid_columnconfigure(0, weight=1)

        self.dry_run_check = ttk.Checkbutton(options_frame, text="Dry Run (Preview only)", variable=self.dry_run_var)
        self.dry_run_check.grid(row=0, column=0, sticky="w", padx=(0, 20))

        self.recursive_check = ttk.Checkbutton(options_frame, text="Include Subdirectories", variable=self.recursive_var, command=self._on_recursive_toggle)
        self.recursive_check.grid(row=0, column=1, sticky="w")

        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        svg_path = os.path.join(assets_dir, 'Sort--Streamline-Solar.svg')

        self.organize_img = None
        if HAS_SVG_SUPPORT and os.path.exists(svg_path):
            try:
                png_bytes = cairosvg.svg2png(url=svg_path, output_width=48, output_height=48)
                img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
                self.organize_img = ImageTk.PhotoImage(img)
                self.organize_button = tk.Button(main_frame, image=self.organize_img, command=self.start_organizing_thread, bd=0, highlightthickness=0, relief='flat', cursor='hand2', bg=self.BG_DARK, activebackground=self.BG_DARK)
            except Exception:
                self.organize_button = self._create_text_button(main_frame)
        else:
            self.organize_button = self._create_text_button(main_frame)

        self.organize_button.grid(row=2, column=0, pady=(8, 8))

        secondary_frame = ttk.Frame(main_frame)
        secondary_frame.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        secondary_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.undo_button = ttk.Button(secondary_frame, text="Undo", command=self.undo_last_action, state='disabled')
        self.undo_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.settings_button = ttk.Button(secondary_frame, text="Settings", command=self.open_settings)
        self.settings_button.grid(row=0, column=1, sticky="ew", padx=4)

        self.open_folder_button = ttk.Button(secondary_frame, text="Open Folder", command=self.open_organized_folder)
        self.open_folder_button.grid(row=0, column=2, sticky="ew", padx=4)

        self.clear_log_button = ttk.Button(secondary_frame, text="Clear Log", command=self.clear_log)
        self.clear_log_button.grid(row=0, column=3, sticky="ew", padx=(4, 0))

        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=4, column=0, sticky="ew", pady=(0, 8))

        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=5, column=0, sticky="w")

        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=6, column=0, sticky="nsew", pady=(10, 0))
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(6, weight=1)

        log_bg = self.BG_MID if not self.theme_is_aqua else "#F5F5F5"
        log_fg = self.FG_LIGHT if not self.theme_is_aqua else "#1D1D1F"

        self.log_text = tk.Text(log_frame, height=8, bg=log_bg, fg=log_fg, font=("Menlo" if IS_MACOS else "Consolas", 9), relief='flat', bd=0, wrap='word', state='disabled')
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scrollbar.set)

    def _create_text_button(self, parent):
        return tk.Button(parent, text="Organize", command=self.start_organizing_thread, font=("Inter", 12, "bold"), bd=0, highlightthickness=0, relief='flat', cursor='hand2', bg=self.ACCENT_COLOR, fg=self.FG_LIGHT, activebackground='#005A9E', padx=20, pady=8)

    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)

    def select_via_nautilus(self):
        """Open Nautilus/Finder folder picker."""
        path = select_folder_via_nautilus()
        if path:
            self.path_var.set(path)

    def open_organized_folder(self):
        """Open the selected folder in Nautilus/Finder."""
        path = self.path_var.get()
        if path and os.path.isdir(path):
            open_in_file_manager(path)
        else:
            messagebox.showwarning("Warning", "Please select a valid folder first.")

    def _on_recursive_toggle(self):
        self.config["organize_subdirectories"] = self.recursive_var.get()
        self.organizer.organize_subdirectories = self.recursive_var.get()
        save_config(self.config)

    def _log_to_ui(self, message: str):
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def clear_log(self):
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.log_messages.clear()

    def open_settings(self):
        SettingsDialog(self, self.config, self.on_settings_save, self.theme_is_aqua)

    def on_settings_save(self, new_config: dict):
        self.config = new_config
        self.organizer.config = new_config
        self.organizer.extension_map = new_config.get("extension_map", DEFAULT_CONFIG["extension_map"])
        self.organizer.organize_subdirectories = new_config.get("organize_subdirectories", False)
        self.organizer.create_log_file = new_config.get("create_log_file", True)
        self.recursive_var.set(self.organizer.organize_subdirectories)
        save_config(new_config)
        messagebox.showinfo("Settings", "Settings saved successfully!")

    def start_organizing_thread(self):
        directory_path = self.path_var.get()
        if not os.path.isdir(directory_path):
            messagebox.showerror("Error", "Please select a valid directory first.")
            return

        self._set_ui_state(disabled=True)
        self.status_var.set("Processing... Please wait.")
        self.progress_bar['value'] = 0
        self.clear_log()

        self.log_messages = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_messages.append(f"=== Organization started at {timestamp} ===")
        self.log_messages.append(f"Directory: {directory_path}")
        self.log_messages.append(f"Mode: {'Dry Run' if self.dry_run_var.get() else 'Live'}")
        self.log_messages.append(f"Recursive: {self.recursive_var.get()}")
        self.log_messages.append("")

        self.thread = threading.Thread(target=self.organize_action, args=(directory_path, self.dry_run_var.get()), daemon=True)
        self.thread.start()

    def undo_last_action(self):
        if not self.organizer._move_history:
            messagebox.showinfo("Undo", "Nothing to undo.")
            return

        if not messagebox.askyesno("Confirm Undo", "Restore all moved files to their original locations?"):
            return

        self._set_ui_state(disabled=True)
        self.status_var.set("Undoing... Please wait.")
        self.progress_bar['value'] = 0

        self.thread = threading.Thread(target=self.undo_action, daemon=True)
        self.thread.start()

    def undo_action(self):
        try:
            restored = self.organizer.undo_last_organization(self.update_status)
            if restored > 0:
                final_message = f"Undo complete! Restored {restored} files."
            else:
                final_message = "Nothing to restore."
            self.after(0, lambda: messagebox.showinfo("Undo Complete", final_message))
            self.after(0, self.reset_ui)
        except Exception as e:
            err = str(e)
            self.after(0, lambda: messagebox.showerror("Error", f"Undo failed: {err}"))
            self.after(0, self.reset_ui)

    def update_status(self, message, progress_value):
        try:
            self.after(0, lambda: self._update_status_ui(message, progress_value))
        except Exception:
            self._update_status_ui(message, progress_value)

    def _update_status_ui(self, message, progress_value):
        self.status_var.set(message)
        try:
            self.progress_bar['value'] = progress_value * 100
        except Exception:
            pass
        self.log_messages.append(message)
        self._log_to_ui(message)
        self.update_idletasks()

    def organize_action(self, directory_path, dry_run: bool):
        try:
            self.organizer.organize_subdirectories = self.recursive_var.get()
            files_moved = self.organizer.organize_directory(directory_path, self.update_status, dry_run=dry_run)

            if dry_run:
                final_message = f"Preview complete! {files_moved} files would be moved." if files_moved > 0 else "No files to move, directory is already tidy."
            else:
                final_message = f"Organization complete! Moved {files_moved} files." if files_moved > 0 else "No files to move, directory is already tidy."

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_messages.append("")
            self.log_messages.append(f"=== Organization completed at {timestamp} ===")
            self.log_messages.append(f"Files {'would be moved' if dry_run else 'moved'}: {files_moved}")

            if not dry_run and self.organizer.create_log_file:
                self._save_log_file(directory_path)

            self.after(0, lambda: messagebox.showinfo("Success", final_message))
            self.after(0, lambda: self.undo_button.config(state='normal' if files_moved > 0 and not dry_run else 'disabled'))
            self.after(0, self.reset_ui)

        except FileNotFoundError as e:
            err = str(e)
            self.log_messages.append(f"ERROR: {err}")
            if self.organizer.create_log_file:
                self._save_log_file(directory_path)
            self.after(0, lambda: messagebox.showerror("Error", err))
            self.after(0, self.reset_ui)
        except Exception as e:
            err = str(e)
            self.log_messages.append(f"ERROR: {err}")
            if self.organizer.create_log_file:
                self._save_log_file(directory_path)
            self.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {err}"))
            self.after(0, self.reset_ui)

    def _save_log_file(self, directory_path):
        try:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            log_filename = f"bobnox-log-{timestamp}.txt"
            log_path = os.path.join(directory_path, log_filename)
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.log_messages))
            self._log_to_ui(f"Log saved to: {log_filename}")
            logger.info(f"Log saved to: {log_path}")
        except Exception as e:
            logger.error(f"Failed to save log file: {e}")

    def _set_ui_state(self, disabled: bool):
        state = 'disabled' if disabled else 'normal'
        self.organize_button.config(state=state)
        self.path_entry.config(state=state)
        self.dry_run_check.config(state=state)
        self.recursive_check.config(state=state)
        self.settings_button.config(state=state)
        self.open_folder_button.config(state=state)
        if not disabled:
            self.undo_button.config(state='normal' if self.organizer._move_history else 'disabled')

    def reset_ui(self):
        self._set_ui_state(disabled=False)
        self.path_var.set("")
        self.status_var.set("Ready. Select a folder to begin.")
        self.progress_bar['value'] = 0


if __name__ == "__main__":
    app = FileOrganizerApp()
    app.mainloop()
