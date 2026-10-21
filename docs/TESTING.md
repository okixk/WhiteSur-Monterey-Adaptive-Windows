# Testing — 2026.10.21-21

## Native Firefox on Windows

Run with Python 3.13+, Firefox 158+, and geckodriver 0.37+:

```powershell
py tests/test_editable_tabs_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

This suite has no Python package dependencies. It invokes the real PowerShell installer with a disposable profile, runtime copy, and shortcut directory. Firefox loads the installed AutoConfig itself; initial activation is not injected by the test. WebDriver chrome context is enabled only for this test session.

Coverage includes native navigation, focus and Escape, Google/Qwant routing without network requests, light/dark adaptive colour variables, normal/private windows, field alignment at 600/800/1368/1384 pixels, constant strip allocation across selections, rapid native Ctrl+W/T/Tab/PageDown, pinned tabs, vertical-tab fallback, disabling, and reinitialization. Console checks catch loader errors and ResizeObserver loops. Search routing checks capture destinations; they do not assert external search-service availability.

Results are written to ignored `tests/artifacts/editable-tabs/firefox-report.json` and `firefox.png`, including on assertion failure. `--artifacts` selects another directory. The test waits for Firefox to exit before removing its temporary runtime.

Keyboard alignment is measured in the next animation frame, after the scheduled selection/scroll layout. Immediate offsets sampled before that frame are also retained in the report; those intermediate tasks can run before the updated layout is painted.

On Windows 11 with Firefox 158.0.1: **25 checks passed**, including a wider address field with few tabs, a narrower field with many tabs, and a native visibility-scroll request queued after selection, with zero measured field offset and zero total-width drift in the selection cases. These checks do not cover every extension combination, native window-caption hit testing, or every drag/detach interaction.

## Search-engine pill (issue #4)

```powershell
py tests/test_search_mode_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

Uses separate editable and classic profiles created by the real installer, sharing a disposable Firefox copy. Checks the default engine and Google/DuckDuckGo search-mode pills in normal, maximized, and 800 px windows. Measures the host, painted shadow button, icon, label, and close button against the address field's vertical centre; also checks containment, balanced horizontal padding, and the native close action. Reports and screenshots are saved under `tests/artifacts/search-mode/`.

Current result: **18 checks passed**, with zero measured vertical offset. Fresh-profile classic desktop cases also check that the default sidebar toggle cannot make tabs cover the address field.

## Windows installer

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_installer.ps1
```

Runs under Windows PowerShell 5.1. Uses temporary fake executable files that are never launched, and real filesystem/preferences/shortcut operations. Covers default install, profile launchers, UTF-8/LF loader files, update preservation, binary upgrades without downgrades, owned-runtime reuse, Windows 8.3 profile paths, diagnostics, multiple profiles, classic mode, uninstall restoration, unrelated preferences, modified launchers, older Firefox, AutoConfig conflicts, and unmanaged directories. Shared runtime retention is intentional. Current result: **27 checks passed**.

## Classic layout and package checks

Install `requirements-dev.txt` and Playwright Chromium, then run the commands in the README. These fixtures model the classic CSS toolbar; they do not substitute for native editable-tab tests. They cover 15 widths from 600 through 1668 pixels, navigation-button stability, URL-bar containment, selected-tab styling, tab-close spacing, window-drag CSS, popup styling, extension toolbar reservations, imports, assets, and installer/package structure.

Current results: all rendered widths passed, r7 **8/8**, r8 **5/5**, r9 **5/5**, package **16/16 groups**. On Linux, `CHROMIUM_EXECUTABLE` can select a system browser instead of the bundled Chromium.

GitHub Actions retains these Linux checks and adds Windows installer and native Firefox checks. Remote CI results are separate from the local validation recorded here.
