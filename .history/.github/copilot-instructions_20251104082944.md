# boBnox File Organizer - AI Coding Agent Instructions

## Project Overview
boBnox is a Python GUI application for organizing files into categorized folders. Single-file architecture (`bobnox.py`) with clear separation between business logic (`FileOrganizer`) and UI (`FileOrganizerApp`).

## Architecture Pattern
**Separation of Concerns**:
- `FileOrganizer` class: Pure business logic, no GUI dependencies. Accepts callbacks for progress reporting.
- `FileOrganizerApp` class: Tkinter GUI inheriting from `TkinterDnD.Tk` for drag-and-drop support.
- Threading model: File operations run in daemon threads to keep UI responsive. Use `self.after()` for thread-safe GUI updates.

## Key Dependencies
- `tkinter`: Standard GUI library
- `tkinterdnd2`: Drag-and-drop functionality (must be installed: `pip install tkinterdnd2`)
- Virtual environment: `.venv/` (Python, not tracked in git)

## File Categorization System
Files are organized by extension via `EXTENSION_MAP` dictionary in `FileOrganizer`:
- Maps file extensions (lowercase) to folder names
- Unknown extensions: Creates folders like `"XYZ Files"` for `.xyz` extensions
- No extension: Goes to `"Other Files"`

**When adding file types**: Update `EXTENSION_MAP` with lowercase extension keys.

## Duplicate Handling
Conflicts resolved by appending `(1)`, `(2)`, etc. to base filename:
```python
# file.txt -> file (1).txt -> file (2).txt
```
Logic in `organize_directory()` method before `shutil.move()`.

## UI Styling Approach
Dark theme using `ttk.Style` with 'clam' base:
- Colors: `#1E1E1E` (background), `#0078D4` (accent blue), `#2D2D30` (mid-dark)
- Font: "Inter" throughout (fallback to system default if unavailable)
- Custom ttk styles: `"Title.TLabel"`, `"Status.TLabel"` for specific components

## Threading Safety Rules
1. **Never** call Tkinter methods directly from worker threads
2. Use `self.after(0, lambda: ...)` to schedule GUI updates on main thread
3. Progress updates via callback: `status_callback(message, progress_percent)` where progress is 0.0-1.0

## Error Handling Philosophy
- File move failures: Log to console but continue processing other files
- Directory validation: Raise `FileNotFoundError` with user-friendly message
- GUI errors: Show `messagebox` dialogs, then reset UI to ready state

## Running the Application
```bash
python bobnox.py
```
No build system, no tests, no CLI arguments. Run directly from project root.

## Workflow Conventions
- Self-contained script: Avoid creating additional modules unless adding major features
- UI state management: Always re-enable buttons and reset `path_var` after operations (see `reset_ui()`)
- Progress reporting: Convert 0-1.0 float to 0-100 scale for Tkinter's Progressbar

## Common Modifications
- **Add file type**: Append to `EXTENSION_MAP` dictionary
- **Change UI colors**: Update `setup_styles()` color constants
- **Adjust folder names**: Modify values in `EXTENSION_MAP` (keys are extensions, values are folder names)
