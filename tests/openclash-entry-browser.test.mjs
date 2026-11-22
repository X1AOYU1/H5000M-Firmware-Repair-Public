import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { createRequire } from "node:module";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, normalize, resolve, sep } from "node:path";

const root = resolve(process.argv[2] ?? "");
const reportPath = process.argv[3];
const moduleRoot = process.env.PLAYWRIGHT_ROOT;
if (!root || !reportPath || !moduleRoot)
  throw new Error("usage: PLAYWRIGHT_ROOT=... node openclash-entry-browser.test.mjs WEB_ROOT REPORT_PATH");

const require = createRequire(join(moduleRoot, "__audit__.cjs"));
const { chromium } = require("playwright");
const luciPath = "/cgi-bin/luci/admin/services/openclash";
const passwallPath = "/cgi-bin/luci/admin/services/passwall";
const luciRequests = [];
const signins = [];
const fixturePassword = "browser-audit-password";
const token = "luci-form-token-fixture";
const configPath = luciPath + "/config";
const geoPath = luciPath + "/settings";
const geoEndpoint = luciPath + "/geo_update_row";
const geoKinds = ["ipdb", "geoip", "geosite", "geoasn", "chnroute"];
const geoRequests = [];
const nativeUploadPath = luciPath + "/backup_upload";
const largeBackupSize = 31 * 1024 * 1024 + 93;
const uploadRecords = [];
let uploadState;
const nativeTemplate = await readFile(process.argv[4] ?? resolve(root, "../../../lib/lua/luci/view/openclash/status.htm"), "utf8");
const uploadTemplate = await readFile(process.argv[5] ?? resolve(root, "../../../lib/lua/luci/view/openclash/upload.htm"), "utf8");
const geoTemplate = await readFile(process.argv[6] ?? resolve(root, "../../../lib/lua/luci/view/openclash/h5000m_geo_update.htm"), "utf8");
const geoMarkup = geoKinds.map(kind => '<div style="padding:20px">' + geoTemplate
  .replace(/data-h5000m-geo="<%=[\s\S]*?%>"/g, `data-h5000m-geo="${kind}"`)
  .replace(/data-endpoint="<%=[\s\S]*?%>"/g, `data-endpoint="${geoEndpoint}"`)
  .replace(/data-token="<%=[\s\S]*?%>"/g, `data-token="${token}"`)
  .replace("<%=pcdata(self.inputtitle)%>", "检查并更新")
  .replace(/<%[\s\S]*?%>/g, "") + "</div>").join("");
function renderLuaFixture(template) {
  return template
    .replace(/data-endpoint="<%=[\s\S]*?%>"/g, `data-endpoint="${nativeUploadPath}"`)
    .replace(/data-token="<%=[\s\S]*?%>"/g, `data-token="${token}"`)
    .replace(/<%:([\s\S]*?)%>/g, "$1")
    .replace(/<%[\s\S]*?%>/g, "");
}
const statusMarkup = nativeTemplate
  .replace(/<script\b(?![^>]*id="h5000m-native-backup")[^>]*>[\s\S]*?<\/script>/gi, "")
  .replace('id="config-file-empty-state" class="config-file-empty-state oc-hidden"', 'id="config-file-empty-state" class="config-file-empty-state"');
