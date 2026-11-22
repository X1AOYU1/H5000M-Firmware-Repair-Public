import assert from 'node:assert/strict';
import {createServer} from 'node:http';
import {createRequire} from 'node:module';
import {readFile} from 'node:fs/promises';
import {resolve,join,extname} from 'node:path';

const root = resolve(process.argv[2]);
const require = createRequire(join(process.env.PLAYWRIGHT_ROOT,'__mobile_audit__.cjs'));
const {chromium} = require('playwright');
let authenticated = false, rebootRequests = 0;
const server = createServer(async (req,res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  const json = (status,data) => res.writeHead(status,{'content-type':'application/json'}).end(JSON.stringify(data));
  if (url.pathname.startsWith('/api/v1/')) {
    if (url.pathname === '/api/v1/auth/me') return json(authenticated ? 200 : 401,{code:authenticated?0:401,data:authenticated?{username:'root'}:null,message:'login required'});
    if (url.pathname === '/api/v1/auth/login' && req.method === 'POST') { authenticated=true; return json(200,{code:0,data:{username:'root'}}); }
    if (url.pathname === '/api/v1/auth/logout') { authenticated=false; return json(200,{code:0,data:{}}); }
    if (!authenticated) return json(401,{code:401,message:'login required'});
    if (url.pathname === '/api/v1/system/info') return json(200,{code:0,data:{deviceModel:'Hiveton H5000M'}});
    if (url.pathname === '/api/v1/system/resources') return json(200,{code:0,data:{cpu:{usage:.2},memory:{used:512000000,total:1000000000,usage:.512},loadAverage:[.12,.18,.2]}});
    if (url.pathname === '/api/v1/system/realtime-speed') return json(200,{code:0,data:{download:14.25,upload:2.5}});
    if (url.pathname === '/api/v1/wifi/settings') return json(200,{code:0,data:[{band:'2.4g',ssid:'Hiveton-2.4G',enabled:true,clients:2},{band:'5g',ssid:'Hiveton-5G',enabled:true,clients:1}]});
    if (url.pathname === '/api/v1/devices') return json(200,{code:0,data:[{name:'Yu-de-S24-Ultra',macAddress:'0A:F1:B0:C0:40:19',ipAddress:'10.0.0.5',connectionType:'wifi',connectionDetail:{kind:'wifi-2g'},isOnline:true},{name:'WIN-DESKTOP',macAddress:'94:C6:91:FA:E7:DD',ipAddress:'10.0.0.2',connectionType:'wired',deviceType:'computer',isOnline:true}]});
    if (url.pathname === '/api/v1/system/reboot' && req.method === 'POST') { rebootRequests++; return json(200,{code:0,data:{accepted:true}}); }
    return json(404,{code:404,message:'not found'});
  }
  const name = url.pathname === '/mobile/' ? 'index.html' : url.pathname.replace(/^\/mobile\//,'');
  const target = resolve(root,name);
  if (!target.startsWith(root)) return res.writeHead(403).end();
  try {
    const body = await readFile(target);
    const type = ({'.html':'text/html;charset=utf-8','.css':'text/css','.js':'text/javascript','.svg':'image/svg+xml','.webmanifest':'application/manifest+json'})[extname(target)] || 'application/octet-stream';
    res.writeHead(200,{'content-type':type,'cache-control':'no-store'}).end(body);
  } catch { res.writeHead(404).end(); }
});
await new Promise(resolveListen => server.listen(0,'127.0.0.1',resolveListen));
const browser = await chromium.launch({headless:true,args:['--no-sandbox'],...(process.env.PLAYWRIGHT_EXECUTABLE_PATH?{executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH}:{})});
try {
  const page = await browser.newPage({viewport:{width:390,height:844},deviceScaleFactor:1});
  page.setDefaultTimeout(8000);
  const errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  page.on('response',response=>{if(response.status()>=400)console.error(`HTTP ${response.status()} ${response.url()}`);});
  await page.goto(`http://127.0.0.1:${server.address().port}/mobile/`);
  await page.getByRole('heading',{name:'登录路由器'}).waitFor();
  await page.getByLabel('密码').fill('test-password');
  await page.getByRole('button',{name:'登录'}).click();
  await page.getByRole('heading',{name:'Hiveton H5000M'}).waitFor().catch(async error=>{console.error('Mobile page after login:',await page.locator('body').innerText(),'runtime errors:',errors);throw error;});
  await page.getByText('Yu-de-S24-Ultra',{exact:true}).waitFor();
  await page.getByText('Hiveton-2.4G',{exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('#download-value')?.textContent!=='--');
  assert.equal(await page.locator('#download-value').textContent(),'14.3');
  const mobileLayout=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,card:document.querySelector('.app-shell').getBoundingClientRect().width}));
  assert.ok(mobileLayout.scroll<=mobileLayout.width,`mobile page overflows horizontally: ${JSON.stringify(mobileLayout)}`);
  await page.screenshot({path:join(process.env.AUDIT_DIR||root,'higoos-mobile-390.png'),fullPage:true});
  page.once('dialog',dialog=>dialog.accept());
  await page.getByRole('button',{name:'重启路由器'}).click();
  await page.getByText('重启请求已发送，请等待路由器重新上线。',{exact:true}).waitFor();
  assert.equal(rebootRequests,1,'reboot action is sent only after confirmation');
  const desktop=await browser.newPage({viewport:{width:1280,height:900}});
  await desktop.goto(`http://127.0.0.1:${server.address().port}/mobile/`);
  await desktop.getByRole('heading',{name:'Hiveton H5000M'}).waitFor();
  const columns=await desktop.locator('.metric').first().evaluate(el=>getComputedStyle(el.parentElement).gridTemplateColumns.split(' ').length);
  assert.equal(columns,4,'desktop status metrics use four columns');
  assert.deepEqual(errors,[],'mobile PWA has no runtime errors');
  console.log(`PASS: PWA login, live status, responsive layouts and confirmed reboot; mobile shell ${mobileLayout.card}px`);
} finally {
  await browser.close();
  await new Promise(resolveClose=>server.close(resolveClose));
}
