"""Build the full and CSS-only Lite release ZIPs, each with Install.cmd."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "Install.cmd", "Install-Lite.cmd", "Uninstall.cmd", "Check-Installation.cmd",
    "Install-WhiteSur-Monterey-Adaptive.ps1", "Editable-Tabs-Runtime.ps1",
    "Install-Editable-Tabs-Loader.ps1", "VERSION.txt", "README.md", "README.de.md",
    "LICENSE", "COPYRIGHT", "THIRD_PARTY_NOTICES.md",
)


def build(tag: str, output: Path) -> list[Path]:
    if not re.fullmatch(r"v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", tag):
        raise ValueError("Expected a version tag such as v0.2.0-beta.3")
    output.mkdir(parents=True, exist_ok=True)
    files = {name: ROOT / name for name in ROOT_FILES}
    for folder in ("chrome", "firefox", "docs"):
        files.update({p.relative_to(ROOT).as_posix(): p for p in (ROOT / folder).rglob("*") if p.is_file()})
    archives = []
    for lite in (False, True):
        package = "WhiteSur-Monterey-Adaptive-Windows" + ("-Lite" if lite else "")
        archive = output / f"{package}-{tag}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
            for name, source in sorted(files.items()):
                if lite and (name.startswith("firefox/") or name in (
                    "chrome/tab-search.uc.js", "chrome/tab-search.css", "Install-Editable-Tabs-Loader.ps1")):
                    continue
                data = source.read_bytes()
                if lite and name == "chrome/userChrome.css":
                    data = data.replace(b'@import "tab-search.css";\r\n', b'').replace(b'@import "tab-search.css";\n', b'')
                if lite and name == "Install.cmd":
                    data = data.replace(b' -Launch %*', b' -ClassicToolbar %*')
                bundle.writestr(f"{package}/{name}", data)
            bundle.writestr(f"{package}/PACKAGE-FLAVOR.txt", "Lite\n" if lite else "Full\n")
            if lite:
                bundle.writestr(f"{package}/README-LITE.md",
                    "# WhiteSur Lite\n\nClose Firefox, extract this archive, and run Install.cmd.\n"
                    "Installs the classic userChrome CSS theme, with normal tabs and a separate address bar.\n"
                    "No editable-tab script, AutoConfig loader, Firefox copy, or extra shortcut is installed.\n"
                    "Firefox installation files are left untouched. User.js enables custom stylesheets and disables editable tabs.\n"
                    "Existing customChrome.css and unrelated preferences are preserved. Uninstall.cmd restores the previous theme.\n"
                    "Use the full ZIP if you want searchable tabs.\n")
        archives.append(archive)
    checksums = output / "SHA256SUMS.txt"
    checksums.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in archives), encoding="ascii")
    return archives + [checksums]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    for artifact in build(args.tag, args.output.resolve()):
        print(artifact)
