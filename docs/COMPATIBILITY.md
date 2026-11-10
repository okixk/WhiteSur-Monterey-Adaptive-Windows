# Full without AutoConfig

Full now defaults to **Compatible**, a profile-only `userChrome.css` implementation.
It does not install a loader, request elevation, change Firefox binaries, set
`general.config.*`, edit certificates, change proxy settings, modify policies, or
disable extension signing. Existing `zscaler.cfg` and similar configurations keep
loading normally. If an administrator locks stylesheet loading off, the theme
cannot apply; this installer does not bypass that lock.

## Implementation and project audit

`Install-WhiteSur-Monterey-Adaptive.ps1` still selects profiles from `installs.ini`
and `profiles.ini`, backs up unrelated chrome folders, preserves `customChrome.css`,
and manages a delimited `user.js` block. Full adds `full-compatible.css` after the
existing Windows layer and before user overrides. It removes `tab-search.uc.js`
from the installed profile and sets `userChrome.tabSearch.enabled=false`, so a
shared loader from an earlier release cannot activate the legacy implementation.

`Monterey/theme-adaptive.css` imports the controls, address field, popups, tabs,
sidebar, dialogs, notifications, icons and light/dark variables. Linux CSD,
title-button and toolbox files remain intentionally unused on Windows. The
content/page styles remain unimported by `userContent.css`, which deliberately
does not restyle websites. `windows.css` supplies the caption buttons, autoscroll
artwork, drag regions and classic responsive layout; it remains the Lite baseline.
The Compatible layer overrides its narrow-window tab hiding and toolbar geometry.

`tab-search.uc.js` is the original privileged implementation. It observes tab,
focus, drag and resize events; calculates toolbar/tab/input/icon rectangles;
temporarily wraps native tab creation/removal, scrolling and focus methods; and
uses the Web Animations API for tab expansion, entrances and close snapshots.
It also implements Escape-to-title, middle-click closing inside the editor,
and `g`/`q` search shortcuts. None of this script runs in Compatible mode.
`tab-search.css` is gated on the script's `tabsearch-ready` marker. The legacy
`whitesur.cfg` startup observer loads that script only into marked profiles.

Compatible uses **CSS anchor positioning** to attach the real native address
field to the selected horizontal tab. The tab remains the source of its real
title and favicon. `Ctrl+L`, `Alt+D`, F6 and native new-tab focus reveal the input;
hovering the selected tab reveals it for mouse editing. Input visibility uses
opacity rather than `visibility:hidden`, preserving keyboard focus. An invisible
editor does not intercept pointer events. The edges retain native tab targets.
Suggestions use the real Firefox panel, bounded to the viewport. Native identity,
permission, search-engine and bookmark controls are retained.

When anchors are unavailable, at widths at or below 980 CSS pixels, or when a
pinned tab is selected, the layout uses a native address toolbar with a separate
tab row. Vertical tabs retain their sidebar and native address field. Feature
detection uses `@supports`, not a claimed minimum Firefox version. Native testing
for this change used Firefox **159.0**, Windows 11, and geckodriver **0.37.1**.

## Feature comparison

| Feature | Full Compatible (default) | Legacy AutoConfig | Lite / Classic |
| --- | --- | --- | --- |
| Monterey colours, rounded surfaces, native Windows buttons | Yes | Yes | Yes |
| Adaptive Tab Bar Color / standard themes | Yes | Yes | Yes |
| Centred titles with neighbouring native favicons | Yes, horizontal tabs | Yes | Classic arrangement |
| Native field aligned to selected tab | CSS anchors, roomy horizontal windows | JS geometry, Firefox 158+ | Separate field |
| Centred single-tab capsule | Yes, with room | Yes | Classic arrangement |
| Native search suggestions, security controls, engine selector | Yes | Yes | Yes |
| Select background tab, edit selected tab | Select, then hover/click field | Second click starts editing | Separate field |
| Ctrl+L / Alt+D / F6 / Ctrl+T | Native behavior | Script-assisted native behavior | Native behavior |
| Escape | Native cancel/close; focus may remain in field | Returns to tab title | Native behavior |
| Click page | Returns to title unless pointer remains over tab | Returns to title | Native behavior |
| Editor space | All ordinary tabs reserve 280px editing slots; native scrolling | Compact tabs with animated focus-only expansion | Separate field |
| Open/close animations | CSS fade/slide/scale during native lifecycle | Custom entrances/detached close snapshots | Native motion |
| Editor/title motion | 140ms crossfade without resizing | Coordinated expansion/collapse and fade | Native behavior |
| Reduced motion | Disables the decorative CSS transitions | Also cancels custom motion | Native motion |
| Middle-click inside address input closes tab | No; normal Firefox input behavior | Yes | No |
| `g`/`q` search prefixes | Configure native bookmark keywords / search shortcuts | Built in | Configure natively |
| Tab drag/context menu | Native tab edges/background tabs; input has native input actions | Script coordinates dragging | Native tabs |
| Older engines / narrow windows | Separate address/tab rows | Classic fallback | Classic compact layout hides tabs below 981px |
| Admin rights / installation writes | None | Explicit clean-install opt-in | None |
| Coexistence with foreign AutoConfig | Yes | Refuses installation | Yes |

