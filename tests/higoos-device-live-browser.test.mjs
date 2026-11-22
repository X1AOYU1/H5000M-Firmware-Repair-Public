import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {readFile,readdir} from 'node:fs/promises';
import {resolve,join,extname,sep} from 'node:path';

const root = resolve(process.argv[2]);
const require = createRequire(join(process.env.PLAYWRIGHT_ROOT,'__audit__.cjs'));
const {chromium} = require('playwright');
const assets = await readdir(join(root,'assets'));
const entry = assets.find(x=>x.startsWith('index-DhOCiPK2'));
const charts = assets.find(x=>x.startsWith('charts-Dg-AV5Yx'));
const mac = 'C6:AC:9F:F6:94:22';
const linkMac = '0a:f1:b0:c0:40:9a';
const phone = {id:'audit-phone',name:'Yu-de-S24-Ultra',deviceType:'other',osType:'android',
  macAddress:mac,ipAddress:'10.0.0.4',connectionType:'wifi',isOnline:true,
  connectedTime:100,downloadSpeed:1,uploadSpeed:1,trafficToday:100,
  connectionDetail:{kind:'wifi-mlo',iface:'phy1-ap0',linkMac,signalDbm:-45,rxRateMbps:2594,txRateMbps:2161}};
let stage = 'discovering', snapshots = 0, deviceRequests = 0;
const markers = {};
const errors = [];
const server = createServer(async(req,res)=>{
  const url = new URL(req.url,'http://localhost');
  if (url.pathname.endsWith('/device_history')) {
    let data={markers,token:'test-token'};
    if(req.method==='POST') {
      let body='';for await (const part of req) body+=part;
      const form=new URLSearchParams(body);
      assert.equal(form.get('token'),'test-token');
      if(form.get('action')==='forget') {markers[form.get('mac')]='test-generation';data={ok:true,generation:'test-generation'};}
      else {delete markers[form.get('mac')];data={ok:true};}
    }
    return res.writeHead(200,{'content-type':'application/json'}).end(JSON.stringify(data));
  }
  if (url.pathname.endsWith('/device_wireless')) {
    snapshots++;
    const data = {complete:true,interfaces:[{iface:'phy1-ap0',band:'wifi-5g',clients:stage!=='offline'?[{mac:linkMac,signalDbm:-45}]:{}}]};
    return res.writeHead(200,{'content-type':'application/json'}).end(JSON.stringify(data));
  }
  if (url.pathname.startsWith('/api/v1/')) {
    let data = {};
    if (url.pathname==='/api/v1/auth/me') data={username:'audit',role:'admin',permissions:['*']};
    else if (url.pathname==='/api/v1/devices') { deviceRequests++; data=stage==='discovering'?[]:[{...phone,isOnline:stage!=='reconnecting',...(stage==='reconnecting'?{connectionType:'unknown',connectionDetail:undefined}:{})},{...phone,id:'unknown-old',name:'10.0.0.8',macAddress:'02:00:00:00:00:08',connectionType:'unknown',connectionDetail:undefined,isOnline:false}]; }
    else if (url.pathname==='/api/v1/devices/audit-phone') data=phone;
    else if (url.pathname==='/api/v1/system/info') data={uptime:100,deviceModel:'Hiveton H5000M'};
    else if (url.pathname==='/api/v1/system/features') data={modules:{wifi:{installed:true}}};
    else if (/notifications$|network-interfaces$|blacklist$|ranking$/.test(url.pathname)) data=[];
    res.writeHead(200,{'content-type':'application/json'}).end(JSON.stringify({code:0,data}));
    return;
  }
  if (extname(url.pathname)==='.css') return res.writeHead(200,{'content-type':'text/css'}).end('');
  if (!extname(url.pathname)) return res.writeHead(200,{'content-type':'text/html;charset=utf-8'}).end(
    `<!doctype html><html><head><meta charset="utf-8"><style>[_echarts_instance_]{width:1100px!important;height:520px!important}</style></head><body><div id="app"></div><script type="module" src="/assets/${entry}"></script></body></html>`);
  const target=resolve(root,'.'+decodeURIComponent(url.pathname));
  if (!target.startsWith(root+sep)) return res.writeHead(403).end();
  try {
    const body=await readFile(target);
    res.writeHead(200,{'content-type':extname(target)==='.js'?'text/javascript':extname(target)==='.svg'?'image/svg+xml':'application/octet-stream'}).end(body);
  } catch {res.writeHead(404).end();}
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true,args:['--no-sandbox'],
  ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{})});
