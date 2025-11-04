import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
# drag-and-drop removed for simplicity; use standard file dialog instead
import threading
import io
import base64
import shlex
import urllib.parse
from tkinter import scrolledtext
from datetime import datetime

# Optional SVG rendering support (cairosvg + Pillow). If unavailable we fall back to text button.
HAS_SVG_SUPPORT = False
try:
    import cairosvg
    class FileOrganizerApp(tk.Tk):
        """
        Aesthetically improved GUI application for FileOrganizer.
        """

        def __init__(self):
            super().__init__()
            self.organizer = FileOrganizer()
            self.title("boBnox(v2.0)")
            # Smaller, minimal window size
            self.geometry("480x360")
            self.configure(bg="#1E1E1E")
            self.path_var = tk.StringVar()
            self.status_var = tk.StringVar(value="Ready. Select a folder to begin.")

            self.setup_styles()
            self.create_widgets()

        def setup_styles(self):
            """Configures the dark, flat look and feel."""
            style = ttk.Style(self)
            try:
                style.theme_use('clam')
            except Exception:
                pass

            # Background colors and fonts (attached to self for reuse)
            self.BG_DARK = "#1E1E1E"
            self.BG_MID = "#2D2D30"
            self.FG_LIGHT = "#FFFFFF"
            self.ACCENT_COLOR = "#0078D4"  # Blue accent

            # Configure ttk styles
            style.configure("TFrame", background=self.BG_DARK)
            style.configure("TLabel", background=self.BG_DARK, foreground=self.FG_LIGHT, font=("Inter", 12))
            style.configure("Title.TLabel", font=("Inter", 18, "bold"), foreground=self.ACCENT_COLOR)
            style.configure("Status.TLabel", background=self.BG_DARK, foreground="#999999", font=("Inter", 10, "italic"))

            # Entry/Input
            style.configure("TEntry", fieldbackground=self.BG_MID, foreground=self.FG_LIGHT, borderwidth=0, relief="flat", padding=6)

            # Button Styles - prefer dark backgrounds so ttk Buttons don't create large blue bars
            style.configure("TButton",
                            font=("Inter", 11, "bold"),
                            background=self.BG_DARK,
                            foreground=self.FG_LIGHT,
                            borderwidth=0,
                            relief="flat",
                            padding=[10, 6])
            try:
                style.map("TButton",
                          background=[('active', '#005A9E'), ('disabled', '#555555')],
                          foreground=[('active', 'white')])
            except Exception:
                pass

            # Progress Bar
            style.configure("TProgressbar",
                            troughcolor=self.BG_MID,
                            background=self.ACCENT_COLOR,
                            troughrelief="flat",
                            borderwidth=0)

        def create_widgets(self):
            """Creates and positions all UI elements using grid for precise control."""
            # Main Frame with smaller padding
            main_frame = ttk.Frame(self, padding="12")
            main_frame.pack(expand=True, fill=tk.BOTH)
            main_frame.grid_columnconfigure(0, weight=1)

            # 1. Folder display area (drag & drop removed for simplicity)
            self.drop_target = tk.Label(
                main_frame,
                text="📁 Select a folder using Browse",
                font=("Inter", 12, "bold"),
                relief="solid",
                borderwidth=1,
                bg=self.BG_MID,
                fg="#AAAAAA",
                padx=8,
                pady=12,
            )
            self.drop_target.grid(row=1, column=0, sticky="ew", pady=(0, 8), ipady=6)

            # Separator or alternative instruction
            ttk.Label(main_frame, text="— OR —", foreground="#555555", background=self.BG_DARK).grid(row=2, column=0, pady=4)

            # Path Entry and Browse Button
            path_frame = ttk.Frame(main_frame)
            path_frame.grid(row=3, column=0, sticky="ew", pady=(6, 12))
            path_frame.grid_columnconfigure(0, weight=1)

            self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var)
            self.path_entry.grid(row=0, column=0, sticky="ew")

            browse_button = ttk.Button(path_frame, text="Browse...", command=self.select_directory)
            browse_button.grid(row=0, column=1, padx=(10, 0))

            # Organize Button - icon-only button (no full-width blue background)
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
                btn.grid(row=4, column=0, pady=(8, 14))
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

            # Progress Bar and Status
            self.progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=400, mode="determinate")
            self.progress_bar.grid(row=5, column=0, sticky="ew", pady=(0, 6))

            # Log console (read-only) to display per-run details
            log_frame = ttk.Frame(main_frame)
            log_frame.grid(row=6, column=0, sticky="nsew", pady=(6, 0))
            main_frame.grid_rowconfigure(6, weight=1)

            self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, state='disabled')
            # Styling for dark theme
            try:
                self.log_text.configure(bg=self.BG_MID, fg=self.FG_LIGHT, insertbackground=self.FG_LIGHT)
            except Exception:
                pass
            self.log_text.pack(expand=True, fill='both')

            self.status_label = ttk.Label(main_frame, textvariable=self.status_var, style="Status.TLabel")
            self.status_label.grid(row=7, column=0, sticky="w", pady=(6, 0))

            # Save log button
            controls_frame = ttk.Frame(main_frame)
            controls_frame.grid(row=8, column=0, sticky='e', pady=(6, 6))
            save_btn = ttk.Button(controls_frame, text="Save Log", command=self.save_log_dialog)
            save_btn.pack(side='right')

        # --- UI EVENT HANDLERS ---

        def handle_drop(self, event):
            # DnD removed; keep this handler for backwards compatibility but ignore
            return

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
                    text="📁 Select a folder using Browse",
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
            try:
                if hasattr(self.organize_button, 'state'):
                    try:
                        self.organize_button.state(['disabled'])
                    except Exception:
                        self.organize_button.config(state='disabled')
                else:
                    self.organize_button.config(state='disabled')
            except Exception:
                pass

            try:
                self.path_entry.state(['disabled'])
            except Exception:
                try:
                    self.path_entry.config(state='disabled')
                except Exception:
                    pass

            self.status_var.set("Processing... Please wait.")
            self.progress_bar['value'] = 0

            # Initialize log console for this run
            try:
                self.log_text.configure(state='normal')
                self.log_text.delete('1.0', 'end')
                self.log_text.configure(state='disabled')
            except Exception:
                pass
            self._append_log(f"=== Organization started at {datetime.now().isoformat()} ===")

            # Start the organization task in a new thread
            self.thread = threading.Thread(target=self.organize_action, args=(directory_path,), daemon=True)
            self.thread.start()

        def update_status(self, message, progress_value):
            """Thread-safe status updater: schedule UI updates on the main thread."""
            try:
                self.after(0, lambda: self._update_status_ui(message, progress_value))
            except Exception:
                self._update_status_ui(message, progress_value)

        def _update_status_ui(self, message, progress_value):
            """Actual UI update executed on the main thread."""
            self.status_var.set(message)
            # Convert 0-1.0 progress to Tkinter's 0-100 scale
            try:
                self.progress_bar['value'] = progress_value * 100
            except Exception:
                pass
            self._append_log(message)
            try:
                self.update_idletasks() # Force GUI redraw
            except Exception:
                pass

        def _append_log(self, text):
            """Append a line to the log console in a thread-safe way."""
            def do_append():
                try:
                    self.log_text.configure(state='normal')
                    self.log_text.insert('end', text + "\n")
                    self.log_text.see('end')
                    self.log_text.configure(state='disabled')
                except Exception:
                    pass

            try:
                self.after(0, do_append)
            except Exception:
                do_append()

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
                    final_message = "ℹ️ Organization complete: no files were moved."

                self.after(0, lambda: messagebox.showinfo("Success", final_message))
                self.after(0, self.reset_ui)

            except FileNotFoundError as e:
                self.after(0, lambda: messagebox.showerror("Error", str(e)))
                self.after(0, self.reset_ui)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred: {e}"))
                self.after(0, self.reset_ui)

        def save_log_dialog(self):
            """Open a Save As dialog and write the current log to the chosen file."""
            try:
                filename = filedialog.asksaveasfilename(
                    defaultextension='.txt',
                    filetypes=[('Text files', '*.txt'), ('All files', '*.*')],
                    title='Save log as'
                )
                if not filename:
                    return
                content = self.log_text.get('1.0', 'end')
                with open(filename, 'w', encoding='utf-8') as fh:
                    fh.write(content)
                messagebox.showinfo('Saved', f'Log saved to: {filename}')
            except Exception as e:
                messagebox.showerror('Error', f'Failed to save log: {e}')

        def reset_ui(self):
            """Resets the UI elements to the initial state."""
            try:
                if hasattr(self.organize_button, 'state'):
                    try:
                        self.organize_button.state(['!disabled'])
                    except Exception:
                        try:
                            self.organize_button.config(state='normal')
                        except Exception:
                            pass
                else:
                    try:
                        self.organize_button.config(state='normal')
                    except Exception:
                        pass
            except Exception:
                pass

            try:
                self.path_entry.state(['!disabled'])
            except Exception:
                try:
                    self.path_entry.config(state='normal')
                except Exception:
                    pass

            self.path_var.set("")
            self.status_var.set("Ready. Select a folder to begin.")
            try:
                self.progress_bar['value'] = 0
            except Exception:
                pass


    if __name__ == "__main__":
        # Note: drag-and-drop was removed for simplicity. Use the Browse button.
        app = FileOrganizerApp()
        app.mainloop()
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

        # Initialize log console for this run
        try:
            self.log_text.configure(state='normal')
            self.log_text.delete('1.0', 'end')
            self.log_text.configure(state='disabled')
        except Exception:
            pass
        self._append_log(f"=== Organization started at {datetime.now().isoformat()} ===")

        # Start the organization task in a new thread
        self.thread = threading.Thread(target=self.organize_action, args=(directory_path,), daemon=True)
        self.thread.start()

    def update_status(self, message, progress_value):
        """Thread-safe status updater: schedule UI updates on the main thread."""
        try:
            self.after(0, lambda: self._update_status_ui(message, progress_value))
        except Exception:
            self._update_status_ui(message, progress_value)

    def _update_status_ui(self, message, progress_value):
        """Actual UI update executed on the main thread."""
        self.status_var.set(message)
        # Convert 0-1.0 progress to Tkinter's 0-100 scale
        try:
            self.progress_bar['value'] = progress_value * 100
        except Exception:
            pass
        self._append_log(message)
        self.update_idletasks() # Force GUI redraw

    def _append_log(self, text):
        """Append a line to the log console in a thread-safe way."""
        def do_append():
            try:
                self.log_text.configure(state='normal')
                self.log_text.insert('end', text + "\n")
                self.log_text.see('end')
                self.log_text.configure(state='disabled')
            except Exception:
                pass

        try:
            self.after(0, do_append)
        except Exception:
            do_append()

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
