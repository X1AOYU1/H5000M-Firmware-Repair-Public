// Small vector silhouettes remain sharp at the topology's 14px label size.
export function topologyDeviceIcon(node, color) {
  const paths = {
    computer: '<rect x="2" y="3" width="20" height="13" rx="2"/><path d="M8 21h8m-4-5v5"/>',
    mobile: '<rect x="6" y="1" width="12" height="22" rx="3"/><path d="M10 4h4m-3 16h2"/>',
    tablet: '<rect x="3" y="1" width="18" height="22" rx="2"/><path d="M11 20h2"/>',
    tv: '<rect x="1" y="4" width="22" height="15" rx="2"/><path d="M8 23l4-4 4 4M8 1l4 3 4-3"/>',
    iot: '<path d="M8 17h8M9 20h6m-3-18a7 7 0 0 0-4 13h8a7 7 0 0 0-4-13Z"/>',
    game: '<path d="M7 7h10c4 0 7 14 3 14l-5-4H9l-5 4C0 21 3 7 7 7Zm0 4v4m-2-2h4m7-2h.01m2 3h.01"/>',
    other: '<rect x="4" y="4" width="16" height="16" rx="4"/><path d="M9 9h6v6H9z"/>',
  };
  const body = paths[node.deviceType] || paths.other;
  const safeColor = /^#[0-9a-f]{3,8}$/i.test(color) ? color : '#64748b';
  return 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="${safeColor}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${body}</svg>`);
}
