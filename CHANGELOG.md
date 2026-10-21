# Changelog

## 2026.10.21-20

- Made the selected tab the native address/search field, with native icons, suggestions, default-engine search, and optional `g`/`q` search prefixes.
- Kept the selected field visible, limited selected tabs to 280 px, and made background tabs shrink from 180 to 88 px as space fills.
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
