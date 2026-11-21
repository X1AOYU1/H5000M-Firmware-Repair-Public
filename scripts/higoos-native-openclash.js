import {e as defineComponent, a as node} from "./__vue_bundle__.js";

const base = "/cgi-bin/luci/admin/services/";
const plugins = {
  openclash: { path: base + "openclash", title: "OpenClash (LuCI)" },
  passwall: { path: base + "passwall", title: "PassWall (LuCI)" },
};

function fitNativePage(event, path) {
  const doc = event.currentTarget.contentDocument;
  const pathname = doc?.location?.pathname;
  if (!(pathname === path || pathname?.startsWith(path + "/")) || !doc.body?.classList.contains("logged-in")) return;
  if (doc.getElementById("higoos-luci-frame-style")) return;
  const style = doc.createElement("style");
  style.id = "higoos-luci-frame-style";
  style.textContent = [
    "#mainmenu, .main-right > header { display: none !important; }",
    ".main-right { margin-left: 0 !important; width: 100% !important; max-width: none !important; }",
    "#maincontent { margin-left: 0 !important; margin-top: 0 !important; }",
    "@media (min-width: 860px) { body.logged-in .oc .main-cards-container { grid-template-columns: repeat(2, minmax(0, 1fr)); } }",
  ].join("\n");
  doc.head.append(style);
}

export default defineComponent({
  name: "HigoosNativePlugin",
  props: { passwall: Boolean },
  setup(props) {
    return () => {
      const { path, title } = props.passwall ? plugins.passwall : plugins.openclash;
      return node("iframe", {
        key: path,
        title,
        src: path,
        referrerpolicy: "same-origin",
        onLoad: event => fitNativePage(event, path),
        style: {
          display: "block", width: "100%", height: "calc(100dvh - 8rem)",
          minHeight: "26rem", border: "0", background: "transparent",
        },
      });
    };
  },
});
