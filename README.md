# WhiteSur Monterey Adaptive for Windows

A Monterey-inspired Firefox theme for Windows 11, available in **Full** and **Lite**.

| | Full | Lite |
| --- | --- | --- |
| Adaptive colours, rounded capsules, Windows caption buttons | Yes | Yes |
| Hover-to-edit | No | No |
| Click selected tab to edit | Yes | Use Ctrl+L / Alt+D / F6 |
| Middle-click selected browsing tab | Closes the tab | Native tab closing |
| Middle-click inside the address editor | Closes the selected tab | Native Firefox input behavior |
| Multiple ordinary tabs | Up to 160px while browsing | Fixed 240px slots |
| Single-tab capsule | Wide and centred | Wide and centred where space permits |
| Custom expansion/open/close animations | Yes | CSS fades/slide/scale, native lifecycle |
| GitHub release updater | Yes; enabled by default | None |
| AutoConfig | Required; guarded installation/reuse | Never installed |

Full is for the complete click editor and updater. Lite is for installations
with existing AutoConfig such as `zscaler.cfg`, enterprise policies, or a
preference for profile CSS only. Existing AutoConfig and security configurations
are never overwritten or chained into.

## Install

Close Firefox before installing. Extract one complete release ZIP and run its
`Install.cmd`. Full and Lite archives select their own edition, including direct
PowerShell invocation. In a source checkout:

```powershell
.\Install.cmd          # Full: guarded AutoConfig + click editor + updater
.\Install-Lite.cmd     # Lite: CSS only

# Explicit profile / executable and edition
powershell -NoProfile -ExecutionPolicy Bypass -File .\Install-WhiteSur-Monterey-Adaptive.ps1 -Edition Lite -ProfilePath "C:\path\to\profile" -FirefoxPath "C:\Program Files\Mozilla Firefox\firefox.exe"

# Full with automatic updates initially disabled
.\Install.cmd -DisableAutoUpdate
```

Full requires Firefox 158+ and an available AutoConfig slot. A completed,
matching WhiteSur loader is reused read-only, without rewriting its cfg,
pref-loader or installation marker. A new loader may need administrator rights.
Foreign AutoConfig, differing owned cfg contents and detected enterprise policy
management cause a refusal recommending Lite. `-Force` bypasses only the
running-Firefox check; it does not bypass configuration protection.

Lite never writes Firefox installation files or installs privileged scripts or
an updater. The installer backs up an unrelated chrome folder, preserves your
`customChrome.css` on updates and manages only its own `user.js` preference block.
Administrator-locked stylesheet preferences remain authoritative.

`-InstallationMethod AutoConfig` remains an alias for Full behavior;
`-InstallationMethod Compatible` selects Lite. `-ClassicToolbar` retains the
older CSS layout for compatibility. See [edition details](docs/COMPATIBILITY.md).

## Use

In Full, click a background tab to select it, then click the selected tab to
edit its native address field. The second click does not need to be a fast
double-click. Hovering only changes the highlight. A middle-button press and
release inside the editor closes exactly that selected tab; releasing outside
cancels the gesture. Ctrl+L, Alt+D and F6 edit immediately; Escape, navigation or
clicking the page restores the title. Native suggestions and site-information
controls remain available. Reduced motion is respected.

Lite keeps browsing tabs available for native left/middle clicks. Hovering does
not open the editor. Ctrl+L, Alt+D, F6 and new-tab focus reveal the real field;
Escape follows normal Firefox behavior. Engines with CSS anchors align that
field with the selected horizontal tab. Narrow windows (up to 980 CSS pixels),
pinned selections and engines without anchors use a separate address field.
Vertical tabs retain their native sidebar. Middle-clicking inside a focused
native input cannot be reassigned by CSS.

Both editions consume Firefox's standard theme variables. For site-dependent
colours, install [Adaptive Tab Bar Color](https://addons.mozilla.org/firefox/addon/adaptive-tab-bar-colour/).
Without it, Firefox's selected theme supplies the colours.

## Full automatic updates

Full checks published releases from
[`okixk/WhiteSur-Monterey-Adaptive-Windows`](https://github.com/okixk/WhiteSur-Monterey-Adaptive-Windows/releases)
after startup and at most once a day. Prereleases are included during this beta
project. Use **Tools → WhiteSur Updates** (Alt+T on Windows) to check now, see
status, or turn automatic updates off. An opted-out setting survives normal
installer updates.

A verified newer Full ZIP is downloaded and staged while you browse. Its theme
is applied during normal shutdown, before the profile lock is released, so the
next start loads the update. The running theme is not replaced mid-session.
The updater verifies GitHub's SHA-256 asset digest, the package manifest and
every managed theme file, and rejects unsafe ZIP paths and incompatible packages.
It never runs downloaded installers or modifies Firefox, AutoConfig, policies,
extensions, bookmarks, preferences or certificates. `customChrome.css` is copied
from your active theme at application time, preserving changes made after download.

Only managed theme files under `chrome` are updated, including Full's browser-UI
JavaScript. This trusts the fixed repository's release publisher; checksums
detect corruption and are not independent author signatures. Put personal CSS
changes in `customChrome.css`, since other managed theme files are replaced.
Loader-protocol changes require manual installation instead of rewriting cfg.

Updates require a normal quit/restart to apply. After a crash they remain staged
until a normal shutdown. Previous theme copies are retained for recovery. If a
power interruption occurs between directory moves and leaves `chrome` missing,
rerunning the installer restores its owned backup before reinstalling. Details:
[updater behavior, validation and recovery](docs/AUTO-UPDATES.md).

## Update, diagnose, remove

Close Firefox and rerun the chosen edition's installer for a manual update or
edition switch. Switching to Lite removes the privileged profile script and
updater settings and cancels queued Full updates. Shared installation-level
loader files stay untouched for other profiles.

`Check-Installation.cmd` reports profiles, version, edition/method, AutoConfig
and policy-source detection. Use `about:policies` for effective enterprise policy
details. Close Firefox and run `Uninstall.cmd` to remove the theme and managed
preferences, restoring the earlier chrome backup when available. Owned updater
cache/rollback directories are retained for manual recovery; they cannot apply
without the Full runtime and settings.

## Development and tests

All browser testing uses disposable Firefox copies and profiles. The updater
suite uses real ZIPs, real hashing/extraction, simulated GitHub transport and a
real quit/relaunch, plus an optional read-only request to GitHub:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_installer.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tests/test_compatible_installer.ps1
python tests/test_full_updater_firefox.py --firefox "C:\clean-firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe" --network
python tests/test_compatible_firefox.py --firefox "C:\clean-firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
python tests/test_release_packages.py
```

Run native suites sequentially because input focus is shared on Windows. See
[testing notes](docs/TESTING.md). Firefox chrome CSS and privileged UI internals
are not stable public APIs; browser updates may require theme changes. This is
an unofficial community project, unaffiliated with Mozilla, Apple or the
upstream theme authors.

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
