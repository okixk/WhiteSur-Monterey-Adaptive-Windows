"""Real Windows Firefox coverage for profile-only Full, including active AutoConfig.

No production JavaScript is injected. Chrome context is used only by WebDriver
to measure UI and arrange test states. All installations and policies are lab
fixtures in a disposable copy; the source Firefox is read only.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import ExitStack
import hashlib
import http.server
import json
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from test_editable_tabs_firefox import Firefox, settle
from test_window_titlebar_firefox import NativeWindow, POINTS

ROOT = Path(__file__).resolve().parents[1]


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def install(profile, binary, *extra):
    result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', str(ROOT/'Install-WhiteSur-Monterey-Adaptive.ps1'), '-ProfilePath', str(profile),
        '-FirefoxPath', str(binary), '-Force', *extra], capture_output=True, text=True, errors='replace')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout


class Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        data = b'''<!doctype html><title>Monterey Lab</title>
        <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='5' fill='%23315d53'/%3E%3Cpath d='M4 11 8 4l4 7' fill='none' stroke='white' stroke-width='2'/%3E%3C/svg%3E">
        <style>body{background:#f5f0e6;color:#313c3a;font:20px system-ui;margin:8vh 8vw}
        h1{font-size:54px;font-weight:500;letter-spacing:-2px}p{max-width:650px;line-height:1.6}
        a{color:#345c57}article{padding:40px;border:1px solid #b7c8bd;border-radius:20px}</style>
        <article><small>WHITESUR / FIREFOX LAB</small><h1>A calmer place to browse.</h1>
        <p>Native Firefox navigation, Monterey-inspired capsules and adaptive colours.
        This page is served locally in an isolated test profile.</p><a href="/next">Next page</a></article>'''
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


MEASURE = '''
const rect=e=>{let r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}};
const u=document.getElementById('urlbar-container'),t=gBrowser.selectedTab;
return {url:rect(u),tab:rect(t),strip:rect(document.getElementById('TabsToolbar')),
  input:rect(gURLBar.inputField),width:innerWidth,opacity:getComputedStyle(u).opacity,
  focused:document.activeElement===gURLBar.inputField,focusedId:document.activeElement?.id,count:gBrowser.tabs.length,
  stripVisible:getComputedStyle(document.getElementById('TabsToolbar')).display!=='none',
  anchors:CSS.supports('left:anchor(--test left)'),overflow:gBrowser.tabContainer.hasAttribute('overflow')};
'''


def move(browser, x, y, click=False, button=0):
    actions = [{'type': 'pointerMove', 'duration': 100, 'origin': 'viewport', 'x': round(x), 'y': round(y)}]
    if click:
        actions.extend([{'type': 'pointerDown', 'button': button}, {'type': 'pointerUp', 'button': button}])
    browser.call('POST', 'actions', {'actions': [{'type': 'pointer', 'id': 'mouse',
        'parameters': {'pointerType': 'mouse'}, 'actions': actions}]})


def run(source, driver, artifacts):
    results = []
    artifacts.mkdir(parents=True, exist_ok=True)

    def check(name, condition, details=None):
        results.append({'name': name, 'pass': bool(condition), 'details': details})
        print(f"{'PASS' if condition else 'FAIL'}: {name}", flush=True)
        if not condition:
            raise AssertionError(f'{name}: {details}')

    def screenshot(browser, name):
        (artifacts/name).write_bytes(base64.b64decode(browser.call('GET', 'screenshot')))

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Page)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    browser = None
    def finish_browser():
        nonlocal browser
        if browser:
            try:
                screenshot(browser, 'last-state.png')
            finally:
                browser.close()
                browser = None
    try:
        with tempfile.TemporaryDirectory(prefix='whitesur-compatible-') as temporary, ExitStack() as lifecycle:
            lab = Path(temporary)
            target = lab/'Firefox'
            shutil.copytree(source.parent, target, ignore=shutil.ignore_patterns('updates', 'tobedeleted'))
            # These are newly created harmless fixtures, never company files.
            if list(target.glob('*.cfg')):
                raise RuntimeError('Supply a clean Firefox source for this test; no existing cfg will be replaced.')
            (target/'defaults/pref/lab-autoconfig.js').write_text('pref("general.config.filename", "zscaler.cfg");\npref("general.config.obscure_value", 0);\n')
            (target/'zscaler.cfg').write_text('// Lab fixture, not Zscaler software\nlockPref("whitesur.lab.locked", true);\nif(getPref("whitesur.lab.blockCss"))lockPref("toolkit.legacyUserProfileCustomizations.stylesheets",false);\n')
            (target/'distribution').mkdir(exist_ok=True)
            (target/'distribution/policies.json').write_text('{"policies":{"DisableTelemetry":true}}')
            profile = lab/'profile'
            (profile/'chrome').mkdir(parents=True)
            (profile/'chrome/original.css').write_text('/* original */')
            (profile/'user.js').write_text('user_pref("whitesur.unrelated", true);\n')
            before = hashes(target)
            output = install(profile, target/'firefox.exe')
            check('default Full detects AutoConfig and recommends compatible mode', 'AutoConfig detected' in output, output)
            check('installation changes no Firefox, AutoConfig or policy files', hashes(target) == before)
            check('Full installs CSS with no privileged script or launcher',
                (profile/'chrome/full-compatible.css').exists() and not (profile/'chrome/tab-search.uc.js').exists()
                and not (profile/'.whitesur-editable-tabs.json').exists())
            (profile/'chrome/customChrome.css').write_text('/* custom override preserved */')
            install(profile, target/'firefox.exe')
            check('update preserves custom CSS and unrelated preferences',
                (profile/'chrome/customChrome.css').read_text() == '/* custom override preserved */'
                and 'whitesur.unrelated' in (profile/'user.js').read_text(encoding='utf-8-sig'))
            browser = Firefox(driver, target/'firefox.exe', profile)
            lifecycle.callback(finish_browser)
            check('existing AutoConfig really loads and its locked preference stays locked', browser.js(
                'return Services.prefs.getStringPref("general.config.filename")==="zscaler.cfg"'
                '&&Services.prefs.prefIsLocked("whitesur.lab.locked")&&Services.prefs.getBoolPref("whitesur.lab.locked");'))
            check('enterprise policy remains active', browser.js('return Services.policies.getActivePolicies().DisableTelemetry===true;'))
            check('no privileged WhiteSur script is loaded', browser.js('return !window.TabSearch;'))
            browser.call('POST', 'window/rect', {'width': 1384, 'height': 850})
            browser.call('POST', 'moz/context', {'context': 'content'})
            browser.call('POST', 'url', {'url': f'http://127.0.0.1:{server.server_port}/'})
            browser.call('POST', 'moz/context', {'context': 'chrome'})
            browser.js('gBrowser.selectedBrowser.focus();')
            move(browser, 700, 400)
            settle(browser)
            sample = browser.js(MEASURE)
            check('supporting Firefox uses a centred single-tab capsule', sample['anchors'] and abs(sample['tab']['x']+sample['tab']['w']/2-sample['width']/2)<2, sample)
            check('browsing shows the actual page title', browser.js('return gBrowser.selectedTab.label==="Monterey Lab";'))
            screenshot(browser, 'wide-browsing.png')
            native=NativeWindow(browser)
            points=browser.js(POINTS)
            check('empty toolbar space remains a native window drag region',native.hit(points['tail'])==2,points['tail'])
            check('tab and new-tab targets remain ordinary controls',native.hit(points['tab'])==1 and native.hit(points['plus'])==1)
            native.double_click(points['tail'])
            browser.until(lambda:browser.js('return window.windowState===window.STATE_MAXIMIZED;'))
            check('real double-click maximizes the lab window',True)
            browser.call('POST','window/rect',{'width':1384,'height':850})
            browser.chord('l')
            settle(browser)
            sample = browser.js(MEASURE)
            check('Ctrl+L focuses the visible native input aligned with its tab', sample['focused'] and sample['opacity']=='1' and abs(sample['url']['x']-sample['tab']['x']-3)<1, sample)
            screenshot(browser, 'wide-editing.png')
            identity=browser.js('return ["trust-icon-container","identity-icon-box"].map(id=>document.getElementById(id)).find(e=>e?.getBoundingClientRect().width>0);')
            browser.call('POST',f'element/{identity["element-6066-11e4-a52e-4f735466cecf"]}/click',{})
            browser.until(lambda:browser.js('return [...document.querySelectorAll("panel,moz-panel")].some(e=>/trust|identity/.test(e.id)&&(e.state==="open"||e.hasAttribute("open")));'))
            check('native site-identity popup opens from the anchored field',True)
            move(browser, sample['url']['x']+60, sample['url']['bottom']+80)
            check('security popup keeps its address field visible',browser.js(MEASURE)['opacity']=='1')
            browser.call('POST','actions',{'actions':[{'type':'key','id':'security-esc','actions':[{'type':'keyDown','value':'\ue00c'},{'type':'keyUp','value':'\ue00c'}]}]})
            browser.until(lambda:browser.js('return [...document.querySelectorAll("panel,moz-panel")].filter(e=>/trust|identity/.test(e.id)).every(e=>!e.state||e.state==="closed");'))
            browser.chord('l')
            browser.text('monterey local search')
            browser.until(lambda: browser.js('return gURLBar.view.isOpen;'))
            panel = browser.js('let r=gURLBar.view.panel.getBoundingClientRect(); return {x:r.x,right:r.right,y:r.y,w:r.width};')
            check('native suggestions stay inside the viewport', panel['x']>=0 and panel['right']<=sample['width']+1 and panel['w']>200, panel)
            screenshot(browser, 'suggestions.png')
            browser.call('POST','actions',{'actions':[{'type':'key','id':'esc','actions':[{'type':'keyDown','value':'\ue00c'},{'type':'keyUp','value':'\ue00c'}]}]})
            browser.until(lambda:browser.js('return !gURLBar.view.isOpen;'))
            check('Escape closes native suggestions', True)
            move(browser,700,400,click=True)
            settle(browser)
            sample = browser.js(MEASURE)
            check('clicking the page restores the title capsule', sample['opacity']=='0', sample)
            move(browser, sample['tab']['x']+sample['tab']['w']/2, sample['tab']['y']+16)
            settle(browser)
            check('hover reveals a visible address field before mouse editing', browser.js('return getComputedStyle(document.getElementById("urlbar-container")).opacity==="1";'))
            move(browser, sample['tab']['x']+sample['tab']['w']/2, sample['tab']['y']+16,click=True)
            check('mouse click focuses the native address input', browser.js('return document.activeElement===gURLBar.inputField;'))
            browser.js('gBrowser.selectedBrowser.focus();')
            move(browser,700,400)
            plus=browser.js('return [...document.querySelectorAll("#tabs-newtab-button,#new-tab-button")].find(e=>e.getBoundingClientRect().width&&getComputedStyle(e).visibility==="visible");')
            browser.call('POST',f'element/{plus["element-6066-11e4-a52e-4f735466cecf"]}/click',{})
            settle(browser)
            check('native + opens exactly one ready-to-type tab',browser.js('return gBrowser.tabs.length===2&&document.activeElement===gURLBar.inputField;'))
            browser.chord('w')
            settle(browser)
            check('native Ctrl+W restores the single capsule without gaps',browser.js('return gBrowser.tabs.length===1;'))
            for count in (3,14):
                browser.js('while(gBrowser.tabs.length<arguments[0])gBrowser.addTab("about:blank",{triggeringPrincipal:Services.scriptSecurityManager.getSystemPrincipal()});',count)
                browser.chord('\ue004')
                browser.until(lambda:browser.js('return !gBrowser._switcher?.switchInProgress;'))
                settle(browser)
                for width in (600,800,980,1384,1600):
                    browser.call('POST','window/rect',{'width':width,'height':850})
                    browser.chord('l')
                    settle(browser)
                    sample=browser.js(MEASURE)
                    check(f'{count} tabs at {width}px keep tabs and address input usable', sample['stripVisible'] and sample['focused'] and sample['opacity']=='1' and sample['input']['w']>=80 and sample['url']['x']>=0 and sample['url']['right']<=sample['width'],sample)
                    screenshot(browser,f'{count}-tabs-{width}.png')
                    if count==3 and width==800:
                        browser.js('gURLBar.view.close();gBrowser.selectedBrowser.focus();')
                        move(browser,400,400)
                        settle(browser)
                        screenshot(browser,'narrow-browsing.png')
            for width,index in ((1384,0),(1384,7),(1384,13),(1000,13)):
                browser.call('POST','window/rect',{'width':width,'height':850})
                browser.js('gBrowser.selectedBrowser.focus();')
                browser.js('gBrowser.selectedTab=gBrowser.tabs[arguments[0]];',index)
                browser.until(lambda:browser.js('return !gBrowser._switcher?.switchInProgress;'))
                before_focus=browser.js('return gBrowser.selectedTab.getBoundingClientRect().width;')
                browser.chord('l')
                settle(browser)
                # Native smooth tab-strip scrolling is separate from element
                # Web Animations and may continue after two animation frames.
                try:
                    browser.until(lambda:browser.js('let u=document.getElementById("urlbar-container").getBoundingClientRect(),s=document.getElementById("TabsToolbar").getBoundingClientRect();return u.x>=s.x-1&&u.right<=s.right+1;'),timeout=3)
                except TimeoutError:
                    pass
                sample=browser.js(MEASURE)
                check(f'overflow selection {index} at {width}px stays inside its strip',sample['url']['x']>=sample['strip']['x']-1 and sample['url']['right']<=sample['strip']['right']+1 and sample['input']['w']>80 and abs(sample['tab']['w']-before_focus)<1,sample)
            browser.call('POST','window/rect',{'width':1384,'height':850})
            browser.js('gBrowser.pinTab(gBrowser.selectedTab);')
            browser.chord('l')
            settle(browser)
            sample=browser.js(MEASURE)
            check('pinned selection uses a separate usable native address field',sample['input']['w']>80 and sample['url']['bottom']<=sample['strip']['y']+1,sample)
            browser.js('gBrowser.unpinTab(gBrowser.selectedTab);Services.prefs.setBoolPref("sidebar.verticalTabs",true);')
            settle(browser)
            browser.chord('l')
            sample=browser.js(MEASURE)
            check('vertical tabs keep the native address field usable',sample['focused'] and sample['input']['w']>80,sample)
            screenshot(browser,'vertical-tabs.png')
            browser.js('Services.prefs.setBoolPref("sidebar.verticalTabs",false);')
            main=browser.call('GET','window')
            browser.js('window.labPrivate=OpenBrowserWindow({private:true});')
            browser.until(lambda:browser.js('return window.labPrivate?.gBrowserInit?.delayedStartupFinished;'))
            handles=browser.call('GET','window/handles')
            browser.call('POST','window',{'handle':next(h for h in handles if h!=main)})
            browser.chord('l')
            settle(browser)
            check('private windows get a native usable editor without a loader',browser.js('return document.documentElement.hasAttribute("privatebrowsingmode")&&!window.TabSearch&&document.activeElement===gURLBar.inputField;'))
            screenshot(browser,'private.png')
            browser.call('DELETE','window')
            browser.call('POST','window',{'handle':main})
            browser.call('POST','window/fullscreen',{})
            browser.chord('l')
            settle(browser)
            sample=browser.js(MEASURE)
            check('fullscreen keeps the native editor on screen',sample['focused'] and sample['opacity']=='1' and sample['url']['x']>=0 and sample['url']['right']<=sample['width'],sample)
            screenshot(browser,'fullscreen.png')
            browser.js('window.fullScreen=false;gCustomizeMode.enter();')
            browser.until(lambda:browser.js('return document.documentElement.hasAttribute("customizing");'))
            check('customization suspends CSS anchor positioning',browser.js('return getComputedStyle(document.getElementById("urlbar-container")).position!=="fixed";'))
            browser.js('gCustomizeMode.exit();')
            browser.until(lambda:browser.js('return !document.documentElement.hasAttribute("customizing");'))
            browser.call('POST','window/maximize',{})
            browser.chord('l')
            settle(browser)
            check('maximized editor remains visible',browser.js(MEASURE)['opacity']=='1')
            browser.js('Services.prefs.setIntPref("ui.prefersReducedMotion",1);')
            settle(browser)
            check('reduced motion suppresses decorative transitions',browser.js('return getComputedStyle(gBrowser.selectedTab.querySelector(".tab-background")).transitionDuration==="0s";'))
            for mode in ('light','dark'):
                browser.js('const done=arguments[arguments.length-1];ChromeUtils.importESModule("resource://gre/modules/AddonManager.sys.mjs").AddonManager.getAddonByID("firefox-compact-"+arguments[0]+"@mozilla.org").then(a=>a.enable()).then(()=>done(true));',mode,asynchronous=True)
                settle(browser)
                browser.until(lambda:browser.js('return Services.prefs.getStringPref("extensions.activeThemeID")==="firefox-compact-"+arguments[0]+"@mozilla.org";',mode))
                check(f'actual built-in {mode} theme is enabled',True)
                screenshot(browser, f'{mode}.png')
            # A normal temporary theme WebExtension proves the CSS consumes the
            # supported theme API. It needs no host/tabs permissions or signing bypass.
            addon=lab/'theme.xpi'
            with zipfile.ZipFile(addon,'w') as z:
                z.writestr('manifest.json',json.dumps({'manifest_version':2,'name':'WhiteSur lab theme','version':'1.0',
                    'browser_specific_settings':{'gecko':{'id':'whitesur-lab@example.invalid'}},
                    'theme':{'colors':{'frame':'#315d53','tab_background_text':'#ffffff','toolbar':'#315d53','toolbar_text':'#ffffff'}}}))
            browser.call('POST','moz/addon/install',{'path':str(addon),'temporary':True})
            settle(browser)
            check('standard theme extension colours reach the toolbar',browser.js('return getComputedStyle(document.documentElement).getPropertyValue("--lwt-accent-color").includes("49, 93, 83");'))
            screenshot(browser,'adaptive-theme.png')
            errors=browser.js('return Services.console.getMessageArray().map(x=>x.message).filter(x=>/WhiteSur.*Error|ResizeObserver loop/.test(x));')
            check('no WhiteSur runtime errors or resize loops',not errors,errors)
            browser.close()
            browser=None
            blocked=lab/'blocked-profile'
            blocked.mkdir()
            (blocked/'user.js').write_text('user_pref("whitesur.lab.blockCss",true);\n')
            install(blocked,target/'firefox.exe')
            browser=Firefox(driver,target/'firefox.exe',blocked)
            check('a locked stylesheet prohibition is respected',browser.js('return Services.prefs.prefIsLocked("toolkit.legacyUserProfileCustomizations.stylesheets")&&!Services.prefs.getBoolPref("toolkit.legacyUserProfileCustomizations.stylesheets")&&getComputedStyle(document.getElementById("urlbar-container")).position!=="fixed";'))
            browser.close()
            browser=None
            install(profile,target/'firefox.exe','-Uninstall')
            check('uninstall restores the original theme', (profile/'chrome/original.css').read_text()=='/* original */')
            check('install, update, browser use and uninstall preserve security file bytes',all(
                hashes(target).get(p)==value for p,value in before.items() if p.endswith(('.cfg','.js','policies.json'))))
    finally:
        if browser:
            screenshot(browser,'failure.png')
            browser.close()
        server.shutdown()
        (artifacts/'report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(f'Result: {len(results)} compatible Firefox checks passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firefox',type=Path,required=True)
    parser.add_argument('--geckodriver',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,default=ROOT/'tests/artifacts/compatible')
    args=parser.parse_args()
    run(args.firefox.resolve(),args.geckodriver.resolve(),args.artifacts.resolve())
