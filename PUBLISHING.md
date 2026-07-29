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

## First release

A useful first tag is:

```powershell
git tag -a v2026.07.28-15 -m "First repository release"
git push origin v2026.07.28-15
```

Then create a GitHub Release from that tag and attach a ZIP containing the repository files.
