# Changelog

## 2026.10.22-22 (v0.2.0-beta.2)

- Install the editable-tab loader directly into the existing Firefox so normal desktop, Start menu, and taskbar shortcuts work.
- Elevate only the loader helper when the Firefox installation directory needs administrator rights; profile selection and theme installation stay with the original user.
- `Install.cmd` opens the configured existing Firefox with the installed profile after successful installation. A separate runtime is available only through explicit `-RuntimeDirectory` selection.
- Require editable-tab runtime setup by default; unsupported Firefox, AutoConfig conflicts, and runtime errors stop installation before replacing the profile theme.
- Keep classic CSS available explicitly with `Install.cmd -ClassicToolbar` and forward command-line options from the CMD launcher.
- Add installer regression coverage for automatic launch and failed setup leaving profile themes untouched.

## 2026.10.21-21 (v0.2.0-beta.1 — Editable Tabs Update)

This is a larger interface update from the 0.1 betas, including the editable-tab implementation developed in v20 below.

- Fixed issue #4: the modern search-engine pill's inner button no longer overflows its shorter host, keeping the icon, engine name, and close control centred.
- Retained native search-engine switching, close behaviour, and theme colours in editable and classic layouts.
- Added installer-backed Firefox regression checks for default/Google/DuckDuckGo controls in normal, maximized, and narrow windows.
- Reserved the default sidebar button in the classic desktop layout so a fresh Firefox profile cannot place tabs over the address field.
- Preserved the layout frame queued after Firefox's native selection scroll, fixing a rapid close/switch race found by Windows CI.
- Normalized Windows 8.3 profile paths before the chrome-directory boundary check, preserving the guard without rejecting valid shortened paths.
- Packaged editable tabs, adaptive 300–260 px selected-tab sizing, compact background tabs, close/switch stability fixes, and the user-local runtime installer as the new beta default.
- Updated setup documentation and release notes to explain the new launcher and compatibility fallback.

## 2026.10.21-20

- Made the selected tab the native address/search field, with native icons, suggestions, default-engine search, and optional `g`/`q` search prefixes.
- Kept the selected field visible, made selected tabs adapt from 300 to 260 px as space fills, and made background tabs shrink from 180 to 88 px.
- Fixed stale geometry after rapid Ctrl+W/T/Tab and width/overflow oscillation using native non-animated tab insertion/removal and stable strip allocation.
- Added an administrator-free user-local Firefox copy, profile launchers, loader updates, diagnostics, and uninstall cleanup.
- Retained adaptive theme variables and the classic CSS fallback for older Firefox, vertical tabs, and detected AutoConfig conflicts. Existing AutoConfig files are preserved.
- Added Windows PowerShell installer and native Firefox integration tests, including private windows, narrow layouts, search routing, adaptive colours, keyboard stress, and disable/reinitialization.

## 2026.09.29-19 (v0.1.0-beta.3)

- Kept Firefox 156's "Not Secure" address-bar label on one line.
- Restored Firefox's native anchoring for notification permission prompts.
- Gave executable-file dialogs an opaque background, removing the dark rectangle seen with MSI downloads.

## 2026.08.21-18

- Restored native window dragging across the real post-tab shadow-scrollbox tail on Firefox 154, including windows that expose `customtitlebar` instead of `tabsintitlebar`.
- Kept tabs, New Tab, overflow buttons, private-window tabs, reordering, and detaching as native no-drag controls.
- Styled Firefox's Add tab to taskbar page action as a compact URL-bar icon aligned with Translate and Bookmark.
- Reserved the actual Downloads, Unified Extensions, and pinned-extension toolbar slots so the overlaid tab strip cannot cover the puzzle icon or extension controls.
- Added live-geometry-backed r7–r9 regression fixtures for tab-tail dragging, taskbar-action styling, and toolbar collision prevention.

## 2026.08.19-17

- Fixed selected-tab styling on Firefox 154 by replacing string-valued pseudo-boolean selectors with boolean tab-state selectors.
- Anchored the active tab background to the tab's selected/visual state as well as the tab-background node.
- Added a Firefox 154 selected-tab regression test.
## 2026.08.03-16

- Added a macOS-inspired middle-click autoscroll puck with separate light, dark, vertical, horizontal, and four-direction artwork.
- Excluded Firefox's autoscroller from generic popup styling so its icon is no longer stripped.
- Expanded native window dragging into empty tab-strip space while keeping tabs, buttons, URL-bar controls, and caption buttons interactive.
- Stabilised Firefox's `movingtab` state so reordering and detaching tabs no longer shifts or duplicates the compact tab-strip UI.
- Reduced the desktop URL-bar-to-first-tab reservation from 510 px to 498 px after visual testing.
- Added static regression coverage for autoscroll assets, popup exclusions, moving-tab geometry, safe drag hit-testing, and the updated desktop spacing.


## 2026.07.28-15

- Preserved the disabled Forward button's layout slot so navigation state changes no longer move the URL bar into the first tab.
- Restored native draggable empty regions in non-maximised Windows Firefox windows.
- Kept the URL-bar popover host constrained to its actual toolbar item.
- Removed the detached right-edge URL-bar outline artefact.
- Retained responsive compact mode, clean tab closing, native Windows caption controls, and Adaptive Tab Bar Color support.

Earlier builds were iterative development versions leading to this first repository-ready release.
