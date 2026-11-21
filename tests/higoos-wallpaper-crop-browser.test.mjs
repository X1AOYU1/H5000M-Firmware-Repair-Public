import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import assert from 'node:assert/strict';

const require = createRequire(join(process.env.PLAYWRIGHT_ROOT, 'package.json'));
const { chromium } = require('playwright');
const js = await readFile('scripts/higoos-wallpaper-crop.js');
const server = createServer((req, res) => {
  if (req.url === '/crop.js') { res.writeHead(200, {'Content-Type': 'text/javascript'}); res.end(js); return; }
  res.writeHead(200, {'Content-Type':'text/html', 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:"});
  res.end('<html><head></head><body><script type="module" src="/crop.js"></script></body></html>');
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const browser = await chromium.launch({headless:true});
try {
  const page = await browser.newPage();
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.evaluate(async () => { const m = await import('/crop.js'); m.mountHigoosWallpaperCrop({upload: async () => {}}); });
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
