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
export function brandFromDeviceName(name) {
  const value = (name || '').trim();
  if (/\biphone\b|\bipad\b/i.test(value)) return 'Apple';
  if (/\bsamsung\b|\bgalaxy\b|(?:^|[^a-z0-9])s(?:2[0-9]|1[0-9])(?:[-_ ]?(?:ultra|plus|fe|\+))?(?:$|[^a-z0-9])/i.test(value)) return 'Samsung';
  if (/\bhuawei\b|\b(?:mate|pura)[-_ ]?\d+/i.test(value)) return 'Huawei';
  if (/\bxiaomi\b|\bredmi\b/i.test(value)) return 'Xiaomi';
  return '';
}
export function createDeviceVendor({defineComponent, h, ref}) {
  const vendors = ref(null);
  database ??= fetch('/assets/higoos-ieee-vendors.json', {cache:'force-cache'}).then(r => {
    if (!r.ok) throw new Error('vendor database unavailable');
    return r.json();
  });
  database.then(value => { vendors.value = value; }).catch(() => {});
  return defineComponent({name:'HigoosDeviceVendor', props:{mac:String}, setup(props) {
    return () => { const vendor = vendors.value && findVendor(props.mac, vendors.value); return vendor ? h('p', {class:'break-all',style:{fontSize:'11px',lineHeight:'1.25',opacity:'0.78',maxWidth:'100%'}}, `厂商：${vendor}`) : null; };
  }});
}
export function brandLogo(brand) {
  const logos = {apple:'apple', samsung:'samsung', huawei:'huawei', xiaomi:'xiaomi', oppo:'oppo', vivo:'vivo', honor:'honor', lenovo:'lenovo', asus:'asus', dell:'dell', hp:'hp', google:'google', 'tp-link':'tplink', computer:'computer', phone:'phone', tablet:'tablet', tv:'tv'};
  const slug = logos[(brand || '').toLowerCase()];
  return slug ? `/assets/device-logos/${slug}.svg` : '';
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
  return defineComponent({name:'HigoosDeviceAvatar', props:{mac:String, name:String, fallback:String}, setup(props) {
    const show = ref(false), busy = ref(false), error = ref('');
    const key = () => (props.mac || '').replace(/[:-]/g, '').toLowerCase();
    async function save(value) {
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
      const brand = choices.value[key()] || (vendors.value && vendorBrand(findVendor(props.mac, vendors.value))) || brandFromDeviceName(props.name);
      const logo = brandLogo(brand);
      const image = logo ? h('span', {title:brand,style:{display:'flex',alignItems:'center',justifyContent:'center',width:'60px',height:'60px',borderRadius:'10px',background:'transparent'}}, [h('img',{src:logo,alt:brand,style:{width:'100%',height:'100%',objectFit:'contain',shapeRendering:'geometricPrecision'}})]) : brand
        ? h('span', {title:brand, style:{display:'flex',alignItems:'center',justifyContent:'center',width:'54px',height:'54px',borderRadius:'10px',fontSize:brand.length > 7 ? '12px' : brand.length > 4 ? '14px' : '17px',fontWeight:'700',letterSpacing:'-.3px',color:'#0879bd',background:'transparent',overflow:'hidden'}}, brand)
        : h('img', {src:props.fallback, alt:'', class:'w-9 h-9 object-contain'});
      return h('div', {style:{position:'relative'}}, [
        h('button', {type:'button', title:'选择设备头像', 'aria-label':'选择设备头像', onClick:()=>{show.value=!show.value;error.value='';}}, [image]),
        show.value ? h('div', {role:'dialog','aria-label':'选择设备头像',style:{position:'absolute',top:'calc(100% + 8px)',left:'0',zIndex:'50',width:'220px',padding:'12px',borderRadius:'12px',background:'var(--bg-1, #fff)',color:'var(--text-1, #1f2937)',boxShadow:'0 8px 24px rgba(0,0,0,.2)',border:'1px solid var(--line-1, #e5e7eb)'}}, [
          h('div', {style:{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'10px',fontWeight:'600',fontSize:'14px'}}, [
            h('span', {}, '选择设备头像'), h('button',{type:'button','aria-label':'关闭',onClick:()=>{show.value=false;},style:{border:'0',background:'transparent',color:'inherit',fontSize:'18px',cursor:'pointer'}},'×')
          ]),
          h('div', {style:{display:'grid',gridTemplateColumns:'repeat(3, minmax(0, 1fr))',gap:'6px',maxHeight:'230px',overflowY:'auto'}}, [
            ...[['','自动识别'], ...Object.entries({Samsung:'三星',Huawei:'华为',Apple:'苹果',Xiaomi:'小米',OPPO:'OPPO',vivo:'vivo',Honor:'荣耀',Lenovo:'联想',ASUS:'华硕',Dell:'戴尔',HP:'惠普',Computer:'电脑',Phone:'手机',Tablet:'平板',TV:'电视'})].map(([value,label])=>h('button',{type:'button',disabled:busy.value,onClick:()=>save(value),style:{padding:'7px 3px',border:'1px solid var(--line-1, #e5e7eb)',borderRadius:'7px',background:(choices.value[key()] || '')===value?'rgba(0,123,196,.16)':'transparent',color:'inherit',fontSize:'12px',cursor:'pointer',overflow:'hidden',textOverflow:'ellipsis'}},label))
          ]), error.value ? h('p', {role:'alert',style:{color:'#dc2626',fontSize:'12px'}}, error.value) : null
        ]) : null
      ]);
    };
  }});
}
