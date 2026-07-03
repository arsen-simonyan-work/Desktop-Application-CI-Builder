# Desktop App CI Builder

Standalone desktop utility that generates packaging and GitHub Actions CI/CD scaffolding for Python desktop applications.

What it does:
- choose a target project folder
- reopen an already generated project folder and edit/update the scaffold
- choose a master app icon
- set app name, package name, bundle id, executable name, version, entry script
- choose target platforms: Linux (`deb`), Windows (`msi`), macOS (`dmg`)
- generate `png`, `ico`, `icns`, and Linux icon assets
- generate PyInstaller spec and packaging scripts only for the selected platforms
- generate GitHub Actions release workflow only for the selected platforms

Local run:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

Generated scaffold:
- `.desktop_app_ci_builder.json`
- `version.py`, `app_paths.py`, `VERSION`
- `.github/workflows/release-packages.yml`
- platform-specific build scripts for the selected targets
- platform-specific packaging scripts for the selected targets
- `scripts/generate_icons.py`, `scripts/validate_version.py`
- `assets/icons/*`

Example:
- if you select only `Linux`, the generated scaffold contains only the `deb` flow: `build_linux.sh`, `scripts/build_deb.py`, Linux icon set, and a GitHub Actions matrix with `ubuntu-latest` only

Release flow for a generated project:

```bash
git add .
git commit -m "Prepare release"
git tag 0.1.0
git push origin main --tags
```

The workflow will publish packaged artifacts to the GitHub release for that tag.
