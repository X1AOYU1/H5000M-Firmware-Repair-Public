import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {readFile, readdir} from 'node:fs/promises';
import {join, resolve, extname, sep} from 'node:path';

// Run the actual packed SPA against changing synthetic responses, including a
// deliberately slow ranking endpoint. No live router credentials are needed.
const root = resolve(process.argv[2]);
const require = createRequire(join(process.env.PLAYWRIGHT_ROOT, '__audit__.cjs'));
const {chromium} = require('playwright');
const resources = '/api/v1/system/resources', devices = '/api/v1/devices';
const requests = [], errors = [];
let resourceCycle = 0, deviceCycle = 0, rankingActive = 0, rankingMax = 0;
let speedCycle=0, speedActive=0, speedMax=0;
const speed='/api/v1/system/realtime-speed';
const assets = await readdir(join(root, 'assets'));
const entry = assets.find(x => x.startsWith('index-DhOCiPK2'));
const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost');
  if (url.pathname.startsWith('/api/v1/')) {
    // The persistent shell separately requests resources without a period.
    // Count only the network-overview query whose interval this control owns.
    const overviewResource = url.pathname === resources && url.searchParams.get('points') === '180';
    if (url.pathname !== resources || overviewResource)
      requests.push({path:url.pathname, at:Date.now()});
    let data = {};
    if (url.pathname === speed) {
      speedMax=Math.max(speedMax,++speedActive);
      await new Promise(r=>setTimeout(r,80));
      data={upload:++speedCycle+200,download:speedCycle+300};speedActive--;
    }
    else if (url.pathname === '/api/v1/auth/me') data = {username:'audit',role:'admin',permissions:['*']};
    else if (url.pathname === resources) {
      if (overviewResource) resourceCycle++;
      data = {download:resourceCycle + 10,upload:resourceCycle,activeConnections:resourceCycle + 100,
        history:[{timestamp:Date.now(),download:resourceCycle + 10,upload:resourceCycle}],
        cpuHistory:[],memoryHistory:[],temperatureHistory:[]};
    } else if (url.pathname === devices) {
      deviceCycle++;
      data = [{id:'audit-pc',name:'设备刷新-'+deviceCycle,macAddress:'02:00:00:00:00:01',
        ipAddress:'192.0.2.2',isOnline:true,deviceType:'computer',osType:'windows',
        connectionType:'wired',connectedTime:deviceCycle*2,downloadSpeed:deviceCycle,uploadSpeed:1}];
    } else if (url.pathname === '/api/v1/devices/traffic/ranking') {
      rankingMax = Math.max(rankingMax, ++rankingActive);
      await new Promise(r=>setTimeout(r,6500));
      rankingActive--; data = [];
    } else if (url.pathname === '/api/v1/system/info') data = {uptime:resourceCycle*2};
    else if (url.pathname === '/api/v1/system/features') data = {modules:{wifi:{installed:false},oaf:{installed:false}}};
    else if (url.pathname === '/api/v1/devices/stats/online-daily') data = {delta:0,comparisonAvailable:false};
    else if (/notifications$|network-interfaces$|wifi\/|blacklist$/.test(url.pathname)) data = [];
    res.writeHead(200, {'content-type':'application/json'}).end(JSON.stringify({code:0,data}));
    return;
  }
  if (extname(url.pathname) === '.css') return res.writeHead(200,{'content-type':'text/css'}).end('');
  if (!extname(url.pathname)) return res.writeHead(200,{'content-type':'text/html; charset=utf-8'}).end(
    `<!doctype html><html><head><meta charset="utf-8"></head><body><div id="app"></div><script type="module" src="/assets/${entry}"></script></body></html>`);
  const target = resolve(root, '.' + decodeURIComponent(url.pathname));
  if (!target.startsWith(root + sep)) return res.writeHead(403).end();
  try {
    const content = await readFile(target);
    res.writeHead(200,{'content-type':extname(target)==='.js'?'text/javascript':extname(target)==='.svg'?'image/svg+xml':'application/octet-stream'}).end(content);
  } catch { res.writeHead(404).end(); }
});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser = await chromium.launch({headless:true,args:['--no-sandbox'],
  ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{})});
try {
  const page = await browser.newPage();
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/dashboard`);
  const select = page.getByLabel('仪表板刷新间隔');
  await select.waitFor();
  for (const seconds of [1,2,3,5]) {
    await select.selectOption(String(seconds));
    await page.waitForTimeout(350);
    const since = Date.now(), before = resourceCycle;
    await page.waitForTimeout(seconds*2000+450);
    for (const path of [resources,devices,speed]) {
      const ticks = requests.filter(r=>r.path===path&&r.at>=since);
      assert.equal(ticks.length,2, `${seconds}s: exactly two ${path} updates, got ${JSON.stringify(ticks)}`);
      const gap = ticks[1].at-ticks[0].at;
      assert.ok(Math.abs(gap-seconds*1000)<450, `${path}: incorrect ${seconds}s interval: ${gap}`);
    }
    assert.equal(resourceCycle,before+2);
    const cards=await page.locator('.metric-card').allInnerTexts();
    assert.ok(cards.some(text=>text.includes(String(speedCycle+300))), 'download card uses live speed instead of resource history');
    assert.ok(cards.some(text=>text.includes(String(speedCycle+200))), 'upload card uses the same live sample');
    assert.ok((await page.locator('body').innerText()).includes('设备刷新-'+deviceCycle), 'new device response reaches the rendered UI');
    assert.ok((await page.locator('body').innerText()).includes(String(resourceCycle+100)), 'new connection count reaches the rendered UI');
    console.log(`PASS: ${seconds}s selector controls resource and device HTTP requests and rendered values`);
  }
  assert.equal(rankingMax,1,'slow ranking requests must never overlap');
  assert.equal(speedMax,1,'sidebar and dashboard share one sampler');
  await page.reload();
  await select.waitFor();
  assert.equal(await select.inputValue(),'5','interval survives reload');
  await select.selectOption('2');
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'));});
  await page.waitForTimeout(350);
  const hiddenCount = resourceCycle;
  await page.waitForTimeout(4500);
  assert.equal(resourceCycle,hiddenCount,'hidden dashboard stops polling');
  await page.evaluate(()=>{Object.defineProperty(document,'hidden',{configurable:true,get:()=>false});document.dispatchEvent(new Event('visibilitychange'));});
  await page.waitForTimeout(350);
  assert.equal(resourceCycle,hiddenCount+1,'visible dashboard immediately catches up');
  await page.locator('a[href="/devices"]').first().click();
  await page.waitForURL('**/devices');
  await page.waitForTimeout(350);
  const unmountedCount = resourceCycle;
  await page.waitForTimeout(4500);
  assert.equal(resourceCycle,unmountedCount,'leaving dashboard removes its timer');
  assert.deepEqual(errors,[],'actual SPA has no uncaught errors');
  console.log('PASS: slow query isolation, no overlapping requests, persistence, visibility resume, and route cleanup');
} finally {
  await browser.close();
  server.closeAllConnections();
  await new Promise(r=>server.close(r));
}
