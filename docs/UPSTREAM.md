# Upstream and adaptation notes

The visual base comes from `vinceliuice/WhiteSur-firefox-theme`, with selected layout ideas compared against `rafaelmardojai/firefox-gnome-theme` and `AdamXweb/WhiteSurFirefoxThemeMacOS`.

This package intentionally does not import the Linux toolbox/CSD/title-button geometry. Windows keeps Firefox's native caption controls on the right and uses a dedicated one-row layout.

## Version 15 Windows-specific changes

Firefox can collapse its disabled Forward button and later restore it when browsing history changes. In a normal Firefox layout that is harmless, but this adaptation places the tab toolbar in a separately positioned centre zone. Version 15 keeps the disabled Forward button's slot in layout, preventing the URLbar endpoint from shifting into the first tab.

For restored-window dragging, version 15 follows Firefox's native draggable-region mechanism:

- empty browser-titlebar containers are marked `-moz-window-dragging: drag`;
- actual controls and tabs are marked `no-drag`;
- the tabstrip container itself may contribute empty draggable area, while individual tabs remain interactive.

Version 14's URLbar popover-host geometry reset remains unchanged and continues to prevent the detached right-edge artifact.
