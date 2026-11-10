const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || "playwright");

const root = path.resolve(__dirname, "..");
const output = path.join(root, "outputs", "phase4-visual-qa");
const baseUrl = process.env.PHASE4_URL || "http://localhost:8505";
const executablePath = process.env.PHASE4_CHROME_PATH;
const playwrightModule = process.env.PLAYWRIGHT_MODULE || "playwright";
const cases = [
  ["Dashboard", "Project overview"],
  ["Legacy Geometry Editor", "Define the authoritative CAD solid"],
  ["Engine Loading", "Loads with explicit provenance"],
  ["Simulation", "Linear elastic simulation"],
  ["Optimization & Feasibility", "Optimization & feasibility evidence"],
  ["Results & Comparison", "Refined candidate results"],
  ["Model Analytics", "Phase 4 exploratory model evaluation"],
  ["Reports & Downloads", "Reports and reproducible project data"],
  ["Design Studio", "Parametric geometry families"],
  ["Design Space Explorer", "Material distribution and design-space evidence"],
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

async function mobileSidebarState(page) {
  return page.locator('[data-testid="stSidebar"]').evaluate((sidebar) => {
    const rect = sidebar.getBoundingClientRect();
    const style = getComputedStyle(sidebar);
    const visible = style.visibility !== "hidden" && style.display !== "none" &&
      Number(style.opacity || 1) > 0 && rect.width > 0 && rect.right > 0 && rect.left < innerWidth;
    const main = document.querySelector('[data-testid="stMain"]')?.getBoundingClientRect();
    const overlapsMain = Boolean(main && visible && rect.right > main.left && rect.left < main.right);
    return {
      visible,
      overlapsMain,
      left: rect.left,
      right: rect.right,
      width: rect.width,
      transform: style.transform,
    };
  });
}

async function verifyControls(page, name) {
  if (name === "Legacy Geometry Editor") {
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
  if (name === "Optimization & Feasibility") {
    if (!(await page.getByText("Lowest-mass recorded-screen candidates", { exact: true }).count())) throw new Error("Missing recorded-screen ranking");
    return ["ranked actual CAD/FEA candidates", "unqualified status shown"];
  }
  if (name === "Results & Comparison") {
    if (!(await page.getByRole("combobox", { name: "Refined candidate" }).count())) throw new Error("Missing curated refined-candidate selector");
    if (!(await page.getByText("Peak unaveraged IP stress", { exact: false }).count())) throw new Error("Missing actual solver field metrics");
    return ["candidate selector", "mesh and load-case controls", "actual solver-field view"];
  }
  if (name === "Model Analytics") {
    if (!(await page.getByRole("combobox", { name: "Prediction records" }).count())) throw new Error("Missing Phase 4 prediction-record selector");
    if ((await page.locator('[data-testid="stPlotlyChart"]').count()) < 2) throw new Error("Missing actual row-level prediction and residual charts");
    if (!(await page.getByText("Historical Phase 3 evaluation", { exact: true }).count())) throw new Error("Missing separated historical Phase 3 section");
    return ["Phase 4 grouped evaluation", "historical Phase 3 section", "historical Phase 2 section"];
  }
  if (name === "Design Studio") {
    const family = page.getByRole("combobox", { name: "Geometry family" });
    await family.click();
    const option = page.getByRole("option", { name: "Tapered I section" });
    await option.waitFor({ state: "visible", timeout: 10000 });
    await option.click();
    await waitForAppIdle(page);
    if ((await family.inputValue()) !== "Tapered I section") throw new Error("Geometry-family selection did not update");
    return ["selected Tapered I section without submitting CAD/FEA"];
  }
  if (name === "Design Space Explorer") {
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
  const currentLabel = page.locator('[data-testid="stSidebarNav"] a[aria-current="page"]');
  const alreadySelected =
    (await currentLabel.count()) > 0 &&
    (await currentLabel.innerText()).trim() === name;
  if (!alreadySelected) {
    await openSidebar(page);
    const options = page.locator('[data-testid="stSidebar"]').getByText(name, { exact: true });
    await options.first().waitFor({ state: "visible", timeout: 30000 });
    if (await options.count() !== 1) {
      throw new Error(`Expected one sidebar option for ${name}; found ${await options.count()}`);
    }
    await options.click();
  }
  await page.getByText(expectedText, { exact: false }).first().waitFor({ state: "visible", timeout: 30000 });
  await waitForAppIdle(page);
  const viewportWidth = await page.evaluate(() => window.innerWidth);
  let sidebar = await mobileSidebarState(page);
  if (viewportWidth <= 768) {
    await page.waitForFunction(
      () => {
        const element = document.querySelector('[data-testid="stSidebar"]');
        if (!element) return true;
        const rect = element.getBoundingClientRect();
        const style = getComputedStyle(element);
        return style.visibility === "hidden" || style.display === "none" ||
          Number(style.opacity || 1) === 0 || rect.width === 0 || rect.right <= 0;
      },
      null,
      { timeout: 5000 },
    );
    sidebar = await mobileSidebarState(page);
    if (sidebar.visible) {
      throw new Error(`${name}: mobile sidebar remained open after page selection (${JSON.stringify(sidebar)})`);
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
    mainHeading: (() => {
      const element = document.querySelector(
        '[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3',
      );
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom };
    })(),
  }));
  if (layout.documentWidth > layout.viewportWidth + 1 || layout.mainScrollWidth > layout.mainClientWidth + 2) {
    throw new Error(`${name} horizontal overflow at ${layout.viewportWidth}px: document ${layout.documentWidth}px, main ${layout.mainScrollWidth}/${layout.mainClientWidth}px`);
  }
  if (!layout.mainHeading || layout.mainHeading.left < 0 || layout.mainHeading.right > layout.viewportWidth + 1) {
    throw new Error(`${name}: main heading is clipped at ${layout.viewportWidth}px`);
  }
  if (viewportWidth <= 768 && sidebar.overlapsMain) {
    throw new Error(`${name}: sidebar occludes main content at ${viewportWidth}px`);
  }
  const screenshotPath = path.join(output, `${slug(name)}-${viewportName}-viewport.png`);
  await page.screenshot({
    path: screenshotPath,
    fullPage: false,
    animations: "disabled",
  });
  const fullPagePath = path.join(output, `${slug(name)}-${viewportName}-full.png`);
  await page.screenshot({ path: fullPagePath, fullPage: true, animations: "disabled" });
  const screenshots = [path.relative(root, screenshotPath), path.relative(root, fullPagePath)];
  if (name === "Dashboard") {
    await page.locator('[data-testid="stMain"]').evaluate((el) => {
      el.scrollTo({ top: Math.min(1200, el.scrollHeight), behavior: "instant" });
    });
    const detailPath = path.join(output, `dashboard-details-${viewportName}.png`);
    await page.screenshot({ path: detailPath, fullPage: false, animations: "disabled" });
    screenshots.push(path.relative(root, detailPath));
    await page.locator('[data-testid="stMain"]').evaluate((el) => el.scrollTo({ top: 0, behavior: "instant" }));
  }
  return { page: name, viewport: viewportName, layout, sidebar, visibleJsonCount, controls, screenshots };
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  let browser;
  try {
  browser = await chromium.launch({ headless: true, ...(executablePath ? { executablePath } : {}) });
  const issues = [];
  const viewports = [
    [390, 844],
    [768, 1024],
    [1024, 768],
    [1440, 1000],
    [1920, 1080],
  ];
  const pages = [];
  let initialHttpStatus = null;
  let appTitle = null;
  for (const [width, height] of viewports) {
    const page = await browser.newPage({
      viewport: { width, height },
      deviceScaleFactor: 1,
      acceptDownloads: true,
    });
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
    const response = await page.goto(baseUrl, { waitUntil: "domcontentloaded", timeout: 60000 });
    if (!response || response.status() !== 200) {
      throw new Error(`Application did not return HTTP 200 at ${width}px: ${response?.status()}`);
    }
    if (initialHttpStatus === null) {
      initialHttpStatus = response.status();
      appTitle = await page.title();
    }
    await page.locator(".rodlab-brand").waitFor({ timeout: 45000 });
    await page.getByText("Project overview", { exact: false }).first().waitFor({ timeout: 45000 });
    await page.locator('[data-testid="stSidebarNav"]').waitFor({ state: "attached", timeout: 30000 });
    await waitForAppIdle(page);
    const viewportName = `${width}x${height}`;
    for (const [name, heading] of cases) {
      pages.push(await selectCase(page, name, heading, viewportName));
    }
    await page.close();
  }
  const report = {
    application: baseUrl,
    title: appTitle,
    initialHttpStatus,
    playwrightVersion: require(`${playwrightModule}/package.json`).version,
    browserVersion: browser.version(),
    cases: pages,
    dashboardRawJsonVisible: pages.some(
      (item) => item.page === "Dashboard" && item.visibleJsonCount > 0,
    ),
    browserIssues: issues,
  };
  const outputSha = require("node:crypto").createHash("sha256").update(JSON.stringify(report)).digest("hex");
  report.reportSha256 = outputSha;
  fs.writeFileSync(path.join(output, "browser-qa-report.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify({ cases: pages.length, issues: issues.length, reportSha256: outputSha }, null, 2));
  if (report.dashboardRawJsonVisible || issues.length) process.exitCode = 1;
  } finally {
    if (browser) await browser.close();
  }
})().catch((error) => {
  console.error(error.stack || error);
  process.exitCode = 1;
});
