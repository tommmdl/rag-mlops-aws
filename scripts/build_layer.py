#!/usr/bin/env python3
"""
Compila o Lambda Layer com binários compatíveis com Linux (manylinux2014).
Funciona em Windows, macOS e Linux — substitui o null_resource do Terraform.
"""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT         = Path(__file__).parent.parent
REQUIREMENTS = ROOT / "requirements.txt"
BUILD_DIR    = ROOT / "terraform" / "_layer_build" / "python"
LAYER_ZIP    = ROOT / "terraform" / "layer.zip"


def main() -> None:
    print("Construindo Lambda Layer (Linux-compatible binaries)...")

    if BUILD_DIR.parent.exists():
        shutil.rmtree(BUILD_DIR.parent)
    BUILD_DIR.mkdir(parents=True)

    subprocess.run(
        [
            sys.executable, "-m", "pip", "install",
            "-r", str(REQUIREMENTS),
            "--target", str(BUILD_DIR),
            "--platform", "manylinux2014_x86_64",
            "--only-binary=:all:",
            "--quiet",
        ],
        check=True,
    )

    if LAYER_ZIP.exists():
        LAYER_ZIP.unlink()

    with zipfile.ZipFile(LAYER_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in BUILD_DIR.parent.rglob("*"):
            if file.is_file() and "__pycache__" not in str(file) and file.suffix != ".pyc":
                zf.write(file, file.relative_to(BUILD_DIR.parent.parent))

    shutil.rmtree(BUILD_DIR.parent)

    size_mb = LAYER_ZIP.stat().st_size / 1024 / 1024
    print(f"Layer criado: {LAYER_ZIP}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