const configMarkup = renderLuaFixture(uploadTemplate.replace(/^<script src=.*<\/script>$/gm, ""));
const apiRequests = [];
const remarkEndpoint = luciPath + "/device_remarks";
const devices = [
  { id: "router-audit-phone", name: "测试手机", macAddress: "02:00:00:00:00:01",
    ipAddress: "10.0.0.201", osType: "android", deviceType: "mobile", isOnline: true, trafficAvailable: false },
  { id: "router-audit-pc", name: "测试电脑", macAddress: "02:00:00:00:00:02",
    ipAddress: "10.0.0.202", osType: "windows", deviceType: "computer", isOnline: true, connectionType: "wired", trafficAvailable: false },
];
const remarks = {};
const remarkWrites = [];
const app = {
  name: "package-42",
  featureKey: "feature-42",
  displayName: "OpenClash",
  version: "0.48.002-r4",
  kind: "native",
  entryRoute: { path: "/wrong" },
};
const passwall = { ...app, name: "luci-app-passwall", featureKey: "passwall", displayName: "Pass Wall", entryRoute: { path: "/apps/passwall" } };
const apiData = {
  "/api/v1/auth/me": { username: "route-audit", role: "admin", permissions: ["*"] },
  "/api/v1/plugins/apps": { apps: [app, passwall] },
  "/api/v1/notifications": [],
  "/api/v1/notifications/settings": { enabled: false },
  "/api/v1/devices": devices,
  "/api/v1/system/network-interfaces": [{ name: "eth1", connected: true, speedLabel: "2500 Mbps" }],
  "/api/v1/openclash/status": { running: false, coreAvailable: false },
  "/api/v1/openclash/settings": { revision: "audit", fields: [], values: {} },
  "/api/v1/openclash/files": { rows: [] },
  "/api/v1/openclash/log": { text: "OpenClash audit log" },
};

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");
  const cookie = request.headers.cookie ?? "";
  if (url.pathname === geoEndpoint) {
    if (request.method !== "POST" || !cookie.includes("sysauth_http=audit")) return response.writeHead(403).end();
    const parts = [];
    for await (const part of request) parts.push(part);
    const form = new URLSearchParams(Buffer.concat(parts).toString());
    const kind = form.get("kind");
    if (form.get("token") !== token || !geoKinds.includes(kind)) return response.writeHead(400).end();
    geoRequests.push(kind);
    response.writeHead(200, { "content-type": "application/json" });
    return response.end(JSON.stringify({ status: "queued", kind }));
  }
  if (url.pathname === remarkEndpoint) {
    if (!cookie.includes("sysauth_http=audit")) return response.writeHead(403).end();
    const send = (data) => response.writeHead(200, { "content-type": "application/json" }).end(JSON.stringify(data));
    if (request.method === "GET") return send({ remarks, token });
    if (request.method !== "POST") return response.writeHead(405).end();
    const parts = [];
    for await (const part of request) parts.push(part);
    const form = new URLSearchParams(Buffer.concat(parts).toString());
    if (form.get("token") !== token) return response.writeHead(403, { "content-type": "application/json" }).end(JSON.stringify({ error: "CSRF token invalid" }));
    const mac = form.get("mac"), note = form.get("note");
    remarkWrites.push({ mac, note });
    if (note) remarks[mac] = note;
    else delete remarks[mac];
    return send({ note });
  }
  if (url.pathname === nativeUploadPath) {
    const error = (status, message) => response.writeHead(status, { "content-type": "application/json" }).end(JSON.stringify({ status: "error", message }));
    if (request.method !== "POST" || !cookie.includes("sysauth_http=audit") || url.searchParams.get("token") !== token)
      return error(403, "Authorization required");
    const op = url.searchParams.get("operation");
    const filename = url.searchParams.get("filename");
    const id = url.searchParams.get("upload_id");
    if (!/^[0-9a-f]{32}$/.test(id)) return error(400, "Invalid upload id");
    if (op === "start") uploadState = { id, filename, size: 0, hash: createHash("sha256"), chunks: 0 };
    else if (!uploadState || id !== uploadState.id || filename !== uploadState.filename) return error(400, "Invalid upload session");
    else if (op === "chunk") {
      if (request.headers["content-type"] !== "application/octet-stream" || Number(url.searchParams.get("offset")) !== uploadState.size)
        return error(400, "Invalid chunk request");
      const parts = [];
      for await (const part of request) parts.push(part);
      const chunk = Buffer.concat(parts);
      if (!chunk.length || chunk.length > 65536) return error(413, "Chunk too large");
      uploadState.size += chunk.length;
      uploadState.chunks++;
      uploadState.hash.update(chunk);
    } else if (op === "finish") {
      if (filename === "Invalid backup.tar.gz") return error(422, "备份归档无法读取");
      uploadRecords.push({ filename, size: uploadState.size, chunks: uploadState.chunks, hash: uploadState.hash.digest("hex") });
      uploadState = undefined;
    } else if (op === "cancel") {
      uploadRecords.push({ filename, cancelled: true });
      uploadState = undefined;
    } else return error(400, "Unknown operation");
    response.writeHead(200, { "content-type": "application/json" });
    return response.end(JSON.stringify({ status: "success", message: "备份已导入，OpenClash 保持关闭" }));
  }
  if (url.pathname === "/cgi-bin/luci/admin" && request.method === "POST") {
    const parts = [];
    for await (const part of request) parts.push(part);
    const form = new URLSearchParams(Buffer.concat(parts).toString());
    if (!cookie.includes("higoros_session=audit") ||
        form.get("luci_username") !== "root" || form.get("luci_password") !== fixturePassword) {
      response.writeHead(403).end();
      return;
    }
    signins.push("luci");
    response.writeHead(302, {
      location: "/cgi-bin/luci/admin/status/overview",
      "set-cookie": "sysauth_http=audit; Path=/cgi-bin/luci; HttpOnly; SameSite=Strict",
    }).end();
    return;
  }
  if (url.pathname === passwallPath || url.pathname === passwallPath + "/node_list") {
    if (!cookie.includes("sysauth_http=audit")) return response.writeHead(403).end();
    const heading = url.pathname === passwallPath ? "PassWall Basic Settings" : "PassWall Node List";
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    return response.end(`<!doctype html><body class="logged-in"><aside id="mainmenu">LuCI navigation</aside>
      <div class="main-right"><header>LuCI header</header><main id="maincontent"><h1>${heading}</h1>
      <div id="tabmenu"><a href="${passwallPath}/node_list">Node List</a></div></main></div>`);
  }
  if (url.pathname === luciPath || url.pathname === configPath || url.pathname === geoPath) {
    if (url.pathname === luciPath) luciRequests.push({
      method: request.method,
      mode: request.headers["sec-fetch-mode"],
      destination: request.headers["sec-fetch-dest"],
    });
    if (!cookie.includes("sysauth_http=audit")) {
      response.writeHead(403, { "content-type": "text/html; charset=utf-8" });
      response.end("<!doctype html><title>LuCI</title><main>LuCI sign-in fixture</main>");
      return;
    }
    if (request.method !== "GET") return response.writeHead(413).end("Full multipart POST must not be used for backups");
    response.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    const markup = url.pathname === geoPath ? `<form action="${geoPath}" method="post">${geoMarkup}</form>` : url.pathname === configPath
      ? `<form action="${configPath}" method="post" enctype="multipart/form-data">${configMarkup}</form>`
      : `<a href="${configPath}">配置管理</a><a href="${geoPath}">插件设置</a>${renderLuaFixture(statusMarkup)}`;
    response.end("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>" +
      "<title>OpenClash</title><body class=logged-in><aside id=mainmenu>LuCI navigation</aside>" + markup);
    return;
  }
  if (url.pathname.startsWith("/luci-static/")) {
    response.writeHead(404).end();
    return;
  }
  if (url.pathname.startsWith("/api/v1/")) {
    apiRequests.push(`${request.method} ${url.pathname}`);
    if (url.pathname === "/api/v1/auth/login" && request.method === "POST") {
      const parts = [];
      for await (const part of request) parts.push(part);
      let form;
      try { form = JSON.parse(Buffer.concat(parts).toString()); } catch {}
      if (form?.username !== "root" || form?.password !== fixturePassword) {
        response.writeHead(401, { "content-type": "application/json" });
        response.end(JSON.stringify({ code: 401, message: "invalid credentials" }));
        return;
      }
      signins.push("higoros");
      response.writeHead(200, {
        "content-type": "application/json",
        "set-cookie": "higoros_session=audit; Path=/; HttpOnly; SameSite=Strict",
      });
      response.end(JSON.stringify({ code: 0, data: {} }));
      return;
    }
    if (url.pathname === "/api/v1/auth/me" && !cookie.includes("higoros_session=audit")) {
      response.writeHead(401, { "content-type": "application/json" });
      response.end(JSON.stringify({ code: 401, message: "unauthorized" }));
      return;
    }
    const data = apiData[url.pathname] ?? {};
    response.writeHead(200, { "content-type": "application/json; charset=utf-8" });
    response.end(JSON.stringify({ code: 0, data }));
    return;
  }

  const requested = normalize(decodeURIComponent(url.pathname)).replace(/^([.][.][/\\])+/, "");
  const file = resolve(root, `.${requested === "." ? "/index.html" : `/${requested}`}`);
  if (file !== root && !file.startsWith(`${root}${sep}`)) {
    response.writeHead(403).end();
    return;
  }
  let target = file;
  try {
    const info = await stat(target);
    if (info.isDirectory()) target = join(target, "index.html");
  } catch {
    target = join(root, "index.html");
  }
  try {
    const body = await readFile(target);
    const type = {
      ".html": "text/html; charset=utf-8",
      ".js": "text/javascript; charset=utf-8",
      ".css": "text/css; charset=utf-8",
      ".svg": "image/svg+xml",
      ".png": "image/png",
      ".woff2": "font/woff2",
    }[extname(target)] ?? "application/octet-stream";
    response.writeHead(200, { "content-type": type });
    response.end(body);
  } catch {
    response.writeHead(404).end();
  }
});

