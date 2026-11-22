// One sampler for the sidebar and dashboard. The API reports Mbps in both
// directions. Resource history is deliberately not used as a current speed.
const listeners = new Set();
let timer, pending, current = null;
function interval() {
  try {
    const seconds = Number(localStorage.getItem('h5000m-dashboard-refresh'));
    return ([1, 2, 3, 5].includes(seconds) ? seconds : 1) * 1000;
  } catch { return 1000; }
}
async function tick() {
  if (pending || document.hidden || !listeners.size) return;
  pending = true;
  try {
    const response = await fetch('/api/v1/system/realtime-speed', {
      credentials: 'same-origin', cache: 'no-store', signal: AbortSignal.timeout(2500),
    });
    if (!response.ok || response.redirected) throw new Error('Speed unavailable');
    const payload = await response.json();
    const data = payload.data ?? payload;
    if (!Number.isFinite(data.upload) || !Number.isFinite(data.download) ||
        data.upload < 0 || data.download < 0) throw new Error('Invalid speed sample');
    current = {upload: data.upload, download: data.download};
  } catch { current = null; }
  finally {
    pending = false;
    for (const notify of listeners) notify(current);
  }
}
function schedule() {
  clearInterval(timer);
  if (!listeners.size || document.hidden) return;
  timer = setInterval(tick, interval());
  tick();
}
export function subscribeRealtimeSpeed(notify) {
  listeners.add(notify);
  notify(current);
  if (listeners.size === 1) {
    document.addEventListener('visibilitychange', schedule);
    window.addEventListener('higoos-refresh-change', schedule);
    window.addEventListener('storage', schedule);
    schedule();
  }
  return () => {
    listeners.delete(notify);
    if (listeners.size) return;
    clearInterval(timer);
    current = null;
    document.removeEventListener('visibilitychange', schedule);
    window.removeEventListener('higoos-refresh-change', schedule);
    window.removeEventListener('storage', schedule);
  };
}
