# WhiteSur Monterey Adaptive for Windows

A **Monterey-style, adaptive Firefox UI theme for Windows 11**.

The selected tab becomes Firefox's native address/search field. Click a tab and type a URL or search, while other tabs stay compact. It includes native Windows controls, adaptive colours, a PowerShell installer, profile detection, backups, and uninstall support.

**v0.2.0-beta.2 installs editable tabs by default and opens the configured Firefox automatically.** See the [release notes](docs/releases/v0.2.0-beta.2.md).

![WhiteSur Monterey Adaptive running in Firefox on Windows](docs/screenshot.png)

> [!IMPORTANT]
> This is an unofficial community project. It is not affiliated with or endorsed by Mozilla, Apple, Vince Liuice, Rafael Mardojai, AdamXweb, or the developers of Adaptive Tab Bar Color.

## Features

- Monterey-inspired Firefox appearance on Windows
- Native Windows minimise, maximise, and close buttons on the right
- Editable selected tabs with native address-bar icons and suggestions
- Compact background tabs that shrink as space fills; selected tabs stay open
- Stable switching and closing without animated width changes
- Compatible CSS toolbar for older Firefox, vertical tabs, and existing AutoConfig setups
- Stable spacing when navigation and page-action icons appear
- Clean tab closing without invisible gaps
- Draggable empty toolbar and tab-strip regions without interfering with tab reordering or detaching
- macOS-inspired light/dark middle-click autoscroll indicator
- Adaptive colours through Firefox theme variables
- Automatic Firefox profile detection
- Existing `chrome` folder backup and restoration
- Preserves your `customChrome.css` during updates
- No administrator rights required

## Adaptive colours

The theme is designed to work with **Adaptive Tab Bar Color**:

https://addons.mozilla.org/firefox/addon/adaptive-tab-bar-colour/

The extension changes Firefox's theme colours to match the active website. This theme consumes Firefox's standard lightweight-theme variables, so the toolbar and tabs can follow those colours.

Without the extension, the theme still works, but the colours remain based on Firefox's current theme instead of adapting per website.

## Installation

1. Download or clone this repository.
2. Fully close Firefox. Make sure no `firefox.exe` process remains.
3. Run `Install.cmd`.
4. The installer opens WhiteSur Firefox automatically. Use the new **WhiteSur Firefox - &lt;profile&gt;** desktop shortcut next time.

The installer:

- finds the Firefox profile selected by Firefox's `installs.ini`;
- backs up an existing `chrome` directory;
- installs the theme;
- enables the necessary preferences through a managed `user.js` block;
- on Firefox 158+, creates a user-local Firefox copy with the editable-tab loader and a profile-specific desktop shortcut.

The copy lives in `%LOCALAPPDATA%\Programs\WhiteSur Firefox`. The original Firefox installation is preserved. Use the WhiteSur shortcut for editable tabs; opening the original binary uses the CSS toolbar. Close Firefox before switching launchers for the same profile.

If editable tabs cannot be installed, installation stops with an error before replacing the profile theme. Update to Firefox 158+ or pass a clean installation with `Install.cmd -FirefoxPath "C:\path\to\firefox.exe"`. Classic mode is an explicit choice: `Install.cmd -ClassicToolbar`.

Type an address or search into the selected tab. Normal searches use your Firefox default engine; `g search terms` uses Google and `q search terms` uses Qwant. `Ctrl+L`, `Alt+D`, and `F6` focus the field; `Esc` cancels the draft and keeps the field visible.

