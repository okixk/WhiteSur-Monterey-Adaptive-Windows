# Changelog
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
