from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path

from pygments import lex
from pygments.lexers.shell import PowerShellLexer
from pygments.token import Comment, Error, String

ROOT = Path(__file__).resolve().parent
CHROME = ROOT / "chrome"
PS1 = ROOT / "Install-WhiteSur-Monterey-Adaptive.ps1"
MARKER = ".whitesur-monterey-adaptive-windows"
BEGIN = "// BEGIN WhiteSur Monterey Adaptive Windows"
END = "// END WhiteSur Monterey Adaptive Windows"


def remove_css_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/", "", text, flags=re.S)


def test_css_imports() -> list[str]:
    errors: list[str] = []
    for css in CHROME.rglob("*.css"):
        clean = remove_css_comments(css.read_text(encoding="utf-8"))
        for imported in re.findall(r'@import\s+["\']([^"\']+)["\']', clean):
            target = (css.parent / imported).resolve()
            if not target.is_file():
                errors.append(f"Missing import: {css.relative_to(ROOT)} -> {imported}")
    return errors


def test_local_urls() -> list[str]:
    errors: list[str] = []
    allowed_schemes = ("chrome:", "resource:", "data:", "http:", "https:", "about:", "var(")
    for css in CHROME.rglob("*.css"):
        clean = remove_css_comments(css.read_text(encoding="utf-8"))
        for raw in re.findall(r"url\(([^)]+)\)", clean):
            value = raw.strip().strip('"\'')
            if value.startswith(allowed_schemes):
                continue
            target = (css.parent / value).resolve()
            if not target.is_file():
                errors.append(f"Missing URL asset: {css.relative_to(ROOT)} -> {value}")
    return errors


def test_css_delimiters() -> list[str]:
    errors: list[str] = []
    for css in CHROME.rglob("*.css"):
        text = css.read_text(encoding="utf-8")
        if text.count("/*") != text.count("*/"):
            errors.append(f"Unbalanced comments: {css.relative_to(ROOT)}")
        clean = remove_css_comments(text)
        # Remove quoted strings before checking braces.
        clean = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', "", clean)
        if clean.count("{") != clean.count("}"):
            errors.append(f"Unbalanced braces: {css.relative_to(ROOT)}")
    return errors


def test_powershell_static() -> list[str]:
    errors: list[str] = []
    text = PS1.read_text(encoding="utf-8")
    tokens = list(lex(text, PowerShellLexer()))
    if any(token_type in Error for token_type, _ in tokens):
        errors.append("Pygments reported an invalid PowerShell token")

    code = "".join(value for token_type, value in tokens if token_type not in Comment and token_type not in String)
    for opening, closing, label in (("{", "}", "braces"), ("(", ")", "parentheses"), ("[", "]", "brackets")):
        if code.count(opening) != code.count(closing):
            errors.append(f"PowerShell has unbalanced {label}: {code.count(opening)} vs {code.count(closing)}")

    required = [
        "Get-FirefoxProfiles",
        "chrome.whitesur-backup-",
        "toolkit.legacyUserProfileCustomizations.stylesheets",
        "Remove-ManagedPreferenceBlock",
        "[AllowEmptyString()]",
        "Get-Content -LiteralPath $userJs -Raw",
        "$existing = if ($null -eq $rawExisting) { '' } else { [string]$rawExisting }",
        "Uninstall-ThemeForProfile",
    ]
    for needle in required:
        if needle not in text:
            errors.append(f"PowerShell is missing required logic: {needle}")
    return errors


def remove_pref_block(text: str) -> str:
    pattern = re.compile(
        rf"(?ms)^\s*{re.escape(BEGIN)}\s*\r?\n.*?^\s*{re.escape(END)}\s*\r?\n?"
    )
    return pattern.sub("", text)


