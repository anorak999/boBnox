import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import threading
import io
import base64

# Optional SVG rendering support (cairosvg + Pillow). If unavailable we fall back to text button.
HAS_SVG_SUPPORT = False
try:
    import cairosvg
    from PIL import Image, ImageTk
    HAS_SVG_SUPPORT = True
except Exception:
    # Missing optional packages; button will remain a text button
    HAS_SVG_SUPPORT = False

# --- 1. CORE LOGIC CLASS ---
class FileOrganizer:
    """
    Handles the actual file organization logic, decoupled from the GUI.
    """
    EXTENSION_MAP = {
        # Images
        '.jpg': 'Images', '.jpeg': 'Images', '.png': 'Images', '.gif': 'Images',
        '.bmp': 'Images', '.svg': 'Images', '.tiff': 'Images', '.webp': 'Images',
        '.heic': 'Images',
        # Documents
        '.pdf': 'Documents', '.doc': 'Documents', '.docx': 'Documents',
        '.txt': 'Text Documents', '.rtf': 'Documents', '.odt': 'Documents',
        '.md': 'Text Documents',
        # Spreadsheets & Presentations
        '.xls': 'Spreadsheets', '.xlsx': 'Spreadsheets', '.csv': 'Spreadsheets',
        '.ppt': 'Presentations', '.pptx': 'Presentations',
        # Audio
        '.mp3': 'Audio', '.wav': 'Audio', '.aac': 'Audio', '.flac': 'Audio',
        '.ogg': 'Audio', '.m4a': 'Audio',
        # Video
        '.mp4': 'Videos', '.mov': 'Videos', '.avi': 'Videos', '.mkv': 'Videos',
        '.wmv': 'Videos', '.flv': 'Videos',
        # Archives
        '.zip': 'Archives', '.rar': 'Archives', '.7z': 'Archives', '.tar': 'Archives',
        '.gz': 'Archives',
        # Code & Scripts
        '.py': 'Scripts', '.js': 'Scripts', '.html': 'Web Files', '.css': 'Web Files',
        '.java': 'Code', '.cpp': 'Code', '.c': 'Code', '.sh': 'Scripts',
        # Executables & Installers
        '.exe': 'Executables', '.msi': 'Installers', '.dmg': 'Installers',
    }

    def organize_directory(self, directory_path, status_callback):
        """
        Organizes files in the given directory into subfolders.
        Uses a callback function to report progress back to the GUI.
        """
        if not os.path.isdir(directory_path):
            raise FileNotFoundError("The selected path is not a valid directory.")

        # Filter out directories and the script file itself, only keeping files to move
        files_to_move = [
            f for f in os.listdir(directory_path)
            if os.path.isfile(os.path.join(directory_path, f)) and f != os.path.basename(__file__)
        ]
        
        total_files = len(files_to_move)
        files_moved = 0
        
        if total_files == 0:
            return 0 # No files to move

        for i, item_name in enumerate(files_to_move):
            source_path = os.path.join(directory_path, item_name)

            # 1. Determine destination folder name
            _, file_extension = os.path.splitext(item_name)
            file_extension = file_extension.lower()

            if file_extension in self.EXTENSION_MAP:
                folder_name = self.EXTENSION_MAP[file_extension]
            else:
                # Group unknown files
                folder_name = f"{file_extension[1:].upper()} Files" if file_extension else "Other Files"

            dest_folder_path = os.path.join(directory_path, folder_name)

            # 2. Create folder if needed
            if not os.path.exists(dest_folder_path):
                os.makedirs(dest_folder_path)

            # 3. Handle Duplicate File Names (Robust Naming)
            original_name = item_name
            base_name, ext = os.path.splitext(original_name)
            counter = 1
            destination_path = os.path.join(dest_folder_path, item_name)
            
            while os.path.exists(destination_path):
                # Rename the file if it conflicts (e.g., 'file (1).ext')
                item_name = f"{base_name} ({counter}){ext}"
                destination_path = os.path.join(dest_folder_path, item_name)
                counter += 1

            # 4. Move the file
            try:
                shutil.move(source_path, destination_path)
                files_moved += 1
            except Exception as e:
                # Report failure to move this specific file but continue
                print(f"Failed to move {item_name}: {e}")

            # 5. Report progress back to the GUI
            progress_percent = (i + 1) / total_files
            status_message = f"Moving ({i + 1}/{total_files}): {original_name} -> {folder_name}"
            status_callback(status_message, progress_percent)

        return files_moved


