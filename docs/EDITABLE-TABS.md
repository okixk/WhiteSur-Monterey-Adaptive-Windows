# Full editable tabs (AutoConfig)

Full uses AutoConfig for click editing, middle-click closing and the release updater. Lite uses profile CSS without hover editing or privileged scripts. See [COMPATIBILITY.md](COMPATIBILITY.md) for the edition matrix and [AUTO-UPDATES.md](AUTO-UPDATES.md) for updater behavior.

Full enables editable tabs on Firefox 158+ for Windows. `Install.cmd` opens the configured Firefox and selected profile automatically after a successful installation. Tabs show their native page titles and favicons while browsing. Clicking a background tab selects it without editing; clicking the already selected tab opens Firefox's actual address bar, including its search selector, identity/security controls, page actions, suggestions, and keyboard behaviour. This does not require a rapid double-click. Ctrl+L, Alt+D, and F6 open editing directly. Navigation, Escape, or clicking the webpage restores the title. Native search/identity popups remain usable while editing.

A single ordinary tab is a centred capsule up to 580 CSS pixels wide, both while browsing and editing. It shrinks in narrow windows and leaves room for +, toolbar controls, and window dragging. Opening a second tab animates the capsule into the compact layout; closing back to one animates it into the centre. With multiple tabs, ordinary tabs use the same compact width of 88–160 CSS pixels depending on available space. Clicking the selected tab expands its editor to 300 pixels with plenty of room or 260 pixels when crowded, and further reduces that width when necessary in a narrow window. Background tabs keep their widths during expansion. Pinned tabs keep their icon size and show their field immediately below the icon.

Selection and editing are separate states. Opening the field expands just the selected tab; navigation, Escape, or clicking the page collapses it to its original width. The layout reserves room for the editor without repeatedly shrinking the surrounding tabs, and Firefox scrolls an expanded tab into view when needed. Keyboard switching to a website leaves its normal title visible. Ctrl+T still opens a new tab ready for input. Rounded tab backgrounds follow the active Firefox theme; close-button space remains reserved so hovering does not shift content.

Tab titles are centred, with their native favicon immediately to the left. Address/search text and placeholders are also centred, with the selected page's favicon beside the text. Firefox keeps its original input, selection, autocomplete, engine selector, security and page-action controls. Long values scroll within the native input; on extremely cramped fields the extra favicon yields space to the native controls.

## Files and startup

- `chrome/tab-search.uc.js`: privileged window script; observes tab geometry and positions the field without moving it out of its native toolbar DOM.
- `chrome/tab-search.css`: overrides gated by `tabsearch-ready`; imported before `customChrome.css` so user overrides remain last.
- `firefox/whitesur.cfg`: AutoConfig loader; starts after window initialization, only loads profiles marked by this installer, and skips Firefox Troubleshoot Mode.
- `firefox/defaults/pref/whitesur-autoconfig.js`: selects the loader and enables AutoConfig scripting in the existing Firefox installation.
- `Editable-Tabs-Runtime.ps1`: loader installation, ownership checks, and optional separate runtimes.
- `Install-Editable-Tabs-Loader.ps1`: writes only the installation-level loader files when administrator approval is needed.

The installer adds its two loader files to the detected Firefox installation and tracks them with `.whitesur-loader.json`. Your usual desktop, Start menu, and taskbar shortcuts open Firefox with editable tabs in the installed profile. Each profile has a `.whitesur-editable-tabs.json` installation record. The loader only activates in profiles carrying this theme's marker.

A completed, matching WhiteSur loader is reused read-only: profile updates do
not rewrite its cfg, pref-loader or installation marker, and do not request
elevation simply to reuse those existing files. Foreign or modified cfg files
remain protected by the conflict checks.

Full’s interaction script requires privileged browser access. Lite anchors the native input using CSS, with different click, Escape and motion behavior. The Full loader belongs in the Firefox installation directory. Windows requests administrator approval for protected installations such as Program Files. Only the loader helper is elevated; profile detection and theme installation run as your original user. Declining approval stops installation. A writable per-user Firefox installation needs no elevation.

## Adaptive colours and compatibility

