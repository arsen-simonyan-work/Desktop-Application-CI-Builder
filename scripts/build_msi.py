#!/usr/bin/env python3
import hashlib
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from version import APP_NAME, read_version

EXECUTABLE_NAME = "DesktopAppCiBuilder.exe"
UPGRADE_CODE = "55DAECE9-C86B-5DE3-AF19-8FA331DA46D7"
MANUFACTURER = "Assistant Lab"
WIX_EULA_ID = "wix7"
DESKTOP_SHORTCUT_COMPONENT_ID = "cmp_desktop_shortcut"
ICON_ID = "MainAppIcon"
REGISTRY_KEY = r"Software\DesktopAppCiBuilder"


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
    source_dir = ROOT / "dist" / "DesktopAppCiBuilder"
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
            Id="DesktopAppCiBuilderDesktopShortcut"
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

    wix_file = wix_dir / "DesktopAppCiBuilder.wxs"
    wix_file.write_text(wix_source, encoding="utf-8")

    output_file = output_dir / f"DesktopAppCiBuilder-{version}-windows-x64.msi"
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
