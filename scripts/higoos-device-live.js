import { inferDeviceType } from './higoos-device-type.js';

const endpoint = '/cgi-bin/luci/admin/services/openclash/device_wireless';
const bands = new Set(['wifi-2.4g', 'wifi-5g', 'wifi-6g']);
const macKey = value => String(value || '').toLowerCase().replaceAll('-', ':');
const liveFields = ['signalDbm', 'rxRateMbps', 'txRateMbps', 'mcs', 'bandwidthMhz', 'nss', 'wiredPort'];

// Shared by devices, details, dashboard and topology. Two complete absence
// samples avoid one transient association-table omission causing flicker.
export function createDeviceReconciler(storage) {
  if (storage === undefined) {
    try { storage = globalThis.sessionStorage; } catch { storage = null; }
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
    remembered[key] = {seen: Date.now(), band: state.band};
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
      const hit = associated.get(key) || associated.get(macKey(detail.linkMac));
      const explicitlyWired = device.connectionType === 'wired' || detail.kind === 'wired';
      const wireless = !explicitlyWired && (device.connectionType?.startsWith('wifi') ||
        detail.kind?.startsWith('wifi') || detail.kind === 'wireless' || !!state.iface || !!remembered[key]);
      if (!state.band && bands.has(remembered[key]?.band)) state.band = remembered[key].band;
      const interfaceRow = rows.find(row => row.iface === detail.iface);
      const knownBand = bands.has(interfaceRow?.band) ? interfaceRow.band :
        ({'wifi-2g':'wifi-2.4g', 'wifi-5g':'wifi-5g', 'wifi-6g':'wifi-6g'})[detail.kind];
      if (knownBand) state.band = knownBand;
      if (hit) {
        state.missing = 0;
        if (bands.has(hit.row.band)) state.band = hit.row.band;
        state.iface = hit.row.iface;
        remember(key, state);
        detail.iface = hit.row.iface;
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
      }
      return {...device, connectionDetail: detail};
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
  const [devices, snapshot] = await Promise.all([load(), wirelessSnapshot()]);
  return Array.isArray(devices) ? reconcile(devices, snapshot) : devices;
}

export async function withLiveDevice(load) {
  const [device, snapshot] = await Promise.all([load(), wirelessSnapshot()]);
  return device ? reconcile([device], snapshot)[0] : device;
}
