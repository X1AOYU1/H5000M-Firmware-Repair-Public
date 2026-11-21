import assert from "node:assert/strict";
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
const luciRequests = [];
const apiRequests = [];
const app = {
  name: "package-42",
  featureKey: "feature-42",
  displayName: "OpenClash",
  version: "0.48.002-r4",
  kind: "native",
  entryRoute: { path: "/wrong" },
};
const apiData = {
  "/api/v1/auth/me": { username: "route-audit", role: "admin", permissions: ["*"] },
  "/api/v1/plugins/apps": { apps: [app] },
  "/api/v1/notifications": [],
  "/api/v1/notifications/settings": { enabled: false },
  "/api/v1/openclash/status": { running: false, coreAvailable: false },
  "/api/v1/openclash/settings": { revision: "audit", fields: [], values: {} },
  "/api/v1/openclash/files": { rows: [] },
  "/api/v1/openclash/log": { text: "OpenClash audit log" },
};

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");
  if (url.pathname === luciPath) {
    luciRequests.push({
      method: request.method,
      mode: request.headers["sec-fetch-mode"],
      destination: request.headers["sec-fetch-dest"],
    });
    // The firmware's LuCI CGI requires a running router. Simulate its login challenge.
    response.writeHead(403, { "content-type": "text/html; charset=utf-8" });
    response.end("<!doctype html><title>LuCI</title><main>LuCI sign-in fixture</main>");
    return;
  }
  if (url.pathname.startsWith("/api/v1/")) {
    apiRequests.push(`${request.method} ${url.pathname}`);
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
    if (message.type() === "error") pageErrors.push(message.text());
  });
  await page.goto(`${baseUrl}/plugins`, { waitUntil: "domcontentloaded" });
  const openLink = page.getByRole("link", { name: "打开" });
  await openLink.waitFor({ state: "visible", timeout: 10_000 });
  const href = await openLink.getAttribute("href");
  assert.equal(href, luciPath, `unexpected card link target: ${href}`);
  await openLink.click();
  await page.waitForURL(`**${luciPath}`, { timeout: 10_000 });
  await page.getByText("LuCI sign-in fixture", { exact: true }).waitFor({ state: "visible" });
  assert.deepEqual(luciRequests, [{ method: "GET", mode: "navigate", destination: "document" }]);
  assert.equal(page.frames().length, 1, "LuCI must open as a standalone document");
  const unexpected = pageErrors.filter(message => !message.includes("403"));
  assert.deepEqual(unexpected, []);
  pageErrors.length = 0;

  // Retain the configuration-tab regression check for direct visits to the older URL.
  await page.goto(`${baseUrl}/apps/openclash`, { waitUntil: "domcontentloaded" });
  await page.getByText("基本设置", { exact: true }).waitFor({ state: "visible", timeout: 10_000 });
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
  assert.deepEqual(pageErrors, [], `browser errors: ${pageErrors.join(" | ")}`);

  const report = [
    "PASS: HigoOS app-center OpenClash button was clicked in headless Chromium",
    `PASS: same-tab, top-level document navigation to ${href} (LuCI login response mocked)`,
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
