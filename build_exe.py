#!/usr/bin/env python3
"""
Build script to create a standalone executable (pst2mbox.exe) using PyInstaller.
"""

from pathlib import Path
import subprocess
import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def build_executable() -> bool:
    """Build pst2mbox as a standalone single-file executable."""
    print("=" * 60)
    print("         Building pst2mbox Standalone Executable")
    print("=" * 60)
    print()

    package_map = {
        "PyInstaller": "PyInstaller",
        "libpff-python": "pypff",
        "striprtf": "striprtf",
    }

    print("1. Checking required dependencies...")
    for pkg_name, mod_name in package_map.items():
        try:
            __import__(mod_name)
            print(f"  [OK] {pkg_name} is available")
        except ImportError:
            print(f"  Installing {pkg_name}...")
            subprocess.run([sys.executable, "-m", "pip", "install", pkg_name], check=True)
            print(f"  [OK] {pkg_name} installed successfully")

    print("\n2. Building standalone single-file executable with PyInstaller...")
    spec_file = Path("pst2mbox.spec")

    if spec_file.exists():
        cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", str(spec_file)]
    else:
        data_sep = ";" if sys.platform == "win32" else ":"
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--onefile",
            "--console",
            "--name",
            "pst2mbox",
            "--paths",
            "src",
            "--add-data",
            f"README.md{data_sep}.",
            "--hidden-import",
            "pst2mbox",
            "--hidden-import",
            "pst2mbox.converter",
            "--hidden-import",
            "pst2mbox.header_helper",
            "--hidden-import",
            "pst2mbox.cli",
            "--hidden-import",
            "pypff",
            "--hidden-import",
            "striprtf",
            "--hidden-import",
            "striprtf.striprtf",
            "--clean",
            "--noconfirm",
            "src/pst2mbox/cli.py",
        ]

    try:
        subprocess.run(cmd, check=True)
        print("\n[OK] PyInstaller build completed successfully!")

        exe_name = "pst2mbox.exe" if sys.platform == "win32" else "pst2mbox"
        exe_path = Path("dist") / exe_name

        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print()
            print("=" * 60)
            print("  BUILD SUCCESSFUL!")
            print("=" * 60)
            print(f"  Standalone Executable: {exe_path.resolve()}")
            print(f"  File Size:             {size_mb:.2f} MB")
            print()
            print("You can distribute 'pst2mbox.exe' to any Windows PC without")
            print("needing Python or any external tools installed!")
            print("=" * 60)
            return True
        else:
            print("Error: Output executable not found in dist/ directory.")
            return False

    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with exit code {e.returncode}")
        return False


if __name__ == "__main__":
    success = build_executable()
    sys.exit(0 if success else 1)