# --- 2. GUI APPLICATION CLASS ---
class FileOrganizerApp(TkinterDnD.Tk):
    """
    Aesthetically improved GUI application for FileOrganizer.
    """
    def __init__(self):
        super().__init__()
        self.organizer = FileOrganizer()
        self.title("boBnox(v2.0)")
        self.geometry("650x480")
        self.configure(bg="#1E1E1E")
        self.path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready. Drop a folder or browse to begin.")
        
        self.setup_styles()
        self.create_widgets()

    def setup_styles(self):
        """Configures the dark, flat look and feel."""
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Backgrounds (saved on self so other methods can access them)
        self.BG_DARK = "#1E1E1E"
        self.BG_MID = "#2D2D30"
        self.FG_LIGHT = "#FFFFFF"
        self.ACCENT_COLOR = "#0078D4" # Blue accent

    style.configure("TFrame", background=self.BG_DARK)
    style.configure("TLabel", background=self.BG_DARK, foreground=self.FG_LIGHT, font=("Inter", 12))
    style.configure("Title.TLabel", font=("Inter", 24, "bold"), foreground=self.ACCENT_COLOR)
    style.configure("Status.TLabel", background=self.BG_DARK, foreground="#999999", font=("Inter", 10, "italic"))
        
    # Entry/Input
    style.configure("TEntry", fieldbackground=self.BG_MID, foreground=self.FG_LIGHT, borderwidth=0, relief="flat", padding=8)
        
    # Button Styles
    style.configure("TButton", 
            font=("Inter", 12, "bold"), 
            background=self.ACCENT_COLOR, 
            foreground=self.FG_LIGHT,
            borderwidth=0, 
            relief="flat", 
            padding=[15, 8])
    style.map("TButton",
          background=[('active', '#005A9E'), ('disabled', '#555555')],
          foreground=[('active', 'white')])

    # Progress Bar
    style.configure("TProgressbar", 
            troughcolor=self.BG_MID, 
            background=self.ACCENT_COLOR, 
            troughrelief="flat", 
            borderwidth=0)


    def create_widgets(self):
        """Creates and positions all UI elements using grid for precise control."""
        
        # Main Frame with Padding
        main_frame = ttk.Frame(self, padding="30")
        main_frame.pack(expand=True, fill=tk.BOTH)
        
        main_frame.grid_columnconfigure(0, weight=1)

        # 1. Drop Target Area
        self.drop_target = tk.Label(
            main_frame,
            text="📁 Drag & Drop Folder Here",
            font=("Inter", 14, "bold"),
            relief="solid", 
            borderwidth=2,
            bg="#2D2D30", # Mid-dark background
            fg="#AAAAAA",
            padx=20,
            pady=40,
            cursor="hand2"
        )
        self.drop_target.grid(row=1, column=0, sticky="ew", pady=(0, 15), ipady=10)
        
        # Register the drop target
        self.drop_target.drop_target_register(DND_FILES)
        self.drop_target.dnd_bind('<<Drop>>', self.handle_drop)

        # Separator or alternative instruction
        ttk.Label(main_frame, text="— OR —", foreground="#555555").grid(row=2, column=0, pady=5)
        
        # 3. Path Entry and Browse Button
        path_frame = ttk.Frame(main_frame)
        path_frame.grid(row=3, column=0, sticky="ew", pady=(10, 20))
        path_frame.grid_columnconfigure(0, weight=1)
        
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
        self.path_entry.grid(row=0, column=0, sticky="ew")
        
        browse_button = ttk.Button(path_frame, text="Browse...", command=self.select_directory)
        browse_button.grid(row=0, column=1, padx=(10, 0))

        # 4. Organize Button - use icon-only button (no full-width blue background)
        assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
        svg_name = 'Sort--Streamline-Solar.svg'
        svg_path = os.path.join(assets_dir, svg_name)

        # Helper to create a small, icon-only tk.Button (fallback uses emoji)
        def make_icon_button(image=None):
            if image:
                btn = tk.Button(main_frame, image=image, command=self.start_organizing_thread,
                                bd=0, highlightthickness=0, relief='flat', cursor='hand2', bg=self.BG_DARK, activebackground=self.BG_DARK)
            else:
                # fallback emoji button if no image is available
                btn = tk.Button(main_frame, text='🚀', command=self.start_organizing_thread,
                                bd=0, highlightthickness=0, relief='flat', cursor='hand2', bg=self.BG_DARK, fg=self.FG_LIGHT, activebackground=self.BG_DARK)

            # Center the icon button without stretching across the entire row
            btn.grid(row=4, column=0, pady=(10, 20))
            return btn

        self.organize_img = None
        # Try to render the SVG into a PhotoImage; if it fails, fall back to emoji button
        if HAS_SVG_SUPPORT and os.path.exists(svg_path):
            try:
                png_bytes = cairosvg.svg2png(url=svg_path, output_width=48, output_height=48)
                img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
                self.organize_img = ImageTk.PhotoImage(img)
                self.organize_button = make_icon_button(image=self.organize_img)
            except Exception:
                self.organize_button = make_icon_button()
        else:
            self.organize_button = make_icon_button()

        # 5. Progress Bar and Status
        self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=500, mode="determinate")
        self.progress_bar.grid(row=5, column=0, sticky="ew", pady=(0, 5))

        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=6, column=0, sticky="w")


    # --- UI EVENT HANDLERS ---

    def handle_drop(self, event):
        """Handle the file drop event."""
        path = event.data.strip('{}').split()[0] # In case multiple paths are dropped, take the first one
        if os.path.isdir(path):
            self.path_var.set(path)
            self.update_drop_target_display(path)
        else:
            messagebox.showerror("Error", "Please drop a valid folder, not a file.")
            self.update_drop_target_display(None)

    def select_directory(self):
        """Open a dialog to select a directory."""
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
            self.update_drop_target_display(path)
        else:
             self.update_drop_target_display(None)

    def update_drop_target_display(self, path):
        """Updates the visual appearance of the drop target area."""
        if path and os.path.isdir(path):
            self.drop_target.config(
                text=f"Folder Selected:\n{os.path.basename(path)}",
                fg="#00D478" # Green confirmation color
            )
        else:
            self.drop_target.config(
                text="📁 Drag & Drop Folder Here",
                fg="#AAAAAA"
            )

    # --- THREADING AND ASYNCHRONOUS EXECUTION ---
    
    def start_organizing_thread(self):
        """Starts the file organization in a separate thread to keep the GUI responsive."""
        directory_path = self.path_var.get()
        if not os.path.isdir(directory_path):
            messagebox.showerror("Error", "Please select a valid directory first.")
            return

        # Disable input while processing
        # Support both ttk.Button (has .state) and tk.Button (use config)
        if hasattr(self.organize_button, 'state'):
            try:
                self.organize_button.state(['disabled'])
            except Exception:
                self.organize_button.config(state='disabled')
        else:
            self.organize_button.config(state='disabled')
        self.path_entry.state(['disabled'])
        self.status_var.set("Processing... Please wait.")
        self.progress_bar['value'] = 0

        # Start the organization task in a new thread
        self.thread = threading.Thread(target=self.organize_action, args=(directory_path,), daemon=True)
        self.thread.start()

    def update_status(self, message, progress_value):
        """Callback function to safely update GUI elements from the worker thread."""
        self.status_var.set(message)
        # Convert 0-1.0 progress to Tkinter's 0-100 scale
        self.progress_bar['value'] = progress_value * 100
        self.update_idletasks() # Force GUI redraw

    def organize_action(self, directory_path):
        """The function executed in the worker thread."""
        try:
            files_moved = self.organizer.organize_directory(
                directory_path,
                self.update_status
            )

            # Final success message
            if files_moved > 0:
                final_message = f"✅ Organization complete! Moved {files_moved} files."
            else:
                final_message = "✨ No files to move, directory is already tidy."

            self.after(0, lambda: messagebox.showinfo("Success", final_message))
            self.after(0, self.reset_ui)
            
        except FileNotFoundError as e:
             self.after(0, lambda: messagebox.showerror("Error", str(e)))
             self.after(0, self.reset_ui)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {e}"))
            self.after(0, self.reset_ui)

    def reset_ui(self):
        """Resets the UI elements to the initial state."""
        if hasattr(self.organize_button, 'state'):
            try:
                self.organize_button.state(['!disabled'])
            except Exception:
                self.organize_button.config(state='normal')
        else:
            self.organize_button.config(state='normal')
        self.path_entry.state(['!disabled'])
        self.path_var.set("")
        self.status_var.set("Ready. Drop a folder or browse to begin.")
        self.progress_bar['value'] = 0
        self.update_drop_target_display(None)


if __name__ == "__main__":
    # Note: To run this locally, you need tkinterdnd2: pip install tkinterdnd2
    app = FileOrganizerApp()
    app.mainloop()
