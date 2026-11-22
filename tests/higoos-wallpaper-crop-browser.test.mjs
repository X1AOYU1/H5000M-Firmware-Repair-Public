import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const require = createRequire(join(process.env.PLAYWRIGHT_ROOT, 'package.json'));
const { chromium } = require('playwright');
const js = await readFile('scripts/higoos-wallpaper-crop.js');
const sourceJs = await readFile('scripts/higoos-wallpaper-source.js');
const server = createServer((req, res) => {
  if (req.url === '/crop.js') { res.writeHead(200, {'Content-Type': 'text/javascript'}); res.end(js); return; }
  if (req.url === '/source.js') { res.writeHead(200, {'Content-Type': 'text/javascript'}); res.end(sourceJs); return; }
  res.writeHead(200, {'Content-Type':'text/html', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"});
  res.end('<html><head></head><body><select id="source"><option>本地上传背景</option><option>默认（未配置）</option><option>Bing</option><option>GHSer</option><option>Unsplash</option><option>Wallhaven</option></select><table><tr><td>higoos-cropped-wallpaper-1795324169501.jpg</td></tr><tr><td>higoos-cropped-wallpaper-older.jpg</td></tr></table><script type="module" src="/source.js"></script></body></html>');
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({headless:true});
try {
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.evaluate(async () => { const m = await import('/crop.js'); m.mountHigoosWallpaperCrop({upload: async () => {}}); });
  assert.equal(await page.getByRole('button', {name:/预览壁纸：higoos-cropped-wallpaper/}).count(), 2,
    'each uploaded wallpaper row has a preview action');
  await page.locator('tr').filter({hasText:'older.jpg'}).getByRole('button', {name:'设为登录壁纸'}).click();
  assert.equal(await page.evaluate(() => localStorage.getItem('higoos_argon_login_wallpaper')),
    '/luci-static/argon/background/higoos-cropped-wallpaper-older.jpg', 'older uploads can be explicitly selected');
  assert.equal(await page.locator('tr').filter({hasText:'older.jpg'}).getByRole('button', {name:'当前登录壁纸'}).getAttribute('aria-pressed'), 'true');
  await page.locator('#source').selectOption({label:'GHSer'});
  assert.equal(await page.evaluate(() => localStorage.getItem('higoos_argon_login_wallpaper')), null,
    'selecting an external wallpaper provider clears the uploaded wallpaper override');
  await page.locator('tr').filter({hasText:'older.jpg'}).getByRole('button', {name:'设为登录壁纸'}).click();
  assert.equal(await page.getByRole('button', {name:'裁切登录壁纸'}).count(), 0,
    'uploaded wallpaper rows no longer get a second crop action');
  await page.getByRole('button', {name:/预览壁纸：higoos-cropped-wallpaper-1795324169501/}).click();
  assert.equal(await page.getByRole('dialog').count(), 1, 'the uploaded wallpaper opens in a preview dialog');
  assert.match(await page.getByRole('dialog').locator('img').getAttribute('src'), /higoos-cropped-wallpaper-1795324169501\.jpg/);
  await page.getByRole('button', {name:'关闭', exact:true}).click();
  assert.equal(await page.getByRole('dialog').count(), 0, 'the preview dialog closes');
  const image = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+X2ioAAAAASUVORK5CYII=';
  await page.evaluate(b64 => {
    const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    window.cropPromise = window.higoosCropBeforeUpload(new File([bytes], 'test.png', {type:'image/png'}));
  }, image);
  await page.waitForFunction(() => { const i=document.querySelector('.higoos-crop-preview img'); return i && i.naturalWidth > 0; });
  assert.match(await page.locator('.higoos-crop-preview img').getAttribute('src'), /^data:/);
  await page.locator('[data-action=save]').click();
  const output = await page.evaluate(async () => { const f=await window.cropPromise; return {name:f.name,type:f.type,size:f.size}; });
  assert.match(output.name, /^higoos-cropped-wallpaper-.*\.jpg$/); assert.equal(output.type, 'image/jpeg'); assert.ok(output.size > 0);
  const gif = await page.evaluate(async () => { const f=new File(['gif'], 'animation.gif', {type:'image/gif'}); return await window.higoosCropBeforeUpload(f) === f; });
  assert.equal(gif, true);
  console.log('PASS: crop preview and export work under HigoOS CSP; GIF bypasses crop');
} finally { await browser.close(); server.close(); }
