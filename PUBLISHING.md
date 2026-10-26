# Publishing the repository

## GitHub website + Git

1. Create a new empty public repository named `WhiteSur-Monterey-Adaptive-Windows`.
2. Do not add a generated README, `.gitignore`, or licence on GitHub; this repository already contains them.
3. Open PowerShell in the extracted project folder and run:

```powershell
git init
git add .
git commit -m "Initial release: WhiteSur Monterey Adaptive for Windows"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/WhiteSur-Monterey-Adaptive-Windows.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username.

## GitHub CLI alternative

When GitHub CLI is installed and authenticated:

```powershell
git init
git add .
git commit -m "Initial release: WhiteSur Monterey Adaptive for Windows"
git branch -M main
gh repo create WhiteSur-Monterey-Adaptive-Windows --public --source . --remote origin --push
```

## Releases: Full and Lite

Every release must contain both editions and their SHA-256 checksums. Update `VERSION.txt`, changelog, and `docs/releases/<tag>.md`, then commit and push the release changes. Push a version tag such as `v0.2.0-beta.3` to start `.github/workflows/release.yml`. It runs the Linux/Windows suites, builds both ZIPs with their installers, and publishes the release only after both editions are attached. Tags containing a prerelease suffix are published as prereleases.

For a local build and smoke test:

```powershell
py tests/test_release_packages.py --tag v0.2.0-beta.3
py tools/build_release.py --tag v0.2.0-beta.3
```

`dist/` contains the Full ZIP, Lite ZIP, and `SHA256SUMS.txt`. Both archives include `Install.cmd`, `Uninstall.cmd`, and checks. Lite excludes the editable-tab script/style, Firefox AutoConfig payload, and elevation helper. Its package marker forces CSS-only mode even when running the PowerShell installer directly. The shared runtime helper remains for safe updates/uninstall of existing profile state; Lite never installs a loader or Firefox copy. The Full/source `Install-Lite.cmd` also installs CSS only.

To exercise the extracted installers in disposable Firefox instances, add `--firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"` to the package test. Do not upload raw `Install.cmd` as a standalone installer: it needs the companion files inside its ZIP.

## First repository release (historical)

A useful first tag is:

```powershell
git tag -a v2026.07.28-15 -m "First repository release"
git push origin v2026.07.28-15
```

Then create a GitHub Release from that tag and attach a ZIP containing the repository files.
