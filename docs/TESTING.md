# Testing notes — version 2026.07.28-15

## Test environment

The package is tested in a Linux container using Python, Chromium/Playwright fixtures, CSS/static checks and simulated Firefox profile filesystem flows. Native Windows non-client hit testing cannot be executed in this environment.

## New v15 regression: optional forward button

The browser fixture is rendered with the standard Firefox navigation order:

- Back
- Forward
- Stop/Reload
- URL bar
- tabs

The forward button is first disabled and then enabled without reloading the fixture.

Expected result:

- disabled forward slot width: 32 px
- enabled forward slot width: 32 px
- URLbar x coordinate does not change
- first tab boundary does not change
- URL/tab gap remains at least 8 px

Observed at 1310 px:

- disabled URL/tab gap: 40 px
- enabled URL/tab gap: 40 px
- geometry stable: true

Artifacts:

- `tests/navigation-forward-disabled.png`
- `tests/navigation-forward-enabled.png`
- `tests/navigation-spacing-report.json`

## Restored-window drag model

Static checks require:

- navigation and tabstrip containers use `-moz-window-dragging: drag`;
- all real controls and tabs use `-moz-window-dragging: no-drag`;
- `#tabbrowser-tabs` and its arrowscrollbox remain draggable containers;
- individual `.tabbrowser-tab` elements and toolbar buttons remain non-draggable controls.

This creates empty native drag regions without turning clickable controls into caption areas.

## Existing regression suites

- CSS imports and local assets
- CSS delimiter balance
- PowerShell installer structure
- fresh/empty `user.js`
- install, update, uninstall and backup restoration
- active Firefox Install-default profile selection
- Windows-only visual import boundary
- native Windows caption controls
- responsive one-row layout and compact handoff
- tab close animation and closing spacer
- web-content isolation
- v14 URLbar host/background containment
- rendered widths from 600 through 1668 px

Final result: 16/16 test groups passed.
