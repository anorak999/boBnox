import argparse
import os
import sys
import json
from datetime import datetime

from bobnox import FileOrganizer, load_config, save_config, setup_logging


def main():
    parser = argparse.ArgumentParser(description="boBnox - File Organizer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    organize_parser = subparsers.add_parser("organize", help="Organize files in a directory")
    organize_parser.add_argument("--path", "-p", required=True, help="Path to directory to organize")
    organize_parser.add_argument("--dry-run", "-d", action="store_true", help="Preview changes without moving files")
    organize_parser.add_argument("--recursive", "-r", action="store_true", help="Include subdirectories")
    organize_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    undo_parser = subparsers.add_parser("undo", help="Undo last organization")
    undo_parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    config_parser = subparsers.add_parser("config", help="View or modify configuration")
    config_parser.add_argument("--show", action="store_true", help="Show current configuration")
    config_parser.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set a configuration value")
    config_parser.add_argument("--list-extensions", action="store_true", help="List all extension mappings")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if getattr(args, "verbose", False):
        setup_logging(level=10)

    if args.command == "organize":
        run_organize(args)
    elif args.command == "undo":
        run_undo(args)
    elif args.command == "config":
        run_config(args)


def run_organize(args):
    directory = args.path
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory")
        sys.exit(1)

    config = load_config()
    organizer = FileOrganizer(config)
    organizer.organize_subdirectories = args.recursive

    log_lines = []

    def status_cb(message, progress):
        print(message)
        log_lines.append(message)

    start_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_lines.append(f"=== Organization started at {start_ts} ===")
    log_lines.append(f"Directory: {directory}")
    log_lines.append(f"Mode: {'Dry Run' if args.dry_run else 'Live'}")
    log_lines.append(f"Recursive: {args.recursive}")
    log_lines.append("")

    try:
        moved = organizer.organize_directory(directory, status_cb, dry_run=args.dry_run)
        end_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_lines.append("")
        log_lines.append(f"=== Organization completed at {end_ts} ===")
        log_lines.append(f"Files {'would be moved' if args.dry_run else 'moved'}: {moved}")

        if not args.dry_run and config.get("create_log_file", True):
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = f"bobnox-log-{ts}.txt"
            path = os.path.join(directory, fname)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(log_lines))
            print(f"Log saved to: {path}")

        print(f"\n{'Preview' if args.dry_run else 'Organization'} complete! {moved} files {'would be' if args.dry_run else ''} moved.")

    except Exception as e:
        log_lines.append(f"ERROR: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def run_undo(args):
    config = load_config()
    organizer = FileOrganizer(config)

    if not organizer._move_history:
        print("Nothing to undo.")
        return

    def status_cb(message, progress):
        print(message)

    try:
        restored = organizer.undo_last_organization(status_cb)
        print(f"\nUndo complete! Restored {restored} files.")
    except Exception as e:
        print(f"Error during undo: {e}", file=sys.stderr)
        sys.exit(1)


def run_config(args):
    config = load_config()

    if args.show:
        print(json.dumps(config, indent=2))
    elif args.list_extensions:
        print("Extension Mappings:")
        print("-" * 40)
        for ext, folder in sorted(config.get("extension_map", {}).items()):
            print(f"  {ext:10} -> {folder}")
    elif args.set:
        key, value = args.set
        if key == "organize_subdirectories":
            config[key] = value.lower() in ("true", "1", "yes")
        elif key == "create_log_file":
            config[key] = value.lower() in ("true", "1", "yes")
        else:
            print(f"Unknown config key: {key}")
            print("Valid keys: organize_subdirectories, create_log_file")
            sys.exit(1)
        save_config(config)
        print(f"Configuration updated: {key} = {value}")
    else:
        print("Usage: organize_cli.py config [--show | --list-extensions | --set KEY VALUE]")


if __name__ == "__main__":
    main()
