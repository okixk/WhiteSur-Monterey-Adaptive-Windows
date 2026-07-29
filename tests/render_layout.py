from __future__ import annotations

import os

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
WIDTHS = (600, 650, 720, 820, 900, 960, 980, 981, 1000, 1048, 1070, 1100, 1285, 1437, 1668)
HEIGHT = 500
COMPACT_BREAKPOINT = 980


def rect(page, selector: str) -> dict[str, float]:
    value = page.locator(selector).bounding_box()
    if value is None:
        raise RuntimeError(f"Missing layout box: {selector}")
    return value


def rect_or_none(page, selector: str) -> dict[str, float] | None:
    return page.locator(selector).bounding_box()


def build_html() -> str:
    html = (ROOT / "preview.html").read_text(encoding="utf-8")
    colors = (ROOT.parent / "chrome" / "Monterey" / "colors" / "dark-adaptive.css").read_text(encoding="utf-8")
    windows = (ROOT.parent / "chrome" / "windows.css").read_text(encoding="utf-8")
    html = html.replace(
        '<link rel="stylesheet" href="../chrome/Monterey/colors/dark-adaptive.css">',
        f"<style>{colors}</style>",
    )
    html = html.replace(
        '<link rel="stylesheet" href="../chrome/windows.css">',
        f"<style>{windows}</style>",
    )
    return html