def test_empty_user_js_regression() -> list[str]:
    errors: list[str] = []
    script = PS1.read_text(encoding="utf-8")

    # Regression for package 2026.07.28-1: a fresh profile supplied an empty
    # string to a mandatory [string] parameter and PowerShell rejected it.
    if "[AllowEmptyString()]" not in script:
        errors.append("Empty user.js regression: Remove-ManagedPreferenceBlock does not allow empty strings")
    if "$rawExisting" not in script or "$null -eq $rawExisting" not in script:
        errors.append("Empty user.js regression: missing/zero-byte user.js is not normalised")

    for label, value in (("missing user.js", ""), ("zero-byte user.js", ""), ("existing user.js", 'user_pref("unrelated", true);\n')):
        try:
            result = remove_pref_block(value)
        except Exception as exc:  # pragma: no cover - explicit regression reporting
            errors.append(f"Empty user.js regression ({label}): {exc}")
            continue
        if result != value:
            errors.append(f"Empty user.js regression ({label}): unrelated content changed")

    managed_only = f"{BEGIN}\nuser_pref(\"toolkit.legacyUserProfileCustomizations.stylesheets\", true);\n{END}\n"
    if remove_pref_block(managed_only) != "":
        errors.append("Empty user.js regression: managed-only file was not cleaned to an empty string")
    return errors


def simulate_filesystem_flow() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="whitesur-test-") as temp_dir:
        profile = Path(temp_dir) / "Profiles" / "abc.default-release"
        profile.mkdir(parents=True)
        old_chrome = profile / "chrome"
        old_chrome.mkdir()
        (old_chrome / "old-theme.css").write_text("old", encoding="utf-8")
        (profile / "user.js").write_text('user_pref("unrelated", true);\n', encoding="utf-8")

        # First install: back up old chrome and copy package.
        backup = profile / "chrome.whitesur-backup-20260728-080000"
        old_chrome.rename(backup)
        shutil.copytree(CHROME, profile / "chrome")
        (profile / "chrome" / MARKER).write_text("test", encoding="utf-8")
        prefs = (profile / "user.js").read_text(encoding="utf-8")
        prefs += f"\n{BEGIN}\nuser_pref(\"toolkit.legacyUserProfileCustomizations.stylesheets\", true);\n{END}\n"
        (profile / "user.js").write_text(prefs, encoding="utf-8")

        if not (profile / "chrome" / "windows.css").is_file():
            errors.append("Simulation: windows.css was not copied")
        if not backup.is_dir():
            errors.append("Simulation: existing chrome directory was not backed up")

        # Reinstall: preserve customChrome.css.
        custom = profile / "chrome" / "customChrome.css"
        custom.write_text("/* personal */", encoding="utf-8")
        preserved = custom.read_text(encoding="utf-8")
        shutil.rmtree(profile / "chrome")
        shutil.copytree(CHROME, profile / "chrome")
        (profile / "chrome" / "customChrome.css").write_text(preserved, encoding="utf-8")
        (profile / "chrome" / MARKER).write_text("test", encoding="utf-8")
        if (profile / "chrome" / "customChrome.css").read_text(encoding="utf-8") != "/* personal */":
            errors.append("Simulation: customChrome.css was not preserved on reinstall")

        # Uninstall: remove managed theme, restore backup, clean prefs.
        shutil.rmtree(profile / "chrome")
        backup.rename(profile / "chrome")
        cleaned = remove_pref_block((profile / "user.js").read_text(encoding="utf-8"))
        if BEGIN in cleaned or END in cleaned:
            errors.append("Simulation: managed preference block was not removed")
        if not (profile / "chrome" / "old-theme.css").is_file():
            errors.append("Simulation: previous chrome directory was not restored")
    return errors



def test_install_default_profile_detection() -> list[str]:
    errors: list[str] = []
    text = PS1.read_text(encoding="utf-8")
    required = [
        "installs.ini",
        "InstallDefault",
        "$installDefaults = @($profiles | Where-Object InstallDefault",
        "Firefox install default",
        "Get-NormalizedFirefoxPath",
        "Test-PathEquals",
        "Show-Diagnostics",
    ]
    for needle in required:
        if needle not in text:
            errors.append(f"Install-default profile detection is missing: {needle}")

    # Regression model: current Firefox can mark the unused legacy profile with
    # Default=1 while the active profile is selected by an Install section.
    profiles_ini = {
        "Profile0": {"Path": "Profiles/active.default-release", "Default": "0"},
        "Profile1": {"Path": "Profiles/unused.default", "Default": "1"},
        "InstallABC": {"Default": "Profiles/active.default-release", "Locked": "1"},
    }
    install_default = profiles_ini["InstallABC"]["Default"]
    selected = next(
        section["Path"]
        for name, section in profiles_ini.items()
        if name.startswith("Profile") and section["Path"].lower() == install_default.lower()
    )
    if selected != "Profiles/active.default-release":
        errors.append("Regression model did not select the Install default profile")
    if selected == profiles_ini["Profile1"]["Path"]:
        errors.append("Regression model incorrectly selected legacy Default=1")
    return errors


