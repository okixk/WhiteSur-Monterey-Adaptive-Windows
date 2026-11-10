"""Full updater tests using real Firefox, real ZIPs and a real quit/relaunch.

GitHub responses are supplied by a transport fixture; all validation, extraction,
hashing, shutdown barriers and replacement run in the installed updater itself.
An optional network check only reads the public GitHub release API.
"""
from __future__ import annotations

import argparse
import base64
from contextlib import ExitStack
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import uuid
import zipfile
from pathlib import Path

from test_editable_tabs_firefox import Firefox, install, ROOT
sys.path.insert(0, str(ROOT))
from tools.build_release import build


def tree_hash(path):
    return {p.relative_to(path).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob('*') if p.is_file()}


def run(source, driver, artifacts, network=False):
    artifacts.mkdir(parents=True, exist_ok=True)
    results=[]
    browser=None

    def finish_browser():
        nonlocal browser
        if browser:
            browser.close();browser=None

    def check(name, condition, details=None):
        results.append({'name':name,'pass':bool(condition),'details':details})
        print(f"{'PASS' if condition else 'FAIL'}: {name}",flush=True)
        if not condition:
            raise AssertionError(f'{name}: {details}')

    def ready():
        return browser.js('''const done=arguments[arguments.length-1];
          WhiteSurUpdates.ready.then(()=>{
            const timer=ChromeUtils.importESModule('resource://gre/modules/Timer.sys.mjs');
            timer.clearTimeout(WhiteSurUpdates.timer);timer.clearInterval(WhiteSurUpdates.interval);
            done(WhiteSurUpdates.snapshot());});''',asynchronous=True)

    try:
        with tempfile.TemporaryDirectory(prefix='whitesur-updater-') as temporary, ExitStack() as lifecycle:
            lifecycle.callback(finish_browser)
            lab=Path(temporary)
            profile=lab/'profile';profile.mkdir()
            binary=install(profile,source,lab/'Firefox',lab/'links')
            settings=profile/'.whitesur-updater.json'
            config=json.loads(settings.read_text(encoding='utf-8-sig'))
            config['enabled']=True;settings.write_text(json.dumps(config))
            initial=tree_hash(profile/'chrome')
            security={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                binary.parent/'whitesur.cfg',binary.parent/'defaults/pref/whitesur-autoconfig.js')}
            base_archive=build('v99.0.0',lab/'dist')[0]
            with zipfile.ZipFile(base_archive) as z:
                base={name:z.read(name) for name in z.namelist()}
            package=next(iter(base)).split('/')[0]
            good=base.copy()
            good[package+'/VERSION.txt']=b'2099.01.01-1\n'
            good[package+'/chrome/tab-search.uc.js']=b'document.documentElement.setAttribute("whitesur-update-proof","applied");\n'+good[package+'/chrome/tab-search.uc.js']
            good[package+'/chrome/userChrome.css']+=b'\n:root { --whitesur-update-proof: 1; }\n'
            manifest=json.loads(good[package+'/release-manifest.json'])
            manifest['version']='2099.01.01-1'
            manifest['files']={name:hashlib.sha256(good[package+'/'+name]).hexdigest() for name in manifest['files']}
            good[package+'/release-manifest.json']=json.dumps(manifest).encode()

            def fixture(name, files=None, extra=(), digest=None, url=None, edition=None):
                path=lab/(name+'.zip')
                contents=(good if files is None else files).copy()
                if edition:
                    m=json.loads(contents[package+'/release-manifest.json']);m['edition']=edition
                    contents[package+'/release-manifest.json']=json.dumps(m).encode()
                with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as z:
                    for key,value in [*contents.items(),*extra]:z.writestr(key,value)
                if name=='backslash-path':
                    # ZipInfo normalizes Windows separators while writing;
                    # preserve the hostile raw name in both ZIP headers.
                    data=path.read_bytes().replace((package+'/chrome/outside.txt').encode(),(package+'/chrome\\outside.txt').encode())
                    path.write_bytes(data)
                asset_name=base_archive.name
                release={'tag_name':'v99.0.0','draft':False,'prerelease':False,'assets':[{
                    'name':asset_name,'size':path.stat().st_size,
                    'digest':digest or 'sha256:'+hashlib.sha256(path.read_bytes()).hexdigest(),
                    'browser_download_url':url or f'https://github.com/okixk/WhiteSur-Monterey-Adaptive-Windows/releases/download/v99.0.0/{asset_name}'}]}
                return path,release

            browser=Firefox(driver,binary,profile)
            ready()
            check('Full starts its updater through the installed loader',browser.js('return !!TabSearch&&WhiteSurUpdates.usable;'))
            check('update controls are available in the native Tools menu',browser.js('return !!document.getElementById("whitesur-updates-menu");'))
            # Open actual XUL menus, then use native pointer events on the
            # checkbox. This verifies autocheck and the persisted user control.
            browser.js('document.getElementById("tools-menu").openMenu(true);')
            browser.until(lambda: browser.js('return document.getElementById("menu_ToolsPopup").state==="open";'))
            browser.js('document.getElementById("whitesur-updates-menu").openMenu(true);')
            browser.until(lambda: browser.js('return document.querySelector("#whitesur-updates-menu > menupopup").state==="open";'))
            (artifacts/'updater-menu.png').write_bytes(base64.b64decode(browser.call('GET','screenshot')))
            item=browser.js('let r=document.querySelector("#whitesur-updates-menu > menupopup > menuitem:last-child").getBoundingClientRect();return {x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)};')
            browser.call('POST','actions',{'actions':[{'type':'pointer','id':'updater-mouse','parameters':{'pointerType':'mouse'},'actions':[
                {'type':'pointerMove','duration':0,'x':item['x'],'y':item['y']},
                {'type':'pointerDown','button':0},{'type':'pointerUp','button':0}]}]})
            browser.until(lambda: json.loads(settings.read_text(encoding='utf-8-sig'))['enabled'] is False)
            check('native Tools-menu checkbox disables and persists automatic updates',not json.loads(settings.read_text(encoding='utf-8-sig'))['enabled'])
            config['enabled']=True;settings.write_text(json.dumps(config))
            browser.js('document.querySelector("#whitesur-updates-menu > menupopup").hidePopup();document.getElementById("menu_ToolsPopup").hidePopup();')
            preserved=browser.js('''const done=arguments[arguments.length-1];(async()=>{
              const m=ChromeUtils.importESModule('resource://whitesur/whitesur-updater.sys.mjs');
              const p=PathUtils.join(PathUtils.profileDir,'invalid-state-fixture'),d=PathUtils.join(p,'.whitesur-updates');
              await IOUtils.makeDirectory(d,{createAncestors:true});
              await IOUtils.writeJSON(PathUtils.join(p,'.whitesur-updater.json'),{schema:1,owner:m.OWNER,edition:'Full',enabled:true,allowPrerelease:true});
              await IOUtils.writeJSON(PathUtils.join(d,'owner.json'),{schema:1,owner:m.OWNER});
              const path=PathUtils.join(d,'state.json'),original=JSON.stringify({schema:999,owner:'unmanaged'});
              await IOUtils.writeUTF8(path,original);
              const u=new m.ThemeUpdater(p);u.ready=u.initialize().catch(()=>{});await u.ready;
              let calls=0;await u.checkForUpdates({force:true,fetcher:async()=>{calls++;throw Error('unexpected network');}});
              return !u.usable&&calls===0&&(await IOUtils.readUTF8(path))===original;
            })().then(done,e=>done({error:String(e)}));''',asynchronous=True)
            check('invalid updater ownership/state is preserved without network or writes',preserved is True,preserved)

            def request(path, release, force=True):
                return browser.js('''const done=arguments[arguments.length-1],release=arguments[0],path=arguments[1],force=arguments[2];
                  const fetcher=async url=>url.startsWith('https://api.github.com/')?new TextEncoder().encode(JSON.stringify([release])):IOUtils.read(path);
                  WhiteSurUpdates.checkForUpdates({force,fetcher}).then(done);''',release,str(path),force,asynchronous=True)

            bad_cases=[
                ('corrupt-download',{}, {'digest':'sha256:'+'0'*64}),
                ('wrong-host',{}, {'url':'https://example.invalid/update.zip'}),
                ('lite-package',{}, {'edition':'Lite'}),
                ('zip-slip',{'extra':[(package+'/../outside.txt',b'no')]},{}),
                ('absolute-path',{'extra':[('C:/outside.txt',b'no')]},{}),
                ('backslash-path',{'extra':[(package+'/chrome\\outside.txt',b'no')]},{}),
                ('windows-alias',{'extra':[(package+'/chrome/CON.txt',b'no')]},{}),
                ('case-collision',{'extra':[(package+'/chrome/USERCHROME.css',b'no')]},{}),
            ]
            link=zipfile.ZipInfo(package+'/chrome/link.css');link.create_system=3;link.external_attr=0o120777<<16
            bad_cases.append(('archive-symlink',{'extra':[(link,b'../../outside.css')]},{}))
            altered=good.copy();altered[package+'/chrome/tab-search.uc.js']+=b'/* altered after manifest */'
            bad_cases.append(('bad-file-hash',{'files':altered},{}))
            incomplete=good.copy();del incomplete[package+'/release-manifest.json']
            bad_cases.append(('missing-manifest',{'files':incomplete},{}))
            oversized=good.copy();oversized[package+'/chrome/windows.css']=b'x'*(8*1024*1024+1)
            bad_cases.append(('oversized-file',{'files':oversized},{}))
            for name,options,release_options in bad_cases:
                path,release=fixture(name,**options,**release_options)
                state=request(path,release)
                check(f'{name} is rejected without changing the theme',state['status']=='error' and not state['pending'] and tree_hash(profile/'chrome')==initial,state.get('error'))
            incompatible=good.copy();im=json.loads(incompatible[package+'/release-manifest.json']);im['loaderProtocol']=2
            incompatible[package+'/release-manifest.json']=json.dumps(im).encode()
            path,release=fixture('manual-loader-change',files=incompatible)
            state=request(path,release)
            check('loader changes require manual installation instead of rewriting cfg',state['status']=='manual' and not state['pending'] and tree_hash(profile/'chrome')==initial)
            path,release=fixture('older-version',files=base)
            state=request(path,release)
            check('equal/older releases never replace the installed theme',state['status']=='up-to-date' and not state['pending'] and tree_hash(profile/'chrome')==initial)
            legacy=base.copy();del legacy[package+'/release-manifest.json']
            path,release=fixture('older-legacy-release',files=legacy)
            state=request(path,release)
            check('older pre-manifest releases are ignored without a permanent error',state['status']=='up-to-date' and not state['pending'] and tree_hash(profile/'chrome')==initial)
            throttled=browser.js('const done=arguments[arguments.length-1];let calls=0;WhiteSurUpdates.checkForUpdates({fetcher:async()=>{calls++;throw Error("unexpected network");}}).then(()=>done(calls));',asynchronous=True)
            check('automatic checks are limited to once per day',throttled==0)
            check('failed checks do not escape the profile staging directory',not (lab/'outside.txt').exists() and not (profile/'outside.txt').exists())

            path,release=fixture('valid')
            state=request(path,release)
            check('a valid Full release is staged for the next restart',state['status']=='pending' and state['pending']['version']=='2099.01.01-1',state)
            check('staging leaves the currently running theme untouched',tree_hash(profile/'chrome')==initial and browser.js('return !document.documentElement.hasAttribute("whitesur-update-proof");'))
            # Exercise rollback with a deterministic filesystem failure between
            # the two real directory moves. No production source is injected.
            rolled=browser.js('''const done=arguments[arguments.length-1],u=WhiteSurUpdates,original=u.move;
              let fail=true;u.move=async(from,to,options)=>{if(fail&&from.includes('stage-')&&to===u.chrome){fail=false;throw Error('fixture replacement failure');}return original(from,to,options);};
              u.applyPending().then(()=>done(false),error=>{u.move=original;done(error.message);});''',asynchronous=True)
            check('failed replacement restores the previous working theme',rolled=='fixture replacement failure' and tree_hash(profile/'chrome')==initial)
            check('failed replacement clears its pending update for a clean retry',not browser.js('return WhiteSurUpdates.snapshot().pending;'))

            state=request(path,release)
            stage=profile/'.whitesur-updates'/state['pending']['directory']/'chrome/tab-search.uc.js'
            stage.write_bytes(stage.read_bytes()+b'/* tampered staged file */')
            rejected=browser.js('const done=arguments[arguments.length-1];WhiteSurUpdates.applyPending().then(()=>done(false),e=>done(e.message));',asynchronous=True)
            check('staged files are rehashed before application',bool(rejected) and tree_hash(profile/'chrome')==initial)
            state=request(path,release)
            pending_manifest=profile/'.whitesur-updates'/state['pending']['directory']/'manifest.json'
            pending_manifest.write_text(pending_manifest.read_text()+' ')
            rejected=browser.js('const done=arguments[arguments.length-1];WhiteSurUpdates.applyPending().then(()=>done(false),e=>done(e.message));',asynchronous=True)
            check('a changed staged manifest is rejected before replacement',rejected=='Staged manifest changed.' and tree_hash(profile/'chrome')==initial)

            config['enabled']=False;settings.write_text(json.dumps(config))
            skipped=browser.js('const done=arguments[arguments.length-1];let calls=0;WhiteSurUpdates.checkForUpdates({fetcher:async()=>{calls++;throw Error("unexpected network");}}).then(()=>done(calls));',asynchronous=True)
            check('disabled automatic updates make no network request',skipped==0)
            config['enabled']=True;settings.write_text(json.dumps(config))
            state=request(path,release)
            check('a clean retry can stage a valid update again',state['status']=='pending')
            (profile/'chrome/customChrome.css').write_text('/* edited after staging */\n:root { --whitesur-custom-proof: 42; }\n')
            (artifacts/'before-restart.png').write_bytes(base64.b64decode(browser.call('GET','screenshot')))
            browser.close();browser=None
            applied=json.loads((profile/'.whitesur-updates/state.json').read_text())
            check('real Firefox shutdown applies the staged update',applied['status']=='applied' and applied['pending'] is None,applied)
            check('shutdown preserves custom CSS edited after download','edited after staging' in (profile/'chrome/customChrome.css').read_text())
            check('shutdown leaves updater preferences unchanged',json.loads(settings.read_text())==config)
            check('a rollback copy of the previous theme is retained',(profile/'.whitesur-updates'/applied['backup']/'tab-search.uc.js').is_file())
            check('no AutoConfig installation files change during updating',all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in security.items()))
            browser=Firefox(driver,binary,profile);ready()
            check('the next Firefox start executes the updated theme script',browser.js('return document.documentElement.getAttribute("whitesur-update-proof")==="applied"&&!!TabSearch;'))
            check('the next Firefox start loads updated CSS and user overrides',browser.js('let s=getComputedStyle(document.documentElement);return s.getPropertyValue("--whitesur-update-proof").trim()==="1"&&s.getPropertyValue("--whitesur-custom-proof").trim()==="42";'))
            if network:
                response=browser.js('''const done=arguments[arguments.length-1];const m=ChromeUtils.importESModule('resource://whitesur/whitesur-updater.sys.mjs');m.fetchBytes(m.RELEASES_URL,{maxBytes:2097152}).then(b=>{const r=JSON.parse(new TextDecoder().decode(b));done({array:Array.isArray(r),count:r.length});},e=>done({error:e.message}));''',asynchronous=True)
                check('the real GitHub release API is readable in Firefox',response.get('array') is True,response)
            (artifacts/'after-restart.png').write_bytes(base64.b64decode(browser.call('GET','screenshot')))
            # Switching editions while this isolated browser is alive exercises
            # the shutdown guard: a previously loaded Full updater must not
            # replace the newly installed Lite theme.
            future=good.copy();future[package+'/VERSION.txt']=b'2099.01.02-1\n'
            fm=json.loads(future[package+'/release-manifest.json']);fm['version']='2099.01.02-1'
            future[package+'/release-manifest.json']=json.dumps(fm).encode()
            future_path,future_release=fixture('future',files=future)
            state=request(future_path,future_release)
            check('a second update is pending before switching to Lite',state['status']=='pending')
            subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Install-WhiteSur-Monterey-Adaptive.ps1'),'-ProfilePath',str(profile),'-FirefoxPath',str(binary),'-Edition','Lite','-Force'],check=True,capture_output=True)
            lite=tree_hash(profile/'chrome')
            browser.close();browser=None
            check('Full-to-Lite migration disables and removes the updater',not settings.exists() and not (profile/'chrome/whitesur-updater.sys.mjs').exists())
            check('a loaded Full updater cannot replace Lite during shutdown',tree_hash(profile/'chrome')==lite)
            check('switching to Lite cancels a queued Full update',json.loads((profile/'.whitesur-updates/state.json').read_text(encoding='utf-8-sig'))['pending'] is None)
            browser=Firefox(driver,binary,profile)
            check('Lite restarts without any privileged theme runtime',browser.js('return !window.TabSearch&&!window.WhiteSurUpdates;'))
            browser.close();browser=None
            repair=lab/'repair-profile';repair.mkdir()
            def install_edition(target,edition):
                result=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Install-WhiteSur-Monterey-Adaptive.ps1'),'-ProfilePath',str(target),'-FirefoxPath',str(binary),'-Edition',edition,'-DisableAutoUpdate','-Force'],capture_output=True,text=True,errors='replace')
                if result.returncode:raise RuntimeError(result.stdout+result.stderr)
                return result.stdout
            install_edition(repair,'Full')
            (repair/'chrome/customChrome.css').write_text('/* recover my overrides */')
            updates=repair/'.whitesur-updates';updates.mkdir()
            (updates/'owner.json').write_text(json.dumps({'schema':1,'owner':'WhiteSur-Monterey-Adaptive-Windows'}))
            backup='rollback-'+str(uuid.uuid4())
            shutil.move(repair/'chrome',updates/backup)
            (updates/'transaction.json').write_text(json.dumps({'schema':1,'owner':'WhiteSur-Monterey-Adaptive-Windows','backup':backup}))
            output=install_edition(repair,'Lite')
            check('installer recovers a backup if a power interruption left chrome absent','Recovered the previous Full theme' in output and (repair/'chrome/customChrome.css').read_text()=='/* recover my overrides */')
    finally:
        if browser:browser.close()
        (artifacts/'report.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print(f'Result: {len(results)} Full updater checks passed',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firefox',type=Path,required=True)
    parser.add_argument('--geckodriver',type=Path,required=True)
    parser.add_argument('--artifacts',type=Path,default=ROOT/'tests/artifacts/full-updater')
    parser.add_argument('--network',action='store_true')
    args=parser.parse_args()
    run(args.firefox.resolve(),args.geckodriver.resolve(),args.artifacts.resolve(),args.network)
