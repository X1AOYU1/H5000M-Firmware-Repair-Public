import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('./higoos-uplink-security.js', import.meta.url), 'utf8');
const { uplinkSecurity, uplinkSecurityLabel } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
for (const [scan, expected] of [
  ['WPA2 PSK (CCMP)', 'psk2'], ['psk2', 'psk2'], ['WPA2/WPA3', 'sae-mixed'],
  ['SAE', 'sae'], ['WPA/WPA2', 'psk-mixed'], ['open', 'none'], ['OWE', 'owe'],
  ['WEP', 'wep-open'], ['psk2+ccmp', 'psk2'], ['WPA2 PSK (CCMP)', 'psk2'],
  ['', ''], [undefined, ''], ['vendor-specific', '']
]) assert.equal(uplinkSecurity(scan), expected, String(scan));
assert.equal(uplinkSecurityLabel('psk2'), 'WPA2');
assert.equal(uplinkSecurityLabel('vendor-specific'), '无法识别，请重新扫描');
console.log('PASS: scan encryption conversion, WPA2 recognition and unknown handling');