def test_windows_visual_imports() -> list[str]:
    errors: list[str] = []
    theme = (CHROME / "Monterey" / "theme-adaptive.css").read_text(encoding="utf-8")

    required = [
        '@import "parts/headerbar.css";',
        '@import "parts/headerbar-urlbar.css";',
        '@import "parts/tabsbar.css";',
        '@import "colors/light-adaptive.css";',
        '@import "colors/dark-adaptive.css";',
    ]
    excluded = [
        '@import "parts/toolbox.css";',
        '@import "parts/csd.css";',
        '@import "parts/titlebutton-light.css";',
        '@import "parts/titlebutton-dark.css";',
    ]
    for needle in required:
        if needle not in theme:
            errors.append(f"Required Monterey visual import is missing: {needle}")
    for needle in excluded:
        if needle in theme:
            errors.append(f"Linux-only geometry import is still active: {needle}")
    return errors


def test_windows_titlebar_target() -> list[str]:
    errors: list[str] = []
    css = (CHROME / "windows.css").read_text(encoding="utf-8")
    user_chrome = (CHROME / "userChrome.css").read_text(encoding="utf-8")

    required = [
        "#TabsToolbar > .titlebar-buttonbox-container",
        "#toolbar-menubar > .titlebar-buttonbox-container",
        "#nav-bar > .titlebar-buttonbox-container",
        "-moz-window-button-minimize",
        "-moz-window-button-maximize",
        "-moz-window-button-restore",
        "-moz-window-button-close",
        "--whitesur-native-controls-width: 138px",
        "inset-inline-end: 0 !important",
    ]
    for needle in required:
        if needle not in css:
            errors.append(f"Native Windows titlebar logic is missing: {needle}")

    if "background-color: #ff5f57" in css or "--whitesur-window-control-size" in css:
        errors.append("Traffic-light caption button styling is still active")
    if "left_header_button_3.css" in user_chrome or "right_header_button_3.css" in user_chrome:
        errors.append("Obsolete fixed-position Monterey header imports are still active")
    return errors


def test_responsive_collision_prevention() -> list[str]:
    errors: list[str] = []
    css = (CHROME / "windows.css").read_text(encoding="utf-8")
    required = [
        "--whitesur-left-zone: 498px",
        "--whitesur-right-zone: 300px",
        "#TabsToolbar {",
        "position: absolute !important",
        "inset-inline-start: var(--whitesur-left-zone) !important",
        "inset-inline-end: var(--whitesur-right-zone) !important",
        "#TabsToolbar-customization-target > toolbarspring",
        "#nav-bar-customization-target > toolbarspring",
        "@media (max-width: 1100px)",
        "@media (max-width: 850px)",
        "@media (max-width: 980px)",
        "compact-window fallback",
        "#TabsToolbar {\n    display: none !important",
        "flex: 1 1 auto !important",
        "min-width: 120px !important",
    ]
    for needle in required:
        if needle not in css:
            errors.append(f"Responsive collision prevention is missing: {needle}")

    obsolete = [
        "#titlebar {\n  position: absolute",
        "margin-top: -40px",
        "--whitesur-nav-segment",
        "--whitesur-tabs-right-reserve",
        "grid-template-rows: 48px 40px",
    ]
    for needle in obsolete:
        if needle in css:
            errors.append(f"Obsolete fixed/two-row layout is still active: {needle}")
    return errors



