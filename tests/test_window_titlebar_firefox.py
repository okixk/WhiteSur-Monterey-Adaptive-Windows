"""Native Windows hit-testing and double-click maximize in an installed Firefox."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import tempfile
import time

from test_editable_tabs_firefox import Firefox, ROOT, install, settle


class NativeWindow:
    def __init__(self, browser):
        self.api = ctypes.WinDLL("user32", use_last_error=True)
        self.api.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        self.api.IsWindowVisible.argtypes = [wintypes.HWND]
        self.api.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        self.api.SendMessageW.restype = ctypes.c_ssize_t
        self.api.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.api.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                         ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.api.WindowFromPoint.argtypes = [wintypes.POINT]
        self.api.WindowFromPoint.restype = wintypes.HWND
        self.api.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        self.api.mouse_event.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_size_t]
        pid = browser.js("return Services.appinfo.processID;")
        handles = []
        callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @callback_type
        def visit(hwnd, _):
            actual = wintypes.DWORD()
            self.api.GetWindowThreadProcessId(hwnd, ctypes.byref(actual))
            if actual.value == pid and self.api.IsWindowVisible(hwnd):
                handles.append(hwnd)
            return True

        self.api.EnumWindows.argtypes = [callback_type, wintypes.LPARAM]
        self.api.EnumWindows(visit, 0)
        assert handles, "Firefox has no visible native window"
        self.hwnd = handles[0]
        # SetForegroundWindow can be denied to a background test process.
        # Keep this disposable window above other apps while using real input.
        self.api.SetWindowPos(self.hwnd, wintypes.HWND(-1), 0, 0, 0, 0, 0x0043)

    def hit(self, point):
        x, y = round(point["screenX"]), round(point["screenY"])
        return self.api.SendMessageW(self.hwnd, 0x0084, 0, (y << 16) | (x & 0xffff))

    def double_click(self, point):
        self.api.SetForegroundWindow(self.hwnd)
        time.sleep(.15)
        self.api.SetCursorPos(round(point["screenX"]), round(point["screenY"]))
        assert self.api.WindowFromPoint(wintypes.POINT(round(point["screenX"]),round(point["screenY"]))) == self.hwnd, \
            "Another window covers the test click; do not send input to it"
        for _ in range(2):
            self.api.mouse_event(0x0002, 0, 0, 0, 0)
            self.api.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(.06)


POINTS = """
const strip=document.getElementById('TabsToolbar').getBoundingClientRect();
const button=[...document.querySelectorAll('#tabs-newtab-button,#new-tab-button')]
  .find(e=>e.getBoundingClientRect().width&&getComputedStyle(e).visibility==='visible');
const last=button.getBoundingClientRect().right;
const x=(last+strip.right)/2, y=strip.y+strip.height/2;
function point(x,y){
  const target=document.elementFromPoint(x,y), ancestors=[];
  for(let e=target;e;e=e.parentElement)ancestors.push({id:e.id||e.localName,
    drag:getComputedStyle(e).getPropertyValue('-moz-window-dragging')});
  return {x,y,screenX:(mozInnerScreenX+x)*devicePixelRatio,screenY:(mozInnerScreenY+y)*devicePixelRatio,
    ancestors};
}
return {tail:point(x,y),top:point((strip.left+strip.right)/2,strip.top+4),
  plus:point(button.getBoundingClientRect().x+button.getBoundingClientRect().width/2,y),
  tab:point(gBrowser.selectedTab.getBoundingClientRect().x+50,y),
  input:point(gURLBar.inputField.getBoundingClientRect().x+30,y)};
"""


def run(browser, artifacts):
    results = []

    def check(name, condition, details=None):
        results.append({"name": name, "pass": bool(condition), "details": details})
        print(f"{'PASS' if condition else 'FAIL'}: {name}", flush=True)
        assert condition, f"{name}: {details}"

    try:
        browser.call("POST", "window/rect", {"x": 60, "y": 60, "width": 921, "height": 648})
        browser.js("TabSearch.edit();")
        browser.text("about:robots")
        browser.text("\ue007")
        browser.until(lambda: browser.js("return gBrowser.currentURI.spec==='about:robots';"))
        native = NativeWindow(browser)
        for count, editing in ((1,False),(1,True),(14,False),(14,True)):
            browser.js("while(gBrowser.tabs.length<arguments[0])gBrowser.addTrustedTab('about:robots',{skipAnimation:true});",count)
            browser.js("if(arguments[0])TabSearch.edit();else {TabSearch.hide();gBrowser.selectedBrowser.focus();}", editing)
            settle(browser)
            points = browser.js(POINTS)
            hits = {name: native.hit(point) for name, point in points.items()}
            check(f"empty middle and upper strip use native caption hit-testing ({count} tabs, editing={editing})",
                  hits["tail"] == 2 and hits["top"] in (2,12), {"hits": hits, "points": points})
            check("tabs and + remain ordinary clickable controls", hits["tab"] == 1 and hits["plus"] == 1, hits)
            if editing:
                check("the search field remains an editable client control", hits["input"] == 1, hits)
            count = browser.js("return gBrowser.tabs.length;")
            native.double_click(points["tail"])
            browser.until(lambda: browser.js("return window.windowState===window.STATE_MAXIMIZED;"))
            check("real mouse double-click maximizes without opening a tab", browser.js("return gBrowser.tabs.length;") == count)
            settle(browser)
            points = browser.js(POINTS)
            native.double_click(points["top"])
            browser.until(lambda: browser.js("return window.windowState===window.STATE_NORMAL;"))
            check("real mouse double-click on the upper strip restores the window", True)
        browser.js("TabSearch.hide();gBrowser.removeTabs([...gBrowser.tabs].slice(1),{animate:false,skipPermitUnload:true});"
                   "gBrowser.tabContainer.setAttribute('movingtab','true');")
        settle(browser)
        try:
            point = browser.js(POINTS)["tail"]
            hit = native.hit(point)
            check("tab reordering keeps the strip out of native window dragging", hit == 1, {"hit":hit,"point":point})
        finally:
            browser.js("gBrowser.tabContainer.removeAttribute('movingtab');")
    finally:
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "window-titlebar-report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firefox", type=Path, required=True)
    parser.add_argument("--geckodriver", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "tests/artifacts/window-titlebar")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="whitesur-titlebar-") as directory:
        workspace = Path(directory)
        profile = workspace / "profile"
        profile.mkdir()
        binary = install(profile, args.firefox.resolve(), workspace / "runtime", workspace / "shortcuts")
        browser = Firefox(args.geckodriver.resolve(), binary, profile)
        try:
            results = run(browser, args.artifacts.resolve())
            print(f"Result: {len(results)} native titlebar checks passed", flush=True)
        finally:
            browser.close()
            time.sleep(.3)
