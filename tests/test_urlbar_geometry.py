import os
from pathlib import Path
import json
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
V14_CSS = PACKAGE / 'chrome' / 'windows.css'
FIXTURE = (ROOT / 'urlbar-geometry-fixture.html').read_text(encoding='utf-8')
BROKEN_SHOT = ROOT / 'urlbar-geometry-broken-v13.png'
FIXED_SHOT = ROOT / 'urlbar-geometry-fixed-v14.png'
REPORT = ROOT / 'urlbar-geometry-report.json'


def with_css(css_path: Path | None) -> str:
    css = '' if css_path is None else css_path.read_text(encoding='utf-8')
    return FIXTURE.replace('<link rel="stylesheet" href="../chrome/windows.css">', f'<style>{css}</style>')


def cyan_pixels_beyond(path: Path, right_edge: int) -> int:
    img = Image.open(path).convert('RGB')
    count = 0
    for y in range(0, min(48, img.height)):
        for x in range(min(right_edge + 2, img.width), img.width):
            r, g, b = img.getpixel((x, y))
            if b >= 180 and g >= 120 and r <= 80:
                count += 1
    return count


def geometry(page):
    return page.evaluate("""() => {
      const q = s => document.querySelector(s);
      const rect = e => { const r=e.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}; };
      const u=q('#urlbar'), b=q('#urlbar-background'), i=q('#urlbar-input-container'), c=q('#urlbar-container');
      return {
        urlbar: rect(u), container: rect(c), input: rect(i),
        urlbarPosition: getComputedStyle(u).position,
        urlbarPointerEvents: getComputedStyle(u).pointerEvents,
        backgroundDisplay: getComputedStyle(b).display,
        backgroundVisibility: getComputedStyle(b).visibility,
        inputPointerEvents: getComputedStyle(i).pointerEvents,
        viewDisplay: getComputedStyle(q('.urlbarView')).display,
      };
    }""")


report = {'broken_v13': {}, 'fixed_v14': {'states': {}}}
with sync_playwright() as p:
    launch_options = {'headless': True, 'args': ['--no-sandbox']}
    if executable := os.environ.get('CHROMIUM_EXECUTABLE'):
        launch_options['executable_path'] = executable
    browser = p.chromium.launch(**launch_options)

    # Reproduce the exact long URL-bar rectangle with the previous package.
    broken = browser.new_page(viewport={'width': 1264, 'height': 260}, device_scale_factor=1)
    broken.set_content(with_css(None), wait_until='load')
    broken.screenshot(path=str(BROKEN_SHOT), full_page=True)
    bgeo = geometry(broken)
    report['broken_v13']['geometry'] = bgeo
    broken.close()
    broken_pixels = cyan_pixels_beyond(BROKEN_SHOT, round(bgeo['container']['right']))
    report['broken_v13']['cyan_pixels_beyond_input'] = broken_pixels
    assert broken_pixels > 100, report['broken_v13']

    fixed = browser.new_page(viewport={'width': 1264, 'height': 260}, device_scale_factor=1)
    fixed.set_content(with_css(V14_CSS), wait_until='load')
    for state in ('focused-closed', 'unfocused-closed', 'focused-open'):
        fixed.evaluate("""(state) => {
          const u = document.querySelector('#urlbar');
          u.toggleAttribute('focused', state === 'focused-closed' || state === 'focused-open');
          u.toggleAttribute('open', state === 'focused-open');
        }""", state)
        fixed.wait_for_timeout(30)
        data = geometry(fixed)
        report['fixed_v14']['states'][state] = data
        assert data['urlbarPosition'] == 'absolute', data
        assert data['backgroundDisplay'] == 'none', data
        assert data['urlbarPointerEvents'] == 'none', data
        assert data['inputPointerEvents'] == 'auto', data
        assert abs(data['urlbar']['width'] - data['container']['width']) <= 1, data
        assert data['urlbar']['right'] <= data['container']['right'] + 1, data
        assert data['input']['right'] <= data['container']['right'] + 1, data
        assert (data['viewDisplay'] != 'none') == (state == 'focused-open'), data

    fixed.evaluate("""() => {
      const u = document.querySelector('#urlbar');
      u.setAttribute('focused','');
      u.removeAttribute('open');
    }""")
    fixed.screenshot(path=str(FIXED_SHOT), full_page=True)
    fgeo = geometry(fixed)
    fixed_pixels = cyan_pixels_beyond(FIXED_SHOT, round(fgeo['container']['right']))
    report['fixed_v14']['cyan_pixels_beyond_input'] = fixed_pixels
    assert fixed_pixels == 0, report['fixed_v14']

    fixed.locator('#tab-a').click()
    report['fixed_v14']['tab_clicks'] = fixed.evaluate('window.fixture.clicks')
    assert report['fixed_v14']['tab_clicks'] == 1
    fixed.close()
    browser.close()

REPORT.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
print(f'PASS: broken={BROKEN_SHOT.name}, fixed={FIXED_SHOT.name}')
