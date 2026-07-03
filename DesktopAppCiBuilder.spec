# -*- mode: python ; coding: utf-8 -*-

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
    ["main.py"],
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
    name="DesktopAppCiBuilder",
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
    name="DesktopAppCiBuilder",
)

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="DesktopAppCiBuilder.app",
        bundle_identifier="com.desktopappcibuilder.app",
        icon=str(macos_icon) if macos_icon.exists() else None,
        info_plist={
            "CFBundleName": "Desktop App CI Builder",
            "CFBundleDisplayName": "Desktop App CI Builder",
            "CFBundleIdentifier": "com.desktopappcibuilder.app",
            "CFBundleIconFile": "app-icon.icns",
        },
    )
