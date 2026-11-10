# Full / Lite validation — 2026.11.10-28

The source version was incremented to 2026.11.10-28 for beta.5 packaging; the
native verification below was performed against the otherwise identical
2026.11.10-27 source.

Local Windows 11 testing used Firefox 159.0, geckodriver 0.37.1 and Python 3.13.9.
All browser runs used disposable installations/profiles. No normal-profile
installation, GitHub commit, push or release publication was performed for this
edition split. The previous 50-check Compatible draft is historical evidence;
this record describes the current Full/Lite implementation.

| Suite | Passed |
| --- | ---: |
| Core Windows installer | 49 |
| Compatibility, edition migration, updater settings | 60 |
| Lite with active synthetic AutoConfig and enterprise policy | 65 |
| Full updater, real restart and optional read-only GitHub API | 43 |
| Full tabs and editing | 38 |
| Full motion and native middle-click closing | 27 |
| Native search selector | 18 |
| Windows titlebar hit-testing / real maximize and restore | 19 |
| Centred titles, input and favicons | 18 |
| Full/Lite ZIP installation, including real Firefox launches | 45 |
| Static package groups | 16 |

Native suites ran sequentially. Geometry checks cover narrow/wide windows,
crowded tabs, selected editing, single-tab centring, themes and reduced motion.
Lite retains its synthetic locked AutoConfig preference and policy, verified by
effective values and unchanged file hashes. This tests coexistence with a harmless
lab configuration, not actual Zscaler software or every corporate deployment.

The updater suite downloads local release fixtures through a transport fixture,
then uses the installed production module for ZIP parsing, hashes, staging,
shutdown replacement and rollback. A real subsequent Firefox launch proves the
new JS and CSS load. The separate network probe only reads the GitHub API. It
does not publish a release or auto-install an existing public asset.

It also verifies real Tools-menu checkbox interaction, opt-out, daily throttling,
manual protocol changes, invalid ownership/state preservation, hostile ZIPs,
staged tampering, file-operation rollback, post-download custom CSS edits,
unchanged AutoConfig bytes, queued-update cancellation on Lite migration and
installer recovery after an interrupted rename. See [updater limits and recovery](AUTO-UPDATES.md).

## Visual review

Current screenshots were inspected against the repository's intended Monterey
capsule layout: rounded 32px tab surfaces within the 48px toolbar, smaller
multi-tab capsules, centred native title/favicon pairs, an aligned real address
editor, suggestions below it and available native Windows controls. Full's
ordinary browsing caps are 160px; Lite retains fixed 240px slots to preserve native
scrolling. The lone-tab capsule remains wide. Neither edition reveals on hover.

| State | Capture |
| --- | --- |
| Full compact browsing | [Full](full-browsing.png) |
| Full expanded selected editor | [Full editing](full-editing.png) |
| Lite native inline editor and suggestions | [Lite editing](lite-editing.png) |
| Lite narrow separate-field fallback | [Lite narrow](lite-narrow.png) |

Individual assertions and measurements are retained in
[Full updater](validation/full-updater.json), [Lite](validation/lite-firefox.json)
and [Lite motion](validation/lite-motion.json). Other fresh reports/screenshots
remain in ignored `tests/artifacts/`. Reproduction commands:
[TESTING.md](TESTING.md).

These results do not cover every Firefox/DPI version, extension combination,
custom toolbar, tab-group/drag-detach sequence or enterprise lock. Chrome CSS and
privileged browser internals can change. Power-loss recovery between directory
moves can require rerunning the installer; it is not an atomic filesystem swap.
The GitHub Actions configuration includes the new suites, but no remote CI run
was triggered for these unpublished changes.