The existing Monterey light/dark styles and Firefox theme variables supply colours, including `--lwt-accent-color`, `--toolbar-color`, and `--toolbar-text-color`. Adaptive Tab Bar Color can continue to supply those values; no separate palette is imposed. Native integration tests verify light and dark variable changes.

The explicit AutoConfig method stops before changing the profile theme for Firefox below 158, missing installations, a detected existing AutoConfig loader, or runtime setup errors. It reports the failure instead of silently installing classic CSS. Choose `-ClassicToolbar` explicitly for the classic layout. Unsupported browser windows and vertical tabs do not activate the script. Required DOM capabilities are checked before activation. `chrome/windows.css` remains the fallback with the previous Firefox 154/156 fixes.

Existing AutoConfig files are preserved. Use Lite with a custom loader. This project does not chain into, edit or replace it. Custom toolbar extensions and future Firefox UI changes may need adjustments.

Enabling vertical tabs or setting `userChrome.tabSearch.enabled` to `false` restores the standard toolbar immediately. After returning to horizontal tabs or re-enabling the preference, open a new window or restart Firefox. The managed preference block is reapplied on restart; use `-ClassicToolbar` for a persistent classic installation.

## Installation options

Releases include a separate Lite ZIP for the CSS-only theme. It excludes the editable-tab script and loader, and its `Install.cmd` and direct PowerShell entry point always choose CSS-only mode. The Full ZIP and source checkout also include `Install-Lite.cmd`. Switching from Full to Lite removes the profile's editable-tab files/state and disables the feature while preserving custom CSS; existing shared Firefox loader files are left untouched for other profiles.

Close Firefox, then use `Install.cmd`, or choose explicit paths:

```powershell
.\Install-WhiteSur-Monterey-Adaptive.ps1 `
  -ProfilePath 'D:\Firefox Profiles\Personal' `
  -FirefoxPath 'C:\Program Files\Mozilla Firefox\firefox.exe'
```

`Install.cmd` forwards arguments to the PowerShell installer. `-ClassicToolbar` installs only the CSS layout. `-AllProfiles` installs into all detected profiles. `-Launch` opens the configured Firefox with the first selected profile after installation; `Install.cmd` supplies this automatically. Direct PowerShell calls do not launch Firefox unless requested. `-Diagnose` reports profile, theme, runtime, loader, and launcher paths. `-Force` bypasses the running-Firefox check and is intended for isolated test profiles.

Passing `-RuntimeDirectory 'D:\Apps\WhiteSur Firefox'` explicitly requests a separate Firefox copy with a profile-specific shortcut. `-ShortcutDirectory` chooses the shortcut location for that optional mode. The default AutoConfig method configures the existing installation; normal Full installation uses the guarded AutoConfig method.

## Updating and removal

Full can stage automatic theme updates for the next restart; see [AUTO-UPDATES.md](AUTO-UPDATES.md). Rerun the installer with Firefox closed for manual updates. Existing cfg and loader-pref files are never rewritten: identical WhiteSur payloads may be reused, but changed files cause a refusal recommending Lite. Firefox keeps its normal browser-update mechanism; rerun the installer if an update removes loader files. Upgrading from beta.1 removes the previous unmodified owned WhiteSur shortcut and configures the original Firefox. Any previous separate Firefox copy remains until removed manually.

Uninstall removes managed preferences and any unmodified owned launcher, then restores the earlier chrome backup when available. A launcher repurposed by the user is preserved. The shared loader remains for other installed profiles; it ignores profiles without this theme's marker. Existing `customChrome.css` is preserved during theme updates. In the optional separate-runtime mode, the shared copy remains for other profiles.

## Tab-close behaviour

Native add/remove operations use Firefox's non-animated paths while editable tabs are active. Merely suppressing CSS transitions can leave closing tabs waiting for an event that never arrives. The script restores original browser methods and observers when destroyed. Layout updates synchronize the currently connected selected tab and run before paint on observed geometry changes, avoiding stale fields after quick close/switch sequences.

Each native tab-visibility request queues a matching position update after Firefox's scroll frame, including requests made after tab selection. Synchronous geometry updates preserve that follow-up, and disabling the customization restores the original visibility method.
