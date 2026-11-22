const endpointPath = '/cgi-bin/luci/admin/services/openclash/device_history';
const keyOf = mac => /^[\da-f]{2}(?::[\da-f]{2}){5}$/i.test(mac || '') ? mac.replaceAll(':', '').toLowerCase() : '';
let markers = {}, token, pending, loadedAt = 0;
const restoring = new Map();
const offlineGenerations = new Map();
function endpoints() {
  const list = [endpointPath];
  // HigoOS serves the SPA on :80 while LuCI/uhttpd commonly listens on :8080.
  // Keep the relative URL first for devices that proxy LuCI on the same origin.
  if (typeof location !== 'undefined' && location.hostname) {
    const port = location.port || (location.protocol === 'https:' ? '443' : '80');
    if (port !== '8080') list.push(`${location.protocol}//${location.hostname}:8080${endpointPath}`);
  }
  return list;
}
async function request(options) {
  let lastError;
  for (const endpoint of endpoints()) {
    try {
      const crossPort = endpoint !== endpointPath;
      const response = await fetch(endpoint, {credentials:crossPort?'include':'same-origin',cache:'no-store',signal:AbortSignal.timeout(2000),...options});
      const data = await response.json().catch(()=>null);
      if (!response.ok || response.redirected || response.headers.has('x-luci-login-required') || !data)
        throw new Error(data?.error || `清理服务返回 HTTP ${response.status}`);
      return data;
    } catch (error) { lastError = error; }
  }
  throw new Error(lastError?.message || '清理服务暂不可用，请重新登录后重试');
}
async function load(force=false) {
  if (pending) return pending;
  if (!force && Date.now()-loadedAt<1000) return;
  pending = request().then(data=>{
    if (!data.markers || typeof data.markers !== 'object' || !data.token) throw new Error('无效的清理服务响应');
    markers=data.markers; token=data.token; loadedAt=Date.now();
  }).finally(()=>{pending=null;});
  return pending;
}
export async function prepareDeviceHistory() {
  const task = load().catch(()=>{});
  // Only the first load blocks display; subsequent refreshes keep cached markers.
  if (!loadedAt) await task;
}
export function filterDeviceHistory(devices, isAssociated) {
  return devices.filter(device=>{
    const key=keyOf(device.macAddress), generation=markers[key];
    if (!generation) return true;
    // An old backend online flag cannot resurrect a cleared wireless record.
    // The reconciler knows whether a current association was actually observed.
    const wired=device.connectionType==='wired' || device.connectionDetail?.kind==='wired';
    if (!device.isOnline) offlineGenerations.set(key,generation);
    if (!device.isOnline || (wired ? offlineGenerations.get(key)!==generation : !isAssociated(device))) return false;
    if (!restoring.has(key)) {
      const task=request({method:'POST',body:new URLSearchParams({token,mac:key,action:'restore',generation})})
        .then(()=>{if(markers[key]===generation) delete markers[key];})
        .catch(()=>{}).finally(()=>restoring.delete(key));
      restoring.set(key,task);
    }
    return true;
  });
}
export function createDeviceHistory({defineComponent,h,ref,Modal,Button}) {
  return defineComponent({name:'HigoosDeviceHistory',props:{device:Object},setup(props){
    const show=ref(false),busy=ref(false),error=ref('');
    async function forget() {
      if(busy.value || props.device.isOnline) return;
      busy.value=true; error.value='';
      try {
        await load(true);
        const mac=keyOf(props.device.macAddress);
        const data=await request({method:'POST',body:new URLSearchParams({token,mac,action:'forget'})});
        markers[mac]=data.generation;
        offlineGenerations.set(mac,data.generation);
        show.value=false;
      } catch(cause) {error.value=cause.message;} finally {busy.value=false;}
    }
    return ()=>!props.device.isOnline && keyOf(props.device.macAddress) ? h('div',{class:'flex h-full shrink-0 items-center'},[
      h('button',{type:'button',class:'shrink-0 text-xs text-txt-3 hover:underline',style:{whiteSpace:'nowrap'},onClick:()=>{show.value=true;error.value='';}},'清理离线记录'),
      show.value?h(Modal,{modelValue:true,'onUpdate:modelValue':v=>{if(!busy.value)show.value=v;},title:'清理离线记录',size:'sm'},{
        default:()=>[
          h('p',{class:'text-sm text-txt-2'},`将 ${props.device.name || props.device.macAddress} 从设备列表移除。重新接入后会重新显示，不影响接入或上网规则；历史流量统计保留。`),
          error.value?h('p',{role:'alert',class:'text-sm text-err'},error.value):null,
        ],
        footer:()=>h('div',{class:'flex justify-end gap-2'},[
          h(Button,{disabled:busy.value,variant:'ghost',onClick:()=>{show.value=false;}},()=> '取消'),
          h(Button,{disabled:busy.value || props.device.isOnline,variant:'primary',onClick:forget},()=>busy.value?'正在清理':'确认清理'),
        ]),
      }):null,
    ]):null;
  }});
}
