export function mountHigoosWallpaperCrop({upload}) {
  if (window.__higoosWallpaperCropMounted) return;
  window.__higoosWallpaperCropMounted = true;
  const prefix = "/luci-static/argon/background/";
  const style = document.createElement("style");
  style.textContent = `.higoos-crop-shade,.higoos-wallpaper-preview-shade{position:fixed;inset:0;z-index:100000;display:grid;place-items:center;background:#020617bb;padding:1rem}.higoos-crop-dialog,.higoos-wallpaper-preview-dialog{width:min(900px,96vw);max-height:94vh;overflow:auto;border-radius:.8rem;background:#fff;padding:1rem;color:#0f172a;box-shadow:0 20px 60px #0008}.higoos-crop-preview{position:relative;width:100%;aspect-ratio:16/9;overflow:hidden;background:#111827;touch-action:none;cursor:move}.higoos-crop-preview img{position:absolute;max-width:none;user-select:none;pointer-events:none}.higoos-crop-controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.8rem;margin:1rem 0}.higoos-crop-controls label{display:grid;gap:.25rem;font-size:.9rem}.higoos-crop-actions,.higoos-wallpaper-preview-header{display:flex;justify-content:space-between;align-items:center;gap:.6rem}.higoos-crop-actions button,.higoos-wallpaper-preview-header button{padding:.55rem .9rem;border-radius:.4rem;border:1px solid #64748b;cursor:pointer}.higoos-crop-status{min-height:1.4em;color:#b91c1c}.higoos-wallpaper-preview-image{display:block;width:100%;max-height:75vh;object-fit:contain;margin-top:.75rem;background:#e2e8f0}.higoos-wallpaper-preview-button{display:inline-flex;align-items:center;gap:.45rem;margin-left:.5rem;padding:.15rem .4rem;border:1px solid #94a3b8;border-radius:.35rem;background:#fff;color:#1e293b;cursor:pointer;font-size:.75rem}.higoos-wallpaper-preview-button img{width:2.5rem;height:1.5rem;object-fit:cover;border-radius:.2rem}@media(max-width:600px){.higoos-crop-controls{grid-template-columns:1fr}}`;

  const showPreview = name => {
    const shade = document.createElement("div");
    shade.className = "higoos-wallpaper-preview-shade";
    const dialog = document.createElement("section");
    dialog.className = "higoos-wallpaper-preview-dialog";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    const header = document.createElement("div");
    header.className = "higoos-wallpaper-preview-header";
    const title = document.createElement("h2");
    title.textContent = name;
    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.textContent = "关闭";
    const image = document.createElement("img");
    image.className = "higoos-wallpaper-preview-image";
    image.alt = name;
    image.src = prefix + encodeURIComponent(name);
    const close = () => { shade.remove(); document.removeEventListener("keydown", onKeyDown); };
    const onKeyDown = event => { if (event.key === "Escape") close(); };
    closeButton.addEventListener("click", close);
    shade.addEventListener("click", event => { if (event.target === shade) close(); });
    document.addEventListener("keydown", onKeyDown);
    header.append(title, closeButton);
    dialog.append(header, image);
    shade.append(dialog);
    document.body.append(shade);
    closeButton.focus();
  };
  style.textContent += `.higoos-wallpaper-select-button{margin-left:.4rem;padding:.2rem .45rem;border:1px solid #94a3b8;border-radius:.35rem;background:#fff;color:#1e293b;cursor:pointer;font-size:.75rem}.higoos-wallpaper-select-button[aria-pressed="true"]{border-color:#15803d;color:#166534;background:#f0fdf4}`;
  document.head.append(style);

  const showEditor = (name, file = null) => new Promise(resolve => {
    const shade = document.createElement("div");
    shade.className = "higoos-crop-shade";
    const dialog = document.createElement("section");
    dialog.className = "higoos-crop-dialog";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.innerHTML = `<h2 style="margin:0 0 .75rem">调整登录壁纸取景</h2><p style="margin:.25rem 0 .75rem">拖动图片调整角度，或调节缩放、水平和垂直位置。</p><div class="higoos-crop-preview"><img alt="壁纸裁切预览"></div><div class="higoos-crop-controls"><label>缩放 <input data-control="zoom" type="range" min="1" max="3" step=".01" value="1"></label><label>水平位置 <input data-control="x" type="range" min="0" max="100" value="50"></label><label>垂直位置 <input data-control="y" type="range" min="0" max="100" value="50"></label></div><div class="higoos-crop-status" aria-live="polite"></div><div class="higoos-crop-actions"><button type="button" data-action="cancel">取消</button><button type="button" data-action="save">保存裁切并应用</button></div>`;
    shade.append(dialog);
    document.body.append(shade);
    const preview = dialog.querySelector(".higoos-crop-preview");
    const image = dialog.querySelector("img");
    const zoom = dialog.querySelector('[data-control="zoom"]');
    const xPosition = dialog.querySelector('[data-control="x"]');
    const yPosition = dialog.querySelector('[data-control="y"]');
    const status = dialog.querySelector(".higoos-crop-status");
    let loaded = false;
    let dx = 0;
    let dy = 0;
    let pointer = null;
    const layout = () => {
      if (!loaded) return;
      const box = preview.getBoundingClientRect();
      const fit = Math.max(box.width / image.naturalWidth, box.height / image.naturalHeight);
      const scale = fit * Number(zoom.value);
      const width = image.naturalWidth * scale;
      const height = image.naturalHeight * scale;
      const maxX = Math.max(0, width - box.width);
      const maxY = Math.max(0, height - box.height);
      dx = Math.max(0, Math.min(maxX, maxX * Number(xPosition.value) / 100));
      dy = Math.max(0, Math.min(maxY, maxY * Number(yPosition.value) / 100));
      image.style.width = `${width}px`;
      image.style.height = `${height}px`;
      image.style.left = `${-dx}px`;
      image.style.top = `${-dy}px`;
    };
    image.onload = () => { loaded = true; layout(); };
    image.onerror = () => { status.textContent = "图片无法加载，请选择有效的 JPEG、PNG 或 WebP 图片。"; };
    // HigoOS permits data: images but blocks blob: images in its CSP.
    const reader = file ? new FileReader() : null;
    if (reader) {
      reader.onload = () => { if (typeof reader.result === "string") image.src = reader.result; };
      reader.onerror = () => { status.textContent = "无法读取图片，请重新选择文件。"; };
      reader.readAsDataURL(file);
    } else {
      image.src = prefix + encodeURIComponent(name) + "?v=" + Date.now();
    }
    [zoom, xPosition, yPosition].forEach(input => input.addEventListener("input", layout));
    preview.addEventListener("pointerdown", event => { pointer = {id:event.pointerId,x:event.clientX,y:event.clientY,dx,dy}; preview.setPointerCapture(event.pointerId); });
    preview.addEventListener("pointermove", event => {
      if (!pointer || pointer.id !== event.pointerId) return;
      const box = preview.getBoundingClientRect();
      const fit = Math.max(box.width / image.naturalWidth, box.height / image.naturalHeight) * Number(zoom.value);
      xPosition.value = String(Math.max(0, Math.min(100, (pointer.dx - (event.clientX-pointer.x)) / Math.max(1,image.naturalWidth*fit-box.width) * 100)));
      yPosition.value = String(Math.max(0, Math.min(100, (pointer.dy - (event.clientY-pointer.y)) / Math.max(1,image.naturalHeight*fit-box.height) * 100)));
      layout();
    });
    preview.addEventListener("pointerup", () => { pointer = null; });
    preview.addEventListener("pointercancel", () => { pointer = null; });
    let finished = false;
    const close = (result = null) => { if (finished) return; finished = true; if (reader && reader.readyState === FileReader.LOADING) reader.abort(); shade.remove(); resolve(result); };
    dialog.querySelector('[data-action="cancel"]').addEventListener("click", () => close());
    shade.addEventListener("click", event => { if (event.target === shade) close(); });
    dialog.querySelector('[data-action="save"]').addEventListener("click", async event => {
      const button = event.currentTarget;
      if (!loaded || !image.naturalWidth || !image.naturalHeight) { status.textContent = "图片尚未加载完成。"; return; }
      button.disabled = true;
      status.textContent = "正在生成并保存裁切图片…";
      try {
        const box = preview.getBoundingClientRect();
        const fit = Math.max(box.width / image.naturalWidth, box.height / image.naturalHeight) * Number(zoom.value);
        const canvas = document.createElement("canvas");
        canvas.width = 1920;
        canvas.height = 1080;
        const sx = dx / fit, sy = dy / fit;
        const sw = box.width / fit, sh = box.height / fit;
        canvas.getContext("2d").drawImage(image, sx, sy, sw, sh, 0, 0, canvas.width, canvas.height);
        const blob = await new Promise((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error("图片编码失败")), "image/jpeg", .92));
        const output = new File([blob], `higoos-cropped-wallpaper-${Date.now()}.jpg`, {type:"image/jpeg"});
        if (file) { close(output); return; }
        localStorage.setItem("higoos_argon_login_wallpaper", prefix + encodeURIComponent(output.name));
        localStorage.removeItem("higoos_argon_login_wallpaper_source");
        await upload(output);
        status.textContent = "裁切壁纸已保存并应用。";
        setTimeout(close, 500);
      } catch (error) {
        status.textContent = "保存失败：" + (error?.message || "请重试");
        button.disabled = false;
      }
    });
    const resize = () => layout();
    window.addEventListener("resize", resize, {once:true});
  });
  window.higoosCropBeforeUpload = file => /\.(?:jpe?g|png|webp)$/i.test(file.name) ? showEditor(file.name, file) : Promise.resolve(file);

  const addPreviews = () => {
    document.querySelectorAll("tr").forEach(row => {
      const cell = row.querySelector("td");
      if (!cell || row.querySelector(".higoos-wallpaper-preview-button")) return;
      const name = cell.textContent.trim();
      if (!/\.(?:jpe?g|png|webp)$/i.test(name) || name.startsWith("higoos-login-wallpaper.")) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "higoos-wallpaper-preview-button";
      button.setAttribute("aria-label", `预览壁纸：${name}`);
      const thumbnail = document.createElement("img");
      thumbnail.alt = "";
      thumbnail.src = prefix + encodeURIComponent(name);
      const label = document.createElement("span");
      label.textContent = "预览";
      button.append(thumbnail, label);
      button.addEventListener("click", () => showPreview(name));
      cell.append(button);
      const select = document.createElement("button");
      select.type = "button";
      select.className = "higoos-wallpaper-select-button";
      select.dataset.wallpaper = name;
      select.addEventListener("click", () => {
        try {
          localStorage.setItem("higoos_argon_login_wallpaper", prefix + encodeURIComponent(name));
          localStorage.removeItem("higoos_argon_login_wallpaper_source");
          updateSelectionLabels();
        } catch {
          select.textContent = "设置失败";
        }
      });
      cell.append(select);
    });
    updateSelectionLabels();
  };
  const updateSelectionLabels = () => {
    let current = "";
    try { current = localStorage.getItem("higoos_argon_login_wallpaper") || ""; } catch {}
    document.querySelectorAll(".higoos-wallpaper-select-button").forEach(button => {
      const selected = current === prefix + encodeURIComponent(button.dataset.wallpaper || "");
      const label = selected ? "当前登录壁纸" : "设为登录壁纸";
      if (button.textContent !== label) button.textContent = label;
      button.setAttribute("aria-pressed", String(selected));
    });
  };
  document.addEventListener("higoos-wallpaper-source-changed", updateSelectionLabels);
  addPreviews();
  new MutationObserver(addPreviews).observe(document.body, {childList:true,subtree:true});

}
