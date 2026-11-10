const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const output = path.join(root, "outputs", "phase4-visual-qa");
const baseUrl = process.env.PHASE4_URL || "http://localhost:8505";
const executablePath = process.env.PHASE4_CHROME_PATH;
const cases = [
  ["Dashboard", "Project overview"],
  ["Geometry Designer", "Define the authoritative CAD solid"],
  ["Engine Loading", "Loads with explicit provenance"],
  ["Simulation", "Linear elastic simulation"],
  ["AI Optimization", "Constrained CAD-mass optimization"],
  ["Results & Comparison", "Solver evidence, not surrogate contours"],
  ["Model Analytics", "Geometry-grouped held-out evaluation"],
  ["Reports & Downloads", "Reproduce and inspect"],
  ["Phase 4 Design Studio", "Parametric geometry families"],
  ["Topology & Shape Exploration", "Material distribution and design-space evidence"],
];

function slug(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

async function openSidebar(page) {
  const expand = page.getByRole("button", { name: "Expand sidebar" });
  if (await expand.count()) {
    const box = await page.locator('[data-testid="stSidebar"]').boundingBox();
    if (!box || box.width < 100 || box.x < -10) {
      await expand.click();
      await page.waitForTimeout(250);
    }
  }
}

async function waitForAppIdle(page) {
  await page.waitForFunction(
    () => {
      const scriptRunning = [...document.querySelectorAll("button")].some(
        (button) => button.innerText.trim() === "Stop",
      );
      const skeletons = document.querySelectorAll('[data-testid*="Skeleton"]').length;
      const status = document.querySelector('[data-testid="stStatusWidget"]')?.innerText || "";
      const busy = document.querySelector('[data-testid="stMain"]')?.getAttribute("aria-busy");
      return !scriptRunning && !/running/i.test(status) && skeletons === 0 && busy !== "true";
    },
    null,
    { timeout: 60000 },
  );
  await page.waitForTimeout(450);
}

async function verifyControls(page, name) {
  if (name === "Geometry Designer") {
    for (const label of ["Apply geometry", "Generate Preview"]) {
      if (!(await page.getByRole("button", { name: label }).count())) throw new Error(`Missing geometry control: ${label}`);
    }
    return ["Apply geometry", "Generate Preview"];
  }
  if (name === "Engine Loading") {
    if (!(await page.getByText("Loading mode", { exact: true }).count())) throw new Error("Missing engine loading mode selector");
    return ["Loading mode selector", "manual/engine calculation views"];
  }
  if (name === "Simulation") {
    for (const label of ["Material", "Maximum mesh size (mm)", "Boundary conditions"]) {
      if (!(await page.getByRole("combobox", { name: label }).count())) throw new Error(`Missing simulation control: ${label}`);
    }
    if (!(await page.getByRole("button", { name: "Run FEA" }).count())) throw new Error("Missing Run FEA action");
    return ["material", "mesh size", "boundary conditions", "Run FEA action"];
  }
  if (name === "AI Optimization") {
    if (!(await page.getByText("Run Optimization", { exact: true }).count())) throw new Error("Missing Run Optimization action");
    return ["optimization constraints", "Run Optimization action rendered; disabled until model criteria are met"];
  }
  if (name === "Phase 4 Design Studio") {
    const family = page.getByRole("combobox", { name: "Geometry family" });
    await family.click();
    const option = page.getByRole("option", { name: "Tapered I section" });
    await option.waitFor({ state: "visible", timeout: 10000 });
    await option.click();
    await waitForAppIdle(page);
    if ((await family.inputValue()) !== "Tapered I section") throw new Error("Geometry-family selection did not update");
    return ["selected Tapered I section without submitting CAD/FEA"];
  }
  if (name === "Topology & Shape Exploration") {
    await page.waitForFunction(
      () => document.querySelectorAll('[data-testid="stPlotlyChart"]').length >= 2,
      null,
      { timeout: 30000 },
    );
    return ["family distribution chart", "actual mass/stress chart"];
  }
  if (name === "Reports & Downloads") {
    if (!(await page.getByRole("button", { name: "Download report" }).count())) throw new Error("Missing report download action");
    return ["engineering report", "download action"];
  }
  return [];
}

async function selectCase(page, name, expectedText, viewportName) {
  await openSidebar(page);
  const options = page.locator('[data-testid="stSidebar"]').getByText(name, { exact: true });
  await options.first().waitFor({ state: "visible", timeout: 30000 });
  if (await options.count() !== 1) {
    throw new Error(`Expected one sidebar option for ${name}; found ${await options.count()}`);
  }
  await options.click();
  await page.getByText(expectedText, { exact: false }).first().waitFor({ state: "visible", timeout: 30000 });
  await waitForAppIdle(page);
  if (await page.evaluate(() => window.innerWidth < 600)) {
    const collapse = page.getByRole("button", { name: "Collapse sidebar" });
    if (await collapse.count()) {
      await collapse.click();
      await page.waitForTimeout(200);
    }
  }
  const controls = await verifyControls(page, name);
  await waitForAppIdle(page);
  const exceptionCount = await page.locator('[data-testid="stException"]').count();
  if (exceptionCount) {
    throw new Error(`${name} rendered a Streamlit exception`);
  }
  const visibleJsonCount = await page.locator('[data-testid="stJson"]').evaluateAll(
    (els) => els.filter((el) => el.checkVisibility()).length,
  );
  if (visibleJsonCount) {
    throw new Error(`${name} rendered ${visibleJsonCount} visible raw JSON component(s)`);
  }
  const visibleText = await page.locator('[data-testid="stAppViewContainer"]').innerText();
  const rawDataTokens = [
    '"attempted_geometries"',
    '"INFEASIBLE_ON_TESTED_MESH"',
    "solver_configuration",
    "implementation_sha256",
    "mesh_configuration",
    "coarse_sha256",
  ];
  const visibleRawTokens = rawDataTokens.filter((token) => visibleText.includes(token));
  if (visibleRawTokens.length) {
    throw new Error(`${name} exposes raw internal data fields: ${visibleRawTokens.join(", ")}`);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  const layout = await page.evaluate(() => ({
    viewportWidth: window.innerWidth,
    documentWidth: document.documentElement.scrollWidth,
    documentHeight: document.documentElement.scrollHeight,
    mainClientWidth: document.querySelector('[data-testid="stMain"]')?.clientWidth,
    mainScrollWidth: document.querySelector('[data-testid="stMain"]')?.scrollWidth,
    mainScrollHeight: document.querySelector('[data-testid="stMain"]')?.scrollHeight,
  }));
  if (layout.documentWidth > layout.viewportWidth + 1 || layout.mainScrollWidth > layout.mainClientWidth + 2) {
    throw new Error(`${name} horizontal overflow at ${layout.viewportWidth}px: document ${layout.documentWidth}px, main ${layout.mainScrollWidth}/${layout.mainClientWidth}px`);
  }
  const screenshotPath = path.join(output, `${slug(name)}-${viewportName}.png`);
  await page.screenshot({
    path: screenshotPath,
    fullPage: false,
    animations: "disabled",
  });
  const screenshots = [path.relative(root, screenshotPath)];
  if (name === "Dashboard") {
    await page.locator('[data-testid="stMain"]').evaluate((el) => {
      el.scrollTo({ top: Math.min(1200, el.scrollHeight), behavior: "instant" });
    });
    const detailPath = path.join(output, `dashboard-details-${viewportName}.png`);
    await page.screenshot({ path: detailPath, fullPage: false, animations: "disabled" });
    screenshots.push(path.relative(root, detailPath));
    await page.locator('[data-testid="stMain"]').evaluate((el) => el.scrollTo({ top: 0, behavior: "instant" }));
  }
  return { page: name, viewport: viewportName, layout, visibleJsonCount, controls, screenshots };
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  let browser;
  try {
  browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1 });
  const issues = [];
  page.on("console", (message) => {
    if (message.type() === "error") issues.push({ type: "console", text: message.text() });
  });
  page.on("pageerror", (error) => issues.push({ type: "pageerror", text: error.message }));
  page.on("requestfailed", (request) =>
    issues.push({ type: "requestfailed", url: request.url(), error: request.failure()?.errorText }),
  );
  page.on("response", (response) => {
    if (response.status() >= 400) issues.push({ type: "http", status: response.status(), url: response.url() });
  });

  const initialResponse = await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
  if (!initialResponse || initialResponse.status() !== 200) {
    throw new Error(`Application did not return HTTP 200: ${initialResponse?.status()}`);
  }
  await page.getByRole("heading", { name: /RodLab/i }).first().waitFor({ timeout: 45000 });
  await page.getByText("Project overview", { exact: false }).first().waitFor({ timeout: 45000 });
  await page.locator('[data-testid="stSidebar"] label').nth(1).waitFor({ state: "visible", timeout: 30000 });
  await waitForAppIdle(page);

  const pages = [];
  for (const [name, heading] of cases) {
    pages.push(await selectCase(page, name, heading, "desktop"));
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(500);
  for (const [name, heading] of cases) {
    pages.push(await selectCase(page, name, heading, "mobile"));
  }

  await page.setViewportSize({ width: 1440, height: 1000 });
  await openSidebar(page);
  await page.locator('[data-testid="stSidebar"]').getByText("Dashboard", { exact: true }).click();
  await page.getByText("Project overview", { exact: false }).first().waitFor({ state: "visible", timeout: 30000 });
  await waitForAppIdle(page);
  const dashboardText = await page.locator('[data-testid="stAppViewContainer"]').innerText();
  const report = {
    application: baseUrl,
    title: await page.title(),
    initialHttpStatus: initialResponse.status(),
    playwrightVersion: require("playwright/package.json").version,
    browserVersion: browser.version(),
    cases: pages,
    dashboardRawJsonVisible: dashboardText.includes('"attempted_geometries"') || dashboardText.includes('"INFEASIBLE_ON_TESTED_MESH"'),
    browserIssues: issues,
  };
  fs.writeFileSync(path.join(output, "browser-qa-report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  if (report.dashboardRawJsonVisible || issues.length) process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
