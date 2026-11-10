/* WhiteSur Full release updater. Profile theme files only; no installer execution. */
Cu.importGlobalProperties(['fetch', 'TextDecoder', 'TextEncoder', 'AbortController', 'crypto']);
const { AsyncShutdown } = ChromeUtils.importESModule('resource://gre/modules/AsyncShutdown.sys.mjs');
const { setTimeout, clearTimeout, setInterval, clearInterval } = ChromeUtils.importESModule('resource://gre/modules/Timer.sys.mjs');

export const OWNER = 'WhiteSur-Monterey-Adaptive-Windows';
export const REPOSITORY = 'okixk/WhiteSur-Monterey-Adaptive-Windows';
export const RELEASES_URL = `https://api.github.com/repos/${REPOSITORY}/releases?per_page=20`;
const MARKER = '.whitesur-monterey-adaptive-windows';
const LIMIT = 32 * 1024 * 1024;
const DAY = 24 * 60 * 60 * 1000;
const decoder = new TextDecoder('utf-8', { fatal: true });
const encoder = new TextEncoder();
class ManualInstallRequired extends Error {}

export function compareVersions(a, b) {
  const parse = value => {
    const m = /^(\d{4})\.(\d{2})\.(\d{2})-(\d{1,8})$/.exec(value || '');
    if (!m) throw new Error('Invalid theme version.');
    const v = m.slice(1).map(Number), date = new Date(Date.UTC(v[0], v[1] - 1, v[2]));
    if (date.getUTCFullYear() !== v[0] || date.getUTCMonth() + 1 !== v[1] || date.getUTCDate() !== v[2]) throw new Error('Invalid theme version date.');
    return v;
  };
  const x = parse(a), y = parse(b);
  for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return Math.sign(x[i] - y[i]);
  return 0;
}

