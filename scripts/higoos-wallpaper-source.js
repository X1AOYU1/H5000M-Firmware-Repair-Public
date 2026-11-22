const wallpaperKey = "higoos_argon_login_wallpaper";
const sourceKey = "higoos_argon_login_wallpaper_source";
const providers = /^(?:bing|ghser|unsplash|wallhaven)$/i;

export function clearUploadedWallpaperOnSourceChange(event) {
  const select = event.target;
  if (!(select instanceof HTMLSelectElement)) return;
  const options = Array.from(select.options, option => option.textContent.trim());
  if (options.filter(value => providers.test(value)).length < 2) return;
  const selected = select.selectedOptions[0]?.textContent.trim() || "";
  if (!providers.test(selected) && !/默认/.test(selected)) return;
  try {
    localStorage.removeItem(wallpaperKey);
    localStorage.removeItem(sourceKey);
  } catch {}
  document.dispatchEvent(new Event("higoos-wallpaper-source-changed"));
}

export function mountWallpaperSourceListener() {
  if (window.__higoosWallpaperSourceListener) return;
  window.__higoosWallpaperSourceListener = true;
  document.addEventListener("change", clearUploadedWallpaperOnSourceChange);
}

mountWallpaperSourceListener();
