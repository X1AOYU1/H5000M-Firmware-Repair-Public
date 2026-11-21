// The LAN interface rate describes the router's port, which may lead to a switch.
export function lanLinkLabel(interfaces) {
  if (!Array.isArray(interfaces)) return '';
  const matches = interfaces.filter(item => item && item.name === 'eth1');
  if (matches.length !== 1 || matches[0].connected !== true) return '';
  const speed = String(matches[0].speedLabel ?? '').trim();
  return /^\d+(?:\.\d+)?\s*(?:[KMGT]bps)$/i.test(speed) && parseFloat(speed) > 0 ? speed : '';
}

export function createLanLink(h) {
  return {
    name: 'H5000mLanLink',
    props: { device: Object },
    data() { return { speed: '', timer: null, stopped: false }; },
    mounted() {
      const update = async () => {
        try {
          const response = await fetch('/api/v1/system/network-interfaces', { credentials: 'same-origin', cache: 'no-store' });
          const payload = response.ok ? await response.json() : null;
          if (!this.stopped) this.speed = lanLinkLabel(Array.isArray(payload) ? payload : payload?.data);
        } catch { if (!this.stopped) this.speed = ''; }
        if (!this.stopped) this.timer = setTimeout(update, 5000);
      };
      update();
    },
    unmounted() { this.stopped = true; clearTimeout(this.timer); },
    render() {
      const d = this.device;
      if (!d?.isOnline || (d.connectionDetail?.kind !== 'wired' && d.connectionType !== 'wired') || !this.speed) return null;
      return h('span', { class: 'text-xs text-txt-3', title: '路由器 LAN 端口协商速率；经过交换机时不代表终端速率' }, `（LAN 口 ${this.speed}）`);
    },
  };
}
