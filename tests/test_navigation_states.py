from __future__ import annotations

import os

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


def build_html() -> str:
    html = (ROOT / 'preview.html').read_text(encoding='utf-8')
    colors = (ROOT.parent / 'chrome' / 'Monterey' / 'colors' / 'dark-adaptive.css').read_text(encoding='utf-8')
    windows = (ROOT.parent / 'chrome' / 'windows.css').read_text(encoding='utf-8')
    return html.replace(
        '<link rel="stylesheet" href="../chrome/Monterey/colors/dark-adaptive.css">',
        f'<style>{colors}</style>',
    ).replace(
        '<link rel="stylesheet" href="../chrome/windows.css">',
        f'<style>{windows}</style>',
    )


def box(page, selector: str) -> dict[str, float]:
    rect = page.locator(selector).bounding_box()
    if rect is None:
        raise RuntimeError(selector)
    rect['right'] = rect['x'] + rect['width']
    return {k: round(v, 2) for k, v in rect.items()}


def main() -> int:
    report: dict[str, object] = {}
    with sync_playwright() as p:
        launch_options = {'headless': True, 'args': ['--no-sandbox']}
        if executable := os.environ.get('CHROMIUM_EXECUTABLE'):
            launch_options['executable_path'] = executable
        browser = p.chromium.launch(**launch_options)
        page = browser.new_page(viewport={'width': 1310, 'height': 260}, device_scale_factor=1)
        page.set_content(build_html(), wait_until='load')
        page.wait_for_timeout(50)

        disabled = {
            'forward': box(page, '#forward-button'),
            'urlbar': box(page, '#urlbar-container'),
            'tabs': box(page, '#TabsToolbar'),
            'visibility': page.locator('#forward-button').evaluate('el => getComputedStyle(el).visibility'),
        }
        page.screenshot(path=str(ROOT / 'navigation-forward-disabled.png'))

        page.locator('#forward-button').evaluate("el => el.removeAttribute('disabled')")
        page.wait_for_timeout(50)
        enabled = {
            'forward': box(page, '#forward-button'),
            'urlbar': box(page, '#urlbar-container'),
            'tabs': box(page, '#TabsToolbar'),
            'visibility': page.locator('#forward-button').evaluate('el => getComputedStyle(el).visibility'),
        }
        page.screenshot(path=str(ROOT / 'navigation-forward-enabled.png'))
        browser.close()

    disabled['url_tab_gap'] = round(disabled['tabs']['x'] - disabled['urlbar']['right'], 2)
    enabled['url_tab_gap'] = round(enabled['tabs']['x'] - enabled['urlbar']['right'], 2)
    report = {'disabled': disabled, 'enabled': enabled}
    report['stable'] = (
        abs(disabled['forward']['width'] - enabled['forward']['width']) < 0.6
        and abs(disabled['urlbar']['x'] - enabled['urlbar']['x']) < 0.6
        and disabled['url_tab_gap'] >= 8
        and enabled['url_tab_gap'] >= 8
    )
    (ROOT / 'navigation-spacing-report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['stable'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