To install just the classic adaptive toolbar:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-WhiteSur-Monterey-Adaptive.ps1 -ClassicToolbar
```

See [editable-tab setup and compatibility](docs/EDITABLE-TABS.md) for custom paths and loader details.

Use `Check-Installation.cmd` to verify the active profile and installed version.

## Updating

Close Firefox and run `Install.cmd` from the newer release. A user-created `customChrome.css` is preserved. The installer refreshes its loader and copies a newer source Firefox when available; it does not downgrade a newer WhiteSur copy.

## Uninstalling

Close Firefox and run `Uninstall.cmd`. It removes its managed preferences and owned profile launcher, and restores the previous `chrome` backup when available. The shared Firefox copy remains for other profiles. Once no profiles use it, you may remove `%LOCALAPPDATA%\Programs\WhiteSur Firefox` manually.

## Compatibility

Version `2026.10.22-22` (`v0.2.0-beta.2`) targets Firefox 158+ on Windows 11 with horizontal tabs. Older versions and detected AutoConfig conflicts require explicit `-ClassicToolbar` installation, which retains the previous Firefox 154/156 fixes. Vertical tabs leave the editable-tab implementation inactive.

Adaptive Tab Bar Color compatibility is retained: both layouts use Firefox's existing theme colour variables. Native tests cover light and dark variable changes; extension-specific behaviour also depends on the extension's settings.

Firefox does not officially support third-party browser chrome CSS as a stable public API. A future Firefox update can rename UI elements or change layout behaviour. Please report theme-specific breakage here rather than to Mozilla.

## Development and testing

This project was **heavily vibe-coded with ChatGPT**, then iteratively tested and corrected in real Firefox sessions on Windows. The final layout was shaped by repeated visual testing, especially around URL-bar geometry, tab closing, responsive widths, toolbar spacing, and native window dragging.

Native Windows checks use a disposable profile and runtime. Run with Firefox 158+ and [geckodriver](https://github.com/mozilla/geckodriver/releases) 0.37+:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_installer.ps1
py tests/test_editable_tabs_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
py tests/test_search_mode_firefox.py --firefox "C:\Program Files\Mozilla Firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

See [testing notes](docs/TESTING.md) for coverage and artifacts. The classic layout and package checks run with:

```powershell
py -m pip install -r requirements-dev.txt
py -m playwright install chromium
py tests/render_layout.py
py tests/test_navigation_states.py
py tests/test_urlbar_geometry.py
py tests/test_tab_selected_firefox154.py
py tests/test_v18_r7_regressions.py
py tests/test_v18_r8_regressions.py
py tests/test_v18_r9_toolbar_integration.py
py tests/render_v18_r7_fixture.py
py tests/render_v18_r9_fixture.py
py test_package.py
```

On Linux, set `CHROMIUM_EXECUTABLE` to a system Chromium path when you prefer not to use Playwright's bundled browser.

## Upstream and inspiration

This project is **heavily based on and inspired by**:

- [WhiteSur Firefox Theme](https://github.com/vinceliuice/WhiteSur-firefox-theme) by Vince Liuice — the main visual and CSS base
- [Firefox GNOME Theme](https://github.com/rafaelmardojai/firefox-gnome-theme) by Rafael Mardojai and contributors — layout and Firefox chrome implementation ideas
- [WhiteSurFirefoxThemeMacOS](https://github.com/AdamXweb/WhiteSurFirefoxThemeMacOS) by AdamXweb — Windows/macOS WhiteSur adaptation ideas

The Windows geometry, installer, responsive behaviour, regression tests, URL-bar containment fixes, tab-close handling, and packaging in this repository were adapted specifically for this project.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) and the files in [`licenses/`](licenses/) for attribution and upstream licence texts.

## Licence

The Windows adaptation, installer, tests, documentation, and modifications in this repository are licensed under the **GNU Affero General Public License v3.0 or later** (`AGPL-3.0-or-later`). See [`LICENSE`](LICENSE).

Portions derived from upstream projects retain their original copyright and licence notices. In particular, the main WhiteSur Firefox source is MIT-licensed. The required notices are preserved in `licenses/` and `THIRD_PARTY_NOTICES.md`.

The AGPL choice applies to this combined adapted distribution and to original contributions in this repository. It does not remove the upstream authors' ability to distribute their original code under their original licences.

## Trademark note

Firefox and the Firefox logo are trademarks of the Mozilla Foundation. macOS, Monterey, and Safari are trademarks of Apple Inc. WhiteSur is used descriptively to identify the upstream visual project and style inspiration.
