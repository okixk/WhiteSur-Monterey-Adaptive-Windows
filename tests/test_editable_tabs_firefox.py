"""Native Windows Firefox integration test; no Selenium dependency or UI injection.

Installs the repository into a disposable profile/runtime using the real
PowerShell installer, then exercises the AutoConfig-loaded customization.
"""
from __future__ import annotations

import argparse
import base64
import ctypes
import json
import os
import shutil
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class Firefox:
    def __init__(self, driver: Path, binary: Path, profile: Path):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        self.base = f"http://127.0.0.1:{port}"
        self.session = ""
        self.browser_handle = None
        self.process = subprocess.Popen(
            [str(driver), "--port", str(port), "--allow-system-access", "--log", "error"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        try:
            self.until(lambda: self.request("GET", "/status"), timeout=10)
            capabilities = self.request("POST", "/session", {"capabilities": {"alwaysMatch": {
                "browserName": "firefox", "moz:firefoxOptions": {
                    "binary": str(binary), "args": ["-no-remote", "-profile", str(profile)],
                    "prefs": {"browser.shell.checkDefaultBrowser": False,
                              "browser.tabs.warnOnClose": False,
                              "browser.startup.homepage": "about:blank",
                              "app.update.auto": False},
                },
            }}})
            self.session = capabilities["sessionId"]
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            self.browser_handle = kernel.OpenProcess(
                0x00100000, False, capabilities["capabilities"]["moz:processID"])
            self.call("POST", "moz/context", {"context": "chrome"})
        except Exception:
            self.close()
            raise

    def request(self, method, path, body=None):
        encoded = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=encoded, method=method,
                                         headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return json.load(response)["value"]
        except urllib.error.HTTPError as error:
            raise RuntimeError(error.read().decode()) from error

    def call(self, method, path, body=None):
        return self.request(method, f"/session/{self.session}/{path}".rstrip("/"), body)

    def js(self, script, *args, asynchronous=False):
        endpoint = "execute/async" if asynchronous else "execute/sync"
        return self.call("POST", endpoint, {"script": script, "args": list(args)})

    def until(self, function, timeout=10):
        deadline = time.monotonic() + timeout
        last_error = None
        while time.monotonic() < deadline:
            try:
                value = function()
                if value:
                    return value
            except (urllib.error.URLError, OSError) as error:
                last_error = error
            time.sleep(0.1)
        raise TimeoutError(f"Timed out waiting for Firefox: {last_error}")

    def text(self, text):
        element = self.js("return gURLBar.inputField;")
        key = element["element-6066-11e4-a52e-4f735466cecf"]
        self.call("POST", f"element/{key}/value", {"text": text})

    def chord(self, key):
        self.call("POST", "actions", {"actions": [{"type": "key", "id": "keyboard", "actions": [
            {"type": "keyDown", "value": "\ue009"}, {"type": "keyDown", "value": key},
            {"type": "keyUp", "value": key}, {"type": "keyUp", "value": "\ue009"},
        ]}]})

    def close(self):
        if self.session:
            try:
                self.call("DELETE", "")
            except (RuntimeError, OSError):
                pass
            self.session = ""
        self.process.terminate()
        self.process.wait(timeout=15)
        if self.browser_handle:
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            try:
                if kernel.WaitForSingleObject(self.browser_handle, 15000) != 0:
                    raise TimeoutError("Firefox did not exit after deleting the WebDriver session")
            finally:
                kernel.CloseHandle(self.browser_handle)
                self.browser_handle = None


def install(profile, source, runtime, shortcuts):
    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(ROOT / "Install-WhiteSur-Monterey-Adaptive.ps1"),
        "-ProfilePath", str(profile), "-FirefoxPath", str(source),
        "-ShortcutDirectory", str(shortcuts), "-Force",
    ]
    if runtime is not None:
        command.extend(["-RuntimeDirectory", str(runtime)])
    completed = subprocess.run(command, capture_output=True, text=True, errors="replace")
    if completed.returncode:
        raise RuntimeError(completed.stdout + completed.stderr)
    state = profile / ".whitesur-editable-tabs.json"
    if not state.is_file():
        raise RuntimeError("Editable runtime was not installed:\n" + completed.stdout + completed.stderr)
    return Path(json.loads(state.read_text(encoding="utf-8-sig"))["Executable"])


def run(browser, artifacts):
    results = []

    def check(name, condition, details=None):
        results.append({"name": name, "pass": bool(condition), "details": details})
        print(f"{'PASS' if condition else 'FAIL'}: {name}", flush=True)
        if not condition:
            raise AssertionError(f"{name}: {details}")

    try:
        check("AutoConfig starts the packaged script", browser.js("return !!window.TabSearch;"))
        check("the selected field remains compact", browser.js(
            "return gBrowser.selectedTab.getBoundingClientRect().width<=301;"))
        browser.call("POST", "window/rect", {"width": 1384, "height": 850})
        browser.js("gBrowser.addTrustedTab('about:blank',{skipAnimation:true});"
                   "gBrowser.addTrustedTab('about:blank',{skipAnimation:true});"
                   "gBrowser.selectedTab=gBrowser.tabs[1];TabSearch.edit();")
        check("selected native input is focused", browser.js(
            "return document.activeElement===gURLBar.inputField;"))
        browser.text("about:robots")
        browser.text("\ue007")
        browser.until(lambda: browser.js("return gBrowser.currentURI.spec==='about:robots';"))
        check("native URL navigation keeps the editor visible", browser.js(
            "return document.documentElement.hasAttribute('tabsearch-editing');"))

        browser.js("window.whiteSurOriginalOpen=openTrustedLinkIn;"
                   "window.whiteSurRequests=[];window.openTrustedLinkIn=(url)=>whiteSurRequests.push(url);")
        try:
            for prefix, expected in (("g", "https://www.google.com/search?q=compact%20tabs"),
                                     ("q", "https://www.qwant.com/?q=compact%20tabs&t=web")):
                browser.js("TabSearch.edit();")
                browser.text(prefix + " compact tabs")
                browser.text("\ue007")
                requested = browser.js("return whiteSurRequests.at(-1);")
                check(f"{prefix} search routes to its engine", requested == expected, requested)
        finally:
            browser.js("window.openTrustedLinkIn=whiteSurOriginalOpen;delete window.whiteSurOriginalOpen;")

        browser.js("TabSearch.edit();")
        browser.text("cancel this draft")
        browser.text("\ue00c")
        check("Escape restores the address and preserves the field", browser.js(
            "return gURLBar.value!=='cancel this draft'&&document.documentElement.hasAttribute('tabsearch-editing')"
            "&&document.activeElement!==gURLBar.inputField;"))

        saved_colors = browser.js("return ['--lwt-accent-color','--toolbar-color','--toolbar-text-color']"
                                 ".map(k=>[k,document.documentElement.style.getPropertyValue(k)]);")
        try:
            for accent, foreground in (("rgb(27, 64, 97)", "rgb(255, 255, 255)"),
                                       ("rgb(240, 223, 190)", "rgb(17, 17, 17)")):
                colors = browser.js("const r=document.documentElement;"
                    "r.style.setProperty('--lwt-accent-color',arguments[0],'important');"
                    "r.style.setProperty('--toolbar-color',arguments[1],'important');"
                    "r.style.setProperty('--toolbar-text-color',arguments[1],'important');"
                    "return {header:getComputedStyle(document.getElementById('navigator-toolbox')).backgroundColor,"
                    "text:getComputedStyle(gURLBar.inputField).color};", accent, foreground)
                check("adaptive theme variables reach the header and URL text",
                      colors == {"header": accent, "text": foreground}, colors)
        finally:
            browser.js("for(const [k,v] of arguments[0]){if(v)document.documentElement.style.setProperty(k,v);"
                       "else document.documentElement.style.removeProperty(k);}", saved_colors)

        for private in (False, True):
            browser.js("window.whiteSurExtra=OpenBrowserWindow({private:arguments[0]});", private)
            browser.until(lambda: browser.js("return !!window.whiteSurExtra?.TabSearch;"))
            correct_privacy = browser.js(
                "return PrivateBrowsingUtils.isWindowPrivate(whiteSurExtra)===arguments[0];", private)
            browser.js("whiteSurExtra.close();")
            browser.until(lambda: browser.js("return whiteSurExtra.closed&&!whiteSurExtra.TabSearch;"))
            check(f"new window loads and cleans up (private={private})", correct_privacy)
            browser.js("delete window.whiteSurExtra;")

        sizes = {}
        for width, count in ((1384, 4), (1368, 14), (800, 8), (600, 6)):
            browser.call("POST", "window/rect", {"width": width, "height": 800})
            browser.js("gBrowser.selectedTab=gBrowser.tabs[0];"
                "gBrowser.removeTabs([...gBrowser.tabs].slice(1),{animate:false,skipPermitUnload:true});"
                "for(let i=1;i<arguments[0];i++)gBrowser.addTrustedTab('about:blank',{skipAnimation:true});"
                "gBrowser.selectedTab=gBrowser.tabs[0];gBrowser.selectedBrowser.focus();", count)
            geometry = browser.js("const done=arguments[arguments.length-1];(async()=>{"
                "const frame=()=>new Promise(requestAnimationFrame);let maxError=0,total=null,drift=0;"
                "for(let i=0;i<arguments[0];i++){gBrowser.selectedTab=gBrowser.tabs[i%gBrowser.tabs.length];"
                "await frame();await frame();let t=gBrowser.selectedTab,r=t.getBoundingClientRect(),"
                "c=t.querySelector('.tab-content').getBoundingClientRect(),"
                "e=gURLBar.querySelector('.urlbar-input-container').getBoundingClientRect();"
                "maxError=Math.max(maxError,Math.abs(e.left-Math.max(r.left+4,c.left)));"
                "const sum=[...gBrowser.tabs].reduce((s,t)=>s+t.getBoundingClientRect().width,0);"
                "if(total===null)total=sum;drift=Math.max(drift,Math.abs(sum-total));}"
                "done({maxError,drift});})().catch(e=>done({error:String(e)}));", count * 2, asynchronous=True)
            check(f"selection stays aligned at {width}px with {count} tabs",
                  not geometry.get("error") and geometry["maxError"] < 2 and geometry["drift"] < 1, geometry)
            sizes[count] = browser.js("return {tab:gBrowser.selectedTab.getBoundingClientRect().width,"
                "field:gURLBar.querySelector('.urlbar-input-container').getBoundingClientRect().width};")

        check("the address gets more room with few tabs and shrinks in a crowded strip",
              280 < sizes[4]["tab"] <= 301 and 259 <= sizes[14]["tab"] < 280
              and sizes[4]["field"] > sizes[14]["field"] + 20, sizes)

        browser.call("POST", "window/rect", {"width": 1384, "height": 800})
        late_scroll = browser.js("const done=arguments[arguments.length-1];"
            "while(gBrowser.tabs.length<14)gBrowser.addTrustedTab('about:blank',{skipAnimation:true});"
            "const box=gBrowser.tabContainer.arrowScrollbox;"
            "box.scrollbox.scrollTo({left:0,behavior:'instant'});"
            "gBrowser.selectedTab=gBrowser.tabs[0];gBrowser.selectedTab=gBrowser.tabs.at(-1);"
            "box.ensureElementIsVisible(gBrowser.selectedTab,true);"
            "requestAnimationFrame(()=>{const t=gBrowser.selectedTab,r=t.getBoundingClientRect(),"
            "c=t.querySelector('.tab-content').getBoundingClientRect(),"
            "e=gURLBar.querySelector('.urlbar-input-container').getBoundingClientRect();"
            "done({error:Math.abs(e.left-Math.max(r.left+4,c.left)),scroll:box.scrollPosition});});",
            asynchronous=True)
        check("the editor follows a native visibility scroll queued after selection", late_scroll["error"] < 2, late_scroll)

        for width in (1384, 800):
            browser.call("POST", "window/rect", {"width": width, "height": 800})
            browser.js("while(gBrowser.tabs.length<8)gBrowser.addTrustedTab('about:newtab',{skipAnimation:true});"
                       "gBrowser.selectedBrowser.focus();")
            maximum = 0
            immediate_maximum = 0
            outliers = []
            for key in ("t", "w", "\ue004", "\ue00f", "w", "t") * 4:
                browser.chord(key)
                # Observe the next frame, when native selection/scroll work is
                # presented. An immediate WebDriver task can run before the
                # already-scheduled layout frame, which has not painted yet.
                sample = browser.js("const done=arguments[arguments.length-1];"
                    "const measure=()=>{let t=gBrowser.selectedTab,r=t.getBoundingClientRect(),"
                    "c=t.querySelector('.tab-content').getBoundingClientRect(),"
                    "e=gURLBar.querySelector('.urlbar-input-container').getBoundingClientRect();"
                    "return {error:Math.abs(e.left-Math.max(r.left+4,c.left)),field:e.left,"
                    "expected:Math.max(r.left+4,c.left),count:gBrowser.tabs.length,"
                    "selected:[...gBrowser.tabs].indexOf(t),"
                    "scroll:gBrowser.tabContainer.arrowScrollbox.scrollPosition,"
                    "nativeFramePending:gBrowser.tabContainer.arrowScrollbox._ensureElementIsVisibleAnimationFrame};};"
                    "const immediate=measure();requestAnimationFrame(()=>done({immediate,frame:measure()}));",
                    asynchronous=True)
                maximum = max(maximum, sample["frame"]["error"])
                immediate_maximum = max(immediate_maximum, sample["immediate"]["error"])
                if sample["frame"]["error"] >= 2:
                    outliers.append({"key": key, **sample})
            check(f"rapid Ctrl+W/T/Tab/PageDown stays aligned at {width}px", maximum < 2,
                  {"frameMaxError": maximum, "immediateMaxError": immediate_maximum, "outliers": outliers})

        browser.call("POST", "window/rect", {"width": 1384, "height": 850})
        browser.js("gBrowser.selectedTab=gBrowser.tabs[0];gBrowser.pinTab(gBrowser.selectedTab);TabSearch.edit();")
        check("pinned editor stays below its icon", browser.js(
            "return gURLBar.getBoundingClientRect().top>=gBrowser.selectedTab.getBoundingClientRect().bottom;"))
        browser.js("gBrowser.unpinTab(gBrowser.selectedTab);gBrowser.selectedBrowser.focus();")
        browser.js("Services.prefs.setBoolPref('sidebar.verticalTabs',true);")
        check("vertical tabs restore the standard toolbar", browser.js(
            "return !window.TabSearch&&!document.documentElement.hasAttribute('tabsearch-ready');"))
        browser.js("Services.prefs.setBoolPref('sidebar.verticalTabs',false);")
        browser.js("window.whiteSurExtra=OpenBrowserWindow();")
        browser.until(lambda: browser.js("return !!window.whiteSurExtra?.TabSearch;"))
        browser.js("whiteSurExtra.close();delete window.whiteSurExtra;")
        check("horizontal tabs activate in a new window", True)
        browser.js("Services.prefs.setBoolPref('userChrome.tabSearch.enabled',false);")
        check("disabling editable tabs removes all active layout changes", browser.js(
            "return !window.TabSearch&&!document.documentElement.hasAttribute('tabsearch-ready')"
            "&&!document.getElementById('tabsearch-spacer')&&gBrowser.addTab.name!=='addTabInstant'"
            "&&gBrowser.tabContainer.arrowScrollbox.ensureElementIsVisible.name!=='ensureVisibleWithEditor';"))
        browser.js("Services.prefs.setBoolPref('userChrome.tabSearch.enabled',true);"
                   "Services.scriptloader.loadSubScript('resource://whitesur/tab-search.uc.js?test='+Date.now(),window,'UTF-8');")
        check("native browser methods and runtime can be reinitialized", browser.js("return !!window.TabSearch;"))
        errors = browser.js("return Services.console.getMessageArray().map(m=>m.message)"
                            ".filter(m=>/WhiteSur editable tabs:|WhiteSur loader:|ResizeObserver loop/.test(m));")
        check("no customization errors or resize loops", not errors, errors)
    finally:
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "firefox-report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        if browser.session:
            screenshot = browser.call("GET", "screenshot")
            (artifacts / "firefox.png").write_bytes(base64.b64decode(screenshot))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firefox", type=Path, required=True, help="Unmodified source Firefox executable (158+)")
    parser.add_argument("--geckodriver", type=Path, required=True, help="geckodriver 0.37+ executable")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "tests" / "artifacts" / "editable-tabs")
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("This integration suite runs on Windows.")
    with tempfile.TemporaryDirectory(prefix="whitesur-firefox-") as directory:
        workspace = Path(directory).resolve()
        profile = workspace / "profile"
        profile.mkdir()
        # Model an existing installation in a disposable directory. Exercise the
        # default installer without requesting a separate runtime.
        existing = workspace / "existing Firefox"
        shutil.copytree(args.firefox.resolve().parent, existing,
                        ignore=shutil.ignore_patterns("tobedeleted", "updates"))
        binary = install(profile, existing / "firefox.exe", None, workspace / "shortcuts")
        if binary != existing / "firefox.exe" or (workspace / "shortcuts").exists():
            raise AssertionError("Default installation must use the existing Firefox without a new shortcut")
        browser = Firefox(args.geckodriver.resolve(), binary, profile)
        try:
            results = run(browser, args.artifacts.resolve())
            print(f"Result: {len(results)} native Firefox checks passed", flush=True)
        finally:
            browser.close()
            time.sleep(0.3)


if __name__ == "__main__":
    main()
