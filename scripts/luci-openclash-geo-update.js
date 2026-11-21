(() => {
  if (window.h5000mGeoUpdatesBound) return;
  window.h5000mGeoUpdatesBound = true;
  document.addEventListener("click", async (event) => {
    const button = event.target.closest?.("button[data-h5000m-geo]");
    if (!button) return;
    event.preventDefault();
    if (button.disabled) return;
    const status = button.nextElementSibling;
    button.disabled = true;
    status.textContent = "正在提交…";
    try {
      const response = await fetch(button.dataset.endpoint, {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        signal: AbortSignal.timeout(12000),
        body: new URLSearchParams({ token: button.dataset.token, kind: button.dataset.h5000mGeo }),
      });
      if (response.redirected || [401, 403].includes(response.status))
        throw new Error("请重新登录后再试");
      if (!response.ok || !response.headers.get("content-type")?.includes("application/json"))
        throw new Error("未能提交更新，请重试");
      const result = await response.json();
      if (result.kind !== button.dataset.h5000mGeo || result.status !== "queued")
        throw new Error("未能提交更新，请重试");
      status.textContent = "已提交更新，请在插件日志查看结果";
    } catch (error) {
      status.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  });
})();
