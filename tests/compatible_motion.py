"""Measure real CSS motion in the installer-created Compatible Firefox window.

Chrome JavaScript invokes native UI methods and samples animation frames only;
no styles or production script are injected. Outer tab rectangles must stay
stable during editing because Firefox owns tab visibility and scrolling.
"""
from __future__ import annotations

import base64
import json


SAMPLE = '''
const kind=arguments[0],done=arguments[arguments.length-1];
const field=document.getElementById('urlbar-container'),tabs=gBrowser.tabContainer;
let tab=gBrowser.selectedTab, stack=tab.querySelector('.tab-stack');
const start=performance.now(),frames=[];
function sample(){
  const t=tab.getBoundingClientRect(),u=field.getBoundingClientRect();
  const s=getComputedStyle(stack);
  frames.push({time:performance.now()-start,connected:tab.isConnected,closing:tab.closing,
    opacity:Number(s.opacity),translate:s.translate,scale:s.scale,
    fieldOpacity:Number(getComputedStyle(field).opacity),
    titleOpacity:Number(getComputedStyle(gBrowser.selectedTab.querySelector('.tab-label-container')).opacity),
    tabX:t.x,tabWidth:t.width,urlX:u.x,urlWidth:u.width,
    ghosts:document.querySelectorAll('.tabsearch-close-ghost').length});
}
sample();
if(kind==='edit')gURLBar.focus();
if(kind==='hide'){gURLBar.view.close();gBrowser.selectedBrowser.focus();}
if(kind==='open'){
  tab=gBrowser.addTrustedTab('about:robots',{skipAnimation:false});
  stack=tab.querySelector('.tab-stack');
  window.whiteSurMotionTab=tab;
}
if(kind==='close'){
  tab=window.whiteSurMotionTab;stack=tab.querySelector('.tab-stack');
  gBrowser.removeTab(tab,{animate:true,skipPermitUnload:true});
}
function frame(){
  sample();
  if(performance.now()-start<260)requestAnimationFrame(frame);else done(frames);
}
requestAnimationFrame(frame);
'''


def run_motion(browser, artifacts, settle, move):
    results=[]

    def check(name, condition, details=None):
        results.append({'name':name,'pass':bool(condition),'details':details})
        print(f"{'PASS' if condition else 'FAIL'}: {name}",flush=True)
        if not condition:
            raise AssertionError(f'{name}: {details}')

    def capture(kind):
        return browser.js(SAMPLE,kind,asynchronous=True)

    artifacts.mkdir(parents=True,exist_ok=True)
    old_pref=browser.js('return Services.prefs.prefHasUserValue("ui.prefersReducedMotion")?Services.prefs.getIntPref("ui.prefersReducedMotion"):null;')
    try:
        browser.js('Services.prefs.setIntPref("ui.prefersReducedMotion",0);gURLBar.view.close();gBrowser.selectedBrowser.focus();')
        move(browser,700,400)
        browser.until(lambda:browser.js('return !matchMedia("(prefers-reduced-motion: reduce)").matches;'))
        settle(browser)
        reveal=capture('edit')
        check('CSS editor reveal has intermediate opacity frames',any(0.02<f['fieldOpacity']<.98 for f in reveal),reveal)
        check('CSS title and editor crossfade ends in an editable field',reveal[-1]['fieldOpacity']>.99 and reveal[-1]['titleOpacity']<.01)
        check('CSS reveal never changes tab or editor width',max(f['tabWidth'] for f in reveal)-min(f['tabWidth'] for f in reveal)<.5 and max(f['urlWidth'] for f in reveal)-min(f['urlWidth'] for f in reveal)<.5)
        hide=capture('hide')
        check('CSS editor dismissal fades and restores the title',any(.02<f['fieldOpacity']<.98 for f in hide) and hide[-1]['fieldOpacity']<.01 and hide[-1]['titleOpacity']>.99,hide)
        check('a fading-out editor immediately stops intercepting clicks',browser.js('return getComputedStyle(document.getElementById("urlbar-container")).pointerEvents==="none";'))
        opened=capture('open')
        check('new capsules fade and slide into their native tab slots',any(f['connected'] and .02<f['opacity']<.98 for f in opened[1:]) and opened[-1]['opacity']>.99 and any(f['translate'] not in ('none','0px','0px 0px') for f in opened[1:]),opened)
        closed=capture('close')
        check('native closing capsules fade before Firefox removes them',any(f['connected'] and f['closing'] and .02<f['opacity']<.98 for f in closed[1:]) and not closed[-1]['connected'],closed)
        settle(browser)
        check('closing leaves no ghost elements or invisible tab slots',browser.js('return gBrowser.tabs.length===1&&!document.querySelector(".tabbrowser-tab[closing],.tabsearch-close-ghost");'))
        check('no privileged animation runtime is required',browser.js('return !window.TabSearch&&!document.getElementById("tabsearch-spacer");'))

        # Reverse an actual transition before it finishes. The final state must
        # belong to the latest focus change, with no delayed pointer capture.
        reversed_frames=browser.js('''const done=arguments[arguments.length-1];
          gURLBar.focus();setTimeout(()=>{gURLBar.view.close();gBrowser.selectedBrowser.focus();},45);
          setTimeout(()=>done({opacity:getComputedStyle(document.getElementById('urlbar-container')).opacity,
            pointer:getComputedStyle(document.getElementById('urlbar-container')).pointerEvents}),320);''',asynchronous=True)
        check('rapid focus reversal finishes without an invisible editor overlay',float(reversed_frames['opacity'])<.01 and reversed_frames['pointer']=='none',reversed_frames)
        for width in (800,1384):
            browser.call('POST','window/rect',{'width':width,'height':850})
            settle(browser)
            opened=capture('open')
            capture('close')
            settle(browser)
            check(f'open and close motion keeps native tab removal working at {width}px',browser.js('return gBrowser.tabs.length===1&&!document.querySelector(".tabbrowser-tab[closing]");'))

        browser.js('Services.prefs.setIntPref("ui.prefersReducedMotion",1);')
        browser.until(lambda:browser.js('return matchMedia("(prefers-reduced-motion: reduce)").matches;'))
        settle(browser)
        reduced=capture('edit')
        check('reduced motion makes the editor reveal immediate',not any(.02<f['fieldOpacity']<.98 for f in reduced[1:]),reduced)
        check('reduced motion disables decorative capsule and title transitions',browser.js('return [...document.querySelectorAll("#urlbar-container,#TabsToolbar .tab-stack,#TabsToolbar .tab-label-container,#TabsToolbar .tab-background")].every(e=>getComputedStyle(e).transitionDuration==="0s");'))
        capture('hide')
    finally:
        browser.js('if(window.whiteSurMotionTab?.isConnected)gBrowser.removeTab(window.whiteSurMotionTab,{animate:false,skipPermitUnload:true});delete window.whiteSurMotionTab;gURLBar.view.close();gURLBar.handleRevert();gBrowser.selectedBrowser.focus();if(arguments[0]===null)Services.prefs.clearUserPref("ui.prefersReducedMotion");else Services.prefs.setIntPref("ui.prefersReducedMotion",arguments[0]);',old_pref)
        settle(browser)
        (artifacts/'motion-report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        (artifacts/'motion-final.png').write_bytes(base64.b64decode(browser.call('GET','screenshot')))
    return results
