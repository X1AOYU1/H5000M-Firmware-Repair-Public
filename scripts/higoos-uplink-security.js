// Translate scan results to OpenWrt station encryption values. Unknown scans
// use WPA2 as a selectable default; users can correct it before applying.
export function uplinkSecurity(value) {
  const s = String(value ?? '').trim().toLowerCase();
  if (/^(none|open|off|disabled?|owe)$/.test(s)) return s === 'owe' ? 'owe' : 'none';
  if (/wep/.test(s)) return 'wep-open';
  if (/sae|wpa3/.test(s) && /psk|wpa2|mixed/.test(s)) return 'sae-mixed';
  if (/sae|wpa3/.test(s)) return 'sae';
  if (/psk-mixed|psk\+psk2|wpa.?\/wpa2/.test(s)) return 'psk-mixed';
  if (/wpa2|psk2/.test(s)) return 'psk2';
  if (/^psk$|^wpa$/.test(s)) return 'psk';
  return 'psk2';
}
