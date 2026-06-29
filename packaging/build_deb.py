#!/usr/bin/env python3
"""Build a .deb package from a staged directory using ar + tar (no dpkg-deb needed)."""

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile


def md5sums_for_dir(root):
    """Generate MD5SUMS content for all files under root."""
    lines = []
    for dirpath, _, filenames in os.walk(root):
        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            if os.path.islink(fpath):
                continue
            rel = os.path.relpath(fpath, root)
            with open(fpath, "rb") as f:
                digest = hashlib.md5(f.read()).hexdigest()
            lines.append(f"{digest}  ./{rel}")
    return "\n".join(lines) + "\n"


def conffiles_for_dir(root):
    """Generate CONFFILES listing config files (desktop, icons)."""
    conf_paths = []
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            rel = os.path.relpath(fpath, root)
            if any(rel.startswith(p) for p in ["usr/share/applications/", "usr/share/icons/"]):
                conf_paths.append(f"/{rel}")
    return "\n".join(sorted(conf_paths)) + "\n" if conf_paths else ""


def build_deb(stage_dir, output_dir, version):
    pkg_name = "bobnox"
    arch = "all"
    deb_ver = f"{version}-1"

    os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        ctrl_dir = os.path.join(tmp, "control")
        data_dir = os.path.join(tmp, "data")
        os.makedirs(ctrl_dir)
        os.makedirs(data_dir)

        # Copy staged files into data/
        subprocess.run(["cp", "-a", stage_dir + "/.", data_dir], check=True)

        # Build control file
        control_content = f"""Package: {pkg_name}
Version: {deb_ver}
Architecture: {arch}
Maintainer: BoBnox Contributors <bobnox@example.com>
Homepage: https://github.com/anorak999/boBnox
Description: Modern file organizer with Bento Grid dark UI
 BoBnox is a file organizer for Linux that automatically sorts files into
 categorized folders. Features include advanced deduplication, real-time
 file system monitoring, and a transactional rollback ledger.
Depends: python3 (>= 3.10), python3-pil
Recommends: python3-magic, python3-inotify-simple, python3-cairosvg
Section: utils
Priority: optional
Installed-Size: {subprocess.run(['du', '-sk', data_dir], capture_output=True, text=True).stdout.split()[0]}
"""

        with open(os.path.join(ctrl_dir, "control"), "w") as f:
            f.write(control_content)

        # Write MD5Sums
        with open(os.path.join(ctrl_dir, "md5sums"), "w") as f:
            f.write(md5sums_for_dir(data_dir))

        # Write conffiles
        conffiles = conffiles_for_dir(data_dir)
        if conffiles:
            with open(os.path.join(ctrl_dir, "conffiles"), "w") as f:
                f.write(conffiles)

        # Copy postinst script
        postinst_src = os.path.join(os.path.dirname(__file__), "postinst.sh")
        if os.path.exists(postinst_src):
            shutil.copy2(postinst_src, os.path.join(ctrl_dir, "postinst"))
            os.chmod(os.path.join(ctrl_dir, "postinst"), 0o755)

        # Create control.tar.xz
        control_tar = os.path.join(tmp, "control.tar.xz")
        with tarfile.open(control_tar, "w:xz") as tar:
            for entry in os.listdir(ctrl_dir):
                tar.add(os.path.join(ctrl_dir, entry), arcname=entry)

        # Create data.tar.xz
        data_tar = os.path.join(tmp, "data.tar.xz")
        with tarfile.open(data_tar, "w:xz") as tar:
            for entry in os.listdir(data_dir):
                tar.add(os.path.join(data_dir, entry), arcname=entry)

        # Create debian-binary
        deb_bin = os.path.join(tmp, "debian-binary")
        with open(deb_bin, "w") as f:
            f.write("2.0\n")

        # Assemble .deb using ar
        deb_name = f"{pkg_name}_{deb_ver}_{arch}.deb"
        deb_path = os.path.join(output_dir, deb_name)

        subprocess.run(
            ["ar", "rcsD", deb_path, deb_bin, control_tar, data_tar],
            check=True,
        )

        print(f"  Created: {deb_path}")
        return deb_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build .deb package")
    parser.add_argument("--stage", required=True, help="Staged install directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--version", required=True, help="Package version")
    args = parser.parse_args()
    build_deb(args.stage, args.output, args.version)
