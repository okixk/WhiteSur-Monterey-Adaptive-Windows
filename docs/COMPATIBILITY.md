# Full and Lite

Full provides privileged click editing, custom motion and release updates through
AutoConfig. Lite supplies the Monterey appearance through profile CSS, including
when Firefox already uses `zscaler.cfg` or another AutoConfig. Neither edition
overwrites existing cfg files or changes enterprise/security configurations.

| Feature | Full | Lite |
| --- | --- | --- |
| Adaptive colours, rounded surfaces, native Windows buttons | Yes | Yes |
| Centred native titles and favicons | Yes | Yes, horizontal tabs |
| Centred single-tab capsule | Up to 580px | Up to 560px where space permits |
| Multiple ordinary tabs | 88–160px while browsing | Stable 240px editing slots |
| Edit selected tab | Left click or Ctrl+L / Alt+D / F6 | Ctrl+L / Alt+D / F6 / new-tab focus |
| Hover opens editor | No | No |
| Middle-click closes selected browsing tab | Yes | Native handling |
| Middle-click inside focused address field closes tab | Yes; release outside cancels | No; native input behavior |
| Native suggestions, site information, engine selector | Yes | Yes |
| Escape / navigate / click page restores title | Yes | Native focus behavior; Escape may retain editor |
| Editor motion | Coordinated expansion and fade | 140ms crossfade at fixed width |
| Tab opening/closing | Custom entrances and detached close snapshot | CSS slide/scale/fade during native lifecycle |
| Reduced motion | Cancels custom motion | Disables decorative CSS motion |
| Narrow window / pinned selection | Field fits available space | Separate address toolbar and tab row |
| Vertical tabs | Native fallback | Native sidebar and address field |
| `g` / `q` search prefixes | Built in | Configure native bookmark/search keywords |
| Automatic release updates | Optional, enabled by default | None |
| Firefox installation writes | Initial loader setup only | None |
| Foreign AutoConfig / detected enterprise management | Refuses, recommends Lite | Supported; effective policy locks remain authoritative |

The smaller browsing widths preserve Full's expanded editor and lone-tab width.
Lite keeps stable slots because selection/focus-dependent sizing breaks native
tab-strip scrolling. Its focused address field has input context menus and drag
behavior; use a background tab or tab edge to reorder. CSS cannot dispatch mouse
events, implement custom search routing/Escape-to-title, or retain a removed tab
for a detached closing snapshot.

Lite uses CSS anchors to align the real field with the selected horizontal tab.
At widths up to 980 CSS pixels, without anchor support, or with a pinned selection,
it uses a separate field. Feature detection determines this fallback; the manifest
minimum is not a promise of anchor support. Locked stylesheet loading cannot be
bypassed. Browser chrome CSS is not a stable public API.

## Implementation audit

The installer selects profiles from `installs.ini` / `profiles.ini`, backs up
unrelated chrome folders, preserves `customChrome.css` and manages a delimited
`user.js` block. Both editions import `Monterey/theme-adaptive.css` and
`windows.css`: controls, tabs, address field, popups, sidebar, dialogs, icons and
light/dark variables. Linux CSD/title-button files are intentionally not used.
`userContent.css` does not import website restyling modules.

Full imports `tab-search.css` and loads `tab-search.uc.js` through `whitesur.cfg`
only in marked profiles. It observes tab/focus/drag/resize events, calculates
geometry, wraps selected native tab/scroll methods, and uses the Web Animations
API. Rules activate behind its `tabsearch-ready` marker. Its updater is a
separate profile module; see [AUTO-UPDATES.md](AUTO-UPDATES.md).

Lite removes both tab-search files and the updater, disables the script's managed
preference and imports `lite.css` before `customChrome.css`. The native field stays
in its original DOM. Opacity and pointer-event rules control reveal; animations
affect the painted `.tab-stack`, preserving native outer-tab sizing/removal.
See [COMPATIBLE-MOTION.md](COMPATIBLE-MOTION.md).

## Install and migrate

```powershell
.\Install.cmd                         # Full, guarded AutoConfig
.\Install-Lite.cmd                    # Lite, profile CSS
.\Install.cmd -Edition Lite           # same Lite edition
.\Install.cmd -ClassicToolbar         # older classic CSS layout
```

`Auto` resolves to the selected edition. `-InstallationMethod AutoConfig` requests
Full behavior; `Compatible` selects Lite. Lite archives force CSS-only mode even
with conflicting Full/AutoConfig arguments. Full archives include the Lite
launcher. `-ClassicToolbar` / `-InstallationMethod Classic` retain the old layout.

Full requires Firefox 158+ and an available AutoConfig slot. Detection includes
inline/multiline/dynamic config preferences, orphan cfg files, differing WhiteSur
files and invalid ownership markers. Detected file/registry enterprise policy
sources cause a refusal recommending Lite. Matching completed owned loader files,
including installation metadata, are reused read-only. They are never rewritten.
New loader setup may elevate the loader helper only. `-Force` bypasses only the
running-Firefox check, never these guards.

Explicit `-RuntimeDirectory` retains the separate-runtime option. Copying rejects
managed/custom-default installations rather than stripping their configuration.
No config chaining is attempted. Switching to Lite removes privileged profile
files/settings and cancels staged updates; shared loader files remain untouched
for other profiles. Diagnostics report edition/method and detected configuration
sources, not every effective MDM or preference lock.

## Alternatives evaluated

- **Profile CSS plus a standard theme extension:** chosen for Lite. Native theme
  variables allow Adaptive Tab Bar Color to supply page colours. No companion
  extension or broad website permissions are necessary.
- **Ordinary WebExtensions:** tabs/search/theme APIs can offer a sidebar, popup
  or new-tab interface. Content scripts cannot inject into Firefox's privileged
  UI or move its native field. See [Mozilla's content-script restrictions](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Content_scripts).
- **WebExtension Experiments:** privileged APIs require a privileged extension;
  ordinary release distribution cannot assume this privilege. No signing
  restriction is weakened. See [Mozilla's implementation documentation](https://firefox-source-docs.mozilla.org/toolkit/components/extensions/webextensions/basics.html).
- **AutoConfig chaining:** competing `general.config.filename` values or edits
  to a corporate cfg interfere with ownership. Full refuses; Lite avoids the
  slot. See [Mozilla AutoConfig configuration](https://support.mozilla.org/en-US/kb/customizing-firefox-using-autoconfig).
- **Policies, native messaging, debugging endpoints, patched binaries:** these
  do not supply the required native UI through an ordinary extension. Persistent
  debugging access, binary patches and unsigned privileged extensions are not
  used. WebDriver system access exists only in disposable tests.

Current local verification uses Firefox 159.0 on Windows 11 and geckodriver
0.37.1. See [TESTING.md](TESTING.md) for coverage and limitations.
