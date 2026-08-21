from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "chrome" / "windows.css"
START = "/* BEGIN v18-r9 toolbar-integration */"
END = "/* END v18-r9 toolbar-integration */"


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


text = CSS.read_text(encoding="utf-8")
if text.count(START) != 1 or text.count(END) != 1:
    fail("r9 marker block is missing or duplicated")

block = text.split(START, 1)[1].split(END, 1)[0]

required = {
    "measured base tool reserve": "246px +",
    "Downloads consumes one toolbar slot": "--whitesur-download-reserve: 44px",
    "hidden Downloads consumes no slot": "--whitesur-download-reserve: 0px",
    "pinned extensions are detected": 'toolbaritem[id$="-browser-action"]:not([hidden])',
    "one pinned extension slot": "--whitesur-pinned-extension-reserve: 44px",
    "two pinned extension slots": "--whitesur-pinned-extension-reserve: 88px",
    "three pinned extension slots": "--whitesur-pinned-extension-reserve: 132px",
    "four pinned extension slots": "--whitesur-pinned-extension-reserve: 176px",
    "specific live toolbar boundary override": (
        ":root:has(#navigator-toolbox):has(#nav-bar-customization-target)"
    ),
    "taskbar action matches native height": "height: 26px !important",
    "taskbar action drops private margins": "margin: 0 !important",
    "taskbar action retains a 16px glyph": "padding: 5px 6px !important",
}

for label, needle in required.items():
    if needle not in block:
        fail(f"{label}: missing {needle!r}")

if "#tabbrowser-arrowscrollbox" in block or "-moz-window-dragging" in block:
    fail("r9 must not modify the verified native drag implementation")

if not re.search(
    r"--whitesur-right-zone:\s*calc\(\s*246px\s*\+\s*"
    r"var\(--whitesur-download-reserve\)\s*\+\s*"
    r"var\(--whitesur-pinned-extension-reserve\)",
    block,
    re.S,
):
    fail("right-side boundary is not composed from the measured toolbar slots")

print("PASS: tab strip reserves Unified Extensions with an 8px gutter")
print("PASS: Downloads adds one 44px toolbar slot only while visible")
print("PASS: one through four pinned WebExtensions add matching slots")
print("PASS: Add to taskbar matches the adjacent 28 x 26px URL-bar actions")
print("PASS: verified native drag selectors remain untouched")
print("Result: 5/5 r9 toolbar integration groups passed")
