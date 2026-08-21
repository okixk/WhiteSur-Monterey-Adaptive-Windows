from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "chrome" / "windows.css"
START = "/* BEGIN v18-r8 taskbar-action-icon */"
END = "/* END v18-r8 taskbar-action-icon */"

def fail(msg):
    print("FAIL:", msg)
    raise SystemExit(1)

text = CSS.read_text(encoding="utf-8")
if text.count(START) != 1 or text.count(END) != 1:
    fail("r8 marker block missing or duplicated")

block = text.split(START, 1)[1].split(END, 1)[0]

required = [
    ':root:not([taskbartab]) #taskbar-tabs-button:not([hidden])',
    'width: 28px !important',
    'height: 28px !important',
    'background: transparent !important',
    'border: 0 !important',
    'border-radius: 7px !important',
    'list-style-image: url("chrome://browser/skin/taskbar-tabs-add-tab.svg") !important',
    'width: 16px !important',
    ':root[taskbartab] #taskbar-tabs-button',
    'display: none !important',
]

for needle in required:
    if needle not in block:
        fail(f"missing {needle!r}")

if "-moz-window-dragging" in block:
    fail("r8 must not alter the tab/window-drag experiment")

if "#tabbrowser-tabs" in block:
    fail("r8 must not alter the successful full-width tab geometry")

print("PASS: Add tab to taskbar is icon-only")
print("PASS: native Firefox taskbar-tabs-add-tab.svg is used")
print("PASS: normal page action gets a 28px transparent icon hit target")
print("PASS: dedicated Taskbar Tab keeps its redundant action hidden")
print("PASS: r8 does not touch tab width or drag behavior")
print("Result: 5/5 r8 static groups passed")