function safePath(name) {
  if (typeof name !== 'string' || !name || name.length > 240 || /[\\:<>"|?*\x00-\x1f]/.test(name) || name.startsWith('/')) throw new Error('Unsafe package path.');
  const parts = name.replace(/\/$/, '').split('/');
  if (parts.some(p => !p || p === '.' || p === '..' || /[. ]$/.test(p) || /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(p))) throw new Error('Unsafe package path.');
  return parts;
}

async function digest(bytes) {
  const hash = await crypto.subtle.digest('SHA-256', new Uint8Array(bytes));
  return [...new Uint8Array(hash)].map(b => b.toString(16).padStart(2, '0')).join('');
}

async function ordinary(path, type = null, missing = false) {
  try {
    const stat = await IOUtils.stat(path, { followSymlinks: false });
    if (stat.type === 'symlink' || (type && stat.type !== type)) throw new Error(`Unsafe update path: ${PathUtils.filename(path)}`);
    return stat;
  } catch (error) {
    if (missing && error.name === 'NotFoundError') return null;
    throw error;
  }
}

async function readJSON(path) {
  await ordinary(path, 'regular');
  return JSON.parse(await IOUtils.readUTF8(path, { maxBytes: 2 * 1024 * 1024 }));
}

async function writeJSON(path, data) {
  await ordinary(path, 'regular', true);
  await ordinary(path + '.tmp', 'regular', true);
  await IOUtils.writeJSON(path, data, { tmpPath: path + '.tmp' });
}

async function treeFiles(directory) {
  await ordinary(directory, 'directory');
  const files = [];
  async function visit(path, prefix) {
    for (const child of await IOUtils.getChildren(path)) {
      const name = PathUtils.filename(child), relative = prefix + name;
      safePath(relative);
      const stat = await ordinary(child);
      if (stat.type === 'directory') await visit(child, relative + '/');
      else if (stat.type === 'regular') files.push(relative);
      else throw new Error('Update folders must contain ordinary files only.');
      if (files.length > 1024) throw new Error('Too many update files.');
    }
  }
  await visit(directory, '');
  return files;
}

export async function fetchBytes(url, { maxBytes = LIMIT, signal } = {}) {
  const response = await fetch(url, { signal, credentials: 'omit', cache: 'no-store', referrerPolicy: 'no-referrer', headers: { Accept: 'application/vnd.github+json' } });
  if (!response.ok) throw new Error(`GitHub returned HTTP ${response.status}.`);
  const final = new URL(response.url);
  if (final.protocol !== 'https:' || !['api.github.com', 'github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com'].includes(final.hostname)) throw new Error('Unexpected download redirect.');
  if (Number(response.headers.get('content-length')) > maxBytes) throw new Error('Download is too large.');
  const reader = response.body.getReader(), chunks = [];
  let length = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      length += value.length;
      if (length > maxBytes) throw new Error('Download is too large.');
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(() => {}); }
  const result = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { result.set(chunk, offset); offset += chunk.length; }
  return result;
}

export function releaseAsset(release) {
  if (!release || release.draft || !/^v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?$/.test(release.tag_name || '')) throw new Error('Invalid published release.');
  const names = [`WhiteSur-Monterey-Adaptive-Windows-Full-${release.tag_name}.zip`, `WhiteSur-Monterey-Adaptive-Windows-${release.tag_name}.zip`];
  const asset = names.map(name => release.assets?.find(a => a.name === name)).find(Boolean);
  if (!asset || !/^sha256:[a-f0-9]{64}$/i.test(asset.digest || '') || !Number.isSafeInteger(asset.size) || asset.size <= 0 || asset.size > LIMIT) throw new Error('Release has no verified Full package.');
  const expected = `https://github.com/${REPOSITORY}/releases/download/${encodeURIComponent(release.tag_name)}/${encodeURIComponent(asset.name)}`;
  if (asset.browser_download_url !== expected) throw new Error('Unexpected release download URL.');
  return asset;
}

// Inspect raw names before nsIZipReader can normalize them (notably Windows
// backslashes). Only ordinary, single-disk, non-ZIP64 release archives are used.
export function validateArchive(bytes) {
  if (!(bytes instanceof Uint8Array)) bytes = new Uint8Array(bytes);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  let end = -1;
  for (let i = bytes.length - 22; i >= Math.max(0, bytes.length - 65557); i--) {
    if (view.getUint32(i, true) === 0x06054b50 && i + 22 + view.getUint16(i + 20, true) === bytes.length) { end = i; break; }
  }
  if (end < 0 || view.getUint16(end + 4, true) || view.getUint16(end + 6, true)) throw new Error('Invalid release ZIP.');
  const count = view.getUint16(end + 10, true), size = view.getUint32(end + 12, true), offset = view.getUint32(end + 16, true);
  if (!count || count > 2048 || count !== view.getUint16(end + 8, true) || offset + size !== end) throw new Error('Unsupported release ZIP structure.');
  const seen = new Set(); let position = offset, root = null;
  for (let i = 0; i < count; i++) {
    if (position + 46 > end || view.getUint32(position, true) !== 0x02014b50) throw new Error('Invalid ZIP directory.');
    const nameLength = view.getUint16(position + 28, true), extraLength = view.getUint16(position + 30, true), commentLength = view.getUint16(position + 32, true);
    const next = position + 46 + nameLength + extraLength + commentLength;
    if (next > end || !nameLength) throw new Error('Invalid ZIP entry.');
    const name = decoder.decode(bytes.subarray(position + 46, position + 46 + nameLength)), parts = safePath(name);
    const alias = name.replace(/\/$/, '').toLowerCase();
    if ((root && root !== parts[0]) || seen.has(alias) || (view.getUint16(position + 8, true) & 1) || view.getUint16(position + 34, true) ||
        ((view.getUint32(position + 38, true) >>> 16) & 0o170000) === 0o120000) throw new Error('Unsafe release archive.');
    root = parts[0]; seen.add(alias);
    const local = view.getUint32(position + 42, true), compressed = view.getUint32(position + 20, true);
    if (local + 30 > offset || view.getUint32(local, true) !== 0x04034b50) throw new Error('Invalid local ZIP entry.');
    const localName = view.getUint16(local + 26, true), localExtra = view.getUint16(local + 28, true);
    if (local + 30 + localName + localExtra + compressed > offset || decoder.decode(bytes.subarray(local + 30, local + 30 + localName)) !== name) throw new Error('ZIP entry names or boundaries disagree.');
    position = next;
  }
  if (position !== end) throw new Error('Invalid ZIP directory length.');
  return root;
}

function readZipFile(zip, name) {
  const entry = zip.getEntry(name);
  if (entry.isDirectory || entry.realSize > 8 * 1024 * 1024) throw new Error('Invalid package file.');
  const stream = Cc['@mozilla.org/binaryinputstream;1'].createInstance(Ci.nsIBinaryInputStream);
  stream.setInputStream(zip.getInputStream(name));
  try { return new Uint8Array(stream.readByteArray(entry.realSize)); } finally { stream.close(); }
}

function manifestFromZip(zip, root, tag) {
  const read = name => readZipFile(zip, name);
  const manifest = JSON.parse(decoder.decode(read(root + '/release-manifest.json')));
  if (manifest.edition !== 'Full' || manifest.tag !== tag || !Number.isInteger(manifest.minimumFirefoxMajor)) throw new Error('Not a compatible Full package.');
  if (manifest.schema !== 1 || manifest.loaderProtocol !== 1 || manifest.minimumFirefoxMajor > Number.parseInt(Services.appinfo.version, 10)) throw new ManualInstallRequired('This release needs manual installation or a newer Firefox.');
  compareVersions(manifest.version, manifest.version);
  const entries = Object.entries(manifest.files || {});
  if (!entries.length || entries.length > 1024) throw new Error('Invalid update manifest.');
  let total = 0;
  const seen = new Set();
  for (const [name, hash] of entries) {
    safePath(name);
    if (!name.startsWith('chrome/') || !/^[a-f0-9]{64}$/i.test(hash) || seen.has(name.toLowerCase())) throw new Error('Invalid theme update file.');
    seen.add(name.toLowerCase());
    const entry = zip.getEntry(root + '/' + name);
    if (!entry || entry.isDirectory || entry.realSize > 8 * 1024 * 1024) throw new Error('Missing or oversized theme file.');
    total += entry.realSize;
  }
  if (total > 64 * 1024 * 1024) throw new Error('Expanded theme is too large.');
  for (const required of ['chrome/userChrome.css', 'chrome/userContent.css', 'chrome/tab-search.uc.js', 'chrome/tab-search.css', 'chrome/whitesur-updater.sys.mjs']) {
    if (!Object.hasOwn(manifest.files, required)) throw new Error('Incomplete Full theme.');
  }
  if (decoder.decode(read(root + '/VERSION.txt')).trim() !== manifest.version) throw new Error('Package version mismatch.');
  const names = zip.findEntries(null);
  while (names.hasMore()) {
    const name = names.getNext();
    if (name.startsWith(root + '/chrome/') && !zip.getEntry(name).isDirectory && !Object.hasOwn(manifest.files, name.slice(root.length + 1))) throw new Error('Unmanifested theme file.');
  }
  return { manifest, read };
}

export class ThemeUpdater {
  constructor(profile, { move = (...args) => IOUtils.move(...args) } = {}) {
    this.profile = profile;
    this.chrome = PathUtils.join(profile, 'chrome');
    this.directory = PathUtils.join(profile, '.whitesur-updates');
    this.settingsPath = PathUtils.join(profile, '.whitesur-updater.json');
    this.state = { schema: 1, owner: OWNER, status: 'idle', pending: null, lastChecked: 0 };
    this.move = move;
    this.views = new Set();
    this.usable = false;
  }

  async settings() {
    try {
      const settings = await readJSON(this.settingsPath);
      if (settings.schema !== 1 || settings.owner !== OWNER || settings.edition !== 'Full') return null;
      if (typeof settings.enabled !== 'boolean' || typeof settings.allowPrerelease !== 'boolean') throw new Error('Invalid updater settings.');
      return settings;
    } catch (error) { if (error.name === 'NotFoundError') return null; throw error; }
  }

  async initialize() {
    await ordinary(this.profile, 'directory');
    if (!await this.settings()) { this.state.status = 'disabled'; return; }
    const exists = await ordinary(this.directory, 'directory', true);
    if (!exists) {
      await IOUtils.makeDirectory(this.directory, { ignoreExisting: false });
      await writeJSON(PathUtils.join(this.directory, 'owner.json'), { schema: 1, owner: OWNER });
    }
    const owner = await readJSON(PathUtils.join(this.directory, 'owner.json'));
    if (owner.owner !== OWNER || owner.schema !== 1) throw new Error('Unmanaged updater directory was preserved.');
    const path = PathUtils.join(this.directory, 'state.json');
    if (await ordinary(path, 'regular', true)) {
      const saved = await readJSON(path);
      if (saved.owner !== OWNER || saved.schema !== 1) throw new Error('Invalid update state.');
      this.state = saved;
    }
    const enabled = (await this.settings()).enabled;
    this.state.status = this.state.pending ? (enabled ? 'pending' : 'paused') : (enabled ? 'idle' : 'disabled');
    this.usable = true;
    this.notify();
  }

  async save() {
    if (!this.usable) throw new Error('Updater state was not validated.');
    await ordinary(this.directory, 'directory');
    if ((await readJSON(PathUtils.join(this.directory, 'owner.json'))).owner !== OWNER) throw new Error('Updater directory ownership changed.');
    await writeJSON(PathUtils.join(this.directory, 'state.json'), this.state);
    this.notify();
  }

  notify() { for (const view of this.views) { try { view(); } catch {} } }
  snapshot() { return JSON.parse(JSON.stringify(this.state)); }

  async installed() {
    await ordinary(this.chrome, 'directory');
    await ordinary(PathUtils.join(this.chrome, MARKER), 'regular');
    const marker = await IOUtils.readUTF8(PathUtils.join(this.chrome, MARKER));
    if (!/^Edition: Full\s*$/m.test(marker) || !/^Method: AutoConfig\s*$/m.test(marker)) throw new Error('Only an installed Full theme can update.');
    const version = /^Version: (.+)$/m.exec(marker)?.[1].trim();
    compareVersions(version, version);
    return { marker, version };
  }

  async checkForUpdates({ force = false, fetcher = fetchBytes } = {}) {
    if (this.checking) return this.checking;
    this.checking = this.check({ force, fetcher }).catch(async error => {
      this.state.status = this.state.pending ? 'pending' : (error instanceof ManualInstallRequired ? 'manual' : 'error');
      this.state.error = String(error.message || error).slice(0, 300);
      await this.save().catch(() => {});
      return this.snapshot();
    }).finally(() => { this.checking = null; });
    return this.checking;
  }

  async check({ force, fetcher }) {
    await this.ready;
    const settings = await this.settings();
    if (!this.usable || !settings || this.stopping || (!settings.enabled && !force)) return this.snapshot();
    if (this.state.pending || (!force && Date.now() - this.state.lastChecked < DAY)) return this.snapshot();
    const installed = await this.installed();
    this.state.lastChecked = Date.now();
    this.state.status = 'checking'; this.state.error = null; this.notify();
    this.abort = new AbortController();
    const timeout = setTimeout(() => this.abort.abort(), 30000);
    try {
      const bytes = await fetcher(RELEASES_URL, { maxBytes: 2 * 1024 * 1024, signal: this.abort.signal });
      const releases = JSON.parse(decoder.decode(bytes));
      if (!Array.isArray(releases)) throw new Error('Invalid GitHub release response.');
      const release = releases.find(r => !r.draft && (settings.allowPrerelease || !r.prerelease) && r.assets?.some(a => a.name === `WhiteSur-Monterey-Adaptive-Windows-Full-${r.tag_name}.zip` || a.name === `WhiteSur-Monterey-Adaptive-Windows-${r.tag_name}.zip`));
      if (!release) throw new Error('No compatible published Full release is available.');
      const asset = releaseAsset(release);
      if (this.state.lastAsset === asset.digest && this.state.lastVersion && compareVersions(this.state.lastVersion, installed.version) <= 0) { this.state.status = 'up-to-date'; await this.save(); return this.snapshot(); }
      this.state.status = 'downloading'; this.notify();
      const archive = await fetcher(asset.browser_download_url, { maxBytes: LIMIT, signal: this.abort.signal });
      if (archive.length !== asset.size || await digest(archive) !== asset.digest.slice(7).toLowerCase()) throw new Error('Release checksum mismatch.');
      await this.stage(archive, release.tag_name);
      if (this.state.pending && !settings.enabled) this.state.status = 'paused';
      this.state.lastAsset = asset.digest;
      await this.save();
      return this.snapshot();
    } finally { clearTimeout(timeout); this.abort = null; }
  }

  async stage(archive, tag) {
    const installed = await this.installed();
    validateArchive(archive);
    const id = 'stage-' + Services.uuid.generateUUID().toString().replace(/[{}]/g, '');
    const directory = PathUtils.join(this.directory, id);
    await IOUtils.makeDirectory(directory, { ignoreExisting: false });
    const zipPath = PathUtils.join(directory, 'release.zip');
    await IOUtils.write(zipPath, archive, { mode: 'create' });
    const file = Cc['@mozilla.org/file/local;1'].createInstance(Ci.nsIFile); file.initWithPath(zipPath);
    const zip = Cc['@mozilla.org/libjar/zip-reader;1'].createInstance(Ci.nsIZipReader); zip.open(file);
    try {
      const names = zip.findEntries(null), seen = new Set();
      let root = null, count = 0;
      while (names.hasMore()) {
        const name = names.getNext(), parts = safePath(name), entry = zip.getEntry(name);
        if (++count > 2048 || (root && root !== parts[0]) || seen.has(name.toLowerCase()) || (entry.permissions & 0o170000) === 0o120000) throw new Error('Unsafe release archive.');
        root = parts[0]; seen.add(name.toLowerCase());
      }
      // Older public archives predate manifests. Read their bounded version
      // without extracting/executing anything so an old release is simply
      // ignored, rather than displaying a permanent update error.
      const version = decoder.decode(readZipFile(zip, root + '/VERSION.txt')).trim();
      if (compareVersions(version, installed.version) <= 0) {
        this.state.lastVersion = version; this.state.status = 'up-to-date'; return;
      }
      const { manifest, read } = manifestFromZip(zip, root, tag);
      this.state.lastVersion = manifest.version;
      if (compareVersions(manifest.version, installed.version) <= 0) { this.state.status = 'up-to-date'; return; }
      const chrome = PathUtils.join(directory, 'chrome');
      await IOUtils.makeDirectory(chrome, { ignoreExisting: false });
      for (const [name, hash] of Object.entries(manifest.files)) {
        const bytes = read(root + '/' + name);
        if (await digest(bytes) !== hash.toLowerCase()) throw new Error('Theme file checksum mismatch.');
        const target = PathUtils.join(directory, ...safePath(name));
        await IOUtils.makeDirectory(PathUtils.parent(target), { ignoreExisting: true });
        await IOUtils.write(target, bytes, { mode: 'create' });
      }
      await writeJSON(PathUtils.join(directory, 'manifest.json'), manifest);
      await this.verifyStage(id, manifest);
      this.state.pending = { directory: id, version: manifest.version, tag, manifestHash: await IOUtils.computeHexDigest(PathUtils.join(directory, 'manifest.json'), 'sha256') };
      this.state.status = 'pending';
    } finally { zip.close(); }
  }

  async verifyStage(id, manifest) {
    if (!/^stage-[a-f0-9-]{36}$/.test(id)) throw new Error('Invalid staged update path.');
    const directory = PathUtils.join(this.directory, id);
    await ordinary(this.directory, 'directory'); await ordinary(directory, 'directory');
    const files = await treeFiles(PathUtils.join(directory, 'chrome'));
    const expected = Object.keys(manifest.files).map(p => p.slice(7)).sort();
    if (JSON.stringify(files.sort()) !== JSON.stringify(expected)) throw new Error('Staged theme files changed.');
    for (const relative of files) {
      const path = PathUtils.join(directory, 'chrome', ...safePath(relative));
      if (await IOUtils.computeHexDigest(path, 'sha256') !== manifest.files['chrome/' + relative].toLowerCase()) throw new Error('Staged file checksum mismatch.');
    }
  }

  async applyPending() {
    try { return await this.applyValidatedPending(); }
    catch (error) {
      this.state.pending = null; this.state.lastAsset = null;
      this.state.status = 'error'; this.state.error = String(error.message || error).slice(0, 300);
      await this.save().catch(() => {});
      throw error;
    }
  }

  async applyValidatedPending() {
    await this.ready;
    const settings = await this.settings(), pending = this.state.pending;
    if (!this.usable || !settings?.enabled || !pending) return false;
    const installed = await this.installed();
    if (!/^stage-[a-f0-9-]{36}$/.test(pending.directory)) throw new Error('Invalid staged update path.');
    const directory = PathUtils.join(this.directory, pending.directory);
    await ordinary(directory, 'directory');
    if (await IOUtils.computeHexDigest(PathUtils.join(directory, 'manifest.json'), 'sha256') !== pending.manifestHash) throw new Error('Staged manifest changed.');
    const manifest = await readJSON(PathUtils.join(directory, 'manifest.json'));
    if (manifest.schema !== 1 || manifest.edition !== 'Full' || manifest.version !== pending.version || manifest.loaderProtocol !== 1 || compareVersions(manifest.version, installed.version) <= 0) throw new Error('Staged update is no longer compatible.');
    await this.verifyStage(pending.directory, manifest);
    // Refuse links anywhere in the active theme before renaming it. Preserve
    // the user's overrides as they exist at shutdown, not at download time.
    await treeFiles(this.chrome);
    const prepared = PathUtils.join(directory, 'chrome');
    const custom = PathUtils.join(this.chrome, 'customChrome.css');
    if (await ordinary(custom, 'regular', true)) await IOUtils.copy(custom, PathUtils.join(prepared, 'customChrome.css'));
    await IOUtils.writeUTF8(PathUtils.join(prepared, MARKER), installed.marker.replace(/^Version: .+$/m, 'Version: ' + manifest.version));
    const backup = PathUtils.join(this.directory, 'rollback-' + Services.uuid.generateUUID().toString().replace(/[{}]/g, ''));
    const journal = PathUtils.join(this.directory, 'transaction.json');
    await writeJSON(journal, { schema: 1, owner: OWNER, backup: PathUtils.filename(backup), version: manifest.version });
    await this.move(this.chrome, backup, { noOverwrite: true });
    try { await this.move(prepared, this.chrome, { noOverwrite: true }); }
    catch (error) {
      await this.move(backup, this.chrome, { noOverwrite: true });
      await IOUtils.remove(journal);
      throw error;
    }
    this.state.pending = null; this.state.status = 'applied'; this.state.installedVersion = manifest.version;
    this.state.backup = PathUtils.filename(backup); this.state.error = null;
    await this.save();
    await IOUtils.remove(journal);
    return true;
  }

  attachWindow(win) {
    const doc = win.document, parent = doc.getElementById('menu_ToolsPopup');
    if (!parent || doc.getElementById('whitesur-updates-menu')) return;
    const menu = doc.createXULElement('menu'); menu.id = 'whitesur-updates-menu'; menu.setAttribute('label', 'WhiteSur Updates');
    const popup = doc.createXULElement('menupopup'), status = doc.createXULElement('menuitem'); status.setAttribute('disabled', 'true');
    const check = doc.createXULElement('menuitem'); check.setAttribute('label', 'Check for theme updates');
    check.addEventListener('command', () => this.checkForUpdates({ force: true }));
    const enabled = doc.createXULElement('menuitem'); enabled.setAttribute('type', 'checkbox'); enabled.setAttribute('label', 'Automatic theme updates');
    enabled.addEventListener('command', async () => {
      const settings = await this.settings(); if (!settings) return;
      settings.enabled = enabled.getAttribute('checked') === 'true';
      await writeJSON(this.settingsPath, settings);
      this.state.status = settings.enabled ? (this.state.pending ? 'pending' : 'idle') : (this.state.pending ? 'paused' : 'disabled');
      await this.save();
    });
    popup.append(status, check, enabled); menu.append(popup); parent.append(menu);
    const update = () => {
      const labels = { idle: 'Checks GitHub once a day', checking: 'Checking GitHub…', downloading: 'Downloading update…', pending: 'Ready — applies when Firefox restarts', paused: 'Update ready — enable automatic updates to apply', 'up-to-date': 'Theme is up to date', applied: 'Theme update applied', error: 'Update unavailable — try again later', manual: 'Manual theme installation or Firefox update needed', disabled: 'Automatic updates are off' };
      status.setAttribute('label', labels[this.state.status] || 'Theme updater');
      this.settings().then(s => enabled.setAttribute('checked', s?.enabled ? 'true' : 'false')).catch(() => {});
    };
    this.views.add(update); update();
    win.addEventListener('unload', () => this.views.delete(update), { once: true });
  }

  start() {
    this.ready = this.initialize().catch(error => { this.state.status = 'error'; this.state.error = String(error); this.notify(); });
    // Earlier than IOUtils' own shutdown barrier: all theme I/O finishes before
    // the profile lock is released and the next Firefox instance can start.
    AsyncShutdown.profileChangeTeardown.addBlocker('WhiteSur: staged theme update', async () => {
      this.stopping = true; clearTimeout(this.timer); clearInterval(this.interval); this.abort?.abort();
      await this.checking;
      try { await this.applyPending(); } catch (error) {
        this.state.status = 'error'; this.state.error = String(error.message || error).slice(0, 300);
        await this.save().catch(() => {});
      }
    });
    this.timer = setTimeout(() => this.checkForUpdates(), 30000);
    this.interval = setInterval(() => this.checkForUpdates(), DAY);
    return this;
  }
}

let updater;
export function startFullUpdater(win) {
  if (!updater) updater = new ThemeUpdater(PathUtils.profileDir).start();
  updater.attachWindow(win);
  return updater;
}
