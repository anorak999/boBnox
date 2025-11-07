import argparse
import os
from datetime import datetime

from bobnox import FileOrganizer


def main():
    parser = argparse.ArgumentParser(description="Run boBnox organizer in headless mode")
    parser.add_argument("--path", "-p", required=True, help="Path to the directory to organize (host path mounted into container)")
    args = parser.parse_args()

    directory = args.path
    if not os.path.isdir(directory):
        print(f"Error: '{directory}' is not a valid directory")
        raise SystemExit(1)

    organizer = FileOrganizer()
    log_lines = []

    def status_cb(message, progress):
        print(message)
        log_lines.append(message)

    start_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_lines.append(f"=== Organization started at {start_ts} ===")
    log_lines.append(f"Directory: {directory}")
    log_lines.append("")

    try:
        moved = organizer.organize_directory(directory, status_cb)
        end_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_lines.append("")
        log_lines.append(f"=== Organization completed at {end_ts} ===")
        log_lines.append(f"Files moved: {moved}")

        # write log
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        fname = f"bobnox-log-{ts}.txt"
        path = os.path.join(directory, fname)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(log_lines))
        print(f"Log saved to: {path}")

    except Exception as e:
        log_lines.append(f"ERROR: {e}")
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        fname = f"bobnox-log-error-{ts}.txt"
        path = os.path.join(directory, fname)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(log_lines))
            print(f"Error log saved to: {path}")
        except Exception:
            print("Failed to write log file")
        raise


if __name__ == "__main__":
    main()
