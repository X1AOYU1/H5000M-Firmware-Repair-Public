let database;
export function findVendor(mac, vendors) {
  const key = (mac || '').replace(/[:-]/g, '').toUpperCase();
  if (!/^[0-9A-F]{12}$/.test(key) || (parseInt(key.slice(0, 2), 16) & 3)) return '';
  return vendors[key.slice(0,9)] || vendors[key.slice(0,7)] || vendors[key.slice(0,6)] || '';
}
export function createDeviceVendor({defineComponent, h, ref}) {
  const vendors = ref(null);
  database ??= fetch('/assets/higoos-ieee-vendors.json', {cache:'force-cache'}).then(r => {
    if (!r.ok) throw new Error('vendor database unavailable');
    return r.json();
  });
  database.then(value => { vendors.value = value; }).catch(() => {});
  return defineComponent({name:'HigoosDeviceVendor', props:{mac:String}, setup(props) {
    return () => { const vendor = vendors.value && findVendor(props.mac, vendors.value); return vendor ? h('p', {class:'break-all'}, `厂商：${vendor}`) : null; };
  }});
}
