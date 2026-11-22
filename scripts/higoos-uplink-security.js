// Translate scan results to OpenWrt station encryption values. Unknown scans
// stay unknown so the UI never applies credentials with a guessed cipher.
export function uplinkSecurity(value) {
  const s = String(value ?? '').trim().toLowerCase();
  if (!s) return '';
  if (/^(none|open|off|disabled?|no encryption)$/.test(s)) return 'none';
  if (/^owe$/.test(s)) return 'owe';
  if (/wep/.test(s)) return 'wep-open';
  if (/sae|wpa3/.test(s) && /psk|wpa2|mixed/.test(s)) return 'sae-mixed';
  if (/sae|wpa3/.test(s)) return 'sae';
  if (/psk-mixed|psk\+psk2|wpa.?\/wpa2/.test(s)) return 'psk-mixed';
  if (/wpa2|psk2/.test(s)) return 'psk2';
  if (/^psk$|^wpa$/.test(s)) return 'psk';
  return '';
}

export function uplinkSecurityLabel(value) {
  return ({
    'psk2': 'WPA2',
    'sae-mixed': 'WPA2/WPA3',
    'sae': 'WPA3',
    'psk-mixed': 'WPA/WPA2',
    'psk': 'WPA',
    'wep-open': 'WEP',
    'owe': 'OWE',
    'none': '无加密',
  })[uplinkSecurity(value)] || '无法识别，请重新扫描';
}