def test_windowed_hit_testing_and_tab_close() -> list[str]:
    errors: list[str] = []
    css = (CHROME / "windows.css").read_text(encoding="utf-8")

    required = [
        "#nav-bar-customization-target > *",
        "-moz-window-dragging: no-drag !important",
        "#TabsToolbar,\n#TabsToolbar > .toolbar-items,\n#TabsToolbar-customization-target",
        "pointer-events: none !important",
        "#tabbrowser-tabs,\n#tabbrowser-arrowscrollbox",
        "pointer-events: auto !important",
        ".tabbrowser-tab:not([pinned]):not([fadein])",
        "min-width: 0.1px !important",
        "#tabbrowser-arrowscrollbox-periphery > .closing-tabs-spacer",
        "display: none !important",
        'list-style-image: url("resource://content-accessible/close-12.svg") !important',
    ]
    for needle in required:
        if needle not in css:
            errors.append(f"v6 interaction/tab-close fix is missing: {needle}")

    obsolete = [
        '.tabbrowser-tab:not([pinned]) {\n  min-width: 88px !important;',
        'list-style-image: url("chrome://global/skin/icons/close.svg") !important',
        '.close-icon:not(.titlebar-button)',
    ]
    for needle in obsolete:
        if needle in css:
            errors.append(f"Obsolete tab-close rule is still active: {needle}")
    return errors


def test_v8_compact_mode_and_spring_artifact() -> list[str]:
    errors: list[str] = []
    css = (CHROME / "windows.css").read_text(encoding="utf-8")

    required = [
        "#tabbrowser-arrowscrollbox::part(scrollbox)",
        "#pinned-tabs-container::part(scrollbox)",
        "overflow-y: hidden !important",
        "scrollbar-width: none !important",
        "#tabbrowser-arrowscrollbox::part(overflow-start-indicator)",
        "#tabbrowser-arrowscrollbox::part(overflow-end-indicator)",
        "inline-size: 0 !important",
        "@media (max-width: 980px)",
        "visibility: hidden !important",
        "#nav-bar-overflow-button",
        "#unified-extensions-button",
        "@media (min-width: 981px) and (max-width: 1100px)",
        "--whitesur-left-zone: 498px",
        "toolbarpaletteitem:has(> toolbarspring)",
        "wrapper-customizableui-special-spring",
        "#wrapper-vertical-spacer",
        "spring-only wrapper",
    ]
    for needle in required:
        if needle not in css:
            errors.append(f"v8 compact/spring fix is missing: {needle}")

    # Keep the current arrowscrollbox containment, but also remove the actual
    # spring-only wrappers that can paint a seven-line flexible-space grip.
    if "::part(scrollbox)" not in css or "::part(overflow-end-indicator)" not in css:
        errors.append("Current Firefox arrowscrollbox shadow parts are not targeted")
    if css.count("toolbarpaletteitem:has(> toolbarspring)") < 2:
        errors.append("Spring wrapper and its pseudo-elements are not both neutralised")
    return errors



def test_web_content_isolation() -> list[str]:
    errors: list[str] = []
    content = (CHROME / "userContent.css").read_text(encoding="utf-8")
    forbidden = [
        "@import",
        "scrollbar-color:",
        "scrollbar-width:",
        "--newtab-background-color",
        ".context-menu",
        ":root {",
    ]
    for needle in forbidden:
        if needle in content:
            errors.append(f"Global web-content styling is still active: {needle}")
    required = [
        "Intentionally no global website rules",
        "Browser chrome remains fully themed through userChrome.css",
    ]
    for needle in required:
        if needle not in content:
            errors.append(f"Web-content isolation marker is missing: {needle}")
    return errors


