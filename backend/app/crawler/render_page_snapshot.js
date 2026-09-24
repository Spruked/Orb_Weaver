const { chromium } = require("playwright");

const url = process.argv[2];
const timeoutMs = Number(process.argv[3] || 15000);
const executablePath = process.env.CHROME_PATH || process.env.CHROME_BIN || undefined;

if (!url) {
  process.stderr.write("A URL is required\n");
  process.exit(2);
}

(async () => {
  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: [
      "--no-sandbox",
      "--disable-gpu",
      "--disable-dev-shm-usage",
      "--disable-background-networking",
      "--mute-audio",
    ],
  });

  try {
    const context = await browser.newContext({
      reducedMotion: "reduce",
      serviceWorkers: "block",
    });
    const page = await context.newPage();
    const diagnostics = {
      console_errors: [],
      page_errors: [],
      failed_requests: [],
      failed_responses: [],
    };
    page.on("console", (message) => {
      if (message.type() === "error" && diagnostics.console_errors.length < 50) {
        diagnostics.console_errors.push(message.text());
      }
    });
    page.on("pageerror", (error) => {
      if (diagnostics.page_errors.length < 50) {
        diagnostics.page_errors.push(String(error && error.stack ? error.stack : error));
      }
    });
    page.on("requestfailed", (request) => {
      if (diagnostics.failed_requests.length < 50) {
        diagnostics.failed_requests.push({ url: request.url(), error: request.failure() && request.failure().errorText });
      }
    });
    page.on("response", (response) => {
      if (response.status() >= 400 && diagnostics.failed_responses.length < 50) {
        diagnostics.failed_responses.push({ url: response.url(), status: response.status() });
      }
    });
    page.setDefaultTimeout(timeoutMs);
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    // Allow hydration and route content to settle, but never wait on audio,
    // analytics, WebSockets, or an application-owned tour timer.
    await page.waitForTimeout(Math.min(2000, Math.max(500, timeoutMs / 5)));
    const html = await page.content();
    const bodyText = await page.locator("body").innerText().catch(() => "");
    const rootText = await page.locator("#root, #app, [data-reactroot]").first().innerText().catch(() => "");
    const diagnosticsEnvelope = {
      ...diagnostics,
      body_text_length: bodyText.length,
      root_text_length: rootText.length,
      has_root_mount: Boolean(await page.locator("#root, #app, [data-reactroot]").count()),
      html_length: html.length,
    };
    process.stderr.write(`ORB_RENDER_DIAGNOSTICS:${JSON.stringify(diagnosticsEnvelope)}\n`);
    process.stdout.write(html);
  } finally {
    await browser.close();
  }
})().catch((error) => {
  process.stderr.write(`${error && error.stack ? error.stack : error}\n`);
  process.exit(1);
});
