// Compact tabs show a page title until clicked or focused for native editing.
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
      typeof gURLBar.focus !== 'function' ||
      typeof gURLBar.getBrowserState !== 'function' ||
      typeof tabs.arrowScrollbox.ensureElementIsVisible !== 'function' ||
      typeof ResizeObserver !== 'function' || typeof AbortController !== 'function') return;
  const abort = new AbortController();
  const listeners = { signal: abort.signal };
  let activeTab = null, editingTab = null, frame = 0, clickFrame = 0, clickTab = null, pointer = null, suspended = true;
  let newTabPress = false, newTabReleaseFrame = 0;
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

  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const visuals = new Map(), ghosts = new Set(), closeSnapshots = new WeakMap();
  let visualFrame = 0, closeFrame = 0, closeBefore = null, fadingTab = null, removing = 0, middleTab = null;
  const motionAllowed = () => !reducedMotion.matches && !abort.signal.aborted && !window.closed;
  function visualTick() {
    visualFrame = 0;
    if (abort.signal.aborted || window.closed) return;
    layout();
    if (visuals.size) visualFrame = requestAnimationFrame(visualTick);
  }
  function animateVisual(element, keyframes, duration = 180, finish = null) {
    visuals.get(element)?.cancel();
    const animation = element.animate(keyframes, { duration, easing: 'cubic-bezier(.2,.7,.2,1)' });
    visuals.set(element, animation);
    animation.finished.catch(() => {}).then(() => {
      if (visuals.get(element) !== animation) return;
      visuals.delete(element); finish?.();
      if (!abort.signal.aborted && !window.closed) layout();
    });
    if (!visualFrame) visualFrame = requestAnimationFrame(visualTick);
  }
  function tabRects() {
    return new Map(gBrowser.visibleTabs.filter(t => !t.closing && !t.pinned)
      .map(t => [t, t.getBoundingClientRect()]));
  }
  function animateTabs(before) {
    if (!before || !motionAllowed() || tabs.hasAttribute('movingtab')) return;
    for (const [tab, old] of before) {
      if (!tab.isConnected || tab.closing || tab.pinned) continue;
      visuals.get(tab)?.cancel(); visuals.delete(tab);
      const current = tab.getBoundingClientRect();
      if (!old.width || !current.width) continue;
      const dx = old.left - current.left, scale = old.width / current.width;
      if (Math.abs(dx) < .5 && Math.abs(scale - 1) < .005) continue;
      animateVisual(tab, [
        { transformOrigin: 'left center', transform: `translateX(${dx}px) scaleX(${scale})` },
        { transformOrigin: 'left center', transform: 'translateX(0) scaleX(1)' }
      ], 180, () => {
        if (tab === editingTab && tab === gBrowser.selectedTab && !tab.pinned) {
          scrollbox.ensureElementIsVisible(tab, true);
        }
      });
    }
    layout();
  }
  function closePicture(tab) {
    const r = tab.getBoundingClientRect(), style = getComputedStyle(tab.querySelector('.tab-background'));
    return { x:r.left+3, y:r.top, width:Math.max(0,r.width-6), height:r.height,
      background:style.backgroundColor, color:getComputedStyle(tab).color,
      text:tab === editingTab ? (gURLBar.value || gURLBar.inputField.placeholder) : tab.label,
      icon:tab.getAttribute('image'), pinned:tab.pinned };
  }
  function showClosePicture(picture) {
    if (!picture || picture.width < 10 || !motionAllowed()) return;
    const ghost = document.createElementNS('http://www.w3.org/1999/xhtml', 'div');
    ghost.className = 'tabsearch-close-ghost'; ghost.setAttribute('aria-hidden', 'true');
    Object.assign(ghost.style, { left:picture.x+'px', top:picture.y+'px', width:picture.width+'px',
      height:picture.height+'px', background:picture.background, color:picture.color });
    if (picture.icon) {
      const icon = document.createElementNS('http://www.w3.org/1999/xhtml', 'img');
      icon.src = picture.icon; ghost.append(icon);
    }
    if (!picture.pinned) {
      const label = document.createElementNS('http://www.w3.org/1999/xhtml', 'span');
      label.textContent = picture.text; ghost.append(label);
    }
    document.documentElement.append(ghost); ghosts.add(ghost);
    // Bound visual leftovers when many tabs are closed in the same frame.
    if (ghosts.size > 6) {
      const oldest = ghosts.values().next().value;
      visuals.get(oldest)?.cancel(); visuals.delete(oldest); oldest.remove(); ghosts.delete(oldest);
    }
    animateVisual(ghost, [
      { opacity:1, transform:'scaleX(1)', clipPath:'inset(0 0 0 0 round 9px)' },
      { opacity:0, transform:'scaleX(.8)', clipPath:'inset(0 65% 0 0 round 9px)' }
    ], 150, () => { ghost.remove(); ghosts.delete(ghost); });
  }
  function clearMotion() {
    cancelAnimationFrame(visualFrame); cancelAnimationFrame(closeFrame);
    visualFrame = closeFrame = 0; closeBefore = null;
    for (const animation of visuals.values()) animation.cancel();
    visuals.clear();
    for (const ghost of ghosts) ghost.remove();
    ghosts.clear(); fadingTab = null; root.removeAttribute('tabsearch-hiding');
  }
  function stopEditorMotion() {
    // A transform captured for the previous editor must not scale a different
    // logical width after switching or interfere with Firefox's drag transform.
    // Decorative close ghosts can finish independently.
    for (const [element, animation] of visuals) {
      if (element === container || element.classList.contains('tabbrowser-tab')) {
        animation.cancel(); visuals.delete(element);
      }
    }
    fadingTab = null; root.removeAttribute('tabsearch-hiding');
  }
  on(reducedMotion, 'change', () => { if (reducedMotion.matches) { clearMotion(); layout(); } });

  function layout() {
    if (root.hasAttribute('customizing')) return;
    // Native close/focus work can change selection after the original event.
    // Never position the field using a detached or previously selected tab.
    const selected = gBrowser.selectedTab;
    const validSelection = selected?.isConnected && !selected.closing;
    if (activeTab !== (validSelection ? selected : null)) {
      activeTab?.removeAttribute('tabsearch-active');
      activeTab = validSelection ? selected : null;
      activeTab?.setAttribute('tabsearch-active', 'true');
    }
    if (fadingTab && fadingTab !== activeTab) {
      visuals.get(container)?.cancel(); visuals.delete(container);
      fadingTab = null; root.removeAttribute('tabsearch-hiding');
    }
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
    // Reserve room for one expanded editor without changing the other tabs'
    // widths. Idle tabs all use the compact width; editing consumes that room.
    const visible = gBrowser.visibleTabs.filter(tab => !tab.closing);
    const ordinary = visible.filter(tab => !tab.pinned);
    const pinnedWidth = visible.filter(tab => tab.pinned)
      .reduce((width, tab) => width + tab.getBoundingClientRect().width, 0);
    // Include both scroll arrows even when they are hidden, so overflow cannot
    // change the width calculation and repeatedly toggle itself on and off.
    const budget = Math.max(100, space.width - pinnedWidth - 112);
    const count = Math.max(1, ordinary.length);
    // Give the address a little extra room in a sparse strip, then gradually
    // trim it as tabs fill the available space. Use the fixed budget/count,
    // not measured tab widths, so selection and overflow cannot feed back.
    const crowding = Math.max(0, Math.min(1, (180 - budget / count) / 92));
    const activeWidth = Math.min(budget, Math.round(300 - 40 * crowding));
    const backgroundWidth = Math.max(88, Math.min(180,
      Math.floor((budget - activeWidth) / Math.max(1, count - 1))));
    set('tab-width', backgroundWidth);
    set('active-width', activeWidth);
    // Track the selected tab even while the editor is hidden, so the field is
    // already aligned when a compact tab expands into the editor.
    const positionTab = editingTab || activeTab;
    if (!positionTab) return;
    const rect = positionTab.getBoundingClientRect();
    const close = positionTab.querySelector('.tab-close-button')?.getBoundingClientRect();
    const content = positionTab.querySelector('.tab-content')?.getBoundingClientRect() || rect;
    if (positionTab.pinned) {
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
  function schedule() {
    if (!frame) frame = requestAnimationFrame(() => { frame = 0; layout(); });
  }
  function reveal() {
    if (root.hasAttribute('customizing')) return;
    suspended = false;
    const tab = gBrowser.selectedTab;
    if (!tab?.isConnected || tab.closing) { layout(); schedule(); return; }
    const opening = editingTab !== tab || !root.hasAttribute('tabsearch-editing');
    const before = opening && motionAllowed() && !removing ? tabRects() : null;
    const opacity = opening ? Number(getComputedStyle(container).opacity) : 1;
    root.removeAttribute('tabsearch-hiding'); fadingTab = null;
    if (editingTab && editingTab !== tab) editingTab.removeAttribute('tabsearch-editing');
    editingTab = tab;
    if (!tab.hasAttribute('tabsearch-editing')) tab.setAttribute('tabsearch-editing', 'true');
    if (!root.hasAttribute('tabsearch-editing')) root.setAttribute('tabsearch-editing', 'true');
    layout();
    if (before) {
      animateTabs(before);
      animateVisual(container, [{ opacity }, { opacity:1 }], 140);
    }
    // Expansion near the viewport edge can put the input outside the strip.
    // Keep it visible using Firefox's native scroll and our paired update.
    if (opening && !tab.pinned) scrollbox.ensureElementIsVisible(tab, true);
    // Firefox scrolls the newly selected tab in its own animation frame.
    // Queue behind that native scroll, even if TabOpen queued an earlier
    // update. Synchronous close/resize layouts must not cancel this follow-up.
    if (frame) cancelAnimationFrame(frame);
    frame = 0;
    schedule();
  }
  function hide({ revert = false, animate = true } = {}) {
    const tab = editingTab;
    const before = tab && animate && motionAllowed() && !removing ? tabRects() : null;
    const opacity = before ? Number(getComputedStyle(container).opacity) : 0;
    gURLBar.view.close();
    suspended = true;
    if (revert) gURLBar.handleRevert();
    editingTab?.removeAttribute('tabsearch-editing');
    editingTab = null;
    root.removeAttribute('tabsearch-editing');
    if (before) {
      layout(); animateTabs(before);
      if (tab === gBrowser.selectedTab) {
        fadingTab = tab; root.setAttribute('tabsearch-hiding', 'true');
        animateVisual(container, [{ opacity }, { opacity:0 }], 140, () => {
          fadingTab = null; root.removeAttribute('tabsearch-hiding');
        });
      }
    }
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
  function cancelClickEdit() { cancelAnimationFrame(clickFrame); clickFrame = 0; clickTab = null; }
  function finishClickEdit() {
    const tab = clickTab;
    if (abort.signal.aborted || window.closed || !tab || gBrowser.selectedTab !== tab) {
      cancelClickEdit(); return;
    }
    // Rendering a newly selected remote tab can finish after several frames.
    // Use its completion event rather than racing native page-focus restore.
    if (gBrowser._switcher?.switchInProgress) return;
    cancelClickEdit(); edit(tab);
  }
  function requestEditing(tab) {
    cancelClickEdit(); clickTab = tab;
    clickFrame = requestAnimationFrame(() => { clickFrame = 0; finishClickEdit(); });
  }
  on(tabs, 'mousedown', event => {
    const tab = event.target.closest('.tabbrowser-tab');
    pointer = event.button === 0 && tab && !isTabControl(event.target) &&
      !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey
      ? { tab, wasSelected: gBrowser.selectedTab === tab,
          x: event.screenX, y: event.screenY, dragged: false } : null;
  }, true);
  on(tabs, 'dragstart', () => {
    if (pointer) pointer.dragged = true;
    stopEditorMotion(); hide({ animate:false });
  }, true);
  on(tabs, 'dragend', () => { stopEditorMotion(); hide({ animate:false }); }, true);
  on(window, 'click', event => {
    const click = pointer;
    pointer = null;
    if (!click || click.dragged || event.button !== 0 || isTabControl(event.target)) return;
    if (Math.hypot(event.screenX - click.x, event.screenY - click.y) > 5) return;
    // Mousedown has already changed native selection by the time click fires.
    // Only a tab that was selected before this gesture should open editing.
    if (!click.wasSelected) {
      cancelClickEdit(); hide(); gBrowser.selectedBrowser.focus(); return;
    }
    // A later click/key cancels this gesture, so a completed background render
    // cannot steal focus after the user has already moved on.
    requestEditing(click.tab);
  });
  on(window, 'TabSwitchDone', finishClickEdit, true);
  on(window, 'focusin', event => {
    if (container.contains(event.target)) reveal();
    else if (event.target === gBrowser.selectedBrowser && !newTabPress) hide();
  }, true);
  on(container, 'focusout', () => {
    // Let focus move into suggestions or a native identity/search popup before
    // deciding to collapse. Never hide a control in the middle of its click.
    queueMicrotask(() => {
      if (abort.signal.aborted || window.closed || newTabPress) return;
      const focused = document.activeElement;
      if (!container.contains(focused) && !gURLBar.view.isOpen &&
          !focused?.closest('panel, panel-list, .urlbarView')) hide();
    });
  });
  const inInputRow = event => !!event.target.closest?.('.urlbar-input-container');
  on(container, 'mousedown', event => {
    if (event.button !== 1 || !editingTab || !inInputRow(event)) return;
    event.preventDefault(); event.stopImmediatePropagation(); middleTab = editingTab;
  }, true);
  on(window, 'mouseup', event => {
    if (event.button !== 1 || !middleTab) return;
    const tab = middleTab; middleTab = null;
    event.preventDefault(); event.stopImmediatePropagation();
    if (inInputRow(event) && tab.isConnected && gBrowser.selectedTab === tab) {
      cancelClickEdit();
      gBrowser.removeTab(tab, { animate:true, triggeringEvent:event });
    }
  }, true);
  on(container, 'auxclick', event => {
    if (event.button === 1 && inInputRow(event)) {
      event.preventDefault(); event.stopImmediatePropagation();
    }
  }, true);
  on(window, 'mousedown', event => {
    middleTab = null;
    cancelClickEdit();
    // Collapsing here moves + before mouseup, so Firefox never receives its
    // click. Let the native button finish the gesture before changing widths.
    cancelAnimationFrame(newTabReleaseFrame); newTabReleaseFrame = 0;
    newTabPress = event.button === 0 && !!event.target.closest('#tabs-newtab-button, #new-tab-button');
    if (editingTab && !container.contains(event.target) &&
        !newTabPress && !event.target.closest('.tabbrowser-tab, panel, panel-list')) {
      hide();
    }
  }, true);
  on(window, 'mouseup', event => {
    if (event.button !== 0 || !newTabPress) return;
    const pressedTab = gBrowser.selectedTab;
    // Click/command and TabSelect run after mouseup. A cancelled gesture may
    // still need to collapse after focus has left the old editor.
    newTabReleaseFrame = requestAnimationFrame(() => {
      newTabReleaseFrame = 0; newTabPress = false;
      if (gBrowser.selectedTab === pressedTab &&
          !container.contains(document.activeElement) && !gURLBar.view.isOpen) hide();
    });
  }, true);
  on(window, 'command', event => {
    if (event.target.id === 'Browser:OpenLocation') {
      event.preventDefault(); event.stopImmediatePropagation(); edit();
    }
  }, true);
  on(window, 'keydown', event => {
    middleTab = null;
    newTabPress = false;
    cancelClickEdit();
    if (((event.ctrlKey || event.metaKey) && !event.shiftKey && event.key.toLowerCase() === 'l') ||
        (event.altKey && event.key.toLowerCase() === 'd') || event.key === 'F6') {
      event.preventDefault(); event.stopImmediatePropagation(); edit(); return;
    }
    if (!container.contains(event.target)) return;
    if (event.key === 'Escape' && !event.isComposing) {
      event.preventDefault();
      event.stopImmediatePropagation();
      hide({ revert: true });
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
  // Selecting a website with the keyboard leaves a normal tab. Native new-tab
  // focus (including when the field was already focused) still opens editing.
  on(tabs, 'TabSelect', () => {
    stopEditorMotion();
    hide({ animate:false }); layout();
    const selectingByClick = pointer?.tab === gBrowser.selectedTab && !pointer.wasSelected;
    if (selectingByClick) {
      // Native switching otherwise restores the address field if it was
      // focused last time this tab was active. The first click means browse.
      gURLBar.getBrowserState(gBrowser.selectedBrowser).urlbarFocused = false;
    }
    const uri = gBrowser.selectedBrowser.currentURI.spec;
    if (!selectingByClick && ['about:blank', 'about:newtab', 'about:home'].includes(uri)) {
      requestEditing(gBrowser.selectedTab);
      if (container.contains(document.activeElement)) reveal();
    }
  });
  for (const type of ['TabOpen', 'TabClose', 'TabMove', 'TabPinned', 'TabUnpinned', 'TabAttrModified']) on(tabs, type, schedule);
  on(tabs, 'TabClose', event => {
    const snapshot = closeSnapshots.get(event.target); closeSnapshots.delete(event.target);
    if (!snapshot?.animate || !motionAllowed()) return;
    showClosePicture(snapshot.picture);
    closeBefore ||= snapshot.rects;
    if (!closeFrame) closeFrame = requestAnimationFrame(() => {
      closeFrame = 0; const before = closeBefore; closeBefore = null;
      if (!abort.signal.aborted && !window.closed) { layout(); animateTabs(before); }
    });
  }, true);
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
  on(window, 'beforecustomization', () => { clearMotion(); hide({ animate:false }); });
  on(window, 'aftercustomization', () => { hide({ animate:false }); layout(); });
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
  const nativeEnsureVisible = scrollbox.ensureElementIsVisible;
  const nativeFocus = gURLBar.focus;
  function focusEditor(...args) {
    // A hidden input cannot receive focus, so reveal before Firefox's native
    // search/location entry points try to focus it (not just our shortcuts).
    if (!abort.signal.aborted) reveal();
    return nativeFocus.apply(this, args);
  }
  let nativeScrollFrame = 0;
  function ensureVisibleWithEditor(...args) {
    const result = nativeEnsureVisible.apply(this, args);
    if (!abort.signal.aborted && !window.closed) {
      // Firefox can request visibility after TabSelect, replacing its earlier
      // scroll frame. Follow each actual request, independently of the normal
      // layout queue, so its final scroll always precedes our position update.
      cancelAnimationFrame(nativeScrollFrame);
      nativeScrollFrame = requestAnimationFrame(() => {
        nativeScrollFrame = 0;
        if (!abort.signal.aborted && !window.closed) layout();
      });
    }
    return result;
  }
  function addTabInstant(url, options = {}) {
    try {
      const tab = nativeAddTab.call(this, url, { ...options, skipAnimation: true });
      if (tab?.isConnected && options.skipAnimation !== true && motionAllowed()) {
        // Animate the painted contents independently of native insertion and
        // editor-width transforms, so selection/focus can complete normally.
        const stack = tab.querySelector('.tab-stack');
        if (stack) animateVisual(stack, [
          { opacity:0, transform:'translateY(4px) scale(.97)' },
          { opacity:1, transform:'translateY(0) scale(1)' }
        ]);
      }
      return tab;
    }
    finally { if (!window.closed) layout(); }
  }
  function removeTabInstant(tab, options = {}) {
    if (tab?.isConnected && !tab.closing && motionAllowed()) {
      closeSnapshots.set(tab, { animate:options.animate !== false, rects:tabRects(), picture:closePicture(tab) });
    }
    removing++;
    try { return nativeRemoveTab.call(this, tab, { ...options, animate: false }); }
    finally { removing--; if (!window.closed) layout(); }
  }
  gBrowser.addTab = addTabInstant;
  gBrowser.removeTab = removeTabInstant;
  scrollbox.ensureElementIsVisible = ensureVisibleWithEditor;
  gURLBar.focus = focusEditor;
  root.setAttribute('tabsearch-ready', 'true');
  layout();
  window.TabSearch = {
    edit, hide, layout,
    destroy() {
      cancelClickEdit();
      cancelAnimationFrame(newTabReleaseFrame); newTabPress = false;
      abort.abort(); hide({ animate:false }); clearMotion();
      resize.disconnect(); observer.disconnect(); tabChanges.disconnect();
      Services.prefs.removeObserver('userChrome.tabSearch.enabled', modeChanged);
      Services.prefs.removeObserver('sidebar.verticalTabs', modeChanged);
      if (gBrowser.addTab === addTabInstant) gBrowser.addTab = nativeAddTab;
      if (gBrowser.removeTab === removeTabInstant) gBrowser.removeTab = nativeRemoveTab;
      if (scrollbox.ensureElementIsVisible === ensureVisibleWithEditor) scrollbox.ensureElementIsVisible = nativeEnsureVisible;
      if (gURLBar.focus === focusEditor) gURLBar.focus = nativeFocus;
      cancelAnimationFrame(nativeScrollFrame);
      activeTab?.removeAttribute('tabsearch-active');
      activeTab = null;
      cancelAnimationFrame(frame); spacer.remove(); root.removeAttribute('tabsearch-ready');
      if (originalSmoothScroll === null) scrollbox.removeAttribute('smoothscroll');
      else scrollbox.setAttribute('smoothscroll', originalSmoothScroll);
      for (const key of [...root.style]) if (key.startsWith('--tabsearch-')) root.style.removeProperty(key);
      delete window.TabSearch;
    }
  };
  if (container.contains(document.activeElement)) reveal();
})();