CSS cannot listen for a second click, synthesize keyboard commands, implement
custom search routing, cancel native focus after navigation/Escape, or create a
JavaScript close snapshot. The editable centre has address-field context-menu
and drag behavior: drag/reorder using the tab's outer edge or a background
tab. Exact custom interaction parity requires privileged browser code.
Crowded/customized toolbars and future Firefox chrome changes may require using
the separate-field layout or Classic. The built-in title bar and taskbar-app
windows are not a promise of compact inline-editor support.

Compatible's capsule effects run on the painted `.tab-stack`, not the outer tab
that Firefox measures for scrolling or uses as the address field's anchor. The
native width transition and completion event remain untouched. This supports
short opening/closing effects without retaining a removed tab. See
[CSS motion and validation](COMPATIBLE-MOTION.md) for measured behavior and limits.

## Alternatives evaluated

* **userChrome.css + standard theme extension (chosen):** keeps native browser
  navigation and security UI, does not consume the AutoConfig slot, and allows
  Adaptive Tab Bar Color to supply page-dependent colours. No companion extension
  is needed; shipping another colour extension would duplicate an existing API
  integration. Third-party browser chrome CSS is not a stable public Mozilla API.
* **Ordinary WebExtension:** `tabs` can query/select/open/close tabs, `search` can
  use engines and `theme` can change colours. A sidebar, popup or new-tab page can
  offer an alternative tab/search UI, but cannot move the native address field
  into native tabs or inject chrome CSS. Content scripts style web documents,
  not Firefox's privileged browser interface. Broad host permissions would add
  no useful capability for this theme.
* **WebExtension Experiments:** can provide privileged API implementations, but
  out-of-tree privileged extensions cannot be signed by AMO for normal release
  Firefox distribution. Requiring Developer Edition/Nightly or changing signing
  restrictions is unsuitable as a default installer method.
* **AutoConfig chaining:** Firefox has one `general.config.filename`. Editing or
  importing a corporate cfg, changing its sandbox preference, or adding a
  competing filename would interfere with its ownership and startup behavior.
  No chaining is attempted. Detection conservatively includes inline/multiline
  pref assignments, dynamic values, orphan cfg files and invalid ownership data.
* **Enterprise policies / native messaging / remote debugging:** policies do not
  expose native-tab DOM relocation; native messaging needs an installed host and
  still cannot grant ordinary extensions chrome access. Keeping an automation
  endpoint open would grant excessive access. WebDriver's chrome access exists
  only in disposable tests, never in the installed theme.
* **Patched binaries, omni.ja, unsigned privileged extensions:** introduce
  maintenance/security changes and break update assumptions. Not used.

## Installation and migration

```
Install.cmd                              # Full Compatible; no installation writes
Install.cmd -InstallationMethod Compatible
Install.cmd -ClassicToolbar               # original Lite layout
Install.cmd -InstallationMethod AutoConfig # explicit legacy loader, clean Firefox only
```

`Auto` selects Compatible. For backwards compatibility an explicit
`-RuntimeDirectory` with `Auto` still requests the legacy isolated runtime. Use
`-InstallationMethod Compatible` to force profile-only installation even when
old tooling passes a runtime path. A Lite package always selects Classic.

Legacy loading refuses foreign AutoConfig and detected enterprise policies. Existing cfg and pref-loader files,
even WhiteSur-owned files, are **never rewritten**: an identical WhiteSur file
may be reused; differing contents cause a refusal recommending Compatible.
Separate-runtime copying excludes cfg/loaders and refuses installations with
`distribution/policies.json`; a destination with policies or custom installation
defaults is also refused. Source installations with custom defaults are not copied.
No installer path edits registry policies or removes existing shared loaders.

Updating an old Full profile with the new default migrates that profile to CSS.
Other profiles and installation-level cfg files remain untouched. Check the
installed marker's `Method:` line with `Check-Installation.cmd`. Diagnostics
report detected AutoConfig, file-based/registry policy-source presence and recommended mode;
they do not claim to evaluate every effective registry/MDM preference lock.

## Primary references

* [Mozilla AutoConfig documentation](https://support.mozilla.org/en-US/kb/customizing-firefox-using-autoconfig)
* [Mozilla policy configuration](https://firefox-admin-docs.mozilla.org/guides/policies-configuration/)
* [MDN CSS anchor positioning](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_anchor_positioning)
* [MDN WebExtension tabs API](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/API/tabs)
* [MDN theme manifest](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/theme)
* [MDN content scripts](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Content_scripts)
* [Mozilla Experimental API implementation and signing restrictions](https://firefox-source-docs.mozilla.org/toolkit/components/extensions/webextensions/basics.html)
* [Mozilla geckodriver system-access flag](https://firefox-source-docs.mozilla.org/testing/geckodriver/Flags.html)
* [Mozilla advanced customization support boundary](https://support.mozilla.org/en-US/kb/firefox-advanced-customization-and-configuration)