def main() -> int:
    reports: list[dict[str, object]] = []
    failures: list[str] = []
    html = build_html()

    with sync_playwright() as p:
        launch_options = {'headless': True, 'args': ['--no-sandbox']}
        if executable := os.environ.get('CHROMIUM_EXECUTABLE'):
            launch_options['executable_path'] = executable
        browser = p.chromium.launch(**launch_options)
        try:
            for width in WIDTHS:
                page = browser.new_page(viewport={"width": width, "height": HEIGHT}, device_scale_factor=1)
                page.set_content(html, wait_until="load")
                page.wait_for_timeout(50)

                compact = width <= COMPACT_BREAKPOINT
                toolbox = rect(page, "#navigator-toolbox")
                nav_bar = rect(page, "#nav-bar")
                urlbar = rect(page, "#urlbar-container")
                forward_disabled = rect(page, "#forward-button")
                forward_disabled_visibility = page.locator("#forward-button").evaluate(
                    "el => getComputedStyle(el).visibility"
                )
                page.locator("#forward-button").evaluate("el => el.removeAttribute('disabled')")
                page.wait_for_timeout(20)
                urlbar_forward_enabled = rect(page, "#urlbar-container")
                forward_enabled = rect(page, "#forward-button")
                forward_enabled_visibility = page.locator("#forward-button").evaluate(
                    "el => getComputedStyle(el).visibility"
                )
                page.locator("#forward-button").evaluate(
                    "el => el.setAttribute('disabled', 'true')"
                )
                page.wait_for_timeout(20)
                tabs_toolbar = rect_or_none(page, "#TabsToolbar")
                controls = rect(page, "#nav-bar > .native-controls")
                panel_ui = rect(page, "#PanelUI-button")
                first_right_tool = rect_or_none(page, "#downloads-button")
                duplicate_display = page.locator("#TabsToolbar > .duplicate-controls").evaluate(
                    "el => getComputedStyle(el).display"
                )
                tabs_display = page.locator("#TabsToolbar").evaluate("el => getComputedStyle(el).display")
                tabs_visibility = page.locator("#TabsToolbar").evaluate("el => getComputedStyle(el).visibility")
                toolbar_pointer_events = page.locator("#TabsToolbar").evaluate(
                    "el => getComputedStyle(el).pointerEvents"
                )
                tabs_pointer_events = page.locator("#tabbrowser-tabs").evaluate(
                    "el => getComputedStyle(el).pointerEvents"
                )
                closing_tab = rect_or_none(page, ".closing-test-tab")
                closing_spacer_display = page.locator(".closing-tabs-spacer").evaluate(
                    "el => getComputedStyle(el).display"
                )
                selected_close_image = page.locator(
                    ".tabbrowser-tab[selected] .tab-close-button"
                ).evaluate("el => getComputedStyle(el).listStyleImage")
                downloads_display = page.locator("#downloads-button").evaluate(
                    "el => getComputedStyle(el).display"
                )
                spring_wrapper_display = page.locator("#wrapper-customizableui-special-spring-test").evaluate(
                    "el => getComputedStyle(el).display"
                )
                spring_display = page.locator("#artifact-spring").evaluate(
                    "el => getComputedStyle(el).display"
                )

                controls_right_gap = width - (controls["x"] + controls["width"])
                panel_controls_gap = controls["x"] - (panel_ui["x"] + panel_ui["width"])

                checks: dict[str, bool] = {
                    "header_48px": abs(toolbox["height"] - 48) < 0.6 and abs(nav_bar["height"] - 48) < 0.6,
                    "controls_flush_right": abs(controls_right_gap) < 0.6,
                    "panel_before_controls": panel_controls_gap >= -0.6,
                    "duplicate_controls_hidden": duplicate_display == "none",
                    "urlbar_usable": urlbar["width"] >= (120 if compact else 150),
                    "closing_spacer_removed": closing_spacer_display == "none",
                    "simple_close_icon": "close-12.svg" in selected_close_image,
                    "spring_artifact_removed": spring_wrapper_display == "none" and spring_display == "none",
                    "forward_slot_reserved": (
                        forward_disabled["width"] >= 30
                        and abs(forward_disabled["width"] - forward_enabled["width"]) < 0.6
                        and abs(urlbar["x"] - urlbar_forward_enabled["x"]) < 0.6
                        and forward_disabled_visibility == "hidden"
                        and forward_enabled_visibility != "hidden"
                    ),
                }

                urlbar_tabs_gap = None
                tabs_right_tools_gap = None
                tabs_controls_gap = None

                if compact:
                    checks.update(
                        {
                            "compact_tabs_hidden": tabs_display == "none" and tabs_visibility == "hidden",
                            "compact_nonessential_tool_hidden": downloads_display == "none",
                            "compact_url_before_menu": urlbar["x"] + urlbar["width"] <= panel_ui["x"] + 0.6,
                        }
                    )
                else:
                    if tabs_toolbar is None or first_right_tool is None or closing_tab is None:
                        checks["desktop_required_boxes_exist"] = False
                    else:
                        tabs = rect(page, "#tabbrowser-tabs")
                        urlbar_tabs_gap = tabs_toolbar["x"] - (urlbar["x"] + urlbar["width"])
                        urlbar_tabs_gap_forward_enabled = tabs_toolbar["x"] - (
                            urlbar_forward_enabled["x"] + urlbar_forward_enabled["width"]
                        )
                        tabs_right_tools_gap = first_right_tool["x"] - (
                            tabs_toolbar["x"] + tabs_toolbar["width"]
                        )
                        tabs_controls_gap = controls["x"] - (
                            tabs_toolbar["x"] + tabs_toolbar["width"]
                        )
                        checks.update(
                            {
                                "desktop_single_row": (
                                    abs(nav_bar["y"]) < 0.6
                                    and abs(tabs_toolbar["y"]) < 0.6
                                    and abs(tabs_toolbar["height"] - 48) < 0.6
                                ),
                                "urlbar_before_tabs": urlbar_tabs_gap >= 7.5,
                                "urlbar_before_tabs_with_forward": urlbar_tabs_gap_forward_enabled >= 7.5,
                                "tabs_before_right_tools": tabs_right_tools_gap >= 7.5,
                                "tabs_before_controls": tabs_controls_gap >= -0.6,
                                "tabs_visible": tabs_toolbar["width"] >= 180,
                                "transparent_toolbar_does_not_capture": (
                                    toolbar_pointer_events == "none" and tabs_pointer_events == "auto"
                                ),
                                "closing_tab_collapses": closing_tab["width"] <= 1,
                            }
                        )

                for name, passed in checks.items():
                    if not passed:
                        failures.append(f"{width}px: {name}")

                page.screenshot(path=str(ROOT / f"preview-{width}.png"), full_page=True)
                reports.append(
                    {
                        "width": width,
                        "compact": compact,
                        "toolbox": toolbox,
                        "nav_bar": nav_bar,
                        "urlbar": urlbar,
                        "urlbar_forward_enabled": urlbar_forward_enabled,
                        "forward_disabled": forward_disabled,
                        "forward_enabled": forward_enabled,
                        "forward_disabled_visibility": forward_disabled_visibility,
                        "forward_enabled_visibility": forward_enabled_visibility,
                        "tabs_toolbar": tabs_toolbar,
                        "controls": controls,
                        "panel_ui": panel_ui,
                        "first_right_tool": first_right_tool,
                        "duplicate_display": duplicate_display,
                        "tabs_display": tabs_display,
                        "tabs_visibility": tabs_visibility,
                        "toolbar_pointer_events": toolbar_pointer_events,
                        "tabs_pointer_events": tabs_pointer_events,
                        "closing_tab": closing_tab,
                        "closing_spacer_display": closing_spacer_display,
                        "selected_close_image": selected_close_image,
                        "downloads_display": downloads_display,
                        "spring_wrapper_display": spring_wrapper_display,
                        "spring_display": spring_display,
                        "urlbar_tabs_gap": None if urlbar_tabs_gap is None else round(urlbar_tabs_gap, 2),
                        "urlbar_tabs_gap_forward_enabled": (
                            None
                            if compact or tabs_toolbar is None
                            else round(urlbar_tabs_gap_forward_enabled, 2)
                        ),
                        "tabs_right_tools_gap": None if tabs_right_tools_gap is None else round(tabs_right_tools_gap, 2),
                        "tabs_controls_gap": None if tabs_controls_gap is None else round(tabs_controls_gap, 2),
                        "controls_right_gap": round(controls_right_gap, 2),
                        "checks": checks,
                    }
                )
                page.close()
        finally:
            browser.close()

    (ROOT / "layout-report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")

    lines = ["WhiteSur Monterey Adaptive Windows v15 rendered interaction/layout test", ""]
    for report in reports:
        checks = report["checks"]
        status = "PASS" if all(checks.values()) else "FAIL"
        if report["compact"]:
            lines.append(
                f"{status} {report['width']}px — compact navigation-only mode; tabs hidden; "
                f"URL {report['urlbar']['width']:.1f}px"
            )
        else:
            lines.append(
                f"{status} {report['width']}px — one row, tabs {report['tabs_toolbar']['width']:.1f}px, "
                f"URL {report['urlbar']['width']:.1f}px, URL/tab gap {report['urlbar_tabs_gap']}px "
                f"(forward on: {report['urlbar_tabs_gap_forward_enabled']}px), "
                f"tab/right-tools gap {report['tabs_right_tools_gap']}px"
            )
    if failures:
        lines.extend(["", "Failures:", *[f"- {item}" for item in failures]])
    else:
        lines.extend(["", "All rendered responsive and collision checks passed."])

    (ROOT / "RENDERED-LAYOUT-RESULTS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
