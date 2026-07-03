from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image

PLATFORM_LINUX = "linux"
PLATFORM_WINDOWS = "windows"
PLATFORM_MACOS = "macos"
PLATFORM_ORDER = (
    PLATFORM_LINUX,
    PLATFORM_WINDOWS,
    PLATFORM_MACOS,
)
PLATFORM_RUNNERS = {
    PLATFORM_LINUX: "ubuntu-latest",
    PLATFORM_WINDOWS: "windows-latest",
    PLATFORM_MACOS: "macos-latest",
}
PLATFORM_ARTIFACTS = {
    PLATFORM_LINUX: "linux-deb",
    PLATFORM_WINDOWS: "windows-msi",
    PLATFORM_MACOS: "macos-dmg",
}
PLATFORM_PACKAGE_LABELS = {
    PLATFORM_LINUX: "deb",
    PLATFORM_WINDOWS: "msi",
    PLATFORM_MACOS: "dmg",
}
PLATFORM_DISPLAY_NAMES = {
    PLATFORM_LINUX: "Linux",
    PLATFORM_WINDOWS: "Windows",
    PLATFORM_MACOS: "macOS",
}

LINUX_ICON_SIZES = [16, 24, 32, 48, 64, 128, 256, 512]
ICO_ICON_SIZES = [16, 24, 32, 48, 64, 128, 256]
ICNS_ICON_SIZES = [
    (16, 16, 1),
    (16, 16, 2),
    (32, 32, 1),
    (32, 32, 2),
    (128, 128, 1),
    (128, 128, 2),
    (256, 256, 1),
    (256, 256, 2),
    (512, 512, 1),
    (512, 512, 2),
]
ICNS_CANVAS_SIZE = 1024
SCAFFOLD_STATE_FILENAME = ".desktop_app_ci_builder.json"


class ScaffoldError(ValueError):
    pass


def normalize_platforms(platforms: Iterable[str]) -> tuple[str, ...]:
    requested = {platform.strip().lower() for platform in platforms if platform.strip()}
    invalid = requested.difference(PLATFORM_ORDER)
    if invalid:
        invalid_list = ", ".join(sorted(invalid))
        raise ScaffoldError(f"Unsupported platforms: {invalid_list}")
    return tuple(platform for platform in PLATFORM_ORDER if platform in requested)


@dataclass(slots=True)
class ScaffoldConfig:
    target_dir: Path
    icon_path: Path
    app_name: str
    version: str
    package_name: str
    executable_name: str
    bundle_id: str
    entry_script: str
    manufacturer: str
    app_data_dir_name: str
    linux_data_dir_name: str
    platforms: tuple[str, ...]

    def validate(self) -> None:
        errors: list[str] = []

        if not self.target_dir:
            errors.append("Target directory is required.")
        if not self.icon_path:
            errors.append("Master icon path is required.")
        if not self.app_name.strip():
            errors.append("App name is required.")
        if not self.version.strip():
            errors.append("Version is required.")
        if not self.package_name.strip():
            errors.append("Package name is required.")
        if not self.executable_name.strip():
            errors.append("Executable name is required.")
        if not self.bundle_id.strip():
            errors.append("Bundle ID is required.")
        if not self.entry_script.strip():
            errors.append("Entry script is required.")
        if not self.manufacturer.strip():
            errors.append("Manufacturer is required.")
        if not self.app_data_dir_name.strip():
            errors.append("App data directory name is required.")
        if not self.linux_data_dir_name.strip():
            errors.append("Linux data directory name is required.")
        try:
            self.platforms = normalize_platforms(self.platforms)
        except ScaffoldError as exc:
            errors.append(str(exc))
        if not self.platforms:
            errors.append("Choose at least one target platform.")

        if self.icon_path and not self.icon_path.exists():
            errors.append(f"Icon file not found: {self.icon_path}")

        if self.package_name and not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.package_name):
            errors.append(
                "Package name must use lowercase letters, numbers, and dashes only."
            )

        if self.bundle_id and not re.fullmatch(
            r"[A-Za-z0-9]+(?:\.[A-Za-z0-9_-]+)+",
            self.bundle_id,
        ):
            errors.append("Bundle ID must look like com.example.app")

        if self.executable_name and not re.fullmatch(r"[A-Za-z0-9._-]+", self.executable_name):
            errors.append(
                "Executable name must contain only letters, numbers, dot, underscore, or dash."
            )

        if self.version and not re.fullmatch(r"\d+\.\d+\.\d+(?:\.\d+)?", self.version):
            errors.append("Version must look like 1.2.3 or 1.2.3.4")

        if errors:
            raise ScaffoldError("\n".join(errors))

    @property
    def spec_filename(self) -> str:
        return f"{self.executable_name}.spec"

    @property
    def windows_executable_name(self) -> str:
        return f"{self.executable_name}.exe"

    @property
    def app_bundle_name(self) -> str:
        return f"{self.executable_name}.app"

    @property
    def wm_class(self) -> str:
        return self.executable_name

    @property
    def upgrade_code(self) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, self.bundle_id)).upper()

    @property
    def supports_linux(self) -> bool:
        return PLATFORM_LINUX in self.platforms

    @property
    def supports_windows(self) -> bool:
        return PLATFORM_WINDOWS in self.platforms

    @property
    def supports_macos(self) -> bool:
        return PLATFORM_MACOS in self.platforms


def slugify_package_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "my-desktop-app"


