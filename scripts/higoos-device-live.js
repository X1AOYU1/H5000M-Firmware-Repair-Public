import { inferDeviceType } from './higoos-device-type.js';
import { filterDeviceHistory, prepareDeviceHistory } from './higoos-device-history.js';

const associatedDevices = new WeakSet();

const endpoint = '/cgi-bin/luci/admin/services/openclash/device_wireless';
const bands = new Set(['wifi-2.4g', 'wifi-5g', 'wifi-6g']);
const macKey = value => String(value || '').toLowerCase().replaceAll('-', ':');
const liveFields = ['signalDbm', 'rxRateMbps', 'txRateMbps', 'mcs', 'bandwidthMhz', 'nss', 'wiredPort'];

// Shared by devices, details, dashboard and topology. Two complete absence
// samples avoid one transient association-table omission causing flicker.
export function createDeviceReconciler(storage, identityStorage) {
  if (storage === undefined) {
    try { storage = globalThis.sessionStorage; } catch { storage = null; }
  }
  if (identityStorage === undefined) {
    try { identityStorage = globalThis.localStorage; } catch { identityStorage = null; }
  }
  const identityKey = 'higoos-device-identity-v1';
  let identities = {};
  try { identities = JSON.parse(identityStorage?.getItem(identityKey) || '{}') || {}; } catch {}
  if (typeof identities !== 'object' || Array.isArray(identities)) identities = {};
  const nowIdentity = Date.now();
  for (const [key, entry] of Object.entries(identities)) {
    if (!entry || !Number.isFinite(entry.seen) || nowIdentity - entry.seen > 30 * 86400000 || entry.seen > nowIdentity) delete identities[key];
  }
  const usefulName = (name, ip) => typeof name === 'string' && !!name.trim() && name !== ip && !/^(?:\d{1,3}\.){3}\d{1,3}$/.test(name.trim());
  function saveIdentity(key, device, detail) {
    if (!key || !usefulName(device.name, device.ipAddress)) return;
    identities[key] = {seen: Date.now(), name: device.name, type: device.deviceType, ssid: detail.ssid};
    const entries = Object.entries(identities).sort((a,b)=>b[1].seen-a[1].seen).slice(0,512);
    identities = Object.fromEntries(entries);
    try { identityStorage?.setItem(identityKey, JSON.stringify(identities)); } catch {}
  }
  const history = new Map();
  const storageKey = 'higoos-associated-wifi-v1';
  let remembered = {};
  try { remembered = JSON.parse(storage?.getItem(storageKey) || '{}') || {}; } catch {}
  if (typeof remembered !== 'object' || Array.isArray(remembered)) remembered = {};
  const now = Date.now();
  for (const [mac, item] of Object.entries(remembered)) {
    if (!item || !Number.isFinite(item.seen) || now - item.seen > 7 * 86400000 || item.seen > now) delete remembered[mac];
  }
  function remember(key, state) {
    if (!key) return;
    remembered[key] = {seen: Date.now(), band: state.band, linkMac: state.linkMac, iface: state.iface};
    const entries = Object.entries(remembered);
    if (entries.length > 512) {
      entries.sort((a, b) => b[1].seen - a[1].seen);
      remembered = Object.fromEntries(entries.slice(0, 512));
    }
    try { storage?.setItem(storageKey, JSON.stringify(remembered)); } catch {}
  }
  return (devices, snapshot) => {
    const rows = Array.isArray(snapshot?.interfaces) ? snapshot.interfaces.filter(row =>
      row && typeof row.iface === 'string' && row.clients && typeof row.clients === 'object') : [];
    const associated = new Map();
    // LuCI serializes an empty Lua array as {} on some bridge versions.
    for (const row of rows) for (const client of Object.values(row.clients))
      associated.set(macKey(client.mac), {row, client});
    return devices.map(original => {
      let device = inferDeviceType(original);
      const detail = {...device.connectionDetail};
      const key = macKey(device.macAddress);
      const state = history.get(key) || {missing: 0};
      const linkMac = macKey(detail.linkMac || state.linkMac || remembered[key]?.linkMac);
      const hit = associated.get(key) || associated.get(linkMac);
      const prior = identities[key];
      if (prior && !usefulName(device.name, device.ipAddress)) {
        device = inferDeviceType({...device, name: prior.name,
          deviceType: device.deviceType && device.deviceType !== 'other' ? device.deviceType : prior.type});
        if (!detail.ssid && typeof prior.ssid === 'string') detail.ssid = prior.ssid;
      }
      const explicitlyWired = device.connectionType === 'wired' || detail.kind === 'wired';
      const wireless = !explicitlyWired && (device.connectionType?.startsWith('wifi') ||
        detail.kind?.startsWith('wifi') || detail.kind === 'wireless' || !!state.iface || !!remembered[key]);
      if (!state.band && bands.has(remembered[key]?.band)) state.band = remembered[key].band;
      const interfaceRow = rows.find(row => row.iface === detail.iface);
      const knownBand = bands.has(interfaceRow?.band) ? interfaceRow.band :
        ({'wifi-2g':'wifi-2.4g', 'wifi-5g':'wifi-5g', 'wifi-6g':'wifi-6g'})[detail.kind];
      if (knownBand) state.band = knownBand;
      if (hit) {
        // A stale offline backend record can retain the previous session's
        // rates. Show only measurements from the current association until
        // the backend reports the device online again.
        if (!original.isOnline || (detail.iface && detail.iface !== hit.row.iface))
          for (const field of liveFields) delete detail[field];
        state.missing = 0;
        if (bands.has(hit.row.band)) state.band = hit.row.band;
        state.iface = hit.row.iface;
        state.linkMac = macKey(hit.client.mac);
        remember(key, state);
        if (usefulName(original.name, original.ipAddress)) saveIdentity(key, device, detail);
        detail.iface = hit.row.iface;
        detail.linkMac = state.linkMac;
        detail.kind = ({'wifi-2.4g':'wifi-2g','wifi-5g':'wifi-5g','wifi-6g':'wifi-6g'})[state.band] || detail.kind;
        if (Number.isFinite(hit.client.signalDbm) && hit.client.signalDbm < 0) detail.signalDbm = hit.client.signalDbm;
        device = {...device, isOnline: true, connectionType: state.band || 'wifi'};
      } else if (wireless) {
        // A failed/partial RPC never means "no stations". All APs must be
        // covered to rule out a roam to another radio or guest interface.
        if (snapshot?.complete === true && rows.length) {
          if (state.sample !== snapshot) state.missing++;
          if (state.missing >= 2) device = {...device, isOnline: false};
        } else state.missing = 0;
        if (!bands.has(device.connectionType) && state.band)
          device = {...device, connectionType: state.band};
      }
      state.sample = snapshot;
      if (key) history.set(key, state);
      if (!device.isOnline) {
        for (const field of liveFields) delete detail[field];
        device = {...device, downloadSpeed: 0, uploadSpeed: 0, trafficRateAvailable: false};
        device.connectedTime = 0;
      }
      const result = {...device, connectionDetail: detail};
      if (hit) associatedDevices.add(result);
      return result;
    });
  };
}

const reconcile = createDeviceReconciler();
let pending, last, lastAt = 0;
async function wirelessSnapshot() {
  if (pending) return pending;
  if (Date.now() - lastAt < (last ? 450 : 5000)) return last;
  pending = (async () => {
    try {
      const response = await fetch(endpoint, {credentials:'same-origin', cache:'no-store', signal:AbortSignal.timeout(1800)});
      if (!response.ok || response.redirected || response.headers.has('x-luci-login-required')) return null;
      return await response.json();
    } catch { return null; }
  })().then(value => {last = value; lastAt = Date.now(); return value;}).finally(() => {pending = null;});
  return pending;
}

export async function withLiveDevices(load) {
  const [devices, snapshot] = await Promise.all([load(), wirelessSnapshot(), prepareDeviceHistory()]);
  return Array.isArray(devices) ? filterDeviceHistory(reconcile(devices, snapshot), device => associatedDevices.has(device)) : devices;
}

export async function withLiveDevice(load) {
  const [device, snapshot] = await Promise.all([load(), wirelessSnapshot()]);
  return device ? reconcile([device], snapshot)[0] : device;
}