try {
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.setDefaultTimeout(12000);
  await page.addInitScript(()=>localStorage.setItem('h5000m-dashboard-refresh','5'));
  page.on('pageerror',error=>{errors.push(error.message); console.error('SPA error:',error.message);});
  page.on('console',message=>{if(message.type()==='error') console.error('Console:',message.text());});
  page.on('response',response=>{if(response.status()>=400) console.error('HTTP',response.status(),response.url());});
  await page.goto(`http://127.0.0.1:${server.address().port}/devices`);
  await page.waitForTimeout(2500);
  assert.ok(deviceRequests >= 2, 'device list is polled while backend has not discovered the station');
  assert.equal(await page.getByText(phone.name,{exact:true}).count(), 0, 'association alone does not fabricate a device');
  stage='online';
  const discoveredAt=Date.now();
  await page.getByText(phone.name,{exact:true}).first().waitFor().catch(async error=>{console.error('Rendered page:',await page.locator('body').innerText());throw error;});
  console.log(`Backend record appeared in UI after ${Date.now()-discoveredAt} ms (${deviceRequests} requests)`);
  assert.ok(Date.now()-discoveredAt<3500, 'UI renders promptly after backend discovery');
  await page.getByText('-45 dBm(极好)',{exact:true}).waitFor();
  assert.ok((await page.locator('body').innerText()).includes('↓2161 ↑2594 Mbps'));
  const controlRows = page.locator('.glass-effect [style*="height: 28px"]');
  assert.equal(await controlRows.count(), 2, 'each device reserves the same controls row');
  const rowMetrics = await controlRows.evaluateAll(rows => rows.map(row => ({height:Math.round(row.getBoundingClientRect().height)})));
  assert.deepEqual(rowMetrics.map(row=>row.height),[28,28],'the controls row has a stable height');
  stage='offline';
  const since=Date.now();
  await page.waitForFunction(()=>!document.body.innerText.includes('-45 dBm'),{},{timeout:6500});
  assert.ok(Date.now()-since<6500,'offline state must not wait for the stale 30-second backend status');
  assert.ok(!(await page.locator('body').innerText()).includes('↓2161 ↑2594 Mbps'),'offline card clears negotiated rate too');
  await page.getByText('离线',{exact:true}).first().waitFor({timeout:3000});
  await page.locator('.glass-effect').filter({has:page.getByText(phone.name,{exact:true})}).getByRole('button',{name:'清理离线记录',exact:true}).click();
  await page.getByRole('button',{name:'确认清理',exact:true}).click();
  await page.getByText(phone.name,{exact:true}).waitFor({state:'hidden',timeout:3500});
  assert.equal(Object.keys(markers).length,1,'clearing persists a router-side marker');
  await page.reload();
  await page.waitForTimeout(2300);
  assert.equal(await page.getByText(phone.name,{exact:true}).count(),0,'reload and stale native online flag cannot resurrect cleared record');
  stage='reconnecting';
  await page.getByText('-45 dBm(极好)',{exact:true}).waitFor({timeout:5000});
  assert.ok(!(await page.locator('body').innerText()).includes('↓2161 ↑2594 Mbps'),'reconnect does not display the previous session rate while backend is offline');
  await page.waitForTimeout(300);
  assert.equal(Object.keys(markers).length,0,'actual association restores device without native link detail');
  stage='online';
  await page.getByText('↓2161 ↑2594 Mbps',{exact:true}).waitFor({timeout:5000});
  await page.locator('a[href="/network"]').first().click();
  await page.getByRole('button',{name:'网络拓扑',exact:true}).click();
  await page.locator('[_echarts_instance_]').waitFor();
  const nodes=await page.evaluate(async charts=>{
    const module=await import('/assets/'+charts);
    return module.i(document.querySelector('[_echarts_instance_]')).getOption().series
      .find(series=>series.id==='topology-nodes').data;
  },charts);
  assert.ok(nodes.some(node=>node.originalData.id==='wifi5'),'actual 5G group appears in the rendered chart');
  assert.ok(!nodes.some(node=>node.originalData.id==='wifi-unknown'),'known interface no longer goes into unknown band');
  const unknown=nodes.find(node=>node.originalData.id==='unknown-connection');
  assert.equal(unknown.originalData.name,'离线设备 (1)','unknown offline history is labeled honestly');
  assert.equal(unknown.originalData.status,'offline','offline group must not display a green online indicator');
  const node=nodes.find(node=>node.originalData.mac===mac);
  assert.equal(node.originalData.deviceType,'mobile','hostname inference reaches topology');
  const svg=decodeURIComponent(Object.values(node.label.rich).find(value=>value.backgroundColor?.image).backgroundColor.image);
  assert.ok(svg.includes('width="12" height="22"'),'chart renders phone silhouette instead of desktop');
  assert.deepEqual(errors,[],'no SPA runtime exceptions');
  console.log(`PASS: packed SPA disconnect/reconnect, cleared speed/RSSI, actual 5G group and phone icon (${snapshots} wireless snapshots)`);
} finally {
  await browser.close();
  await new Promise(r=>server.close(r));
}
