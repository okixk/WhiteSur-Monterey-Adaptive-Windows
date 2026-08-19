from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TABS_CSS = ROOT / "chrome" / "Monterey" / "parts" / "tabsbar.css"

FIXTURE_CSS = r"""
:root {
  --gnome-tabbar-tab-color: rgb(220, 220, 225);
  --gnome-tabbar-tab-active-color: rgb(255, 255, 255);
  --gnome-tabbar-tab-background: rgb(42, 42, 48);
  --gnome-inactive-tabbar-tab-background: rgb(35, 35, 40);
  --gnome-tabbar-tab-hover-background: rgb(58, 58, 66);
  --gnome-tabbar-tab-active-background: rgb(76, 76, 86);
  --gnome-inactive-tabbar-tab-active-background: rgb(62, 62, 70);
}
body { margin: 24px; background: rgb(30, 30, 35); }
#TabsToolbar { display: flex; gap: 8px; }
.tabbrowser-tab { display: block; width: 180px; height: 32px; }
.tab-stack, .tab-background { display: block; width: 100%; height: 32px; }
"""

MARKUP = r"""
<div id="TabsToolbar">
  <div id="inactive" class="tabbrowser-tab">
    <div class="tab-stack"><div class="tab-background"></div></div>
  </div>

  <!-- Firefox 154-style boolean state on the tab element. -->
  <div id="selected-parent" class="tabbrowser-tab" selected visuallyselected>
    <div class="tab-stack"><div class="tab-background"></div></div>
  </div>

  <!-- Compatibility if selected state is also propagated to tab-background. -->
  <div id="selected-background" class="tabbrowser-tab">
    <div class="tab-stack"><div class="tab-background" selected></div></div>
  </div>

  <!-- Firefox also exposes this spelling in moving/multiselect state. -->
  <div id="visually-selected-parent" class="tabbrowser-tab" visually-selected>
    <div class="tab-stack"><div class="tab-background"></div></div>
  </div>
</div>
"""


def normalize(value: str) -> str:
    return value.replace(" ", "")


def main() -> None:
    css = TABS_CSS.read_text(encoding="utf-8")

    for selector in (
        "[selected=true]",
        '[selected="true"]',
        '[visuallyselected="true"]',
    ):
        assert selector not in css, f"stale pseudo-boolean selector remains: {selector}"

    with sync_playwright() as p:
        launch_options: dict[str, object] = {
            "headless": True,
            "args": ["--no-sandbox"],
        }
        if executable := os.environ.get("CHROMIUM_EXECUTABLE"):
            launch_options["executable_path"] = executable

        browser = p.chromium.launch(**launch_options)
        page = browser.new_page()
        page.set_content(f"<style>{css}\n{FIXTURE_CSS}</style>{MARKUP}")

        def background(tab_id: str) -> str:
            return page.locator(f"#{tab_id} .tab-background").evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )

        inactive = normalize(background("inactive"))
        selected_parent = normalize(background("selected-parent"))
        selected_background = normalize(background("selected-background"))
        visually_selected = normalize(background("visually-selected-parent"))

        expected_inactive = "rgb(42,42,48)"
        expected_active = "rgb(76,76,86)"

        assert inactive == expected_inactive, (inactive, expected_inactive)
        assert selected_parent == expected_active, (selected_parent, expected_active)
        assert selected_background == expected_active, (selected_background, expected_active)
        assert visually_selected == expected_active, (visually_selected, expected_active)
        assert selected_parent != inactive

        browser.close()

    print("PASS: Firefox 154 selected-tab boolean state is visually distinct")


if __name__ == "__main__":
    main()
