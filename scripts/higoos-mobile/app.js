const $ = (id) => document.getElementById(id);
const state = { busy: false, timer: 0 };
const api = async (path, options = {}) => {
  const response = await fetch(`/api/v1${path}`, {
    credentials: 'same-origin', cache: 'no-store', ...options,
    headers: { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
  });
  if (response.redirected || response.status === 401) throw Object.assign(new Error('登录状态已失效，请重新登录'), { auth: true });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || (payload && typeof payload === 'object' && 'code' in payload && payload.code !== 0)) {
    throw new Error(payload.message || `请求失败 (${response.status})`);
  }
  return payload?.data ?? payload;
};
const fmtRate = (value) => Number.isFinite(Number(value)) ? Number(value).toFixed(Number(value) < 10 ? 2 : 1) : '--';
const setConnected = (online) => {
  const el = $('connection-state'); el.classList.toggle('offline', !online);
  el.innerHTML = `<i></i>${online ? '已连接' : '连接中断'}`;
};
function showLogin(message = '') {
  $('dashboard').hidden = true; $('login-panel').hidden = false;
  $('login-error').textContent = message;
}
function showDashboard() { $('login-panel').hidden = true; $('dashboard').hidden = false; }
function pct(value) {
  const n = Number(value); return Number.isFinite(n) ? `${Math.max(0, Math.min(100, n)).toFixed(0)}%` : '--';
}
function renderResources(data = {}) {
  const cpu = data.cpu ?? data.cpuUsage ?? data.cpu_usage;
  const mem = data.memory ?? data.mem ?? {};
  const cpuValue = typeof cpu === 'object' ? cpu.usage ?? cpu.percent : cpu;
  $('cpu-value').textContent = cpuValue == null ? '--' : (Number(cpuValue) <= 1 ? pct(Number(cpuValue) * 100) : pct(cpuValue));
  const used = mem.used ?? mem.usedBytes ?? mem.used_bytes;
  const total = mem.total ?? mem.totalBytes ?? mem.total_bytes;
  const usage = mem.usage ?? mem.percent ?? (Number(total) > 0 ? Number(used) / Number(total) * 100 : null);
  $('memory-value').textContent = usage == null ? '--' : pct(Number(usage) <= 1 ? Number(usage) * 100 : usage);
  $('memory-detail').textContent = Number(total) > 0 ? `${bytes(used)} / ${bytes(total)}` : '使用情况';
  const load = data.loadAverage ?? data.load_average ?? data.load;
  $('cpu-detail').textContent = Array.isArray(load) ? `负载 ${load.slice(0, 3).map(x => Number(x).toFixed(2)).join(' / ')}` : 'CPU 使用率';
}
function bytes(value) {
  let n = Number(value); if (!Number.isFinite(n)) return '--';
  const units = ['B', 'KB', 'MB', 'GB']; let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i > 1 ? 1 : 0)} ${units[i]}`;
}
function renderWireless(data) {
  const bands = Array.isArray(data) ? data : (data?.bands || data?.interfaces || []);
  $('wireless-count').textContent = `${bands.filter(b => b.enabled !== false).length} 个频段`;
  $('wireless-list').innerHTML = bands.length ? bands.map((band) => {
    const enabled = band.enabled !== false;
    const bandName = String(band.band || band.name || '').toLowerCase();
    const label = bandName.includes('5') ? '5 GHz' : bandName.includes('6') ? '6 GHz' : '2.4 GHz';
    const ssid = band.ssid || band.networkName || bandName || '无线网络';
    const clients = Number(band.clients ?? band.clientCount);
    return `<article class="wireless-row"><span class="row-icon">⌁</span><span class="row-copy"><strong>${escapeHtml(ssid)}</strong><small>${label}${Number.isFinite(clients) ? ` · ${clients} 台设备` : ''}</small></span><span class="row-state ${enabled ? '' : 'offline'}">${enabled ? '已开启' : '已关闭'}</span></article>`;
  }).join('') : '<p class="muted">无线信息暂不可用</p>';
}
function renderDevices(data) {
  const devices = Array.isArray(data) ? data : (data?.devices || data?.items || []);
  const online = devices.filter(d => d.isOnline === true);
  $('device-list').innerHTML = online.length ? online.slice(0, 8).map((device) => {
    const detail = device.connectionDetail || {};
    const band = detail.kind === 'wifi-2g' ? '2.4 GHz' : detail.kind === 'wifi-5g' ? '5 GHz' : device.connectionType === 'wired' ? '有线连接' : '在线';
    const ip = device.ipAddress || device.macAddress || '';
    const type = device.deviceType === 'computer' ? '▣' : device.deviceType === 'phone' ? '▯' : '•';
    return `<article class="device-row"><span class="row-icon">${type}</span><span class="row-copy"><strong>${escapeHtml(device.name || device.macAddress || '未知设备')}</strong><small>${escapeHtml(ip)} · ${band}</small></span><span class="row-state">在线</span></article>`;
  }).join('') : '<p class="muted">当前没有在线设备</p>';
}
function escapeHtml(value) { return String(value).replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]); }
async function refresh() {
  if (state.busy || document.hidden || $('dashboard').hidden) return;
  state.busy = true;
  try {
    const [info, resources, devices, wireless, speed] = await Promise.allSettled([
      api('/system/info'), api('/system/resources'), api('/devices'), api('/wifi/settings'), api('/system/realtime-speed'),
    ]);
    if (info.status === 'fulfilled') {
      const data = info.value || {};
      $('router-name').textContent = data.deviceModel || data.model || data.hostname || 'H5000M';
      setConnected(true);
    } else if (info.reason?.auth) throw info.reason;
    if (resources.status === 'fulfilled') renderResources(resources.value);
    if (devices.status === 'fulfilled') renderDevices(devices.value);
    if (wireless.status === 'fulfilled') renderWireless(wireless.value);
    if (speed.status === 'fulfilled') {
      const data = speed.value || {};
      $('download-value').textContent = fmtRate(data.download);
      $('upload-value').textContent = fmtRate(data.upload);
    }
    const failed = [info, resources, devices, wireless, speed].filter(x => x.status === 'rejected').length;
    $('global-error').hidden = failed === 0;
    $('global-error').textContent = failed ? `${failed} 项状态暂时无法读取，正在自动重试。` : '';
    $('updated-at').textContent = `最近更新 ${new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}`;
    setConnected(info.status === 'fulfilled');
  } catch (error) {
    if (error.auth) { showLogin(error.message); return; }
    setConnected(false);
    $('global-error').hidden = false; $('global-error').textContent = error.message;
  } finally { state.busy = false; }
}
async function checkSession() {
  try { await api('/auth/me'); showDashboard(); await refresh(); }
  catch (error) { showLogin(error.auth ? '' : error.message); }
}
$('login-form').addEventListener('submit', async (event) => {
  event.preventDefault(); const formElement = event.currentTarget; const form = new FormData(formElement);
  const button = formElement.querySelector('button'); button.disabled = true; button.textContent = '登录中…';
  try {
    await api('/auth/login', { method: 'POST', body: JSON.stringify({ username: form.get('username'), password: form.get('password') }) });
    formElement.reset(); showDashboard(); await refresh();
  } catch (error) { $('login-error').textContent = error.message || '登录失败'; }
  finally { button.disabled = false; button.textContent = '登录'; }
});
$('refresh').addEventListener('click', refresh);
$('logout').addEventListener('click', async () => { try { await api('/auth/logout', { method: 'POST' }); } catch {} showLogin('已退出登录'); });
$('reboot').addEventListener('click', async () => {
  if (!window.confirm('确定重启路由器吗？重启期间网络和远程连接会暂时中断。')) return;
  const button = $('reboot'); button.disabled = true; $('action-message').textContent = '正在发送重启请求…';
  try { await api('/system/reboot', { method: 'POST' }); $('action-message').textContent = '重启请求已发送，请等待路由器重新上线。'; }
  catch (error) { $('action-message').textContent = error.message || '重启请求失败'; }
  finally { window.setTimeout(() => { button.disabled = false; }, 15000); }
});
document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
state.timer = window.setInterval(refresh, 3000);
if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => {});
checkSession();
