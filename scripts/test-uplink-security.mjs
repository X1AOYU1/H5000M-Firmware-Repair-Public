import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('./higoos-uplink-security.js', import.meta.url), 'utf8');
const { uplinkSecurity } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
for (const [scan, expected] of [
  ['WPA2 PSK (CCMP)', 'psk2'], ['psk2', 'psk2'], ['WPA2/WPA3', 'sae-mixed'],
  ['SAE', 'sae'], ['WPA/WPA2', 'psk-mixed'], ['open', 'none'], ['OWE', 'owe'],
  ['WEP', 'wep-open'], ['', 'psk2'], [undefined, 'psk2']
]) assert.equal(uplinkSecurity(scan), expected, String(scan));
console.log('PASS: scan encryption conversion for secured, open and unknown networks');
