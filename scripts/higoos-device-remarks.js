const endpoint = "/cgi-bin/luci/admin/services/openclash/device_remarks";

async function request(path, options) {
  const response = await fetch(endpoint + path, {
    credentials: "same-origin", cache: "no-store", signal: AbortSignal.timeout(8000), ...options,
  });
  if (response.redirected || [401, 403].includes(response.status) || response.headers.has("x-luci-login-required"))
    throw new Error("请退出后台并重新登录后再试");
  const data = await response.json().catch(() => null);
  if (!response.ok || !data)
    throw new Error(data?.error || `备注保存失败（HTTP ${response.status}），请重试`);
  return data;
}

export function createDeviceRemark({ defineComponent, h, ref, Modal, Button, Input }) {
  const notes = ref({});
  let initialLoad;
  async function load() {
    const data = await request("");
    notes.value = data.remarks;
    return data.token;
  }

  return defineComponent({
    name: "HigoosDeviceRemark",
    props: { mac: String, name: String },
    setup(props) {
      const key = () => /^[0-9a-f]{2}(?::[0-9a-f]{2}){5}$/i.test(props.mac ?? "")
        ? props.mac.replaceAll(":", "").toLowerCase() : "";
      const show = ref(false);
      const draft = ref("");
      const error = ref("");
      const busy = ref(false);
      const byteLength = () => new TextEncoder().encode(draft.value).length;
      const setOpen = value => { if (!busy.value) show.value = value; };
      if (key()) initialLoad ??= load().catch(() => {});

      async function open() {
        if (busy.value) return;
        busy.value = true;
        error.value = "";
        draft.value = notes.value[key()] ?? "";
        show.value = true;
        try {
          await initialLoad;
          await load();
          draft.value = notes.value[key()] ?? "";
        } catch (cause) {
          error.value = cause.message;
        } finally {
          busy.value = false;
        }
      }

      async function save() {
        if (busy.value || byteLength() > 256 || !key()) return;
        busy.value = true;
        error.value = "";
        const mac = key(), note = draft.value.trim();
        try {
          const token = await load();
          const result = await request("", {
            method: "POST", body: new URLSearchParams({ token, mac, note }),
          });
          notes.value = { ...notes.value, [mac]: result.note };
          show.value = false;
        } catch (cause) {
          error.value = cause.message;
        } finally {
          busy.value = false;
        }
      }

      return () => key() ? h("div", { class: "mt-1 min-w-0 text-sm" }, [
        h("button", {
          type: "button", class: "p-1 -ml-1 rounded text-brand-txt hover:underline focus-visible:outline",
          "aria-label": `备注：${props.name ?? props.mac}`, onClick: open,
        }, "备注"),
        notes.value[key()] ? h("p", { class: "text-txt-3 break-all" }, notes.value[key()]) : null,
        show.value ? h(Modal, { modelValue: true, "onUpdate:modelValue": setOpen, title: "设备备注", size: "sm" }, {
          default: () => [
            h("p", { class: "mb-2 break-all text-sm text-txt-3" }, props.name ?? props.mac),
            h(Input, { modelValue: draft.value, "onUpdate:modelValue": value => draft.value = value,
              placeholder: "输入设备备注", disabled: busy.value, class: "w-full" }),
            byteLength() > 256 ? h("p", { role: "alert", class: "mt-2 text-sm text-err" }, "备注太长，请缩短后再保存") : null,
            error.value ? h("p", { role: "alert", class: "mt-2 text-sm text-err" }, error.value) : null,
          ],
          footer: () => h("div", { class: "flex flex-wrap justify-end gap-2" }, [
            h(Button, { variant: "ghost", disabled: busy.value, onClick: () => setOpen(false) }, () => "取消"),
            h(Button, { variant: "primary", disabled: busy.value || byteLength() > 256, onClick: save },
              () => busy.value ? "请稍候" : "保存"),
          ]),
        }) : null,
      ]) : null;
    },
  });
}
