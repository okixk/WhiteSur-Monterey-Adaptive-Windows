"""Build and install both release archives in disposable directories."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from build_release import build


def run(tag, firefox=None, driver=None):
    checks = 0

    def check(condition, message):
        nonlocal checks
        assert condition, message
        checks += 1
        print(f"PASS: {message}", flush=True)

    def install(package, profile, executable, *extra, cmd=False):
        args = ["-ProfilePath", str(profile), "-FirefoxPath", str(executable), "-Force", *extra]
        if cmd:
            launcher = cmd if isinstance(cmd, str) else "Install.cmd"
            command = '""' + str(package / launcher) + '" ' + subprocess.list2cmdline(args) + '"'
            process = subprocess.run('"' + os.environ["ComSpec"] + '" /d /c ' + command,
                                     input="\n", capture_output=True, text=True, errors="replace")
        else:
            process = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                                      str(package / "Install-WhiteSur-Monterey-Adaptive.ps1"), *args],
                                     capture_output=True, text=True, errors="replace")
        assert process.returncode == 0, process.stdout + process.stderr

    def tree_hash(directory):
        return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in directory.rglob("*") if p.is_file()}

    with tempfile.TemporaryDirectory(prefix="whitesur-release-") as temporary:
        workspace = Path(temporary).resolve()
        assert workspace.is_relative_to(Path(tempfile.gettempdir()).resolve())
        artifacts = build(tag, workspace / "dist")
        checksums = artifacts[-1].read_text(encoding="ascii")
        packages = {}
        for archive in artifacts[:-1]:
            lite = "-Lite-" in archive.name
            with zipfile.ZipFile(archive) as bundle:
                check(bundle.testzip() is None, f"{archive.name} is a valid ZIP")
                names = bundle.namelist()
                root = names[0].split("/")[0]
                check(all(n.startswith(root + "/") and ".." not in Path(n).parts for n in names), "archive has one safe extraction root")
                bundle.extractall(workspace / "extracted")
            package = workspace / "extracted" / root
            packages[lite] = package
            check(hashlib.sha256(archive.read_bytes()).hexdigest() in checksums, "archive checksum matches SHA256SUMS.txt")
            check((package / "Install.cmd").is_file() and (package / "Uninstall.cmd").is_file(), "archive includes install and uninstall launchers")
            check((package / "PACKAGE-FLAVOR.txt").read_text().strip() == ("Lite" if lite else "Full"), "archive declares its installation mode")
            check((package / "chrome/tab-search.uc.js").exists() != lite, "editable-tab script is included only in Full")
            check((package / "firefox").exists() != lite, "AutoConfig payload is included only in Full")
            for css in (package / "chrome").rglob("*.css"):
                for relative in re.findall(r'@import\s+["\']([^"\']+)["\']', css.read_text(encoding="utf-8")):
                    assert (css.parent / relative).is_file(), f"Broken packaged CSS import: {css}: {relative}"
            check(True, "all packaged CSS imports resolve")
            if lite:
                check("-ClassicToolbar %*" in (package / "Install.cmd").read_text(), "Lite Install.cmd selects CSS-only mode")
                check(not (package / "chrome/tab-search.css").exists(), "Lite excludes editable-tab styling")

        if os.name == "nt":
            existing = workspace / "fake Firefox"
            (existing / "defaults/pref").mkdir(parents=True)
            executable = existing / "firefox.exe"
            executable.write_text("fixture; never run")
            (existing / "application.ini").write_text("[App]\nVersion=158.0.1\n")
            profile = workspace / "upgrade profile"
            profile.mkdir()
            (profile / "user.js").write_text('user_pref("my.preference", true);\n')
            install(packages[False], profile, executable)
            check((existing / "whitesur.cfg").is_file() and (profile / ".whitesur-editable-tabs.json").is_file(), "Full archive installs its loader into the chosen Firefox")
            check('tabSearch.enabled", true' in (profile / "user.js").read_text(encoding="utf-8-sig"), "Full archive enables editable tabs")
            browser_files = tree_hash(existing)
            (profile / "chrome/customChrome.css").write_text("/* keep my custom CSS */")
            install(packages[True], profile, executable, cmd=True)
            check(tree_hash(existing) == browser_files, "switching Full to Lite leaves the shared Firefox installation untouched")
            check(not (profile / ".whitesur-editable-tabs.json").exists() and not (profile / "chrome/tab-search.uc.js").exists(), "Lite removes the profile editable-tab state and script")
            check('tabSearch.enabled", false' in (profile / "user.js").read_text(encoding="utf-8-sig"), "Lite CMD installation disables editable tabs")
            check((profile / "chrome/customChrome.css").read_text() == "/* keep my custom CSS */", "Lite upgrade preserves custom CSS")
            check('my.preference' in (profile / "user.js").read_text(encoding="utf-8-sig"), "Lite preserves unrelated preferences")

            clean_firefox = workspace / "older Firefox"
            (clean_firefox / "defaults/pref").mkdir(parents=True)
            (clean_firefox / "firefox.exe").write_text("fixture; never run")
            (clean_firefox / "application.ini").write_text("[App]\nVersion=156.0\n")
            (clean_firefox / "defaults/pref/corporate.js").write_text('pref("general.config.filename","corporate.cfg");')
            before = tree_hash(clean_firefox)
            clean_profile = workspace / "direct Lite profile"
            clean_profile.mkdir()
            install(packages[True], clean_profile, clean_firefox / "firefox.exe",
                    "-RuntimeDirectory", str(workspace / "must not exist"))
            check(tree_hash(clean_firefox) == before and not (workspace / "must not exist").exists(), "direct Lite installer supports older/custom-loader Firefox without changing or copying it")
            check('tabSearch.enabled", false' in (clean_profile / "user.js").read_text(encoding="utf-8-sig"), "Lite remains CSS-only when its PowerShell installer is invoked directly")
            wrapper_profile = workspace / "Full Lite launcher profile"
            wrapper_profile.mkdir()
            install(packages[False], wrapper_profile, clean_firefox / "firefox.exe", cmd="Install-Lite.cmd")
            check(tree_hash(clean_firefox) == before and not (wrapper_profile / "chrome/tab-search.uc.js").exists()
                  and not (wrapper_profile / "chrome/tab-search.css").exists(), "Full archive Install-Lite.cmd installs only CSS without modifying Firefox")

        if firefox and driver:
            from test_editable_tabs_firefox import Firefox
            for lite, package in packages.items():
                target = workspace / ("native Lite Firefox" if lite else "native Full Firefox")
                shutil.copytree(firefox.parent, target, ignore=shutil.ignore_patterns("tobedeleted", "updates"))
                profile = workspace / ("native Lite profile" if lite else "native Full profile")
                profile.mkdir()
                before = tree_hash(target) if lite else None
                install(package, profile, target / "firefox.exe")
                if lite:
                    check(tree_hash(target) == before, "native Lite installation leaves every Firefox file unchanged")
                browser = Firefox(driver, target / "firefox.exe", profile)
                try:
                    check(browser.js("return !!window.TabSearch;") != lite, f"installed {'Lite' if lite else 'Full'} archive starts in its correct Firefox mode")
                    check(browser.js("return getComputedStyle(document.getElementById('nav-bar')).height==='48px';"), "packaged userChrome theme is active in Firefox")
                    browser.chord("l")
                    check(browser.js("return document.activeElement===gURLBar.inputField;"), "packaged Firefox address entry remains usable")
                finally:
                    browser.close()
                    time.sleep(.3)
    print(f"Result: {checks} release-package checks passed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", default="v0.0.0-test")
    parser.add_argument("--firefox", type=Path)
    parser.add_argument("--geckodriver", type=Path)
    args = parser.parse_args()
    if bool(args.firefox) != bool(args.geckodriver):
        parser.error("--firefox and --geckodriver must be supplied together")
    run(args.tag, args.firefox.resolve() if args.firefox else None, args.geckodriver.resolve() if args.geckodriver else None)
