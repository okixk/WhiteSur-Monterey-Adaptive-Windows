"""Native checks for centred chrome labels, favicon spacing and input behaviour."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from test_editable_tabs_firefox import Firefox, ROOT, install, settle


TITLE = """
const tab=gBrowser.selectedTab,label=tab.querySelector('.tab-label'),image=tab.querySelector('.tab-icon-image');
const range=document.createRange();range.selectNodeContents(label);
const r=range.getBoundingClientRect(),t=tab.getBoundingClientRect(),i=image.getBoundingClientRect();
const container=tab.querySelector('.tab-label-container').getBoundingClientRect();
return {centreError:Math.abs((r.left+r.right-t.left-t.right)/2),gap:r.left-i.right,
  clippedCentreError:Math.abs((container.left+container.right-t.left-t.right)/2),
  contained:i.left>=t.left&&i.right<=t.right,labelWidth:container.width,
  icon:!!image.complete&&image.naturalWidth>0};
"""

INPUT = """
const input=gURLBar.inputField,icon=document.querySelector('.tabsearch-input-favicon');
const field=input.getBoundingClientRect(),r=icon.getBoundingClientRect(),style=getComputedStyle(input);
const span=document.createElementNS('http://www.w3.org/1999/xhtml','span');
span.textContent=input.value||input.placeholder;
Object.assign(span.style,{position:'fixed',visibility:'hidden',whiteSpace:'pre',font:style.font});
document.documentElement.append(span);
const width=span.getBoundingClientRect().width;span.remove();
const left=field.left+(field.width-width)/2;
return {align:style.textAlign,gap:left-r.right,icon:icon.complete&&icon.naturalWidth>0,
  hidden:icon.hidden,contained:r.left>=field.left&&r.right<=field.right,
  padding:parseFloat(style.paddingLeft),value:input.value,
  fits:width<=field.width-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight),
  width:field.width,src:icon.getAttribute('src'),expected:gBrowser.selectedTab.getAttribute('image')};
"""


def run(browser, artifacts):
    results = []

    def check(name, condition, details=None):
        results.append({"name": name, "pass": bool(condition), "details": details})
        print(f"{'PASS' if condition else 'FAIL'}: {name}", flush=True)
        assert condition, f"{name}: {details}"

    try:
        browser.js("TabSearch.edit();")
        browser.text("about:robots")
        browser.text("\ue007")
        browser.until(lambda: browser.js("return gBrowser.currentURI.spec==='about:robots';"))
        browser.js("window.centeredTab=gBrowser.selectedTab;window.nativeTextInput=gURLBar.inputField;")
        for width, count in ((1384, 1), (1384, 3), (800, 10)):
            browser.call("POST", "window/rect", {"width": width, "height": 800})
            browser.js("while(gBrowser.tabs.length<arguments[0])gBrowser.addTrustedTab('about:blank',{skipAnimation:true});"
                       "gBrowser.selectedTab=centeredTab;centeredTab.label='Example';"
                       "TabSearch.hide();gBrowser.selectedBrowser.focus();", count)
            browser.until(lambda: browser.js("return !gBrowser._switcher?.switchInProgress;"))
            settle(browser)
            title = browser.js(TITLE)
            check(f"tab title is centred and its favicon stays on the left ({count} tabs)",
                  title["contained"] and title["icon"] and title["clippedCentreError"] < 1
                  and (count == 10 or title["centreError"] < 1 and 5 <= title["gap"] <= 7), title)

            browser.js("TabSearch.edit();gURLBar.view.close();")
            settle(browser)
            value = browser.js(INPUT)
            check("native address text is centred with a loaded current-tab favicon",
                  value["align"] == "center" and value["icon"] and value["contained"]
                  and value["src"] == value["expected"]
                  and (not value["fits"] or 5 <= value["gap"] <= 7), value)
            browser.text("fox")
            browser.js("gURLBar.view.close();")
            settle(browser)
            typed = browser.js(INPUT)
            check("favicon follows a shorter typed query without replacing the native input",
                  typed["value"] == "fox" and typed["align"] == "center" and typed["contained"]
                  and (not typed["fits"] or 5 <= typed["gap"] <= 7), typed)
            browser.js("gURLBar.select();")
            browser.text("https://example.com/" + "long-address-" * 35)
            browser.js("gURLBar.view.close();")
            settle(browser)
            long_value = browser.js(INPUT)
            check("long addresses retain native selection and keep the icon out of the text",
                  long_value["contained"] and long_value["padding"] >= 20 and browser.js(
                      "gURLBar.select();return gURLBar.inputField.selectionStart===0"
                      "&&gURLBar.inputField.selectionEnd===gURLBar.inputField.value.length;"), long_value)
            browser.js("gURLBar.value='tiny';gURLBar.view.close();")
            settle(browser)
            changed = browser.js(INPUT)
            check("native programmatic address updates also reposition the favicon",
                  changed["value"] == 'tiny' and changed["contained"]
                  and (not changed["fits"] or 5 <= changed["gap"] <= 7), changed)
            browser.text("\ue00c")
            browser.until(lambda: browser.js("return !document.documentElement.hasAttribute('tabsearch-editing');"))
        browser.js("gBrowser.selectedTab=gBrowser.tabs[1];")
        browser.until(lambda: browser.js("return !gBrowser._switcher?.switchInProgress;"))
        browser.js("TabSearch.edit();gURLBar.view.close();")
        settle(browser)
        placeholder = browser.js(INPUT)
        check("blank-tab placeholder is centred and its fallback favicon loads",
              placeholder["align"] == "center" and placeholder["icon"] and not placeholder["value"]
              and (not placeholder["fits"] or 5 <= placeholder["gap"] <= 7), placeholder)
        browser.js("const done=arguments[arguments.length-1];gURLBar.setSearchMode({engineName:'DuckDuckGo',"
                   "entry:'oneoff',isPreview:false},gBrowser.selectedBrowser).then(()=>done(true));", asynchronous=True)
        settle(browser)
        check("native search-engine mode remains available", browser.js(
            "return gURLBar.searchMode.engineName==='DuckDuckGo'"
            "&&gURLBar.querySelector('.searchmode-switcher-close').getBoundingClientRect().width>0;"))
        browser.js("TabSearch.destroy();")
        check("disabling restores the input and removes favicon layout additions", browser.js(
            "return !document.querySelector('.tabsearch-input-favicon')"
            "&&!document.querySelector('[tabsearch-tight]')"
            "&&!document.documentElement.hasAttribute('tabsearch-ready')"
            "&&gURLBar.inputField===nativeTextInput;"))
    finally:
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "centered-text-report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firefox", type=Path, required=True)
    parser.add_argument("--geckodriver", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "tests/artifacts/centered-text")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="whitesur-centered-text-") as directory:
        workspace = Path(directory).resolve()
        profile = workspace / "profile"
        profile.mkdir()
        binary = install(profile, args.firefox.resolve(), workspace / "runtime", workspace / "shortcuts")
        browser = Firefox(args.geckodriver.resolve(), binary, profile)
        try:
            result = run(browser, args.artifacts.resolve())
            print(f"Result: {len(result)} centred-text checks passed", flush=True)
        finally:
            browser.close()
            time.sleep(.3)
