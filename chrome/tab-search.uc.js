// The selected Firefox tab displays the native address field and its actions.
(() => {
  if (window.TabSearch || !window.gBrowser || !window.gURLBar) return;
  // Keep the original CSS toolbar on older Firefox and unsupported window
  // types. Only activate after all required UI capabilities are present.
  if (Number.parseInt(Services.appinfo.version, 10) < 158 ||
      !Services.prefs.getBoolPref('userChrome.tabSearch.enabled', true)) return;
  const root = document.documentElement;
  const tabs = gBrowser.tabContainer;
  const container = document.getElementById('urlbar-container');
  const strip = document.getElementById('TabsToolbar');
  if (!container || !strip || root.hasAttribute('taskbartab') || tabs.verticalMode ||
      Services.prefs.getBoolPref('sidebar.verticalTabs', false) ||
      !tabs.arrowScrollbox?.scrollbox || !gURLBar.inputField || !gURLBar.view ||
      typeof gBrowser.addTab !== 'function' || typeof gBrowser.removeTab !== 'function' ||
      typeof ResizeObserver !== 'function' || typeof AbortController !== 'function') return;
  const abort = new AbortController();
  const listeners = { signal: abort.signal };
  let editingTab = null, frame = 0, pointer = null, suspended = false;
  const scrollbox = tabs.arrowScrollbox;
  const originalSmoothScroll = scrollbox.getAttribute('smoothscroll');
  scrollbox.smoothScroll = false;
  const spacer = document.createXULElement('toolbarspacer');
  spacer.id = 'tabsearch-spacer';
  container.after(spacer);
  const set = (key, value) => {
    const name = '--tabsearch-' + key;
    const pixels = Math.round(value * 60) / 60 + 'px';
    if (root.style.getPropertyValue(name) !== pixels) root.style.setProperty(name, pixels);
  };
  const on = (target, name, callback, capture = false) =>
    target.addEventListener(name, callback, { ...listeners, capture });

  function layout() {
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    if (root.hasAttribute('customizing')) return;
    // Native close/focus work can change selection after the original event.
    // Never position the field using a detached or previously selected tab.
    const selected = gBrowser.selectedTab;
    if (!suspended && selected?.isConnected && !selected.closing && editingTab !== selected) {
      editingTab?.removeAttribute('tabsearch-editing');
      editingTab = selected;
      selected.setAttribute('tabsearch-editing', 'true');
      root.setAttribute('tabsearch-editing', 'true');
    }
    if (editingTab && (!editingTab.isConnected || editingTab.closing)) {
      editingTab.removeAttribute('tabsearch-editing');
      editingTab = null;
      root.removeAttribute('tabsearch-editing');
    }
    const space = spacer.getBoundingClientRect();
    set('strip-left', space.left + 4);
    set('strip-right', Math.max(0, window.innerWidth - space.right + 4));
    // Allocate one roomy address tab and compact background tabs. Their total
    // width stays constant across selection, so overflow cannot oscillate.
    const visible = gBrowser.visibleTabs.filter(tab => !tab.closing);
    const ordinary = visible.filter(tab => !tab.pinned);
    const pinnedWidth = visible.filter(tab => tab.pinned)
      .reduce((width, tab) => width + tab.getBoundingClientRect().width, 0);
    // Include both scroll arrows even when they are hidden, so overflow cannot
    // change the width calculation and repeatedly toggle itself on and off.
    const budget = Math.max(100, space.width - pinnedWidth - 112);
    const count = Math.max(1, ordinary.length);
    const activeWidth = Math.min(280, budget);
    const backgroundWidth = Math.max(88, Math.min(180,
      Math.floor((budget - activeWidth) / Math.max(1, count - 1))));
    set('tab-width', backgroundWidth);
    set('active-width', activeWidth);
    if (!editingTab) return;
    const rect = editingTab.getBoundingClientRect();
    const close = editingTab.querySelector('.tab-close-button')?.getBoundingClientRect();
    const content = editingTab.querySelector('.tab-content')?.getBoundingClientRect() || rect;
    if (editingTab.pinned) {
      // Pinned tabs stay icon-sized; their editor opens immediately below.
      set('x', Math.max(12, Math.min(rect.left, window.innerWidth - 292)));
      set('y', rect.bottom + 4);
      set('width', Math.min(280, window.innerWidth - 24));
      set('height', 32);
      set('clip-left', 0);
      set('clip-right', 0);
    } else {
      set('x', Math.max(rect.left + 4, content.left));
      set('y', rect.top + 1);
      const end = close?.width ? close.left - 2 : rect.right - 6;
      set('width', Math.max(60, end - Math.max(rect.left + 4, content.left)));
      set('height', Math.max(26, rect.height - 2));
      // The field lives outside the scrollbox; clip it to the same viewport
      // so a partly scrolled tab cannot paint over the navigation buttons.
      const viewport = tabs.arrowScrollbox?.scrollbox?.getBoundingClientRect();
      set('clip-left', viewport ? Math.max(0, viewport.left - Math.max(rect.left + 4, content.left)) : 0);
      set('clip-right', viewport ? Math.max(0, end - viewport.right) : 0);
    }
  }
  function schedule() { if (!frame) frame = requestAnimationFrame(layout); }
  function reveal() {
    if (root.hasAttribute('customizing')) return;
    suspended = false;
    const tab = gBrowser.selectedTab;
    if (!tab?.isConnected || tab.closing) { layout(); schedule(); return; }
    if (editingTab && editingTab !== tab) editingTab.removeAttribute('tabsearch-editing');
    editingTab = tab;
    if (!tab.hasAttribute('tabsearch-editing')) tab.setAttribute('tabsearch-editing', 'true');
    if (!root.hasAttribute('tabsearch-editing')) root.setAttribute('tabsearch-editing', 'true');
    layout();
    // Firefox scrolls the newly selected tab in its own animation frame.
    // Follow that single native scroll before the next paint.
    schedule();
  }
  function hide({ revert = false } = {}) {
    suspended = true;
    if (revert) gURLBar.handleRevert();
    editingTab?.removeAttribute('tabsearch-editing');
    editingTab = null;
    root.removeAttribute('tabsearch-editing');
    schedule();
  }
  function edit(tab = gBrowser.selectedTab) {
    if (!tab?.isConnected || tab.closing || root.hasAttribute('customizing')) return;
    if (gBrowser.selectedTab !== tab) gBrowser.selectedTab = tab;
    reveal();
    gURLBar.focus();
    gURLBar.select();
  }
  function isTabControl(target) {
    return target.closest('.tab-close-button, .tab-icon-overlay, .tab-audio-button, .tab-secondary-button');
  }
  on(tabs, 'mousedown', event => {
    const tab = event.target.closest('.tabbrowser-tab');
    pointer = event.button === 0 && tab && !isTabControl(event.target) &&
      !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey
      ? { tab, x: event.screenX, y: event.screenY, dragged: false } : null;
  }, true);
  on(tabs, 'dragstart', () => { if (pointer) pointer.dragged = true; hide(); }, true);
  on(tabs, 'dragend', () => reveal(), true);
  on(window, 'click', event => {
    const click = pointer;
    pointer = null;
    if (!click || click.dragged || event.button !== 0 || isTabControl(event.target)) return;
    if (Math.hypot(event.screenX - click.x, event.screenY - click.y) > 5) return;
    // Let Firefox finish selecting the tab before opening its editor.
    queueMicrotask(() => edit(click.tab));
  });
  on(window, 'focusin', event => {
    if (container.contains(event.target)) reveal();
  }, true);
  on(window, 'mousedown', event => {
    if (editingTab && !container.contains(event.target) &&
        !event.target.closest('.tabbrowser-tab, panel, panel-list')) {
      gURLBar.view.close();
    }
  }, true);
  on(window, 'command', event => {
    if (event.target.id === 'Browser:OpenLocation') {
      event.preventDefault(); event.stopImmediatePropagation(); edit();
    }
  }, true);
  on(window, 'keydown', event => {
    if (((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === 'l') ||
        (event.altKey && event.key.toLowerCase() === 'd') || event.key === 'F6') {
      event.preventDefault(); event.stopImmediatePropagation(); edit(); return;
    }
    if (!container.contains(event.target)) return;
    if (event.key === 'Escape' && !event.isComposing) {
      event.preventDefault();
      event.stopImmediatePropagation();
      gURLBar.view.close();
      gURLBar.handleRevert();
      reveal();
      gBrowser.selectedBrowser.focus();
    } else if (event.key === 'Enter' && !event.isComposing) {
      const match = gURLBar.value.match(/^([gq])\s+(.+)$/is);
      if (!match) return; // Native URL loading / default-engine search.
      event.preventDefault();
      event.stopImmediatePropagation();
      const query = encodeURIComponent(match[2].trim());
      const url = match[1].toLowerCase() === 'q'
        ? 'https://www.qwant.com/?q=' + query + '&t=web'
        : 'https://www.google.com/search?q=' + query;
      gURLBar.view.close();
      reveal();
      openTrustedLinkIn(url, event.altKey ? 'tab' : 'current');
      gBrowser.selectedBrowser.focus();
    }
  }, true);
  // Selection controls visibility; focus only controls typing and suggestions.
  on(tabs, 'TabSelect', reveal);
  for (const type of ['TabOpen', 'TabClose', 'TabMove', 'TabPinned', 'TabUnpinned', 'TabAttrModified']) on(tabs, type, schedule);
  on(window, 'resize', schedule);
  on(scrollbox, 'scroll', layout);
  // ResizeObserver runs before paint. Updating synchronously here avoids a
  // visible extra frame when native scroll arrows appear or disappear.
  const resize = new ResizeObserver(layout);
  resize.observe(spacer);
  resize.observe(tabs);
  if (tabs.arrowScrollbox?.scrollbox) resize.observe(tabs.arrowScrollbox.scrollbox);
  const observer = new MutationObserver(schedule);
  observer.observe(root, { attributes: true, attributeFilter: ['customizing', 'sizemode', 'inFullscreen'] });
  on(window, 'beforecustomization', () => hide());
  on(window, 'aftercustomization', () => reveal());
  // Preference observers are held by Services, so release them when a window
  // closes as well as when the feature is explicitly disabled.
  on(window, 'unload', event => {
    if (event.target === document) window.TabSearch?.destroy();
  }, true);
  const modeChanged = { observe() {
    if (!Services.prefs.getBoolPref('userChrome.tabSearch.enabled', true) ||
        Services.prefs.getBoolPref('sidebar.verticalTabs', false)) window.TabSearch?.destroy();
  } };
  Services.prefs.addObserver('userChrome.tabSearch.enabled', modeChanged);
  Services.prefs.addObserver('sidebar.verticalTabs', modeChanged);
  const tabChanges = new MutationObserver(() => {
    // Run after native insertion/removal/style work, before the next paint.
    layout();
  });
  tabChanges.observe(tabs, { childList: true, subtree: true, attributes: true,
    attributeFilter: ['fadein', 'hidden', 'pinned', 'style', 'visuallyselected',
      'overflow', 'overflowing', 'scrolledtostart', 'scrolledtoend'] });
  // Use Firefox's complete no-animation paths, rather than suppressing CSS
  // transitionend (which Firefox otherwise needs to finish removing a tab).
  const nativeAddTab = gBrowser.addTab;
  const nativeRemoveTab = gBrowser.removeTab;
  function addTabInstant(url, options = {}) {
    try { return nativeAddTab.call(this, url, { ...options, skipAnimation: true }); }
    finally { if (!window.closed) layout(); }
  }
  function removeTabInstant(tab, options = {}) {
    try { return nativeRemoveTab.call(this, tab, { ...options, animate: false }); }
    finally { if (!window.closed) layout(); }
  }
  gBrowser.addTab = addTabInstant;
  gBrowser.removeTab = removeTabInstant;
  root.setAttribute('tabsearch-ready', 'true');
  layout();
  window.TabSearch = {
    edit, hide, layout,
    destroy() {
      hide(); abort.abort(); resize.disconnect(); observer.disconnect(); tabChanges.disconnect();
      Services.prefs.removeObserver('userChrome.tabSearch.enabled', modeChanged);
      Services.prefs.removeObserver('sidebar.verticalTabs', modeChanged);
      if (gBrowser.addTab === addTabInstant) gBrowser.addTab = nativeAddTab;
      if (gBrowser.removeTab === removeTabInstant) gBrowser.removeTab = nativeRemoveTab;
      cancelAnimationFrame(frame); spacer.remove(); root.removeAttribute('tabsearch-ready');
      if (originalSmoothScroll === null) scrollbox.removeAttribute('smoothscroll');
      else scrollbox.setAttribute('smoothscroll', originalSmoothScroll);
      for (const key of [...root.style]) if (key.startsWith('--tabsearch-')) root.style.removeProperty(key);
      delete window.TabSearch;
    }
  };
  reveal();
})();
