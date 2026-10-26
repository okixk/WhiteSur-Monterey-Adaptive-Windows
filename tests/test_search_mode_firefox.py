"""Native regression for issue #4, with installer-created editable/classic profiles."""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import subprocess
import tempfile
import time

from test_editable_tabs_firefox import Firefox, ROOT, install


MEASURE = """
const host=gURLBar.querySelector('.searchmode-switcher');
const button=host.shadowRoot.querySelector('[part="button"]');
const icon=host.shadowRoot.querySelector('img');
const label=host.querySelector('.searchmode-switcher-title');
const close=host.querySelector('.searchmode-switcher-close');
const field=gURLBar.querySelector('.urlbar-input-container');
const rect=e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};
const boxes={field:rect(field),host:rect(host),button:rect(button),icon:rect(icon),
             label:rect(label),close:rect(close)};
const centre=r=>r.y+r.h/2;
const visible=Object.entries(boxes).filter(([key,r])=>key!=='field'&&r.w>0&&r.h>0);
return {boxes,engineLabel:label.textContent,
  visible:getComputedStyle(field).visibility==='visible',
  classicGap:gBrowser.selectedTab.getBoundingClientRect().left-
    field.getBoundingClientRect().right,
  maxOffset:Math.max(...visible.map(([,r])=>Math.abs(centre(r)-centre(boxes.field)))),
  overflow:Math.max(0,boxes.field.y-boxes.button.y,
    boxes.button.y+boxes.button.h-boxes.field.y-boxes.field.h),
  horizontalImbalance:boxes.close.w ? Math.abs((boxes.icon.x-boxes.button.x)-
    (boxes.button.x+boxes.button.w-boxes.close.x-boxes.close.w)) : 0};
"""


def frame(browser):
    browser.js("const done=arguments[arguments.length-1];"
               "requestAnimationFrame(()=>requestAnimationFrame(()=>done(true)));", asynchronous=True)


def run(driver, source, artifacts):
    results = []
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="whitesur-search-mode-") as directory:
        workspace = Path(directory)
        profile = workspace / "editable-profile"
        profile.mkdir()
        binary = install(profile, source, workspace / "runtime", workspace / "shortcuts")
        for mode in ("editable", "classic"):
            if mode == "classic":
                profile = workspace / "classic-profile"
                profile.mkdir()
                subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                    str(ROOT / "Install-WhiteSur-Monterey-Adaptive.ps1"), "-ProfilePath", str(profile),
                    "-ClassicToolbar", "-Force"], check=True, capture_output=True)
            browser = Firefox(driver, binary, profile)
            try:
                assert browser.js("return !!window.TabSearch;") == (mode == "editable"), mode
                browser.until(lambda: browser.js("return !gBrowser._switcher?.switchInProgress;"))
                for state in ("normal", "maximized", "narrow"):
                    if state == "maximized":
                        browser.call("POST", "window/maximize", {})
                    else:
                        browser.call("POST", "window/rect", {"width": 800 if state == "narrow" else 1384,
                                                             "height": 850})
                    browser.js("gURLBar.focus();gURLBar.view.close();")
                    frame(browser)
                    idle = browser.js(MEASURE)
                    passed = (idle["visible"] and idle["maxOffset"] < 0.6 and idle["overflow"] < 0.6
                              and (mode != "classic" or state == "narrow" or idle["classicGap"] >= 0))
                    results.append({"mode": mode, "state": state, "engine": "default", "pass": passed, **idle})
                    print(f"{'PASS' if passed else 'FAIL'}: {mode}/{state} default engine centred", flush=True)
                    assert passed, idle
                    for engine in ("Google", "DuckDuckGo"):
                        browser.js("const done=arguments[arguments.length-1];"
                            "gURLBar.setSearchMode({engineName:arguments[0],entry:'oneoff',isPreview:false},"
                            "gBrowser.selectedBrowser).then(()=>{gURLBar.focus();gURLBar.view.close();done(true);});",
                            engine, asynchronous=True)
                        browser.until(lambda: browser.js(
                            "return gURLBar.querySelector('.searchmode-switcher-title').textContent===arguments[0];", engine))
                        frame(browser)
                        measurement = browser.js(MEASURE)
                        passed = (measurement["visible"] and measurement["maxOffset"] < 0.6 and measurement["overflow"] < 0.6
                                  and measurement["horizontalImbalance"] < 1
                                  and measurement["boxes"]["label"]["h"] > 0)
                        if state == "normal" and engine == "Google":
                            (artifacts / f"{mode}-google.png").write_bytes(base64.b64decode(browser.call("GET", "screenshot")))
                        close = browser.js("return gURLBar.querySelector('.searchmode-switcher-close');")
                        element_id = close["element-6066-11e4-a52e-4f735466cecf"]
                        browser.call("POST", f"element/{element_id}/click", {})
                        browser.until(lambda: browser.js("return !gURLBar.searchMode;"))
                        frame(browser)
                        results.append({"mode": mode, "state": state, "engine": engine,
                                        "pass": passed, "nativeClose": True, **measurement})
                        print(f"{'PASS' if passed else 'FAIL'}: {mode}/{state} {engine} centred and closes", flush=True)
                        assert passed, measurement
            finally:
                (artifacts / "search-mode-report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
                browser.close()
                time.sleep(1)
    print(f"Result: {len(results)} search-mode checks passed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firefox", type=Path, required=True)
    parser.add_argument("--geckodriver", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "tests/artifacts/search-mode")
    args = parser.parse_args()
    run(args.geckodriver.resolve(), args.firefox.resolve(), args.artifacts.resolve())
