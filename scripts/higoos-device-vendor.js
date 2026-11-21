let database;
export function findVendor(mac, vendors) {
  const key = (mac || '').replace(/[:-]/g, '').toUpperCase();
  if (!/^[0-9A-F]{12}$/.test(key) || (parseInt(key.slice(0, 2), 16) & 3)) return '';
  return vendors[key.slice(0,9)] || vendors[key.slice(0,7)] || vendors[key.slice(0,6)] || '';
}
export function vendorBrand(vendor) {
  const name = (vendor || '').toUpperCase();
  const brands = [
    [/HUAWEI|HONOR DEVICE/, 'HUAWEI'], [/SAMSUNG/, 'SAMSUNG'],
    [/APPLE/, 'Apple'], [/XIAOMI|BEIJING XIAOMI/, 'Xiaomi'],
    [/OPPO|ONEPLUS/, 'OPPO'], [/VIVO MOBILE|VIVO COMMUNICATION/, 'vivo'],
    [/LENOVO/, 'Lenovo'], [/ASUSTEK|ASUS/, 'ASUS'],
    [/DELL/, 'DELL'], [/HEWLETT.PACKARD|HP INC/, 'HP'],
    [/ELITEGROUP COMPUTER/, 'ECS'], [/MICROSOFT/, 'Microsoft'],
    [/GOOGLE/, 'Google'], [/TP.LINK/, 'TP-Link']
  ];
  return brands.find(([pattern]) => pattern.test(name))?.[1] || '';
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
export function createDeviceAvatar({defineComponent, h, ref}) {
  const vendors = ref(null);
  database.then(value => { vendors.value = value; }).catch(() => {});
  return defineComponent({name:'HigoosDeviceAvatar', props:{mac:String, fallback:String}, setup(props) {
    return () => {
      const brand = vendors.value && vendorBrand(findVendor(props.mac, vendors.value));
      return brand
        ? h('span', {title:brand, style:{display:'flex',alignItems:'center',justifyContent:'center',width:'42px',height:'42px',borderRadius:'10px',fontSize:brand.length > 7 ? '8px' : '10px',fontWeight:'700',letterSpacing:'-.3px',color:'#0879bd',background:'rgba(0,123,196,.08)',overflow:'hidden'}}, brand)
        : h('img', {src:props.fallback, alt:'', class:'w-6 h-6 object-contain'});
    };
  }});
}
