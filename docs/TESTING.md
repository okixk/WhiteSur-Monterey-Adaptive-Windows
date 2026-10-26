# Testing — 2026.10.21-21

## Native Firefox on Windows

Run with Python 3.13+, Firefox 158+, and geckodriver 0.37+:

```powershell
py tests/test_editable_tabs_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

This suite has no Python package dependencies. It invokes the real PowerShell installer with a disposable profile and existing Firefox directory. The default installation adds its loader to that Firefox without creating another runtime or shortcut. Firefox loads the installed AutoConfig itself; initial activation is not injected by the test. WebDriver chrome context is enabled only for this test session.

Coverage includes native navigation, focus and Escape, Google/Qwant routing without network requests, light/dark adaptive colour variables, normal/private windows, field alignment at 600/800/1368/1384 pixels, constant strip allocation across selections, rapid native Ctrl+W/T/Tab/PageDown, pinned tabs, vertical-tab fallback, disabling, and reinitialization. Console checks catch loader errors and ResizeObserver loops. Search routing checks capture destinations; they do not assert external search-service availability.

Results are written to ignored `tests/artifacts/editable-tabs/firefox-report.json` and `firefox.png`, including on assertion failure. `--artifacts` selects another directory. The test waits for Firefox to exit before removing its temporary runtime.

Keyboard alignment is measured in the next animation frame, after the scheduled selection/scroll layout. Immediate offsets sampled before that frame are also retained in the report; those intermediate tasks can run before the updated layout is painted.

On Windows 11 with Firefox 158.0.1: **33 checks passed**, including page-title/favicon restoration, first-click selection versus second-click editing, actual webpage clicks, keyboard switching, new-tab focus, expansion/collapse without resizing neighbours, adaptive editor sizes, and a native visibility-scroll request queued after selection. The click-selection case includes an existing blank tab with previously saved address-bar focus, which must stay compact on the first click. Geometry cases exercise both equal-width browsing tabs and an expanded editor, measuring alignment and total-width drift separately for each mode. Browsing/editing screenshots are saved as `compact-browsing.png` and `compact-editing.png`. These checks do not cover every extension combination, native window-caption hit testing, or every drag/detach interaction.

## Search-engine pill (issue #4)

```powershell
py tests/test_search_mode_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

Uses separate editable and classic profiles created by the real installer, sharing a disposable Firefox copy. Checks the default engine and Google/DuckDuckGo search-mode pills in normal, maximized, and 800 px windows. Measures the host, painted shadow button, icon, label, and close button against the address field's vertical centre; also checks that native focus reveals the editor, containment, balanced horizontal padding, and the native close action. Reports and screenshots are saved under `tests/artifacts/search-mode/`.

Current result: **18 checks passed**, with zero measured vertical offset. Fresh-profile classic desktop cases also check that the default sidebar toggle cannot make tabs cover the address field.

## Editor motion and middle-click closing

```powershell
py tests/test_tab_motion_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

Uses another installer-created profile and runtime. Checks intermediate tab widths and editor opacity, frame-by-frame input alignment, rapid animation reversal, immediate native tab removal with a temporary decorative snapshot, native WebDriver middle-clicks inside the input and releases outside it, reduced-motion behaviour, and cleanup when disabling during motion. Reports go to `tests/artifacts/tab-motion/tab-motion-report.json`. The geometry checks in the main tab suite wait for motion to settle before comparing final widths; the rapid keyboard checks still sample the next frame.

Current result: **25 checks passed** on Windows 11 with Firefox 158.0.1, including expansion at the crowded strip's right edge and actual + clicks while editing with 3/14 tabs at 1384/800 px. The + checks hold the pointer between down/up, confirm exactly one selected tab with a fading entrance and focused editor, and check that returning preserves the original draft. New-tab entrance also respects reduced motion and cleanup. Run all native browser suites sequentially so separate Firefox windows cannot steal test focus.

## Native window titlebar

```powershell
py tests/test_window_titlebar_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

Creates another installed Firefox/profile and checks Windows `WM_NCHITTEST` results, plus real mouse double-clicks to maximize and restore. Covers a 921 px restored window and maximized state, 1/14 tabs, browsing/editing, client hit-testing for tabs/+ and the input, and the no-drag state during tab reordering. The top resize border remains native in restored windows. The disposable test window is temporarily topmost so native clicks cannot land in another application. Results go to `tests/artifacts/window-titlebar/window-titlebar-report.json`.

Current result: **19 checks passed** on Windows 11 with Firefox 158.0.1. Run sequentially with the other native suites.

## Windows installer

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_installer.ps1
```

Runs under Windows PowerShell 5.1. Uses temporary fake executable files that are never launched, and real filesystem/preferences/shortcut operations. Covers default installation into existing Firefox, explicit separate runtimes and profile launchers, UTF-8/LF loader files, update preservation, binary upgrades without downgrades, owned-runtime reuse, Windows 8.3 profile paths, diagnostics, multiple profiles, classic mode, uninstall restoration, unrelated preferences, modified launchers, older Firefox, AutoConfig conflicts, unmanaged directories, launch selection, and elevation of only the loader helper. Shared loader/runtime retention is intentional. Current result: **49 checks passed**.

## Classic layout and package checks

Install `requirements-dev.txt` and Playwright Chromium, then run the commands in the README. These fixtures model the classic CSS toolbar; they do not substitute for native editable-tab tests. They cover 15 widths from 600 through 1668 pixels, navigation-button stability, URL-bar containment, selected-tab styling, tab-close spacing, window-drag CSS, popup styling, extension toolbar reservations, imports, assets, and installer/package structure.

Current results: all rendered widths passed, r7 **8/8**, r8 **5/5**, r9 **5/5**, package **16/16 groups**. On Linux, `CHROMIUM_EXECUTABLE` can select a system browser instead of the bundled Chromium.

GitHub Actions retains these Linux checks and adds Windows installer and native Firefox checks. Remote CI results are separate from the local validation recorded here.
