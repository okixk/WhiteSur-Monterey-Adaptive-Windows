# beta.5 validation — 2026-11-10

Local testing used Windows 11, Firefox 159.0, geckodriver 0.37.1 and Python
3.13.9. Every browser experiment used a disposable installation copy and profile.
The installed source browser and real company settings were not modified.

| Suite | Result |
| --- | --- |
| Compatible installer / security preservation | 57 checks passed |
| Existing installer / legacy compatibility | 49 checks passed |
| Compatible Full in real Firefox | 50 checks passed |
| Legacy editable tabs in real Firefox | 38 checks passed |
| Native search mode, legacy and classic | 18 checks passed |
| Legacy motion / middle-click | 27 checks passed |
| Legacy native Windows titlebar | 19 checks passed |
| Legacy centred text | 18 checks passed |
| Full/Lite release archives, including native Firefox | 40 checks passed |
| Classic package validation | 16/16 groups passed |
| Classic layout, navigation, URL geometry, selected tabs, r7/r8/r9 fixtures/regressions | All passed |

The [Compatible Firefox measurement report](validation/compatible-firefox.json)
records individual assertions and geometry. Installer output paths are omitted
from the committed copy. Fresh local reports/screenshots remain in ignored
`tests/artifacts/`; reproduction commands are in [TESTING.md](TESTING.md).

## Security/configuration evidence

The Compatible browser suite creates a harmless synthetic `zscaler.cfg`, a
loader-pref file and a `DisableTelemetry` policy in a newly copied browser. It
confirms that the cfg actually runs, its lab preference is locked, and Firefox
reports the policy active. It checks file hashes across install/update/uninstall.
A second profile verifies that an AutoConfig lock disabling custom stylesheets
remains effective. This is a coexistence test, not a certification of actual
Zscaler software, certificate handling or company-specific configurations.

Installer fixtures additionally cover inline/multiline/dynamic config values,
orphan cfg files, invalid ownership markers, modified owned cfg files, enterprise
policies, custom installation defaults, old browsers, migration from the legacy
Full method, and explicit Compatible overriding an old runtime argument. No
foreign cfg is imported or rewritten. No enterprise registry values are changed.

## Visual review and iteration

The original repository screenshot and the live lab captures were compared for
the continuous 48px toolbar, rounded tab surfaces, title/favicon centring,
native caption buttons and control spacing. Live tests found and corrected:

* Hidden input styling that prevented Ctrl+L focus: preserve focusability while
  disabling pointer interception when the editor is transparent.
* The classic layer hiding all tabs below 981px: Full now uses a separate tab
  row with its native scroll/new-tab controls.
* Crowded editors too small to type: reserve a 320px selected editor in roomy
  inline mode, keep native overflow scrolling, and allow that scrolling to settle.
* Native scrolling temporarily crossing toolbar controls: keep navigation,
  tools and caption controls above the editor. A clamp based on anchor layout
  coordinates was rejected because native anchor scroll compensation displaced it.
* Light/coloured-theme suggestion text losing contrast: use native popup surface
  and text colours, including suggestion titles/actions.
* Selected-title styling leaking into the narrow fallback and vertical sidebar:
  restore narrow titles and scope capsule title layout to horizontal toolbar tabs.
* Pointer targeting inside native URL controls: allow events in the visible
  input/control descendants while a transparent editor stays inert. The actual
  site-information/trust popup is opened through native input and remains usable.

Captured examples:

| State | Screenshot |
| --- | --- |
| Centred single-tab browsing | [Wide](compatible-browsing.png) |
| Native inline editing and suggestions | [Editing](compatible-editing.png) |
| Narrow browsing with visible tabs | [Narrow](compatible-narrow.png) |
| Built-in light theme | [Light](compatible-light.png) |

Further generated captures include 3/14 tabs at five window sizes, built-in
dark and standard extension colours, private windows, vertical tabs and
fullscreen. Native tests also open/close tabs using real input, check Windows
hit-testing and actually double-click the caption region to maximize.

## Practical limits

This does not establish compatibility with every Firefox release, DPI setting,
toolbar customization, tab grouping extension, enterprise policy, or drag/detach
sequence. Native evidence covers Firefox 159.0; `@supports` provides the
separate-field fallback elsewhere, but an older Firefox binary was not part of
this run. Browser chrome CSS remains an unsupported customization interface.

Compatible uses hover to reveal mouse editing and native Escape/focus behavior.
Native smooth scrolling may briefly move the editor across a strip edge while
toolbar controls stay on top. Use outer tab edges/background tabs for dragging;
the editor centre retains native input actions. Custom JavaScript animations,
exact second-click activation, middle-click closing inside the input and custom
`g`/`q` routing remain privileged features. See [COMPATIBILITY.md](COMPATIBILITY.md).

GitHub Actions is configured to run the new suites alongside the existing ones.
Remote CI results are separate from these local results.
