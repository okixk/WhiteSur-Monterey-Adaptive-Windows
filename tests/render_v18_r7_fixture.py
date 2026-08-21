from pathlib import Path
import os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "v18-r7-toolbar.html"

with sync_playwright() as p:
    launch_options = {"headless": True, "args": ["--no-sandbox"]}
    if executable := os.environ.get("CHROMIUM_EXECUTABLE"):
        launch_options["executable_path"] = executable
    browser = p.chromium.launch(**launch_options)
    page = browser.new_page(viewport={"width": 1285, "height": 100})
    page.set_content(FIXTURE.read_text(encoding="utf-8"), wait_until="load")

    values = page.evaluate("""
    () => {
      const r = s => {
        const x = document.querySelector(s).getBoundingClientRect();
        return {x:x.x, width:x.width, right:x.right};
      };
      return {
        tabs: r("#TabsToolbar"),
        tail: r("#tail-probe"),
        tools: r("#right-tools"),
        rightZone: getComputedStyle(document.documentElement)
          .getPropertyValue("--whitesur-right-zone").trim()
      };
    }
    """)

    browser.close()

assert values["rightZone"] == "224px", values
assert values["tabs"]["width"] == 1285 - 498 - 224, values
assert values["tail"]["width"] > 200, values
assert values["tabs"]["right"] <= values["tools"]["x"] + 15, values

print(f'PASS: hidden Downloads reclaims the real right-side gap ({values["rightZone"]})')
print(f'PASS: TabsToolbar grows to {values["tabs"]["width"]:.0f}px')
print(f'PASS: real post-tab tail remains inside the tab strip ({values["tail"]["width"]:.0f}px)')
