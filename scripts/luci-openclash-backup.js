(function () {
  "use strict";

  const configButton = document.getElementById("upload-submit");
  const type = document.getElementById("file_type");
  const input = document.getElementById("ulfile");
  const overviewButton = document.getElementById("restore_backup_large");
  const context = document.currentScript.dataset;
  let busy = false;

  async function restore(file, show) {
    if (busy || !file) return;
    if (!/\.tar(?:\.gz)?$/i.test(file.name)) return show("请选择 .tar 或 .tar.gz 备份", true);
    if (file.size <= 0 || file.size > 128 * 1024 * 1024) return show("备份必须大于 0 字节且不超过 128 MiB", true);
    if (!context.token) return show("LuCI 登录已过期，请重新登录后重试", true);

    const id = Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, "0")).join("");
    const blockSize = 65536;
    async function request(operation, offset = 0, body) {
      const url = new URL(context.endpoint, location.href);
      url.search = new URLSearchParams({ operation, upload_id: id, filename: file.name, offset, token: context.token });
      const response = await fetch(url, {
        method: "POST", body, credentials: "same-origin", redirect: "manual", cache: "no-store",
        referrerPolicy: "no-referrer", signal: AbortSignal.timeout(operation === "finish" ? 180_000 : 15_000),
        headers: body ? { "Content-Type": "application/octet-stream" } : {},
      });
      if (response.status === 401 || response.status === 403 || response.type === "opaqueredirect")
        throw new Error("LuCI 登录或表单校验已过期，请重新登录后重试");
      if (!response.ok) throw new Error(`备份请求失败（HTTP ${response.status}）`);
      const result = await response.json().catch(() => null);
      if (!result || result.status !== "success") throw new Error(result?.message || "路由器未返回有效的备份结果");
      return result;
    }

    busy = true;
    let started = false;
    try {
      show("正在上传备份：0%", false);
      await request("start");
      started = true;
      for (let offset = 0; offset < file.size; offset += blockSize) {
        const end = Math.min(file.size, offset + blockSize);
        await request("chunk", offset, file.slice(offset, end));
        show(`正在上传备份：${Math.floor(end * 100 / file.size)}%`, false);
      }
      show("上传完成，正在恢复备份…", false);
      const result = await request("finish");
      started = false;
      show(result.message || "备份已恢复，OpenClash 保持关闭", false);
      window.setTimeout(() => location.reload(), 3000);
    } catch (error) {
      show(error.name === "TimeoutError" ? "等待路由器响应超时，请检查配置列表后再试" : error.message, true);
      if (started) request("cancel").catch(() => {});
      busy = false;
    }
    return busy;
  }

  if (configButton && type && input && configButton.form) {
    const result = document.getElementById("upload-result");
    const note = document.getElementById("upload-note-default");
    result.setAttribute("aria-live", "polite");
    const acceptBackup = () => {
      if (type.value === "backup-file") input.accept = ".tar,.tar.gz";
      result.classList.add("oc-hidden");
      note.classList.remove("oc-hidden");
    };
    type.addEventListener("change", acceptBackup);
    if (type.value === "backup-file") input.accept = ".tar,.tar.gz";
    configButton.form.addEventListener("submit", async event => {
      if (type.value !== "backup-file" || (event.submitter && event.submitter !== configButton)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      if (busy || !input.files?.[0]) return;
      configButton.disabled = type.disabled = input.disabled = true;
      const success = await restore(input.files[0], (message, error) => {
        result.textContent = message;
        result.classList.toggle("err", error);
        result.classList.remove("oc-hidden");
        note.classList.add("oc-hidden");
      });
      if (!success) configButton.disabled = type.disabled = input.disabled = false;
    }, true);
  }

  if (overviewButton) {
    const picker = document.createElement("input");
    picker.type = "file";
    picker.accept = ".tar,.tar.gz";
    picker.hidden = true;
    picker.id = "h5000m-native-backup-file";
    const status = document.createElement("span");
    status.className = "upload-result";
    status.setAttribute("aria-live", "polite");
    overviewButton.after(picker, status);
    overviewButton.addEventListener("click", event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!busy) {
        picker.value = "";
        picker.click();
      }
    }, true);
    picker.addEventListener("change", async () => {
      if (!picker.files?.[0] || busy) return;
      overviewButton.disabled = true;
      const success = await restore(picker.files[0], (message, error) => {
        status.textContent = message;
        status.classList.toggle("err", error);
      });
      if (!success) overviewButton.disabled = false;
    });
  }
})();
