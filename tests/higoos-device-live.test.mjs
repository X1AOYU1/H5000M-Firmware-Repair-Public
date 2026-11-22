import assert from 'node:assert/strict';
import {createDeviceReconciler} from '../scripts/higoos-device-live.js';
import {topologyDeviceIcon} from '../scripts/higoos-topology-icons.js';
import {createLanLink} from '../scripts/higoos-lan-link.js';

const phone = {id:'phone',name:'Yu-de-S24-Ultra',deviceType:'other',isOnline:true,
  macAddress:'C6:AC:9F:F6:94:22',connectionType:'wifi',downloadSpeed:12,uploadSpeed:2,
  connectionDetail:{kind:'wifi-mlo',iface:'phy1-ap0',ssid:'home',signalDbm:-45,
    rxRateMbps:2594,txRateMbps:2161,mcs:11,bandwidthMhz:160,nss:2}};
const snapshot = (clients, band='wifi-5g', complete=true) => ({complete,interfaces:[
  {iface:'phy0-ap0',band:'wifi-2.4g',clients:[]},
  {iface:'phy1-ap0',band,clients},
]});
const station = {mac:phone.macAddress.toLowerCase(),signalDbm:-47};
const reconcile = createDeviceReconciler();
let [device] = reconcile([phone],snapshot([station]));
assert.equal(device.deviceType,'mobile');
assert.equal(device.connectionType,'wifi-5g');
assert.equal(device.connectionDetail.signalDbm,-47);
const empty = snapshot([]);
assert.equal(reconcile([phone],empty)[0].isOnline,true,'one missing sample must not flicker');
assert.equal(reconcile([phone],empty)[0].isOnline,true,'cached sample does not count twice');
[device] = reconcile([phone],snapshot([]));
assert.equal(device.isOnline,false,'two fresh absent associations override stale backend online');
assert.equal(device.downloadSpeed,0);
assert.equal(device.uploadSpeed,0);
for (const key of ['signalDbm','rxRateMbps','txRateMbps','mcs','bandwidthMhz','nss']) assert.equal(device.connectionDetail[key],undefined);
assert.equal(device.connectionDetail.ssid,'home','retain connection identity');
assert.equal(phone.connectionDetail.signalDbm,-45,'never mutate cached backend response');
[device] = reconcile([{...phone,isOnline:false}],snapshot([station],'wifi-2.4g'));
assert.equal(device.isOnline,true,'association immediately detects reconnect despite backend lag');
assert.equal(device.connectionType,'wifi-2.4g','roam updates band');
assert.equal(reconcile([phone],snapshot([],'wifi-5g',false))[0].isOnline,true,'partial snapshots cannot prove absence');
assert.equal(reconcile([phone],null)[0].isOnline,true,'RPC failure cannot prove absence');
assert.equal(reconcile([phone],snapshot([]))[0].isOnline,true,'failure resets consecutive missing count');
assert.equal(reconcile([phone],snapshot([station]))[0].isOnline,true,'sleeping associated station stays online without traffic');
const mlo = {...phone,macAddress:'02:00:00:00:00:01',connectionDetail:{...phone.connectionDetail,linkMac:phone.macAddress}};
assert.equal(reconcile([mlo],snapshot([station]))[0].connectionType,'wifi-5g','MLO link MAC resolves current radio');
const known = createDeviceReconciler()([{...phone,connectionDetail:{kind:'wifi-2g'}}],null)[0];
assert.equal(known.connectionType,'wifi-2.4g','preserve known band if live RPC unavailable');
const offline = reconcile([{...phone,isOnline:false}],null)[0];
const rendered = createLanLink((tag,props,text)=>text).render.call({device:offline,speed:'2500 Mbps',fallback:'stale speed'});
assert.equal(rendered,'—','offline card never falls back to stale negotiation rate');
const icons = ['computer','mobile','tablet','tv','iot','game','other'].map(deviceType => topologyDeviceIcon({deviceType},'#e2e8f0'));
assert.equal(new Set(icons).size,7,'each device category has its own topology silhouette');
for (const icon of icons) assert.ok(decodeURIComponent(icon).includes('viewBox="0 0 24 24"'));
assert.equal(reconcile([{...phone,connectionType:'wired',connectionDetail:{kind:'wired'}}],snapshot([]))[0].isOnline,true,'wireless collection never marks wired clients offline');
const store = new Map();
const storage = {getItem:k=>store.get(k), setItem:(k,v)=>store.set(k,v)};
const roam = createDeviceReconciler(storage);
roam([phone], snapshot([station]));
const unknown = {...phone, connectionType:'unknown', connectionDetail:{kind:'unknown'}};
const replacement = {...phone, macAddress:'0A:F1:B0:C0:40:19'};
const newStation = {mac:replacement.macAddress,signalDbm:-50};
assert.equal(roam([unknown],snapshot([newStation]))[0].isOnline,true);
let switched = roam([unknown,replacement],snapshot([newStation]));
assert.equal(switched[0].isOnline,false,'previously associated MAC becomes offline after roam');
assert.equal(switched[1].isOnline,true,'new MAC remains online');
const reload = createDeviceReconciler(storage);
assert.equal(reload([unknown],snapshot([newStation]))[0].isOnline,true);
assert.equal(reload([unknown],snapshot([newStation]))[0].isOnline,false,'association evidence survives reload');
assert.equal(reload([{...unknown,connectionType:'wired',connectionDetail:{kind:'wired'}}],snapshot([]))[0].isOnline,true,'explicit wired evidence takes precedence');
const stranger = {...unknown,macAddress:'00:11:22:33:44:55'};
reload([stranger],snapshot([]));
assert.equal(reload([stranger],snapshot([]))[0].isOnline,true,'unknown device without wireless evidence is not guessed offline');
console.log('PASS: association disconnect/reconnect/roam, MLO, failure fallback, offline metrics, type-aware topology icons');
