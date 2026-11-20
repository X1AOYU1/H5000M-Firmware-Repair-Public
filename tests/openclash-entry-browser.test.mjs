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
const apiRequests = [];
const app = {
  name: "luci-app-openclash",
  featureKey: "luci-app-openclash",
  displayName: "OpenClash",
  version: "0.48.002-r4",
  kind: "native",
  entryRoute: { path: "/wrong" },
};

const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1");
  if (url.pathname.startsWith("/api/v1/")) {
    apiRequests.push(`${request.method} ${url.pathname}`);
    const data = url.pathname === "/api/v1/auth/me"
      ? { username: "route-audit", role: "admin", permissions: ["*"] }
      : url.pathname === "/api/v1/plugins/apps"
        ? [app]
        : {};
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
const browser = await chromium.launch({ headless: true, args: ["--no-sandbox"] });
const page = await browser.newPage();
const pageErrors = [];
page.on("pageerror", (error) => pageErrors.push(error.message));
page.on("console", (message) => {
  if (message.type() === "error") pageErrors.push(message.text());
});

try {
  await page.goto(`${baseUrl}/plugins`, { waitUntil: "domcontentloaded" });
  const openLink = page.getByRole("link", { name: "打开" });
  await openLink.waitFor({ state: "visible", timeout: 10_000 });
  const href = await openLink.getAttribute("href");
  assert.equal(href, "/apps/openclash", `unexpected card link target: ${href}`);
  await openLink.click();
  await page.waitForURL("**/apps/openclash", { timeout: 10_000 });
  await page.getByText("基本设置", { exact: true }).waitFor({ state: "visible", timeout: 10_000 });
  assert.ok(apiRequests.includes("GET /api/v1/auth/me"), "route guard auth probe was not exercised");
  assert.deepEqual(pageErrors, [], `browser errors: ${pageErrors.join(" | ")}`);

  const report = [
    "PASS: HigoOS app-center OpenClash button was clicked in headless Chromium",
    `PASS: card link target ${href}; router reached ${new URL(page.url()).pathname}`,
    "PASS: OpenClash page rendered its native settings tab without browser errors",
    `API probes: ${apiRequests.join(", ")}`,
  ].join("\n") + "\n";
  await (await import("node:fs/promises")).writeFile(reportPath, report, "utf8");
  process.stdout.write(report);
} finally {
  await browser.close();
  await new Promise((resolveClose) => server.close(resolveClose));
}
