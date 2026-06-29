#!/usr/bin/env python3
"""Build an .rpm package from a staged directory using Python rpm module."""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile


def build_rpm(stage_dir, output_dir, version):
    pkg_name = "bobnox"
    release = "1"

    os.makedirs(output_dir, exist_ok=True)

    # Generate an RPM spec file and use rpmbuild if available,
    # otherwise create a tarball-based RPM with the rpm Python module.
    try:
        import rpm
        HAS_RPM = True
    except ImportError:
        HAS_RPM = False

    if HAS_RPM and shutil.which("rpmbuild"):
        build_rpm_with_rpmbuild(stage_dir, output_dir, version, pkg_name, release)
    else:
        build_rpm_tarball(stage_dir, output_dir, version, pkg_name, release)


def build_rpm_with_rpmbuild(stage_dir, output_dir, version, pkg_name, release):
    """Build RPM using rpmbuild (preferred method)."""
    with tempfile.TemporaryDirectory() as tmp:
        for d in ["BUILD", "SOURCES", "SPECS", "RPMS", "SRPMS", "BUILDROOT"]:
            os.makedirs(os.path.join(tmp, d))

        # Create source tarball - rename stage dir to Name-Version inside tarball
        tarball_name = f"{pkg_name}-{version}.tar.gz"
        tarball_path = os.path.join(tmp, "SOURCES", tarball_name)
        stage_parent = os.path.dirname(os.path.abspath(stage_dir))
        with tempfile.TemporaryDirectory() as tar_tmp:
            renamed = os.path.join(tar_tmp, f"{pkg_name}-{version}")
            shutil.copytree(stage_dir, renamed)
            subprocess.run(
                ["tar", "czf", tarball_path, "-C", tar_tmp, f"{pkg_name}-{version}"],
                check=True,
            )

        # Write spec file
        # Build changelog date in RPM format: "Day Mon DD YYYY"
        import datetime
        changelog_date = datetime.datetime.now().strftime("%a %b %d %Y")

        spec_content = f"""Name:           {pkg_name}
Version:        {version}
Release:        {release}%{{?dist}}
Summary:        Modern file organizer with Bento Grid dark UI
License:        MIT
URL:            https://github.com/anorak999/boBnox
BuildArch:      noarch
Source0:        {pkg_name}-{version}.tar.gz

Requires:       python3 >= 3.10
Requires:       python3-pillow
Recommends:     electron
Recommends:     python3-magic
Recommends:     python3-inotify-simple
Recommends:     python3-cairosvg

%description
BoBnox is a file organizer for Linux that automatically sorts files into
categorized folders. Features include advanced deduplication, real-time
file system monitoring, and a transactional rollback ledger.

%prep
%autosetup -n {pkg_name}-%{{version}}

%install
mkdir -p %{{buildroot}}/usr/bin
mkdir -p %{{buildroot}}/usr/lib/{pkg_name}
mkdir -p %{{buildroot}}/usr/share/applications
mkdir -p %{{buildroot}}/usr/share/icons
mkdir -p %{{buildroot}}/usr/share/doc/{pkg_name}

cp -a usr/lib/{pkg_name}/* %{{buildroot}}/usr/lib/{pkg_name}/
cp usr/bin/* %{{buildroot}}/usr/bin/
chmod 755 %{{buildroot}}/usr/bin/{pkg_name} %{{buildroot}}/usr/bin/{pkg_name}-gui
cp usr/share/applications/*.desktop %{{buildroot}}/usr/share/applications/
cp usr/share/icons/*.png %{{buildroot}}/usr/share/icons/
cp usr/share/doc/{pkg_name}/* %{{buildroot}}/usr/share/doc/{pkg_name}/

%files
/usr/bin/{pkg_name}
/usr/bin/{pkg_name}-gui
/usr/lib/{pkg_name}/*
/usr/share/applications/{pkg_name}.desktop
/usr/share/icons/{pkg_name}.png
/usr/share/doc/{pkg_name}/*

%post
update-desktop-database /usr/share/applications/ 2>/dev/null || true
gtk-update-icon-cache -f /usr/share/icons/ 2>/dev/null || true
fc-cache -f 2>/dev/null || true

%changelog
* {changelog_date} BoBnox Contributors <bobnox@example.com> - {version}-{release}
- Package built for system-wide installation
"""
        spec_path = os.path.join(tmp, "SPECS", f"{pkg_name}.spec")
        with open(spec_path, "w") as f:
            f.write(spec_content)

        # Run rpmbuild
        subprocess.run(
            [
                "rpmbuild",
                "--define", f"_topdir {tmp}",
                "-bb", spec_path,
            ],
            check=True,
        )

        # Find and copy the built RPM
        for root, dirs, files in os.walk(os.path.join(tmp, "RPMS")):
            for fname in files:
                if fname.endswith(".rpm"):
                    shutil.copy2(os.path.join(root, fname), output_dir)
                    print(f"  Created: {os.path.join(output_dir, fname)}")