def test_v14_urlbar_geometry_reset() -> list[str]:
    errors: list[str] = []
    css = (CHROME / "windows.css").read_text(encoding="utf-8")
    headerbar = (CHROME / "Monterey" / "parts" / "headerbar.css").read_text(encoding="utf-8")
    urlbar_sheet = (CHROME / "Monterey" / "parts" / "headerbar-urlbar.css").read_text(encoding="utf-8")

    required = [
        "v14 URL-bar geometry reset",
        "#urlbar[breakout] {",
        "position: absolute !important",
        "#urlbar > #urlbar-background",
        "display: none !important",
        "pointer-events: none !important",
        "#urlbar > #urlbar-input-container",
        "pointer-events: auto !important",
        "width: var(--urlbar-width) !important",
    ]
    for needle in required:
        if needle not in css:
            errors.append(f"v14 URL-bar geometry reset is missing: {needle}")

    if "position: static !important" in headerbar:
        errors.append("Imported headerbar sheet still makes the breakout URL bar static")
    if "--urlbar-width: 360px !important" in urlbar_sheet:
        errors.append("Imported URL-bar sheet still hard-codes Firefox's live --urlbar-width")

    import json
    report_path = ROOT / "tests" / "urlbar-geometry-report.json"
    if not report_path.is_file():
        return errors + ["Rendered URL-bar geometry report is missing"]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("broken_v13", {}).get("cyan_pixels_beyond_input", 0) <= 100:
        errors.append("The v13 fixture no longer reproduces the oversized search-box rectangle")
    fixed = report.get("fixed_v14", {})
    if fixed.get("cyan_pixels_beyond_input") != 0:
        errors.append("v14 still paints URL-bar focus/border pixels beyond the visible field")
    if fixed.get("tab_clicks") != 1:
        errors.append("v14 oversized URL-bar host still blocks toolbar/tab clicks")
    for state, data in fixed.get("states", {}).items():
        if data.get("urlbarPosition") != "absolute":
            errors.append(f"v14 URL bar is not absolutely anchored in state {state}")
        if data.get("backgroundDisplay") != "none":
            errors.append(f"v14 detached URL-bar background is visible in state {state}")
        if data.get("urlbarPointerEvents") != "none" or data.get("inputPointerEvents") != "auto":
            errors.append(f"v14 pointer-event containment failed in state {state}")
        if data.get("urlbar", {}).get("right", 0) > data.get("container", {}).get("right", 0) + 1:
            errors.append(f"v14 URL bar extends beyond its toolbar item in state {state}")
    return errors


def test_v16_autoscroll_drag_and_spacing() -> list[str]:
    errors: list[str] = []
    css = (CHROME / "windows.css").read_text(encoding="utf-8")
    popups = (CHROME / "Monterey" / "parts" / "popups.css").read_text(encoding="utf-8")

    required_css = [
        "v16 stable spacing, tab dragging and autoscroll polish",
        "--whitesur-left-zone: 498px",
        "panel#autoscroller.autoscroller",
        "autoscroll-filled-all-light.png",
        "autoscroll-filled-all-dark.png",
        "#tabbrowser-tabs:not([movingtab])",
        "#tabbrowser-tabs[movingtab]",
        '#tabbrowser-tabs[orient="horizontal"][movingtab]',
        "--tab-dragover-transition: none !important",
        ".tabbrowser-tab",
        "-moz-window-dragging: no-drag !important",
    ]
    for needle in required_css:
        if needle not in css:
            errors.append(f"v16 UI polish is missing: {needle}")

    required_popup_rules = [
        "menupopup, panel:not(.autoscroller)",
        "panel:not([remote]):not(.autoscroller), #BMB_bookmarksPopup",
        'panel[type="arrow"]:not(.autoscroller)',
    ]
    for needle in required_popup_rules:
        if needle not in popups:
            errors.append(f"Autoscroller popup exclusion is missing: {needle}")

    for name in (
        "autoscroll-filled-all-light.png",
        "autoscroll-filled-all-dark.png",
        "autoscroll-filled-vertical-light.png",
        "autoscroll-filled-vertical-dark.png",
        "autoscroll-filled-horizontal-light.png",
        "autoscroll-filled-horizontal-dark.png",
    ):
        if not (CHROME / "Monterey" / "assets" / name).is_file():
            errors.append(f"Autoscroll asset is missing: {name}")

    final_section = css.split("v16 stable spacing, tab dragging and autoscroll polish", 1)[-1]
    if "#TabsToolbar-customization-target > *" in final_section:
        errors.append("The final drag rules still catch the whole tab-strip child")
    if ":not([inFullscreen])" not in final_section:
        errors.append("The final drag rules do not exclude fullscreen")

    if '#forward-button[disabled="true"] {\n  display: none !important;' in css:
        errors.append("Disabled forward button still collapses out of layout")

    import json
    report_path = ROOT / "tests" / "layout-report.json"
    if not report_path.is_file():
        return errors + ["Rendered layout report is missing for v16 spacing checks"]

    reports = json.loads(report_path.read_text(encoding="utf-8"))
    nav_report_path = ROOT / "tests" / "navigation-spacing-report.json"
    if not nav_report_path.is_file():
        errors.append("Dedicated forward-button navigation report is missing")
    else:
        nav_report = json.loads(nav_report_path.read_text(encoding="utf-8"))
        if not nav_report.get("stable", False):
            errors.append("Dedicated forward-button navigation report is not stable")
        for state in ("disabled", "enabled"):
            gap = nav_report.get(state, {}).get("url_tab_gap")
            if gap is None or gap < 2:
                errors.append(f"Dedicated {state} URL/tab gap is too small ({gap})")

    for report in reports:
        checks = report.get("checks", {})
        width = report.get("width")
        if not checks.get("forward_slot_reserved", False):
            errors.append(f"{width}px: forward button slot is not stable")
        if not report.get("compact", False):
            if not checks.get("urlbar_before_tabs_with_forward", False):
                errors.append(f"{width}px: enabled forward button overlaps tabs")
            gap = report.get("urlbar_tabs_gap_forward_enabled")
            if gap is None or gap < 1.5:
                errors.append(f"{width}px: URL/tab gutter is too small ({gap})")
    return errors


