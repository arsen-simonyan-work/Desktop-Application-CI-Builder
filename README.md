# Desktop App CI Builder

Standalone desktop utility that generates packaging and GitHub Actions CI/CD scaffolding for Python desktop applications.

What it does:
- choose a target project folder
- choose a master app icon
- set app name, package name, bundle id, executable name, version, entry script
- generate `png`, `ico`, `icns`, and Linux icon assets
- generate PyInstaller spec and packaging scripts for Linux, Windows, and macOS
- generate GitHub Actions release workflow that builds `deb`, `msi`, and `dmg`

Local run:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Generated scaffold:
- `version.py`, `app_paths.py`, `VERSION`
- `.github/workflows/release-packages.yml`
- `build_linux.sh`, `build_macos.sh`, `build_windows.bat`
- `scripts/build_deb.py`, `scripts/build_msi.py`, `scripts/build_dmg.sh`
- `scripts/generate_icons.py`, `scripts/validate_version.py`
- `assets/icons/*`

Release flow for a generated project:

```bash
git add .
git commit -m "Prepare release"
git tag 0.1.0
git push origin main --tags
```

The workflow will publish packaged artifacts to the GitHub release for that tag.
