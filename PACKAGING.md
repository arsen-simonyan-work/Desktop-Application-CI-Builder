# Packaging and Release

This scaffold was generated for `Desktop App CI Builder`.

Generated files:
- `DesktopAppCiBuilder.spec`
- `.github/workflows/release-packages.yml`
- `scripts/generate_icons.py`
- `scripts/build_deb.py`
- `scripts/build_msi.py`
- `scripts/build_dmg.sh`
- `build_linux.sh`
- `build_macos.sh`
- `build_windows.bat`
- `version.py`
- `app_paths.py`
- `assets/icons/*`

Release flow:
1. Update `VERSION`
2. Commit changes
3. Push a git tag matching `VERSION`
4. GitHub Actions will build release packages for Linux, Windows, and macOS

Example:
```bash
git tag 0.1.0
git push origin 0.1.0
```

Notes:
- Your application entry script is set to `main.py`
- Your package name is `desktop-app-ci-builder`
- Your bundle id is `com.desktopappcibuilder.app`
- Your executable name is `DesktopAppCiBuilder`