def build_rpm_tarball(stage_dir, output_dir, version, pkg_name, release):
    """Create an RPM-compatible tarball with metadata (fallback when rpmbuild unavailable)."""
    with tempfile.TemporaryDirectory() as tmp:
        # Create source tarball matching RPM naming
        tarball_name = f"{pkg_name}-{version}.tar.gz"
        tarball_path = os.path.join(tmp, tarball_name)

        stage_parent = os.path.dirname(stage_dir)
        stage_base = os.path.basename(stage_dir)

        # The tarball should contain the files rooted at stage_dir basename
        # so that rpmbuild's %setup -n works
        subprocess.run(
            ["tar", "czf", tarball_path, "-C", stage_parent, stage_base],
            check=True,
        )

        final_tarball = os.path.join(output_dir, tarball_name)
        shutil.copy2(tarball_path, final_tarball)
        print(f"  Created source tarball: {final_tarball}")

        # Write spec file alongside
        spec_content = f"""Name:           {pkg_name}
Version:        {version}
Release:        {release}%{{?dist}}
Summary:        Modern file organizer with Bento Grid dark UI
License:        MIT
URL:            https://github.com/anorak999/boBnox
BuildArch:      noarch

Requires:       python3 >= 3.10
Requires:       python3-pillow
Recommends:     electron
Recommends:     python3-magic
Recommends:     python3-inotify-simple
Recommends:     python3-cairosvg

%description
BoBnox is a file organizer for Linux that automatically sorts files into
categorized folders. Features include advanced deduplication, real-time
file system monitoring, and a transactional rollback ledger.

%prep
%setup -q -n {stage_base}

%install
mkdir -p %{{buildroot}}/usr/bin
mkdir -p %{{buildroot}}/usr/lib/{pkg_name}
mkdir -p %{{buildroot}}/usr/share/applications
mkdir -p %{{buildroot}}/usr/share/icons
mkdir -p %{{buildroot}}/usr/share/doc/{pkg_name}

cp -a usr/lib/{pkg_name}/* %{{buildroot}}/usr/lib/{pkg_name}/
cp usr/bin/* %{{buildroot}}/usr/bin/
chmod 755 %{{buildroot}}/usr/bin/{pkg_name} %{{buildroot}}/usr/bin/{pkg_name}-gui
cp usr/share/applications/*.desktop %{{buildroot}}/usr/share/applications/
cp usr/share/icons/*.png %{{buildroot}}/usr/share/icons/
cp usr/share/doc/{pkg_name}/* %{{buildroot}}/usr/share/doc/{pkg_name}/

%files
/usr/bin/{pkg_name}
/usr/bin/{pkg_name}-gui
/usr/lib/{pkg_name}/*
/usr/share/applications/{pkg_name}.desktop
/usr/share/icons/{pkg_name}.png
/usr/share/doc/{pkg_name}/*

%post
update-desktop-database /usr/share/applications/ 2>/dev/null || true
gtk-update-icon-cache -f /usr/share/icons/ 2>/dev/null || true
fc-cache -f 2>/dev/null || true

%changelog
* $(date "+%a %b %d %Y") BoBnox Contributors <bobnox@example.com> - {version}-{release}
- Package built for system-wide installation
"""
        spec_path = os.path.join(output_dir, f"{pkg_name}.spec")
        with open(spec_path, "w") as f:
            f.write(spec_content)
        print(f"  Created RPM spec: {spec_path}")
        print(f"  To build RPM: rpmbuild -bb {spec_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build .rpm package")
    parser.add_argument("--stage", required=True, help="Staged install directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--version", required=True, help="Package version")
    args = parser.parse_args()
    build_rpm(args.stage, args.output, args.version)