def test_rendered_layout_results() -> list[str]:
    errors: list[str] = []
    results = ROOT / "tests" / "RENDERED-LAYOUT-RESULTS.txt"
    report = ROOT / "tests" / "layout-report.json"
    if not results.is_file() or not report.is_file():
        return ["Rendered layout results are missing"]
    text = results.read_text(encoding="utf-8")
    for width in (600, 650, 720, 820, 900, 960, 980):
        if f"PASS {width}px — compact navigation-only mode" not in text:
            errors.append(f"Rendered compact-mode test did not pass at {width}px")
    for width in (981, 1000, 1048, 1070, 1100, 1285, 1437, 1668):
        if f"PASS {width}px — one row" not in text:
            errors.append(f"Rendered one-row test did not pass at {width}px")
    if "All rendered responsive and collision checks passed." not in text:
        errors.append("Rendered responsive/collision summary is not successful")
    return errors



def main() -> int:
    checks = {
        "CSS active imports": test_css_imports,
        "CSS local assets": test_local_urls,
        "CSS delimiter balance": test_css_delimiters,
        "PowerShell static structure": test_powershell_static,
        "Fresh/empty user.js regression": test_empty_user_js_regression,
        "Install/update/uninstall filesystem flow": simulate_filesystem_flow,
        "Firefox Install-default profile selection": test_install_default_profile_detection,
        "Windows-only visual import boundary": test_windows_visual_imports,
        "Current Firefox Windows titlebar target": test_windows_titlebar_target,
        "Responsive one-row collision prevention": test_responsive_collision_prevention,
        "Windowed hit-testing and tab-close regression": test_windowed_hit_testing_and_tab_close,
        "Compact handoff and flexible-space artifact removal": test_v8_compact_mode_and_spring_artifact,
        "Web-content isolation and native scrollbar restoration": test_web_content_isolation,
        "URL-bar geometry/background containment": test_v14_urlbar_geometry_reset,
        "Autoscroll, tab dragging and desktop spacing": test_v16_autoscroll_drag_and_spacing,
        "Rendered responsive interaction/layout checks": test_rendered_layout_results,
    }
    all_errors: list[str] = []
    passed_groups = 0
    for label, check in checks.items():
        errors = check()
        if errors:
            print(f"FAIL: {label}")
            for error in errors:
                print(f"  - {error}")
            all_errors.extend(errors)
        else:
            print(f"PASS: {label}")
            passed_groups += 1
    print(f"\nResult: {passed_groups}/{len(checks)} groups passed")
    return 1 if all_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
