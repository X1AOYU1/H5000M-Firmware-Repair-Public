import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const source = await readFile("scripts/higoos-device-vendor.js", "utf8");
const { findVendor } = await import("data:text/javascript;base64," + Buffer.from(source).toString("base64"));
const fixture = { "001122": "24-bit", "0011223": "28-bit", "001122334": "36-bit" };
assert.equal(findVendor("00:11:22:33:44:55", fixture), "36-bit");
assert.equal(findVendor("00:11:22:3f:44:55", fixture), "28-bit");
assert.equal(findVendor("00:11:22:ff:44:55", fixture), "24-bit");
assert.equal(findVendor("02:11:22:33:44:55", fixture), "");
assert.equal(findVendor("01:11:22:33:44:55", fixture), "");
assert.equal(findVendor("invalid", fixture), "");
const vendors = JSON.parse(await readFile("scripts/higoos-ieee-vendors.json", "utf8"));
assert.ok(Object.keys(vendors).length > 50000);
console.log("PASS: longest IEEE prefix and randomized MAC filtering");

let requested = '';
globalThis.fetch = async url => { if (url.includes('ieee-vendors')) { requested = url; return {ok:true, json: async () => ({'E00630':'HUAWEI TECHNOLOGIES CO.,LTD'})}; } return {ok:true,json:async()=>({token:'test',avatars:{}})}; };
const { createDeviceVendor, createDeviceAvatar, vendorBrand, brandFromDeviceName } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
const component = createDeviceVendor({defineComponent:x=>x, h:(tag, attrs, text)=>({tag, text}), ref:value=>({value})});
await new Promise(resolve=>setTimeout(resolve, 0));
const renderOffline = component.setup({mac:'E0:06:30:12:34:56', online:false});
assert.equal(requested, '/assets/higoos-ieee-vendors.json');
assert.match(renderOffline().text, /HUAWEI/);
assert.equal(component.setup({mac:'02:11:22:33:44:55', online:false})(), null);
console.log('PASS: offline device vendor renders with database; randomized MAC is not misidentified');
assert.equal(vendorBrand('EliteGroup Computer Systems Co., LTD'), 'ECS');
assert.equal(vendorBrand('Unknown manufacturer'), '');
assert.equal(brandFromDeviceName('iPhone'), 'Apple');
assert.equal(brandFromDeviceName('Yu-de-S24-Ultra'), 'Samsung');
assert.equal(brandFromDeviceName('unknown device'), '');
const avatar = createDeviceAvatar({defineComponent:x=>x, h:(tag, attrs, text)=>({tag, attrs, text}), ref:value=>({value})});
await new Promise(resolve=>setTimeout(resolve, 0));
assert.equal(avatar.setup({mac:'E0:06:30:12:34:56', fallback:'device.svg'})().text[0].text[0].text[0].attrs.src, '/assets/device-logos/huawei.svg');
const fitted = avatar.setup({mac:'E0:06:30:12:34:56', fallback:'device.svg'})();
assert.equal(fitted.text[0].attrs.style.width, '54px');
assert.equal(fitted.text[0].text[0].attrs.style.width, '48px');
assert.equal(fitted.text[0].text[0].text[0].attrs.style.objectFit, 'contain');
assert.equal(avatar.setup({mac:'C6:AC:9F:F6:94:22', fallback:'device.svg'})().text[0].text[0].attrs.src, 'device.svg');
console.log('PASS: recognized brands get avatars, randomized addresses retain device icon');

let saved = {};
globalThis.fetch = async (url, options = {}) => {
  if (options.method === 'POST') {
    const form = options.body;
    saved[form.get('mac')] = form.get('avatar');
    return {ok:true, json:async()=>({avatar:form.get('avatar')})};
  }
  return {ok:true,json:async()=>({token:'test',avatars:{...saved}})};
};
const interactive = createDeviceAvatar({defineComponent:x=>x, h:(tag, attrs, text)=>({tag, attrs, text}), ref:value=>({value})});
await new Promise(resolve=>setTimeout(resolve, 0));
const render = interactive.setup({mac:'C6:AC:9F:F6:94:22', fallback:'device.svg'});
render().text[0].attrs.onClick();
await render().text[1].text[1].text[1].attrs.onClick();
assert.equal(saved.c6ac9ff69422, 'Samsung');
assert.equal(render().text[0].text[0].text[0].attrs.src, '/assets/device-logos/samsung.svg');
render().text[0].attrs.onClick();
await render().text[1].text[1].text[0].attrs.onClick();
assert.equal(render().text[0].text[0].attrs.src, 'device.svg');
console.log('PASS: select, save, display and reset a device avatar');

render().text[0].attrs.onClick();
await render().text[1].text[1].text[12].attrs.onClick();
assert.equal(saved.c6ac9ff69422, 'Computer');
assert.equal(render().text[0].text[0].text[0].attrs.src, '/assets/device-logos/computer.svg');
assert.match(await readFile('scripts/device-logos/huawei.svg', 'utf8'), /fill="#E60012"/);
assert.match(await readFile('scripts/device-logos/huawei.svg', 'utf8'), />HUAWEI<\/text>/);
const appleLogo = await readFile('scripts/device-logos/apple.svg', 'utf8');
assert.match(appleLogo, /viewBox="0 0 64 64"/);
assert.match(appleLogo, /<path[^>]+fill="#111827"/);
assert.doesNotMatch(appleLogo, />Apple<\/text>/);
for (const icon of ['computer','tv','phone','tablet','samsung']) {
  const svg = await readFile(`scripts/device-logos/${icon}.svg`, 'utf8');
  assert.match(svg, /viewBox="0 0 64 64"/);
  assert.match(svg, /#[0-9a-fA-F]{6}/);
}
console.log('PASS: computer selection displays an icon and Huawei logo is colored');