def slugify_executable_name(value: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", value)
    if not parts:
        return "MyDesktopApp"
    return "".join(part[:1].upper() + part[1:] for part in parts)


def slugify_bundle_company(value: str) -> str:
    company = re.sub(r"[^a-z0-9]+", "", value.strip().lower())
    return company or "example"


def make_bundle_id(package_name: str, manufacturer_name: str = "Example Company") -> str:
    company = slugify_bundle_company(manufacturer_name)
    suffix = package_name.replace("-", "")
    return f"com.{company}.{suffix}"


def _read_text_if_exists(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _extract_string_constant(source: str | None, name: str) -> str | None:
    if not source:
        return None
    match = re.search(rf'^{re.escape(name)}\s*=\s*["\'](.+?)["\']', source, re.MULTILINE)
    if not match:
        return None
    return match.group(1)


def _extract_spec_entry_script(source: str | None) -> str | None:
    if not source:
        return None
    match = re.search(r'Analysis\(\s*\[\s*"([^"]+)"\s*\]', source)
    if not match:
        return None
    return match.group(1)


def render_scaffold_state(config: ScaffoldConfig) -> str:
    payload = {
        "schema_version": 1,
        "generated_by": "desktop_app_ci_builder",
        "app_name": config.app_name,
        "version": config.version,
        "package_name": config.package_name,
        "executable_name": config.executable_name,
        "bundle_id": config.bundle_id,
        "entry_script": config.entry_script,
        "manufacturer": config.manufacturer,
        "app_data_dir_name": config.app_data_dir_name,
        "linux_data_dir_name": config.linux_data_dir_name,
        "platforms": list(config.platforms),
        "icon_path": "assets/icons/app-icon-source.png",
    }
    return json.dumps(payload, indent=2) + "\n"


def scaffold_state_path(target_dir: Path) -> Path:
    return target_dir / SCAFFOLD_STATE_FILENAME


def managed_scaffold_paths(config: ScaffoldConfig) -> set[Path]:
    target_dir = config.target_dir.resolve()
    paths = {
        target_dir / "VERSION",
        target_dir / "version.py",
        target_dir / "app_paths.py",
        target_dir / config.spec_filename,
        target_dir / ".github" / "workflows" / "release-packages.yml",
        target_dir / "scripts" / "validate_version.py",
        target_dir / "scripts" / "generate_icons.py",
        target_dir / "PACKAGING.md",
        scaffold_state_path(target_dir),
        target_dir / "assets" / "icons" / "app-icon-source.png",
        target_dir / "assets" / "icons" / "app-icon.png",
    }

    if config.supports_linux:
        paths.add(target_dir / "build_linux.sh")
        paths.add(target_dir / "scripts" / "build_deb.py")
        for size in LINUX_ICON_SIZES:
            paths.add(
                target_dir
                / "assets"
                / "icons"
                / "hicolor"
                / f"{size}x{size}"
                / "apps"
                / f"{config.package_name}.png"
            )

    if config.supports_windows:
        paths.add(target_dir / "build_windows.bat")
        paths.add(target_dir / "scripts" / "build_msi.py")
        paths.add(target_dir / "assets" / "icons" / "app-icon.ico")

    if config.supports_macos:
        paths.add(target_dir / "build_macos.sh")
        paths.add(target_dir / "scripts" / "build_dmg.sh")
        paths.add(target_dir / "assets" / "icons" / "app-icon.icns")

    return paths


def detect_existing_scaffold(target_dir: Path) -> ScaffoldConfig | None:
    target_dir = target_dir.resolve()
    manifest_path = scaffold_state_path(target_dir)
    manifest_text = _read_text_if_exists(manifest_path)
    if manifest_text:
        try:
            data = json.loads(manifest_text)
            return ScaffoldConfig(
                target_dir=target_dir,
                icon_path=target_dir / data.get("icon_path", "assets/icons/app-icon-source.png"),
                app_name=data.get("app_name", "").strip(),
                version=data.get("version", "").strip(),
                package_name=data.get("package_name", "").strip(),
                executable_name=data.get("executable_name", "").strip(),
                bundle_id=data.get("bundle_id", "").strip(),
                entry_script=data.get("entry_script", "").strip(),
                manufacturer=data.get("manufacturer", "").strip(),
                app_data_dir_name=data.get("app_data_dir_name", "").strip(),
                linux_data_dir_name=data.get("linux_data_dir_name", "").strip(),
                platforms=normalize_platforms(data.get("platforms", [])),
            )
        except Exception:
            pass

    packaging_text = _read_text_if_exists(target_dir / "PACKAGING.md")
    if not packaging_text or "This scaffold was generated for `" not in packaging_text:
        return None

    version_py = _read_text_if_exists(target_dir / "version.py")
    app_paths_py = _read_text_if_exists(target_dir / "app_paths.py")
    spec_files = sorted(target_dir.glob("*.spec"))
    spec_text = _read_text_if_exists(spec_files[0]) if spec_files else None
    build_msi_py = _read_text_if_exists(target_dir / "scripts" / "build_msi.py")
    version_text = _read_text_if_exists(target_dir / "VERSION")

    package_name = _extract_string_constant(version_py, "PACKAGE_NAME") or ""
    app_name = _extract_string_constant(version_py, "APP_NAME") or ""
    bundle_id = _extract_string_constant(version_py, "BUNDLE_ID") or ""
    executable_name = spec_files[0].stem if spec_files else ""
    entry_script = _extract_spec_entry_script(spec_text) or "main.py"
    manufacturer = _extract_string_constant(build_msi_py, "MANUFACTURER") or "Example Studio"
    app_data_dir_name = _extract_string_constant(app_paths_py, "APP_DATA_DIR_NAME") or executable_name
    linux_data_dir_name = _extract_string_constant(app_paths_py, "LINUX_DATA_DIR_NAME") or package_name

    platforms: list[str] = []
    if (target_dir / "build_linux.sh").exists() or (target_dir / "scripts" / "build_deb.py").exists():
        platforms.append(PLATFORM_LINUX)
    if (target_dir / "build_windows.bat").exists() or (target_dir / "scripts" / "build_msi.py").exists():
        platforms.append(PLATFORM_WINDOWS)
    if (target_dir / "build_macos.sh").exists() or (target_dir / "scripts" / "build_dmg.sh").exists():
        platforms.append(PLATFORM_MACOS)

    try:
        normalized_platforms = normalize_platforms(platforms)
    except ScaffoldError:
        normalized_platforms = ()

    return ScaffoldConfig(
        target_dir=target_dir,
        icon_path=target_dir / "assets" / "icons" / "app-icon-source.png",
        app_name=app_name,
        version=(version_text or "").strip(),
        package_name=package_name,
        executable_name=executable_name,
        bundle_id=bundle_id,
        entry_script=entry_script,
        manufacturer=manufacturer,
        app_data_dir_name=app_data_dir_name,
        linux_data_dir_name=linux_data_dir_name,
        platforms=normalized_platforms,
    )


def cleanup_stale_scaffold(previous_config: ScaffoldConfig, current_config: ScaffoldConfig) -> list[Path]:
    previous_paths = managed_scaffold_paths(previous_config)
    current_paths = managed_scaffold_paths(current_config)
    removed: list[Path] = []

    for path in sorted(previous_paths.difference(current_paths), key=lambda item: len(item.parts), reverse=True):
        if not path.exists() or not path.is_file():
            continue
        path.unlink()
        removed.append(path)

    parent_dirs = sorted(
        {path.parent for path in previous_paths.difference(current_paths)},
        key=lambda item: len(item.parts),
        reverse=True,
    )
    for directory in parent_dirs:
        if directory == current_config.target_dir.resolve():
            continue
        try:
            directory.rmdir()
        except OSError:
            pass

    return removed


def _fill_template(template: str, mapping: dict[str, str]) -> str:
    result = template
    for key, value in mapping.items():
        result = result.replace(key, value)
    return result


def _write_text(path: Path, content: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _make_square_image(source_path: Path, size: int) -> Image.Image:
    with Image.open(source_path) as source:
        resized = source.convert("RGBA")
        resized.thumbnail((size, size), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset_x = (size - resized.width) // 2
        offset_y = (size - resized.height) // 2
        canvas.paste(resized, (offset_x, offset_y), resized)
        return canvas


def generate_icon_assets(
    icon_path: Path,
    icon_root: Path,
    package_name: str,
    platforms: tuple[str, ...],
) -> list[Path]:
    created: list[Path] = []
    source_target = icon_root / "app-icon-source.png"
    _write_bytes(source_target, icon_path.read_bytes())
    created.append(source_target)

    runtime_icon = icon_root / "app-icon.png"
    runtime_image = _make_square_image(icon_path, 512)
    runtime_image.save(runtime_icon)
    created.append(runtime_icon)

    if PLATFORM_WINDOWS in platforms:
        windows_icon = icon_root / "app-icon.ico"
        windows_sizes = [(size, size) for size in ICO_ICON_SIZES]
        runtime_image.save(windows_icon, sizes=windows_sizes)
        created.append(windows_icon)

    if PLATFORM_MACOS in platforms:
        macos_icon = icon_root / "app-icon.icns"
        icns_image = _make_square_image(icon_path, ICNS_CANVAS_SIZE)
        icns_image.save(macos_icon, sizes=ICNS_ICON_SIZES)
        created.append(macos_icon)

    if PLATFORM_LINUX in platforms:
        for size in LINUX_ICON_SIZES:
            icon_path_out = icon_root / "hicolor" / f"{size}x{size}" / "apps" / f"{package_name}.png"
            linux_image = _make_square_image(icon_path, size)
            icon_path_out.parent.mkdir(parents=True, exist_ok=True)
            linux_image.save(icon_path_out)
            created.append(icon_path_out)

    return created


def render_version_py(config: ScaffoldConfig) -> str:
    template = '''import sys
from pathlib import Path

APP_NAME = "__APP_NAME__"
PACKAGE_NAME = "__PACKAGE_NAME__"
BUNDLE_ID = "__BUNDLE_ID__"


def version_file_candidates() -> list[Path]:
    candidates: list[Path] = []

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "VERSION")

    module_dir = Path(__file__).resolve().parent
    candidates.append(module_dir / "VERSION")
    candidates.append(module_dir.parent / "VERSION")

    return candidates


def read_version() -> str:
    for version_file in version_file_candidates():
        if not version_file.exists():
            continue

        version = version_file.read_text(encoding="utf-8").strip()
        if not version:
            raise ValueError(f"VERSION file is empty: {version_file}")
        return version

    searched = ", ".join(str(path) for path in version_file_candidates())
    raise FileNotFoundError(f"VERSION file not found. Looked in: {searched}")


__version__ = read_version()
'''
    return _fill_template(
        template,
        {
            "__APP_NAME__": config.app_name,
            "__PACKAGE_NAME__": config.package_name,
            "__BUNDLE_ID__": config.bundle_id,
        },
    )


def render_app_paths_py(config: ScaffoldConfig) -> str:
    template = '''import os
import sys
from pathlib import Path

APP_DATA_DIR_NAME = "__APP_DATA_DIR_NAME__"
LINUX_DATA_DIR_NAME = "__LINUX_DATA_DIR_NAME__"


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent


def get_resource_path(*parts: str) -> Path:
    roots: list[Path] = []

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))

    roots.append(get_app_root())
    roots.append(Path(__file__).resolve().parent)

    for root in roots:
        candidate = root.joinpath(*parts)
        if candidate.exists():
            return candidate

    return roots[0].joinpath(*parts)


def get_user_data_root() -> Path:
    if os.name == "nt":
        base_dir = Path(
            os.environ.get(
                "LOCALAPPDATA",
                Path.home() / "AppData" / "Local",
            )
        )
        return base_dir / APP_DATA_DIR_NAME

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DATA_DIR_NAME

    base_dir = Path(
        os.environ.get(
            "XDG_DATA_HOME",
            Path.home() / ".local" / "share",
        )
    )
    return base_dir / LINUX_DATA_DIR_NAME
'''
    return _fill_template(
        template,
        {
            "__APP_DATA_DIR_NAME__": config.app_data_dir_name,
            "__LINUX_DATA_DIR_NAME__": config.linux_data_dir_name,
        },
    )


def render_spec(config: ScaffoldConfig) -> str:
    template = '''# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

project_root = Path(globals().get("SPECPATH", Path.cwd())).resolve()
runtime_icon = project_root / "assets" / "icons" / "app-icon.png"
windows_icon = project_root / "assets" / "icons" / "app-icon.ico"
macos_icon = project_root / "assets" / "icons" / "app-icon.icns"

base_datas = [("VERSION", ".")]

if runtime_icon.exists():
    base_datas.append((str(runtime_icon), "assets/icons"))
if windows_icon.exists():
    base_datas.append((str(windows_icon), "assets/icons"))


a = Analysis(
    ["__ENTRY_SCRIPT__"],
    pathex=[str(project_root)],
    binaries=[],
    datas=base_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="__EXECUTABLE_NAME__",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(windows_icon) if windows_icon.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="__EXECUTABLE_NAME__",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="__APP_BUNDLE_NAME__",
        bundle_identifier="__BUNDLE_ID__",
        icon=str(macos_icon) if macos_icon.exists() else None,
    )
'''
    return _fill_template(
        template,
        {
            "__ENTRY_SCRIPT__": config.entry_script,
            "__EXECUTABLE_NAME__": config.executable_name,
            "__APP_BUNDLE_NAME__": config.app_bundle_name,
            "__BUNDLE_ID__": config.bundle_id,
        },
    )


def render_workflow(config: ScaffoldConfig) -> str:
    matrix_targets = "\n".join(
        [
            "          - label: {label}\n"
            "            runner: {runner}\n"
            "            artifact_name: {artifact}".format(
                label=PLATFORM_PACKAGE_LABELS[platform],
                runner=PLATFORM_RUNNERS[platform],
                artifact=PLATFORM_ARTIFACTS[platform],
            )
            for platform in config.platforms
        ]
    )
    pre_dependency_steps: list[str] = []
    post_build_steps: list[str] = []

    if config.supports_linux:
        pre_dependency_steps.append(
            """      - name: Install Linux packaging tools
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y dpkg-dev"""
        )
        post_build_steps.append(
            """      - name: Package deb
        if: runner.os == 'Linux'
        run: python scripts/build_deb.py"""
        )

    if config.supports_windows:
        post_build_steps.append(
            """      - name: Install WiX
        if: runner.os == 'Windows'
        shell: pwsh
        run: |
          dotnet tool install --global wix
          "$env:USERPROFILE\\.dotnet\\tools" | Out-File -FilePath $env:GITHUB_PATH -Encoding utf8 -Append"""
        )
        post_build_steps.append(
            """      - name: Package msi
        if: runner.os == 'Windows'
        run: python scripts/build_msi.py"""
        )

    if config.supports_macos:
        post_build_steps.append(
            """      - name: Package dmg
        if: runner.os == 'macOS'
        run: bash scripts/build_dmg.sh"""
        )

    template = '''name: Release Packages

on:
  push:
    tags:
      - '*'

permissions:
  contents: write

jobs:
  build:
    name: Build ${{ matrix.target.label }}
    runs-on: ${{ matrix.target.runner }}
    strategy:
      fail-fast: false
      matrix:
        target:
__MATRIX_TARGETS__

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

__PRE_DEPENDENCY_STEPS__

      - name: Install Python dependencies
        shell: bash
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then
            python -m pip install -r requirements.txt
          fi
          python -m pip install pyinstaller pillow

      - name: Verify VERSION matches tag
        run: python scripts/validate_version.py

      - name: Generate icons
        run: python scripts/generate_icons.py

      - name: Build application bundle
        run: python -m PyInstaller __SPEC_FILENAME__ --noconfirm --clean

__POST_BUILD_STEPS__

      - name: Upload packaged artifact
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.target.artifact_name }}
          path: artifacts/*
          if-no-files-found: error

  release:
    name: Publish GitHub Release
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Download packaged artifacts
        uses: actions/download-artifact@v4
        with:
          path: release-artifacts
          merge-multiple: true

      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          files: release-artifacts/*
          generate_release_notes: true
'''
    return _fill_template(
        template,
        {
            "__SPEC_FILENAME__": config.spec_filename,
            "__MATRIX_TARGETS__": matrix_targets,
            "__PRE_DEPENDENCY_STEPS__": "\n\n".join(pre_dependency_steps),
            "__POST_BUILD_STEPS__": "\n\n".join(post_build_steps),
        },
    )


def render_main_py(config: ScaffoldConfig) -> str:
    template = '''import tkinter as tk

from version import APP_NAME, __version__


def main() -> None:
    root = tk.Tk()
    root.title(f"{APP_NAME} {__version__}")
    root.geometry("960x640")
    root.configure(bg="#141a22")

    title = tk.Label(
        root,
        text=APP_NAME,
        bg="#141a22",
        fg="#eef4fb",
        font=("Arial", 24, "bold"),
    )
    title.pack(anchor="w", padx=24, pady=(24, 8))

    subtitle = tk.Label(
        root,
        text="Starter desktop application generated by Desktop App CI Builder.",
        bg="#141a22",
        fg="#9fb0c1",
        font=("Arial", 12),
    )
    subtitle.pack(anchor="w", padx=24)

    body = tk.Label(
        root,
        text=(
            "Replace this starter window with your real app.\\n\\n"
            "Files for packaging and GitHub Actions CI/CD are already generated."
        ),
        justify="left",
        bg="#141a22",
        fg="#d8e2ee",
        font=("Arial", 14),
    )
    body.pack(anchor="w", padx=24, pady=24)

    root.mainloop()


if __name__ == "__main__":
    main()
'''
    return template


def render_build_linux_sh(config: ScaffoldConfig) -> str:
    template = '''#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d venv ]]; then
    python3 -m venv venv
fi

source "$ROOT_DIR/venv/bin/activate"

python -m pip install --upgrade pip
if [[ -f requirements.txt ]]; then
    python -m pip install -r requirements.txt
fi
python -m pip install pyinstaller pillow
python scripts/generate_icons.py

python -m PyInstaller __SPEC_FILENAME__ \
    --noconfirm \
    --clean

echo "Build complete"
'''
    return _fill_template(template, {"__SPEC_FILENAME__": config.spec_filename})


def render_build_macos_sh(config: ScaffoldConfig) -> str:
    template = '''#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

if [[ ! -d venv ]]; then
    python3 -m venv venv
fi

source "$ROOT_DIR/venv/bin/activate"

python -m pip install --upgrade pip
if [[ -f requirements.txt ]]; then
    python -m pip install -r requirements.txt
fi
python -m pip install pyinstaller pillow
python scripts/generate_icons.py

python -m PyInstaller __SPEC_FILENAME__ \
    --noconfirm \
    --clean

echo "Build complete"
'''
    return _fill_template(template, {"__SPEC_FILENAME__": config.spec_filename})


def render_build_windows_bat(config: ScaffoldConfig) -> str:
    template = '''@echo off
setlocal

if not exist venv\\Scripts\\python.exe (
    py -3 -m venv venv
)

call venv\\Scripts\\activate.bat
python -m pip install --upgrade pip
if exist requirements.txt python -m pip install -r requirements.txt
python -m pip install pyinstaller pillow
python scripts\\generate_icons.py

python -m PyInstaller __SPEC_FILENAME__ --noconfirm --clean
if errorlevel 1 exit /b 1

echo Build complete
'''
    return _fill_template(template, {"__SPEC_FILENAME__": config.spec_filename})


def render_validate_version_py() -> str:
    return '''#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from version import read_version

NUMERIC_VERSION_RE = re.compile(r"^\\d+\\.\\d+\\.\\d+(?:\\.\\d+)?$")


def normalize_tag(tag: str) -> str:
    return tag[1:] if tag.startswith("v") else tag


def main() -> int:
    version = read_version()

    if not NUMERIC_VERSION_RE.fullmatch(version):
        print(
            "VERSION must be numeric and use 3 or 4 dot-separated parts, "
            f"got: {version}",
            file=sys.stderr,
        )
        return 1

    tag = os.getenv("GITHUB_REF_NAME")
    if tag:
        normalized_tag = normalize_tag(tag)
        if normalized_tag != version:
            print(
                f"Tag {tag} does not match VERSION {version}",
                file=sys.stderr,
            )
            return 1

    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def render_target_generate_icons_py(config: ScaffoldConfig) -> str:
    template = '''#!/usr/bin/env python3
import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
ICON_ROOT = ROOT / "assets" / "icons"
SOURCE_ICON = ICON_ROOT / "app-icon-source.png"
RUNTIME_ICON = ICON_ROOT / "app-icon.png"
WINDOWS_ICON = ICON_ROOT / "app-icon.ico"
MACOS_ICON = ICON_ROOT / "app-icon.icns"
LINUX_ICON_ROOT = ICON_ROOT / "hicolor"
LINUX_SIZES = [16, 24, 32, 48, 64, 128, 256, 512]
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
ICNS_SIZES = [
    (16, 16, 1),
    (16, 16, 2),
    (32, 32, 1),
    (32, 32, 2),
    (128, 128, 1),
    (128, 128, 2),
    (256, 256, 1),
    (256, 256, 2),
    (512, 512, 1),
    (512, 512, 2),
]
PACKAGE_NAME = "__PACKAGE_NAME__"
GENERATE_WINDOWS_ICON = __GENERATE_WINDOWS_ICON__
GENERATE_MACOS_ICON = __GENERATE_MACOS_ICON__
GENERATE_LINUX_ICONS = __GENERATE_LINUX_ICONS__


def make_square_image(size: int) -> Image.Image:
    with Image.open(SOURCE_ICON) as source:
        resized = source.convert("RGBA")
        resized.thumbnail((size, size), Image.Resampling.LANCZOS)

        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset_x = (size - resized.width) // 2
        offset_y = (size - resized.height) // 2
        canvas.paste(resized, (offset_x, offset_y), resized)
        return canvas


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-icns",
        action="store_true",
        help="Fail if app-icon.icns cannot be produced or found.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not SOURCE_ICON.exists():
        raise FileNotFoundError(f"Missing source icon: {SOURCE_ICON}")

    ICON_ROOT.mkdir(parents=True, exist_ok=True)

    runtime = make_square_image(512)
    runtime.save(RUNTIME_ICON)
    if GENERATE_WINDOWS_ICON:
        runtime.save(WINDOWS_ICON, sizes=[(size, size) for size in ICO_SIZES])

    if GENERATE_MACOS_ICON:
        icns_image = make_square_image(1024)
        icns_image.save(MACOS_ICON, sizes=ICNS_SIZES)
    elif args.require_icns:
        raise RuntimeError("app-icon.icns generation is disabled for this scaffold.")

    if GENERATE_LINUX_ICONS:
        for size in LINUX_SIZES:
            output_path = LINUX_ICON_ROOT / f"{size}x{size}" / "apps" / f"{PACKAGE_NAME}.png"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            make_square_image(size).save(output_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    return _fill_template(
        template,
        {
            "__PACKAGE_NAME__": config.package_name,
            "__GENERATE_WINDOWS_ICON__": "True" if config.supports_windows else "False",
            "__GENERATE_MACOS_ICON__": "True" if config.supports_macos else "False",
            "__GENERATE_LINUX_ICONS__": "True" if config.supports_linux else "False",
        },
    )


def render_build_deb_py(config: ScaffoldConfig) -> str:
    template = '''#!/usr/bin/env python3
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from version import APP_NAME, PACKAGE_NAME, read_version

ARCHITECTURE = "amd64"
INSTALL_DIR = Path("/opt") / PACKAGE_NAME
EXECUTABLE_NAME = "__EXECUTABLE_NAME__"
ICON_NAME = PACKAGE_NAME
STARTUP_WM_CLASS = "__WM_CLASS__"
MAINTAINER = "__MANUFACTURER__"
DESCRIPTION = "Packaged desktop application."


def write_file(path: Path, content: str, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def main() -> int:
    version = read_version()
    source_dir = ROOT / "dist" / EXECUTABLE_NAME
    icon_root = ROOT / "assets" / "icons" / "hicolor"
    if not source_dir.exists():
        raise FileNotFoundError(f"Missing build output: {source_dir}")
    if not icon_root.exists():
        raise FileNotFoundError(f"Missing Linux icon set: {icon_root}")

    package_root = ROOT / "build" / "deb-package"
    output_dir = ROOT / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    if package_root.exists():
        shutil.rmtree(package_root)

    app_dir = package_root / INSTALL_DIR.relative_to("/")
    shutil.copytree(source_dir, app_dir)

    executable_path = app_dir / EXECUTABLE_NAME
    executable_path.chmod(0o755)

    launcher = f'#!/bin/sh\\nexec {INSTALL_DIR}/{EXECUTABLE_NAME} "$@"\\n'
    write_file(package_root / "usr" / "bin" / PACKAGE_NAME, launcher, 0o755)

    desktop_file = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Exec=/usr/bin/{PACKAGE_NAME}
Icon={ICON_NAME}
StartupWMClass={STARTUP_WM_CLASS}
Terminal=false
Categories=Utility;
"""
    write_file(
        package_root / "usr" / "share" / "applications" / f"{PACKAGE_NAME}.desktop",
        desktop_file,
        0o644,
    )

    for icon_file in sorted(icon_root.glob("*/apps/*.png")):
        relative_icon_path = icon_file.relative_to(ROOT / "assets" / "icons")
        destination = package_root / "usr" / "share" / "icons" / relative_icon_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(icon_file, destination)

    control_file = f"""Package: {PACKAGE_NAME}
Version: {version}
Section: utils
Priority: optional
Architecture: {ARCHITECTURE}
Maintainer: {MAINTAINER}
Description: {DESCRIPTION}
"""
    write_file(package_root / "DEBIAN" / "control", control_file, 0o644)

    output_file = output_dir / f"__EXECUTABLE_NAME__-{version}-linux-{ARCHITECTURE}.deb"
    subprocess.run(
        ["dpkg-deb", "--build", "--root-owner-group", str(package_root), str(output_file)],
        check=True,
    )

    print(output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    return _fill_template(
        template,
        {
            "__EXECUTABLE_NAME__": config.executable_name,
            "__WM_CLASS__": config.wm_class,
            "__MANUFACTURER__": config.manufacturer,
        },
    )


def render_build_msi_py(config: ScaffoldConfig) -> str:
    template = r'''#!/usr/bin/env python3
import hashlib
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from version import APP_NAME, read_version

EXECUTABLE_NAME = "__WINDOWS_EXECUTABLE_NAME__"
UPGRADE_CODE = "__UPGRADE_CODE__"
MANUFACTURER = "__MANUFACTURER__"
WIX_EULA_ID = "wix7"
DESKTOP_SHORTCUT_COMPONENT_ID = "cmp_desktop_shortcut"
ICON_ID = "MainAppIcon"
REGISTRY_KEY = r"Software\__EXECUTABLE_NAME__"


def make_wix_id(prefix: str, relative_path: Path) -> str:
    path_value = relative_path.as_posix()
    digest = hashlib.sha1(path_value.encode("utf-8")).hexdigest()[:12]
    stem = relative_path.stem or relative_path.name or "root"
    sanitized_stem = "".join(ch if ch.isalnum() else "_" for ch in stem)
    sanitized_stem = sanitized_stem[:40] or "item"
    return f"{prefix}_{sanitized_stem}_{digest}"


def directory_id(relative_path: Path) -> str:
    if not relative_path.parts:
        return "INSTALLFOLDER"
    return make_wix_id("dir", relative_path)


def build_directory_tree(source_dir: Path, relative_dir: Path = Path()) -> tuple[str, list[str]]:
    current_dir = source_dir / relative_dir
    entries: list[str] = []
    component_ids: list[str] = []

    for child in sorted(current_dir.iterdir(), key=lambda path: (path.is_file(), path.name.lower())):
        child_relative = relative_dir / child.name
        if child.is_dir():
            child_markup, child_components = build_directory_tree(source_dir, child_relative)
            entries.append(
                f'<Directory Id="{directory_id(child_relative)}" Name="{escape(child.name)}">{child_markup}</Directory>'
            )
            component_ids.extend(child_components)
            continue

        component_id = make_wix_id("cmp", child_relative)
        file_xml_id = make_wix_id("fil", child_relative)
        component_ids.append(component_id)
        source_path = escape(str(child))
        entries.append(
            f'<Component Id="{component_id}" Guid="*">'
            f'<File Id="{file_xml_id}" Source="{source_path}" KeyPath="yes" Checksum="yes" />'
            f'</Component>'
        )

    return "".join(entries), component_ids


def main() -> int:
    version = read_version()
    source_dir = ROOT / "dist" / "__EXECUTABLE_NAME__"
    executable_path = source_dir / EXECUTABLE_NAME
    icon_path = ROOT / "assets" / "icons" / "app-icon.ico"
    if not executable_path.exists():
        raise FileNotFoundError(f"Missing Windows build output: {executable_path}")
    if not icon_path.exists():
        raise FileNotFoundError(f"Missing Windows icon: {icon_path}")

    wix_dir = ROOT / "build" / "wix"
    wix_dir.mkdir(parents=True, exist_ok=True)
    output_dir = ROOT / "artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    directory_markup, component_ids = build_directory_tree(source_dir)
    component_refs = "".join(f'<ComponentRef Id="{component_id}" />' for component_id in component_ids)

    registry_component_id = "cmp_registry_install"
    component_refs += f'<ComponentRef Id="{registry_component_id}" />'
    component_refs += f'<ComponentRef Id="{DESKTOP_SHORTCUT_COMPONENT_ID}" />'

    wix_source = f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
    <Package
      Name="{escape(APP_NAME)}"
      Manufacturer="{escape(MANUFACTURER)}"
      Version="{escape(version)}"
      UpgradeCode="{UPGRADE_CODE}"
      Scope="perMachine"
      InstallerVersion="500"
      Compressed="yes">
    <MajorUpgrade DowngradeErrorMessage="A newer version of {escape(APP_NAME)} is already installed." />
    <MediaTemplate EmbedCab="yes" />
    <Icon Id="{ICON_ID}" SourceFile="{escape(str(icon_path))}" />
    <Property Id="ARPPRODUCTICON" Value="{ICON_ID}" />

    <StandardDirectory Id="ProgramFiles64Folder">
      <Directory Id="INSTALLFOLDER" Name="{escape(APP_NAME)}">
        {directory_markup}
        <Component Id="{registry_component_id}" Guid="*">
          <RegistryValue Root="HKLM" Key="{REGISTRY_KEY}" Name="Installed" Type="integer" Value="1" KeyPath="yes" />
        </Component>
      </Directory>
    </StandardDirectory>

    <StandardDirectory Id="DesktopFolder">
      <Component Id="{DESKTOP_SHORTCUT_COMPONENT_ID}" Guid="*">
        <Shortcut
            Id="__EXECUTABLE_NAME__DesktopShortcut"
            Name="{escape(APP_NAME)}"
            Description="{escape(APP_NAME)}"
            Target="[INSTALLFOLDER]{EXECUTABLE_NAME}"
            WorkingDirectory="INSTALLFOLDER"
            Icon="{ICON_ID}"
            IconIndex="0" />
        <RegistryValue Root="HKCU" Key="{REGISTRY_KEY}" Name="DesktopShortcut" Type="integer" Value="1" KeyPath="yes" />
      </Component>
    </StandardDirectory>

    <Feature Id="MainFeature" Title="{escape(APP_NAME)}" Level="1">
      {component_refs}
    </Feature>
  </Package>
</Wix>
"""

    wix_file = wix_dir / "__EXECUTABLE_NAME__.wxs"
    wix_file.write_text(wix_source, encoding="utf-8")

    output_file = output_dir / f"__EXECUTABLE_NAME__-{version}-windows-x64.msi"
    if output_file.exists():
        output_file.unlink()

    subprocess.run(
        [
            "wix",
            "build",
            "-acceptEula",
            WIX_EULA_ID,
            "-arch",
            "x64",
            str(wix_file),
            "-o",
            str(output_file),
        ],
        check=True,
    )

    print(output_file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
    return _fill_template(
        template,
        {
            "__WINDOWS_EXECUTABLE_NAME__": config.windows_executable_name,
            "__UPGRADE_CODE__": config.upgrade_code,
            "__MANUFACTURER__": config.manufacturer,
            "__EXECUTABLE_NAME__": config.executable_name,
        },
    )


def render_build_dmg_sh(config: ScaffoldConfig) -> str:
    template = '''#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(python3 "$ROOT_DIR/scripts/validate_version.py")"
APP_NAME="__EXECUTABLE_NAME__"
APP_BUNDLE="$ROOT_DIR/dist/${APP_NAME}.app"
STAGING_DIR="$ROOT_DIR/build/dmg"
OUTPUT_DIR="$ROOT_DIR/artifacts"
OUTPUT_FILE="$OUTPUT_DIR/${APP_NAME}-${VERSION}-macos.dmg"

if [[ ! -d "$APP_BUNDLE" ]]; then
    echo "Missing app bundle: $APP_BUNDLE" >&2
    exit 1
fi

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR" "$OUTPUT_DIR"
cp -R "$APP_BUNDLE" "$STAGING_DIR/"
ln -s /Applications "$STAGING_DIR/Applications"

rm -f "$OUTPUT_FILE"
hdiutil create \
    -volname "__APP_NAME__" \
    -srcfolder "$STAGING_DIR" \
    -ov \
    -format UDZO \
    "$OUTPUT_FILE"

echo "$OUTPUT_FILE"
'''
    return _fill_template(
        template,
        {
            "__EXECUTABLE_NAME__": config.executable_name,
            "__APP_NAME__": config.app_name,
        },
    )


def render_packaging_readme(config: ScaffoldConfig) -> str:
    generated_files = [
        f"- `{config.spec_filename}`",
        "- `.github/workflows/release-packages.yml`",
        f"- `{SCAFFOLD_STATE_FILENAME}`",
        "- `scripts/generate_icons.py`",
        "- `scripts/validate_version.py`",
        "- `version.py`",
        "- `app_paths.py`",
        "- `assets/icons/*`",
    ]
    if config.supports_linux:
        generated_files.extend(
            [
                "- `build_linux.sh`",
                "- `scripts/build_deb.py`",
            ]
        )
    if config.supports_windows:
        generated_files.extend(
            [
                "- `build_windows.bat`",
                "- `scripts/build_msi.py`",
            ]
        )
    if config.supports_macos:
        generated_files.extend(
            [
                "- `build_macos.sh`",
                "- `scripts/build_dmg.sh`",
            ]
        )

    selected_platforms = ", ".join(PLATFORM_DISPLAY_NAMES[platform] for platform in config.platforms)
    release_targets = ", ".join(PLATFORM_PACKAGE_LABELS[platform] for platform in config.platforms)
    template = '''# Packaging and Release

This scaffold was generated for `__APP_NAME__`.

Generated files:
__GENERATED_FILES__

Release flow:
1. Update `VERSION`
2. Commit changes
3. Push a git tag matching `VERSION`
4. GitHub Actions will build release packages for the selected platforms

Example:
```bash
git tag __VERSION__
git push origin __VERSION__
```

Notes:
- Selected platforms: __SELECTED_PLATFORMS__
- Release artifacts: __RELEASE_TARGETS__
- Your application entry script is set to `__ENTRY_SCRIPT__`
- Your package name is `__PACKAGE_NAME__`
- Your bundle id is `__BUNDLE_ID__`
- Your executable name is `__EXECUTABLE_NAME__`
'''
    return _fill_template(
        template,
        {
            "__APP_NAME__": config.app_name,
            "__GENERATED_FILES__": "\n".join(generated_files),
            "__VERSION__": config.version,
            "__SELECTED_PLATFORMS__": selected_platforms,
            "__RELEASE_TARGETS__": release_targets,
            "__ENTRY_SCRIPT__": config.entry_script,
            "__PACKAGE_NAME__": config.package_name,
            "__BUNDLE_ID__": config.bundle_id,
            "__EXECUTABLE_NAME__": config.executable_name,
        },
    )


def generate_scaffold(
    config: ScaffoldConfig,
    previous_config: ScaffoldConfig | None = None,
) -> list[Path]:
    config.validate()
    target_dir = config.target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    created: list[Path] = []
    if previous_config and previous_config.target_dir.resolve() == target_dir:
        created.extend(cleanup_stale_scaffold(previous_config, config))

    created.extend(
        generate_icon_assets(
            icon_path=config.icon_path.resolve(),
            icon_root=target_dir / "assets" / "icons",
            package_name=config.package_name,
            platforms=config.platforms,
        )
    )

    file_map: dict[Path, tuple[str, bool]] = {
        target_dir / "VERSION": (config.version + "\n", False),
        target_dir / "version.py": (render_version_py(config), False),
        target_dir / "app_paths.py": (render_app_paths_py(config), False),
        target_dir / config.spec_filename: (render_spec(config), False),
        target_dir / ".github" / "workflows" / "release-packages.yml": (render_workflow(config), False),
        target_dir / "scripts" / "validate_version.py": (render_validate_version_py(), False),
        target_dir / "scripts" / "generate_icons.py": (render_target_generate_icons_py(config), False),
        target_dir / "PACKAGING.md": (render_packaging_readme(config), False),
        scaffold_state_path(target_dir): (render_scaffold_state(config), False),
    }

    if config.supports_linux:
        file_map[target_dir / "build_linux.sh"] = (render_build_linux_sh(config), True)
        file_map[target_dir / "scripts" / "build_deb.py"] = (render_build_deb_py(config), False)

    if config.supports_windows:
        file_map[target_dir / "build_windows.bat"] = (render_build_windows_bat(config), False)
        file_map[target_dir / "scripts" / "build_msi.py"] = (render_build_msi_py(config), False)

    if config.supports_macos:
        file_map[target_dir / "build_macos.sh"] = (render_build_macos_sh(config), True)
        file_map[target_dir / "scripts" / "build_dmg.sh"] = (render_build_dmg_sh(config), True)

    entry_script_path = target_dir / config.entry_script
    if not entry_script_path.exists():
        file_map[entry_script_path] = (render_main_py(config), False)

    for path, (content, executable) in file_map.items():
        _write_text(path, content, executable=executable)
        created.append(path)

    return sorted(created)


def summarize_paths(paths: Iterable[Path], root: Path) -> str:
    lines = []
    for path in paths:
        try:
            display_path = path.resolve().relative_to(root.resolve())
        except ValueError:
            display_path = path
        lines.append(f"- {display_path}")
    return "\n".join(lines)
