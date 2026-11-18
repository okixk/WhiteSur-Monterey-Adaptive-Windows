"""Verify native notification banners in disposable Full and Lite profiles."""

import argparse
import base64
import tempfile
from pathlib import Path

from test_compatible_firefox import install as install_lite, move, settle
from test_editable_tabs_firefox import Firefox, ROOT, install as install_full


MEASURE = """
const rect = element => element.getBoundingClientRect().toJSON();
const nav = rect(document.getElementById('nav-bar'));
const tabs = rect(document.getElementById('TabsToolbar'));
const bookmarks = rect(document.getElementById('PersonalToolbar'));
const field = rect(document.getElementById('urlbar-container'));
const content = rect(gBrowser.selectedBrowser);
const banner = document.querySelector('[value="whitesur-banner-test"]');
return {nav, tabs, bookmarks, field, content, banner: banner ? rect(banner) : null};
"""


def header_edges(layout):
    return tuple(layout[part][edge] for part in ('nav', 'tabs', 'bookmarks', 'field')
                 for edge in ('top', 'bottom', 'left', 'right'))


def check_banner(browser, edition, width, scope, artifacts):
    before = browser.js(MEASURE)
    # Use the native box and a stand-in for the slow-page warning. This renders
    # the exact browser widget and buttons without hanging a content process.
    result = browser.js("""
        const done = arguments[arguments.length - 1];
        const windowWide = arguments[0] === 'global';
        const box = windowWide ? gNotificationBox : gBrowser.getNotificationBox();
        window.whitesurBannerClicked = false;
        box.appendNotification('whitesur-banner-test', {
            label: windowWide ? 'This website is slowing down Firefox.' : 'This tab needs your attention.',
            priority: windowWide ? box.PRIORITY_INFO_HIGH : box.PRIORITY_WARNING_HIGH,
        }, [{label: 'Wait', callback() { window.whitesurBannerClicked = true; return false; }}])
            .then(() => done(true), error => done(String(error)));
    """, scope, asynchronous=True)
    assert result is True, result
    browser.until(lambda: browser.js("""
        const banner = document.querySelector('[value="whitesur-banner-test"]');
        return banner?.getBoundingClientRect().height > 0 && !banner.closest('.notificationbox-stack')?.getAnimations({subtree: true}).length;
    """))
    layout = browser.js(MEASURE)
    (artifacts / f'{edition}-{width}-{scope}.png').write_bytes(base64.b64decode(browser.call('GET', 'screenshot')))
    banner = layout['banner']
    assert header_edges(layout) == header_edges(before), (edition, width, scope, before, layout)
    assert banner['top'] >= max(layout[part]['bottom'] for part in ('nav', 'tabs', 'bookmarks', 'field')), layout
    assert banner['bottom'] <= layout['content']['top'], layout

    # Use a real pointer click, after Firefox enables the banner action.
    button = browser.until(lambda: browser.js("""
        const banner = document.querySelector('[value="whitesur-banner-test"]');
        const action = banner.querySelector('moz-button') ?? banner.querySelector('.notification-button');
        if (!action || action.disabled || action.hasAttribute('disabled')) return null;
        const r = action.getBoundingClientRect();
        return r.width && r.height ? {x: r.x + r.width / 2, y: r.y + r.height / 2} : null;
    """))
    move(browser, button['x'], button['y'], click=True)
    browser.until(lambda: browser.js("return window.whitesurBannerClicked && !document.querySelector('[value=\"whitesur-banner-test\"]');"))
    after = browser.js(MEASURE)
    assert header_edges(after) == header_edges(before), after
    assert after['content']['top'] == before['content']['top'], after
    print(f'PASS {edition}, {width}px, {scope} banner and dismissal', flush=True)


def run(source, driver, artifacts):
    artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='whitesur-banners-') as directory:
        lab = Path(directory)
        for edition in ('Full', 'Lite'):
            profile = lab / edition
            profile.mkdir()
            if edition == 'Full':
                binary = install_full(profile, source, lab / 'runtime', lab / 'shortcuts')
            else:
                binary = source
                install_lite(profile, binary)

            browser = Firefox(driver, binary, profile)
            try:
                assert browser.js('return !!window.TabSearch;') == (edition == 'Full')
                browser.js('gBrowser.selectedTab = gBrowser.addTrustedTab("about:robots");')
                browser.until(lambda: browser.js('return gBrowser.selectedBrowser.currentURI.spec === "about:robots";'))
                browser.js('gBrowser.selectedBrowser.focus();')
                for width in (1384, 800):
                    browser.call('POST', 'window/rect', {'width': width, 'height': 820})
                    settle(browser)
                    for scope in ('global', 'tab'):
                        check_banner(browser, edition, width, scope, artifacts)
            finally:
                browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--firefox', type=Path, required=True, help='Path to a clean source Firefox executable')
    parser.add_argument('--geckodriver', type=Path, required=True)
    parser.add_argument('--artifacts', type=Path, default=ROOT / 'tests/artifacts/notification-banners')
    args = parser.parse_args()
    run(args.firefox.resolve(), args.geckodriver.resolve(), args.artifacts.resolve())
