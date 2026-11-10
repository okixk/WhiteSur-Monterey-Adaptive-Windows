# Full release updates

Full checks published releases from the fixed public repository
[`okixk/WhiteSur-Monterey-Adaptive-Windows`](https://github.com/okixk/WhiteSur-Monterey-Adaptive-Windows/releases)
30 seconds after startup and at most once every 24 hours. Prereleases are included
by default during this beta project. Lite contains no updater runtime.

Use **Tools → WhiteSur Updates** (Alt+T on Windows) for status, check now and the
automatic-update toggle. `Install.cmd -DisableAutoUpdate` initially disables it.
Manual reinstalls preserve an existing opt-out/channel choice. A forced check
can download while disabled, but the update stays paused until enabled.
No browser restart is forced.

## Download, stage, restart

1. Read GitHub's non-draft releases and select a compatible Full asset.
2. Download over HTTPS. Verify the required GitHub SHA-256 asset digest, size,
   raw ZIP paths, manifest and every managed theme file. Compare date/build
   versions; equal or older versions never apply.
3. Stage under the profile's `.whitesur-updates` directory. The live theme is
   unchanged for the rest of the session.
4. During normal Firefox shutdown, revalidate the staged manifest/files, preserve
   the current `customChrome.css`, retain the old theme as a rollback copy and
   replace `chrome`. The next start loads the new CSS and JavaScript. All I/O
   finishes before the profile lock is released.

This uses `profileChangeTeardown`, before the shutdown barrier that closes
`IOUtils`. A crash delays application until a normal quit. Closing one of several
windows does not update the theme mid-session.

## Scope and trust

Only managed `chrome` CSS, artwork and Full's privileged UI JavaScript are updated.
Downloaded installers are never executed. The updater never edits AutoConfig,
policies, certificates, proxy/security preferences, Firefox binaries, extensions
or ordinary profile databases. Its settings/cache are owned profile files.
Other edits to managed theme files are replaced; put overrides in `customChrome.css`.

Automatic updates trust the fixed repository's release publisher, including for
privileged JavaScript. GitHub's digest and file hashes detect corruption; they
are not independent author signatures. No GitHub token, website data, browsing
history or credentials are sent. Requests contact GitHub and its release-asset
hosts. Network failures leave the current theme usable.

Limits: 32MB downloaded ZIP, 2MB metadata, 8MB per theme file, 64MB expanded theme,
30-second request budget. Validation rejects traversal, absolute paths, Windows
device/ADS aliases, raw backslashes, case collisions, symlinks, unexpected roots,
missing/unmanifested chrome files and bad hashes. Staged content is checked again
before replacement. Unknown ownership/state and filesystem links are refused and
preserved. Different manifest schemas/loader protocols or a newer required
Firefox report manual installation instead of editing installation configuration.

## Settings and recovery

The profile's `.whitesur-updater.json` contains:

```json
{
  "schema": 1,
  "owner": "WhiteSur-Monterey-Adaptive-Windows",
  "edition": "Full",
  "enabled": true,
  "allowPrerelease": true
}
```

Use the Tools menu for `enabled`. To restrict checks to stable releases, close
Firefox and set `allowPrerelease` to `false`. Preserve the ownership/schema fields.
The updater's `state.json` records status, last check, pending version and a bounded
error message. It is diagnostic state, not a supported configuration API.

An ordinary replacement failure restores the old theme and permits retry. A
transaction journal records the owned backup before the two directory moves.
An abrupt power interruption between moves may leave `chrome` absent; rerun the
installer with Firefox closed to recover that backup before reinstalling. Repair
validates ownership, backup paths/marker and rejects links. The pair of directory
moves is not a single atomic Windows operation.

Rollback folders (`.whitesur-updates/rollback-<UUID>`) and staging/cache files,
including rejected downloads, are retained for recovery and consume disk space.
With Firefox closed and automatic updates disabled, a known-good owned rollback
can be copied back to `chrome` after backing up the current theme. The installer
is the preferred recovery route. Uninstall/Lite migration cancel pending updates
and remove Full settings/runtime; recovery data and shared loaders stay untouched.

No compatible release has been published as part of this local work. Older public
archives without the manifest cannot auto-apply; older/equal releases are quietly
ignored after reading their bounded VERSION file. A compatible future Full release
is required. Real restart behavior was tested with local future-version fixtures,
not a production upload.

## Release contract and tests

The builder emits Full/Lite ZIPs with root `release-manifest.json` and a separate
`SHA256SUMS.txt`. Updates require schema 1, Full edition, loader protocol 1,
matching tag/VERSION and file hashes. GitHub supplies the uploaded asset's digest
in its [release asset API](https://docs.github.com/en/rest/releases/assets).
Loader changes require manual installation and a protocol bump; automatic
theme-only releases must remain compatible with the installed loader.

`tests/test_full_updater_firefox.py` exercises the installed module through the
real loader, ZIP parsing/hashing/staging, and actual Firefox quit/relaunch. A
transport fixture supplies release metadata/download bytes. Optional `--network`
makes a separate read-only request to the real API. Checks cover malicious ZIPs,
staged tampering, rollback, current custom CSS, throttling, opt-out, protocol
changes and Full-to-Lite cancellation. See [TESTING.md](TESTING.md).
