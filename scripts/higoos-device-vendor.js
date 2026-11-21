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
  const choices = ref({});
  const endpoint = '/cgi-bin/luci/admin/services/openclash/device_remarks';
  async function load() {
    const response = await fetch(endpoint, {credentials:'same-origin', cache:'no-store'});
    if (!response.ok || response.redirected) throw new Error('请重新登录后重试');
    const data = await response.json();
    if (!data.token) throw new Error('登录已失效，请重新登录');
    choices.value = data.avatars || {};
    return data.token;
  }
  load().catch(() => {});
  database.then(value => { vendors.value = value; }).catch(() => {});
  return defineComponent({name:'HigoosDeviceAvatar', props:{mac:String, fallback:String}, setup(props) {
    const show = ref(false), busy = ref(false), error = ref('');
    const key = () => (props.mac || '').replace(/[:-]/g, '').toLowerCase();
    async function save(event) {
      const value = event.target.value;
      if (!/^[0-9a-f]{12}$/.test(key())) return;
      busy.value = true; error.value = '';
      try {
        const token = await load();
        const response = await fetch(endpoint, {method:'POST',credentials:'same-origin',body:new URLSearchParams({token,mac:key(),kind:'avatar',avatar:value})});
        const data = await response.json();
        if (!response.ok || response.redirected || data.error) throw new Error(data.error || '保存头像失败');
        choices.value = {...choices.value, [key()]:data.avatar}; show.value = false;
      } catch (cause) { error.value = cause.message || '保存头像失败'; }
      finally { busy.value = false; }
    }
    return () => {
      const brand = choices.value[key()] || (vendors.value && vendorBrand(findVendor(props.mac, vendors.value)));
      const image = brand
        ? h('span', {title:brand, style:{display:'flex',alignItems:'center',justifyContent:'center',width:'42px',height:'42px',borderRadius:'10px',fontSize:brand.length > 7 ? '8px' : '10px',fontWeight:'700',letterSpacing:'-.3px',color:'#0879bd',background:'rgba(0,123,196,.08)',overflow:'hidden'}}, brand)
        : h('img', {src:props.fallback, alt:'', class:'w-6 h-6 object-contain'});
      return h('div', {style:{position:'relative'}}, [
        h('button', {type:'button', title:'选择设备头像', 'aria-label':'选择设备头像', onClick:()=>{show.value=!show.value;error.value='';}}, [image]),
        show.value ? h('div', {style:{position:'absolute',top:'100%',left:'0',zIndex:'30',minWidth:'160px',padding:'8px',borderRadius:'8px',background:'var(--bg-1, #fff)',boxShadow:'0 4px 18px rgba(0,0,0,.25)'}}, [
          h('select', {value:choices.value[key()] || '', disabled:busy.value, onChange:save, 'aria-label':'设备头像', style:{width:'100%',color:'#111',background:'#fff'}}, [
            h('option', {value:''}, '自动识别'), ...['Samsung','Huawei','Apple','Xiaomi','OPPO','vivo','Honor','Lenovo','ASUS','Dell','HP','Computer','Phone','Tablet','TV'].map(name=>h('option',{value:name},name))
          ]), error.value ? h('p', {role:'alert',style:{color:'#dc2626',fontSize:'12px'}}, error.value) : null
        ]) : null
      ]);
    };
  }});
}
