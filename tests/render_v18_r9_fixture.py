from pathlib import Path
import os

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "chrome" / "windows.css").read_text(encoding="utf-8")
r8_start = text.index("/* BEGIN v18-r8 taskbar-action-icon */")
r9_end = text.index("/* END v18-r9 toolbar-integration */")
css = text[r8_start : r9_end]


def markup(extension_count: int, downloads_hidden: bool) -> str:
    extensions = "".join(
        f'<toolbaritem id="extension-{index}-browser-action"></toolbaritem>'
        for index in range(extension_count)
    )
    hidden = " hidden" if downloads_hidden else ""
    return f"""<!doctype html>
<html customtitlebar="true">
<head><style>
* {{ box-sizing: border-box; }}
:root {{ --whitesur-left-zone: 498px; }}
body {{ margin: 0; }}
#navigator-toolbox {{ position: relative; width: 1186px; height: 48px; }}
#TabsToolbar {{
  position: absolute;
  left: var(--whitesur-left-zone);
  right: var(--whitesur-right-zone);
  height: 48px;
}}
#nav-bar-customization-target {{
  position: absolute;
  right: 186px;
  display: flex;
  height: 32px;
}}
#downloads-button, #unified-extensions-button,
#nav-bar-customization-target > toolbaritem {{ width: 44px; height: 32px; }}
#urlbar-actions {{ display: flex; align-items: center; height: 32px; }}
#translations-button, #star-button-box {{ width: 28px; height: 26px; }}
{css}
</style></head>
<body><div id="navigator-toolbox">
  <div id="TabsToolbar"></div>
  <div id="nav-bar-customization-target">
    <button id="downloads-button"{hidden}></button>
    <button id="unified-extensions-button"></button>
    {extensions}
  </div>
</div>
<div id="urlbar-actions">
  <div id="taskbar-tabs-button"><span class="urlbar-icon"></span></div>
  <div id="translations-button"></div>
  <div id="star-button-box"></div>
</div></body></html>"""


with sync_playwright() as p:
    launch_options = {"headless": True, "args": ["--no-sandbox"]}
    if executable := os.environ.get("CHROMIUM_EXECUTABLE"):
        launch_options["executable_path"] = executable
    browser = p.chromium.launch(**launch_options)
    page = browser.new_page(viewport={"width": 1186, "height": 100})

    scenarios = [
        (0, True, 246),
        (1, True, 290),
        (2, True, 334),
        (1, False, 334),
    ]
    for extension_count, downloads_hidden, expected_reserve in scenarios:
        page.set_content(markup(extension_count, downloads_hidden))
        values = page.evaluate("""
        () => {
          const rect = selector => {
            const r = document.querySelector(selector).getBoundingClientRect();
            return { x: r.x, width: r.width, right: r.right, height: r.height };
          };
          const firstTool = document.querySelector(
            '#downloads-button:not([hidden]), #unified-extensions-button'
          );
          return {
            tabs: rect('#TabsToolbar'),
            firstTool: { x: firstTool.getBoundingClientRect().x },
          };
        }
        """)
        used_reserve = 1186 - values["tabs"]["right"]
        gap = values["firstTool"]["x"] - values["tabs"]["right"]
        assert abs(used_reserve - expected_reserve) < 0.6, values
        assert gap >= 8, values

    page.set_content(markup(1, True))
    actions = page.evaluate("""
    () => [...document.querySelector('#urlbar-actions').children].map(node => {
      const r = node.getBoundingClientRect();
      return { id: node.id, x: r.x, width: r.width, height: r.height };
    })
    """)
    browser.close()

assert [item["width"] for item in actions] == [28, 28, 28], actions
assert [item["height"] for item in actions] == [26, 26, 26], actions
assert actions[1]["x"] - actions[0]["x"] == 28, actions
assert actions[2]["x"] - actions[1]["x"] == 28, actions

print("PASS: 0/1/2 pinned-extension and visible-Downloads boundaries do not overlap")
print("PASS: Add to taskbar, Translate and Bookmark use a regular 28px cadence")
