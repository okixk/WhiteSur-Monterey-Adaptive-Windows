# Lite CSS animations — 2026.11.10-27

Lite adds several effects resembling the original AutoConfig theme,
using only profile CSS:

* A 140ms crossfade between the tab title/favicon and the real native address
  field when focusing or leaving the editor; hover never opens it.
* A small 4px entrance slide, 0.97-to-1 scale and fade for new capsules over 160ms.
* A subtle upward slide, scale and fade while Firefox closes a tab.
* Short hover and selection colour/shadow transitions.

`prefers-reduced-motion: reduce` removes these decorative transitions. A fading
editor stops intercepting clicks as soon as it is dismissed. Rapid reversals
follow the latest focus state without a delayed invisible overlay.

## Why widths remain stable

The effects animate the painted `.tab-stack` or opacity, leaving the outer tab
and address-field anchor unchanged. Ordinary slots remain 240px. The previous
native scrolling regression came from selection/focus-dependent sizing; these
effects do not reintroduce that behavior.

Firefox retains ownership of its opening/closing width transition and the
completion event that removes a tab. The theme does not delay native removal,
patch browser methods, inject a window script, or install an AutoConfig loader.
Existing AutoConfig and enterprise policies remain untouched.

The CSS close effect ends when the real tab is removed. A detached closing
snapshot that outlives removal, animated expansion of only the edited tab, and
coordinated movement of surviving tabs into a centred single-tab capsule remain
features of the Full implementation. Pinned tabs use their
native motion and are excluded from the decorative capsule slide/scale.

## Native validation

Tested in real Firefox 159.0 on Windows 11, with geckodriver 0.37.1. The suite
still loads its harmless synthetic `zscaler.cfg` and enterprise policy, checks
their effective values, and verifies their bytes stay unchanged.

**65 Lite checks passed**, including **14 motion checks**. The new
checks sample real animation frames, confirming intermediate opacity and
translation, fixed tab/editor widths during reveal, complete native tab removal,
rapid focus reversal, 800/1384px opening/closing and immediate reduced-motion
behavior. Existing checks cover crowded strips, security popups, normal/private
windows, fullscreen, customization, built-in themes and policy locks.

Run the full suite:

```powershell
python tests/test_compatible_firefox.py --firefox "C:\clean-firefox\firefox.exe" --geckodriver "C:\tools\geckodriver.exe"
```

Generated frame samples are written to
`tests/artifacts/compatible/motion/motion-report.json`, and final-state browser
screenshots to that directory. A committed copy of the 14 animation assertions
and their measurements is in [compatible-motion.json](validation/compatible-motion.json).
The existing [beta.5 validation record](VALIDATION-beta.5.md) describes the
preceding 50-check baseline; it is preserved as historical evidence.

The test sampler uses native UI methods and read-only frame measurements in
WebDriver's test-only chrome context. It does not inject theme styles or a
production animation script. Your normal profile is updated only when you run
`Install.cmd` with Firefox closed.