await new Promise((resolveListen) => server.listen(0, "127.0.0.1", resolveListen));
const address = server.address();
const baseUrl = `http://127.0.0.1:${address.port}`;
let browser;
let page;
const pageErrors = [];

try {
  browser = await chromium.launch({
    headless: true,
    args: ["--no-sandbox"],
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : {}),
  });
  page = await browser.newPage();
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") {
      const location = message.location();
      pageErrors.push(`${message.text()} [${location.url || "unknown"}]`);
    }
  });
  page.on("requestfailed", (request) => {
    pageErrors.push(`request failed: ${request.url()} (${request.failure()?.errorText ?? "unknown"})`);
  });
  await page.goto(baseUrl + "/login", { waitUntil: "domcontentloaded" });
  await page.locator('[autocomplete="username"]').fill("root");
  await page.locator('[autocomplete="current-password"]').fill(fixturePassword);
  await page.getByRole("button", { name: "登录", exact: true }).click();
  await page.waitForURL(url => !url.pathname.startsWith("/login"), { timeout: 12_000 });
  assert.deepEqual(signins, ["higoros", "luci"], "LuCI sign-in must follow successful HigoOS sign-in");
  pageErrors.length = 0;
  await page.goto(baseUrl + "/plugins", { waitUntil: "domcontentloaded" });
  const openLink = page.locator('a[href="/apps/openclash-luci"]').and(page.getByRole("link", { name: "打开", exact: true }));
  await openLink.waitFor({ state: "visible", timeout: 10_000 });
  const href = await openLink.getAttribute("href");
  assert.equal(href, "/apps/openclash-luci");
  await openLink.click();
  await page.waitForURL("**/apps/openclash-luci", { timeout: 10_000 });
  const frame = page.frameLocator('iframe[title="OpenClash (LuCI)"]');
  await frame.locator(".main-cards-container").waitFor({ state: "visible" });
  await frame.locator("#mainmenu").waitFor({ state: "hidden" });
  assert.deepEqual(luciRequests, [{ method: "GET", mode: "navigate", destination: "iframe" }]);
  await page.getByRole("link", { name: "应用中心", exact: true }).waitFor({ state: "visible" });
  for (const [width, columns] of [[1280, 2], [390, 1]]) {
    await page.setViewportSize({ width, height: 900 });
    const cards = frame.locator(".main-cards-container");
    await cards.evaluate((node, expected) => new Promise((resolve, reject) => {
      const deadline = performance.now() + 2_000;
      function check() {
        const style = getComputedStyle(node);
        const columns = style.gridTemplateColumns.split(/\s+/).length;
        if (style.display === "grid" && columns === expected) resolve();
        else if (performance.now() > deadline)
          reject(new Error(`Expected ${expected} grid columns at iframe width ${innerWidth}px; got ${columns}`));
        else requestAnimationFrame(check);
      }
      check();
    }), columns);
    assert.ok(await frame.locator(".main-card").evaluateAll(nodes =>
      nodes.length > 0 && nodes.every(node => getComputedStyle(node).display === "grid")));
  }
  await page.setViewportSize({ width: 1280, height: 900 });
  const waitForUpload = async (text) => frame.getByText(text, { exact: true }).waitFor({ state: "visible", timeout: 35_000 });
  const [fileChooser] = await Promise.all([
    page.waitForEvent("filechooser", { timeout: 8000 }),
    frame.locator("#restore_backup_large").click({ timeout: 8000 }),
  ]);
  await fileChooser.setFiles({ name: "Overview backup.tar.gz", mimeType: "application/gzip", buffer: Buffer.from("overview") });
  await waitForUpload("备份已导入，OpenClash 保持关闭");
  await frame.getByRole("link", { name: "配置管理", exact: true }).click();
  await frame.locator("#file_type").selectOption("backup-file");
  assert.equal(await frame.locator("#ulfile").getAttribute("accept"), ".tar,.tar.gz");
  await frame.locator("#ulfile").setInputFiles({ name: "Invalid backup.tar.gz", mimeType: "application/gzip", buffer: Buffer.from("invalid") });
  await frame.locator("#upload-submit").click();
  await waitForUpload("备份请求失败（HTTP 422）");
  const largeBackup = Buffer.alloc(largeBackupSize, 0x53);
  const filename = "Backup-OpenClash-Hiveton H5000M-aarch64-test.tar";
  await frame.locator("#ulfile").setInputFiles({ name: filename, mimeType: "application/x-tar", buffer: largeBackup });
  await frame.locator("#upload-submit").click();
  await waitForUpload("备份已导入，OpenClash 保持关闭");
  assert.deepEqual(uploadRecords, [
    { filename: "Overview backup.tar.gz", size: 8, chunks: 1, hash: createHash("sha256").update("overview").digest("hex") },
    { filename: "Invalid backup.tar.gz", cancelled: true },
    { filename, size: largeBackupSize, chunks: Math.ceil(largeBackupSize / 65536), hash: createHash("sha256").update(largeBackup).digest("hex") },
  ]);
  assert.equal(page.url(), baseUrl + "/apps/openclash-luci");
  const unexpected = pageErrors.filter(message => !message.includes("404") && !message.includes("422") && !message.includes("ERR_ABORTED"));
  assert.deepEqual(unexpected, []);
  pageErrors.length = 0;

  await frame.locator("body").evaluate((body, home) => body.ownerDocument.location.assign(home), luciPath);
  await frame.getByRole("link", { name: "插件设置", exact: true }).click();
  await frame.locator("[data-h5000m-geo=geoip]").waitFor();
  const order = ["geoip", "ipdb", "geoasn", "chnroute", "geosite"];
  let reloads = 0;
  const trackSettingsLoad = nav => { if (new URL(nav.url()).pathname === geoPath) reloads++; };
  page.on("framenavigated", trackSettingsLoad);
  for (const kind of order) {
    const button = frame.locator(`[data-h5000m-geo=${kind}]`);
    const rowStatus = button.locator("xpath=following-sibling::*[1]");
    await button.click();
    await rowStatus.getByText("已提交更新，请在插件日志查看结果", { exact: true }).waitFor();
    assert.deepEqual(geoRequests, order.slice(0, order.indexOf(kind) + 1));
  }
  assert.equal(reloads, 0, "GEO update must not reload settings");
  page.off("framenavigated", trackSettingsLoad);
  assert.deepEqual(pageErrors.filter(message => !message.includes("404") && !message.includes("ERR_ABORTED")), []);
  pageErrors.length = 0;

  await page.getByRole("link", { name: "应用中心", exact: true }).click();
  const openPasswall = page.locator('a[href="/apps/passwall-luci"]').and(page.getByRole("link", { name: "打开", exact: true }));
  await openPasswall.click({ timeout: 10000 });
  await page.waitForURL("**/apps/passwall-luci");
  const passwallFrame = page.frameLocator('iframe[title="PassWall (LuCI)"]');
  await passwallFrame.getByRole("heading", { name: "PassWall Basic Settings" }).waitFor({ state: "visible" });
  await passwallFrame.locator("#mainmenu").waitFor({ state: "hidden" });
  await page.getByRole("link", { name: "应用中心", exact: true }).waitFor({ state: "visible" });
  await passwallFrame.getByRole("link", { name: "Node List", exact: true }).click();
  await passwallFrame.getByRole("heading", { name: "PassWall Node List" }).waitFor({ state: "visible" });
  assert.equal(page.url(), baseUrl + "/apps/passwall-luci");

  await page.goto(baseUrl + "/devices", { waitUntil: "domcontentloaded" });
  await page.getByText("2500 Mbps", { exact: true }).waitFor({ state: "visible", timeout: 10_000 });
  const remark = page.getByRole("button", { name: "备注：测试手机", exact: true });
  const input = page.getByPlaceholder("输入设备备注");
  const saveRemark = page.getByRole("button", { name: "保存", exact: true });
  const eventuallyVisible = { state: "visible", timeout: 10_000 };
  const note = "客厅手机";
  await remark.click({ timeout: 10_000 });
  await input.fill(note);
  await saveRemark.click();
  await page.getByText(note, { exact: true }).waitFor(eventuallyVisible);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByText(note, { exact: true }).waitFor(eventuallyVisible);
  await page.getByRole("button", { name: "测试手机", exact: true }).waitFor(eventuallyVisible);
  await page.getByRole("button", { name: "备注：测试电脑", exact: true }).waitFor(eventuallyVisible);
  await remark.click();
  await input.fill("");
  await saveRemark.click();
  await page.getByText(note, { exact: true }).waitFor({ state: "hidden", timeout: 10_000 });
  assert.deepEqual(remarkWrites, [{ mac: "020000000001", note }, { mac: "020000000001", note: "" }]);
  assert.ok(!apiRequests.some(value => value.startsWith("PATCH /api/v1/devices/")), "Device names must not be modified");

  // Retain the configuration-tab regression check for direct visits to the older URL.
  await page.goto(`${baseUrl}/apps/openclash`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: "基本设置", exact: true }).waitFor({ state: "visible", timeout: 10_000 });
  await page.getByText("配置文件", { exact: true }).click();
  const operation = page.locator("#oc-backup-file-type");
  await operation.waitFor({ state: "visible", timeout: 5_000 });
  assert.equal(await operation.count(), 1);
  const choose = page.getByRole("button", { name: "选择文件", exact: true });
  const backup = page.getByRole("button", { name: "备份", exact: true });
  const createType = page.locator("#oc-new-file-type");
  await choose.waitFor({ state: "visible" });
  await backup.waitFor({ state: "visible" });
  assert.equal(await createType.isVisible(), false);
  await operation.selectOption("create-file");
  await createType.waitFor({ state: "visible" });
  assert.equal(await choose.isVisible(), false);
  await createType.selectOption("rule-provider");
  assert.equal(await createType.inputValue(), "rule-provider");
  await page.getByPlaceholder("文件名.yaml").fill("audit.yaml");
  assert.ok(await page.getByRole("button", { name: "新建文件", exact: true }).isEnabled());
  await operation.selectOption("backup-file");
  await choose.waitFor({ state: "visible" });
  assert.equal(await createType.isVisible(), false);
  await page.getByText("日志", { exact: true }).click();
  await page.getByText("OpenClash audit log", { exact: true }).waitFor({ state: "visible" });
  assert.equal(await operation.count(), 0);
  await page.getByText("配置文件", { exact: true }).click();
  await operation.waitFor({ state: "visible" });
  assert.ok(apiRequests.includes("GET /api/v1/auth/me"), "route guard auth probe was not exercised");
  const finalUnexpected = pageErrors.filter(message => !message.includes("404") && !message.includes("422") && !message.includes("ERR_ABORTED"));
  assert.deepEqual(finalUnexpected, [], `browser errors: ${finalUnexpected.join(" | ")}`);

  const report = [
    "PASS: HigoOS app-center OpenClash button was clicked in headless Chromium",
    "PASS: the HigoOS route stays open and loads native LuCI in its content frame",
    "PASS: HigoOS sign-in establishes a separate LuCI cookie in the authentication fixture",
    "PASS: native OpenClash cards use two columns on desktop and one on mobile without external CSS",
    "PASS: native OpenClash overview restores .tar.gz and configuration page sends a 31 MiB .tar intact in authenticated chunks; upload errors stay inside the page",
    "PASS: PassWall opens and navigates its native LuCI fixture inside HigoOS using the same LuCI session",
    "PASS: device-management remarks save and reload independently of device name through the OpenClash LuCI route, then clear",
    "PASS: GEO and China route update buttons submitted only their own target, with no settings reload",
    "PASS: previous HigoOS URL still renders its settings tab without browser errors",
    "PASS: Configuration files tab rendered with no profiles; upload and creation switched in one menu and navigation worked in both directions",
    `API probes: ${apiRequests.join(", ")}`,
  ].join("\n") + "\n";
  await (await import("node:fs/promises")).writeFile(reportPath, report, "utf8");
  process.stdout.write(report);
} catch (error) {
  const diagnostics = {
    error: error instanceof Error ? error.stack : String(error),
    url: page?.url() ?? null,
    title: await page?.title().catch(() => "") ?? "",
    body: page ? await page.locator("body").innerText().catch(() => "").then((text) => text.slice(0, 4000)) : "",
    links: page ? await page.locator("a").evaluateAll((items) => items.map((item) => ({
      text: item.innerText.trim(),
      href: item.getAttribute("href"),
    }))).catch(() => []) : [],
    apiRequests,
    pageErrors,
  };
  const report = JSON.stringify(diagnostics, null, 2) + "\n";
  await (await import("node:fs/promises")).writeFile(reportPath, report, "utf8");
  process.stdout.write(`::error title=OpenClash click audit::${JSON.stringify(diagnostics)}\n`);
  process.stdout.write(report);
  throw error;
} finally {
  await browser?.close();
  await new Promise((resolveClose) => server.close(resolveClose));
}
