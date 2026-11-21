// Preserve types identified by HigoOS. Infer only from recognizable hostnames.
export function inferDeviceType(device) {
  if (device.deviceType && device.deviceType !== "other") return device;
  const name = (device.name || "").trim().toLowerCase();
  let type = "other";
  if (/^(win(?:dows)?[-_]|desktop[-_]|laptop[-_]|macbook(?:[-_ ]|$)|imac(?:[-_ ]|$))/.test(name)) type = "computer";
  else if (/(?:^|[-_ ])(?:iphone|android|pixel|galaxy|samsung)(?:[-_ ]|$)/.test(name) || /(?:^|[-_ ])s\d{1,2}[-_ ]?(?:ultra|plus|fe)?$/.test(name)) type = "mobile";
  else if (/(?:^|[-_ ])(?:ipad|tablet)(?:[-_ ]|$)/.test(name)) type = "tablet";
  return type === "other" ? device : { ...device, deviceType: type };
}
