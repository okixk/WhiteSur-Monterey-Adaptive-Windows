from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "chrome" / "windows.css"
START = "/* BEGIN v18-r7 real shadow-scrollbox drag */"
END = "/* END v18-r7 real shadow-scrollbox drag */"

def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)

text = CSS.read_text(encoding="utf-8")

if text.count(START) != 1 or text.count(END) != 1:
    fail("r7 marker block is missing or duplicated")

block = text.split(START, 1)[1].split(END, 1)[0]

checks = {
    "baseline desktop reserve restored": "--whitesur-right-zone: 300px !important",
    "baseline narrow reserve restored": "--whitesur-right-zone: 290px !important",
    "hidden-download desktop reclaim": "--whitesur-right-zone: 224px !important",
    "hidden-download narrow reclaim": "--whitesur-right-zone: 220px !important",
    "real tabs fill toolbar": "inline-size: 100% !important",
    "shadow scrollbox targeted": "#tabbrowser-arrowscrollbox::part(scrollbox)",
    "shadow scrollbox drag enabled": "-moz-window-dragging: drag !important",
    "tabs remain no-drag": ".tabbrowser-tab",
    "new tab remains no-drag": "#tabs-newtab-button",
    "overflow state disables chrome drag": "#tabbrowser-tabs:is([overflow], [movingtab])",
    "private one-pixel alignment retained": "margin-inline-start: 1px !important",
    "Taskbar Tab cleanup retained": ":root[taskbartab] #taskbar-tabs-button",
}

for label, needle in checks.items():
    if needle not in block:
        fail(f"{label}: missing {needle!r}")

if "#TabsToolbar-customization-target > *" in block:
    fail("r7 must not mark every tab-toolbar child as one drag/no-drag rectangle")

live_root_guard = ":root:is([tabsintitlebar], [customtitlebar])"
if live_root_guard not in block:
    fail("drag rules do not match Firefox 154's customtitlebar root")

if ":root[tabsintitlebar]" in block:
    fail("legacy-only tabsintitlebar guard leaves Firefox 154 drag rules inactive")

if "min-width: 96px" in block or "padding-inline-end: 56px" in block:
    fail("old artificial r5/r6 drag-gutter geometry returned")

if not re.search(
    r'#tabbrowser-arrowscrollbox::part\(scrollbox\)\s*\{[^}]*-moz-window-dragging:\s*drag',
    block,
    re.S,
):
    fail("shadow scrollbox is not explicitly draggable")

if not re.search(
    r':root:has\(#downloads-button\[hidden\]\)\s*\{[^}]*224px',
    block,
    re.S,
):
    fail("desktop right-side reclaim is not conditional on hidden Downloads")

print("PASS: r7 removes the old over-reserved v18 desktop gap")
print("PASS: r7 preserves extra room whenever Downloads is actually visible")
print("PASS: r7 restores the real tab browser to 100% of TabsToolbar")
print("PASS: r7 targets the arrowscrollbox shadow scrollbox for native window dragging")
print("PASS: r7 drag rules match Firefox 154 customtitlebar windows")
print("PASS: r7 subtracts tabs/new-tab controls as no-drag")
print("PASS: r7 preserves overflow/reorder behavior")
print("PASS: r7 preserves the private 1px alignment and Taskbar Tab cleanup")
print("Result: 8/8 r7 static groups passed")
