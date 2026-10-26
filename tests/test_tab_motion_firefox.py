"""Installer-backed Firefox checks for editor motion and native middle clicks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time

from test_editable_tabs_firefox import Firefox, ROOT, install, settle


def run(browser, artifacts):
    results = []

    def check(name, condition, details=None):
        results.append({"name": name, "pass": bool(condition), "details": details})
        print(f"{'PASS' if condition else 'FAIL'}: {name}", flush=True)
        assert condition, f"{name}: {details}"

    def middle(release_outside=False):
        element = browser.js("return gURLBar.inputField;")
        actions = [{"type": "pointerMove", "origin": element, "x": 0, "y": 0},
                   {"type": "pointerDown", "button": 1}]
        if release_outside:
            actions.append({"type": "pointerMove", "origin": "viewport", "x": 30, "y": 200})
        actions.append({"type": "pointerUp", "button": 1})
        browser.call("POST", "actions", {"actions": [
            {"type": "pointer", "id": "mouse", "parameters": {"pointerType": "mouse"}, "actions": actions}]})

    try:
        browser.call("POST", "window/rect", {"width": 1384, "height": 850})
        browser.js("Services.prefs.setIntPref('ui.prefersReducedMotion',0);"
                   "gBrowser.addTrustedTab('about:robots',{skipAnimation:true});"
                   "gBrowser.addTrustedTab('about:mozilla',{skipAnimation:true});"
                   "TabSearch.hide({animate:false});gBrowser.selectedBrowser.focus();")
        browser.until(lambda: browser.js("return !matchMedia('(prefers-reduced-motion: reduce)').matches;"))
        settle(browser)

        # Hold the actual pointer over + between down/up. Collapsing the old
        # editor on mousedown used to move + out from under that same gesture.
        for width, count in ((1384, 3), (800, 3), (800, 14)):
            browser.call("POST", "window/rect", {"width": width, "height": 850})
            browser.js("while(gBrowser.tabs.length<arguments[0])gBrowser.addTrustedTab('about:robots',{skipAnimation:true});"
                       "TabSearch.edit();", count)
            browser.text("about:moz")
            settle(browser)
            button = browser.js("return [...document.querySelectorAll('#tabs-newtab-button,#new-tab-button')]"
                                ".find(b=>b.getBoundingClientRect().width&&getComputedStyle(b).visibility==='visible');")
            browser.js("window.plusCount=gBrowser.tabs.length;window.plusOld=gBrowser.selectedTab;window.plusDraft=gURLBar.value;"
                       "window.plusEvents=[];window.plusAbort=new AbortController();"
                       "for(const type of ['mousedown','mouseup','click','focusin','focusout'])"
                       "window.addEventListener(type,event=>plusEvents.push({type,target:event.target.id||event.target.localName,"
                       "button:event.target.closest?.('#tabs-newtab-button,#new-tab-button')?.id,"
                       "editing:document.documentElement.hasAttribute('tabsearch-editing')}),{capture:true,signal:plusAbort.signal});"
                       "window.plusFrames=[];window.plusMade=null;"
                       "gBrowser.tabContainer.addEventListener('TabOpen',event=>{"
                       "window.plusMade=event.target;const start=performance.now();"
                       "function tick(){plusFrames.push({ms:performance.now()-start,"
                       "opacity:Number(getComputedStyle(plusMade.querySelector('.tab-stack')).opacity)});"
                       "if(performance.now()-start<350)requestAnimationFrame(tick);};requestAnimationFrame(tick);"
                       "},{once:true});")
            browser.call("POST", "actions", {"actions": [{"type": "pointer", "id": "mouse",
                "parameters": {"pointerType": "mouse"}, "actions": [
                    {"type": "pointerMove", "origin": button, "x": 0, "y": 0},
                    {"type": "pointerDown", "button": 0}, {"type": "pause", "duration": 120},
                    {"type": "pointerUp", "button": 0}]}]})
            plus = browser.js("plusAbort.abort();return {count:gBrowser.tabs.length,expected:plusCount+1,events:plusEvents,"
                              "newSelected:!!plusMade&&gBrowser.selectedTab===plusMade,"
                              "oldEditing:plusOld.hasAttribute('tabsearch-editing')};")
            check(f"+ opens exactly one new selected tab from editing at {width}px with {count} tabs",
                  plus["count"] == plus["expected"] and plus["newSelected"] and not plus["oldEditing"], plus)
            browser.until(lambda: browser.js("return document.activeElement===gURLBar.inputField"
                                            "&&document.documentElement.hasAttribute('tabsearch-editing');"))
            browser.until(lambda: browser.js("return plusFrames.at(-1)?.ms>=350;"))
            frames = browser.js("return plusFrames;")
            check("the new tab fades in with the editor and finishes fully visible",
                  any(.02 < f["opacity"] < .98 for f in frames) and frames[-1]["opacity"] == 1, frames)
            browser.js("gBrowser.selectedTab=plusOld;gBrowser.removeTab(plusMade,{animate:false});")
            browser.until(lambda: browser.js("return !gBrowser._switcher?.switchInProgress;"))
            settle(browser)
            draft = browser.js("return {value:gURLBar.value,draft:plusDraft,typed:gBrowser.selectedBrowser.userTypedValue};")
            check("returning to the original tab preserves the unfinished address", draft["value"] == draft["draft"], draft)
        browser.js("gBrowser.removeTabs([...gBrowser.tabs].slice(3),{animate:false,skipPermitUnload:true});")
        browser.call("POST", "window/rect", {"width": 1384, "height": 850})
        browser.js("TabSearch.hide({animate:false});gBrowser.selectedBrowser.focus();")
        settle(browser)
        for opening in (True, False):
            samples = browser.js("""
                const done=arguments[arguments.length-1], opening=arguments[0];
                const tab=gBrowser.selectedTab, samples=[], start=performance.now();
                const sample=()=>{
                  const r=tab.getBoundingClientRect(), c=tab.querySelector('.tab-content').getBoundingClientRect();
                  const e=gURLBar.querySelector('.urlbar-input-container').getBoundingClientRect();
                  samples.push({ms:performance.now()-start,width:r.width,
                    opacity:Number(getComputedStyle(document.getElementById('urlbar-container')).opacity),
                    error:Math.abs(e.left-Math.max(r.left+4,c.left))});
                };
                sample();if(opening)TabSearch.edit();else TabSearch.hide();
                function tick(){sample();if(performance.now()-start<320)requestAnimationFrame(tick);else done(samples);}
                requestAnimationFrame(tick);
                """, opening, asynchronous=True)
            widths = [s["width"] for s in samples]
            low, high = min(widths), max(widths)
            check(f"editor {'opens' if opening else 'closes'} through intermediate widths",
                  high-low > 40 and any(low+3 < w < high-3 for w in widths)
                  and (widths[-1] > widths[0] if opening else widths[-1] < widths[0]), samples)
            check("native input stays aligned throughout motion", max(s["error"] for s in samples) < 2, samples)
            check("editor fades during the transition", any(.02 < s["opacity"] < .98 for s in samples), samples)
        check("collapse finishes without an invisible overlay", browser.js(
            "return !document.documentElement.hasAttribute('tabsearch-hiding')"
            "&&getComputedStyle(document.getElementById('urlbar-container')).visibility==='hidden';"))

        reversal = browser.js("""
            const done=arguments[arguments.length-1];
            TabSearch.edit();setTimeout(()=>TabSearch.hide(),45);
            setTimeout(()=>TabSearch.edit(),85);
            setTimeout(()=>done({width:gBrowser.selectedTab.getBoundingClientRect().width,
              editing:document.documentElement.hasAttribute('tabsearch-editing'),
              hiding:document.documentElement.hasAttribute('tabsearch-hiding')}),400);
            """, asynchronous=True)
        check("rapid reversal finishes in the requested editing state",
              280 < reversal["width"] <= 301 and reversal["editing"] and not reversal["hiding"], reversal)

        removed = browser.js("""
            TabSearch.hide({animate:false});
            const tab=gBrowser.tabs[1];gBrowser.removeTab(tab,{animate:true});
            return {connected:tab.isConnected,ghosts:document.querySelectorAll('.tabsearch-close-ghost').length};
            """)
        check("tab removal is immediate while a decorative close animation runs",
              not removed["connected"] and removed["ghosts"] == 1, removed)
        browser.until(lambda: browser.js("return !document.querySelector('.tabsearch-close-ghost');"))
        check("close animation cleans up without closing-tab gaps", browser.js(
            "return !document.querySelector('.tabbrowser-tab[closing]');"))

        browser.js("window.motionMiddle=gBrowser.addTrustedTab('about:robots',{skipAnimation:true});"
                   "gBrowser.selectedTab=motionMiddle;")
        browser.until(lambda: browser.js("return !gBrowser._switcher?.switchInProgress;"))
        browser.js("TabSearch.edit();window.motionCount=gBrowser.tabs.length;")
        settle(browser)
        middle(release_outside=True)
        check("releasing middle-click outside the field preserves the tab", browser.js(
            "return motionMiddle.isConnected&&gBrowser.tabs.length===motionCount;"))
        browser.js("TabSearch.edit();")
        settle(browser)
        middle()
        check("a real middle-click in the input closes exactly its selected tab", browser.js(
            "return !motionMiddle.isConnected&&gBrowser.tabs.length===motionCount-1;"))
        settle(browser)

        browser.call("POST", "window/rect", {"width": 800, "height": 850})
        browser.js("while(gBrowser.tabs.length<14)gBrowser.addTrustedTab('about:robots',{skipAnimation:true});"
                   "gBrowser.selectedTab=gBrowser.tabs.at(-1);")
        browser.until(lambda: browser.js("return !gBrowser._switcher?.switchInProgress;"))
        settle(browser)
        edge = browser.js("""
            const done=arguments[arguments.length-1], start=performance.now();let maxError=0;
            TabSearch.hide({animate:false});TabSearch.edit();
            function tick(){
              const t=gBrowser.selectedTab,r=t.getBoundingClientRect(),
                c=t.querySelector('.tab-content').getBoundingClientRect(),
                e=gURLBar.querySelector('.urlbar-input-container').getBoundingClientRect(),
                v=gBrowser.tabContainer.arrowScrollbox.scrollbox.getBoundingClientRect();
              maxError=Math.max(maxError,Math.abs(e.left-Math.max(r.left+4,c.left)));
              if(performance.now()-start<350)requestAnimationFrame(tick);
              else done({maxError,right:e.right,viewportRight:v.right,left:e.left,viewportLeft:v.left});
            }requestAnimationFrame(tick);
            """, asynchronous=True)
        check("crowded-strip motion keeps the rightmost tab's input aligned", edge["maxError"] < 2, edge)
        check("the expanded editor finishes inside the scroll viewport",
              edge["right"] <= edge["viewportRight"]+1 and edge["left"] >= edge["viewportLeft"]-1, edge)

        browser.js("Services.prefs.setIntPref('ui.prefersReducedMotion',1);")
        browser.until(lambda: browser.js("return matchMedia('(prefers-reduced-motion: reduce)').matches;"))
        settle(browser)
        reduced = browser.js("""
            TabSearch.hide({animate:false});TabSearch.edit();
            const width=gBrowser.selectedTab.getBoundingClientRect().width;
            const tab=gBrowser.addTrustedTab('about:robots');
            const insertedAnimations=tab.querySelector('.tab-stack').getAnimations().length;
            gBrowser.removeTab(tab,{animate:true});TabSearch.hide();
            return {width,collapsed:gBrowser.selectedTab.getBoundingClientRect().width,insertedAnimations,
              ghosts:document.querySelectorAll('.tabsearch-close-ghost').length,
              animations:[...gBrowser.tabs,document.getElementById('urlbar-container')].flatMap(t=>t.getAnimations()).length};
            """)
        check("reduced motion expands, collapses and removes tabs immediately",
              reduced["width"] > reduced["collapsed"]+40 and reduced["ghosts"] == 0
              and reduced["animations"] == 0 and reduced["insertedAnimations"] == 0, reduced)
        browser.js("Services.prefs.setIntPref('ui.prefersReducedMotion',0);")
        browser.until(lambda: browser.js("return !matchMedia('(prefers-reduced-motion: reduce)').matches;"))
        settle(browser)
        cleanup = browser.js("""
            TabSearch.edit();
            const tab=gBrowser.addTrustedTab('about:robots'),stack=tab.querySelector('.tab-stack');
            gBrowser.removeTab(tab,{animate:true});
            TabSearch.destroy();
            return {ghosts:document.querySelectorAll('.tabsearch-close-ghost').length,
              runtime:!!window.TabSearch,hiding:document.documentElement.hasAttribute('tabsearch-hiding'),
              animations:[...gBrowser.tabs,stack,document.getElementById('urlbar-container')]
                .flatMap(t=>t.getAnimations()).filter(a=>!(a instanceof CSSTransition)&&!(a instanceof CSSAnimation))
                .map(a=>({state:a.playState,keys:a.effect.getKeyframes()}))};
            """)
        check("disabling the feature during motion removes all visual leftovers",
              not cleanup["ghosts"] and not cleanup["runtime"] and not cleanup["hiding"]
              and not cleanup["animations"], cleanup)
    finally:
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "tab-motion-report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--firefox", type=Path, required=True)
    parser.add_argument("--geckodriver", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, default=ROOT / "tests/artifacts/tab-motion")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="whitesur-tab-motion-") as directory:
        workspace = Path(directory)
        profile = workspace / "profile"
        profile.mkdir()
        binary = install(profile, args.firefox.resolve(), workspace / "runtime", workspace / "shortcuts")
        browser = Firefox(args.geckodriver.resolve(), binary, profile)
        try:
            results = run(browser, args.artifacts.resolve())
            print(f"Result: {len(results)} motion/middle-click checks passed", flush=True)
        finally:
            browser.close()
            time.sleep(.3)
