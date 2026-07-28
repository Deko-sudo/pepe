import { access, mkdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { chromium } from "playwright";

const appDirectory = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const repositoryRoot = path.resolve(appDirectory, "../..");
const outputDirectory = path.join(repositoryRoot, "artifacts/stage-8-prime-unit");
const baseUrl = process.env.STAGE8_SCREENSHOT_URL ?? "http://127.0.0.1:4000";
const systemChromium = process.env.PLAYWRIGHT_CHROMIUM_PATH ?? "/usr/bin/chromium";
const REFERENCE_TIME = Date.parse("2026-07-28T18:00:00Z");

const assets = [
  {
    id: "00000000-0000-4000-8000-000000000001",
    slug: "btc-usdt",
    symbol: "BTC/USDT",
    display_name: "Bitcoin",
    asset_class: "crypto_spot",
    market_type: "spot",
    base_asset: "BTC",
    quote_asset: "USDT",
    price_precision: 2,
    quantity_precision: 8,
    timezone: "UTC",
    calendar_kind: "always_open",
    trading_calendar: "crypto-24x7",
    metadata_version: 1,
    is_enabled: true,
  },
  {
    id: "00000000-0000-4000-8000-000000000002",
    slug: "eth-usdt",
    symbol: "ETH/USDT",
    display_name: "Ethereum",
    asset_class: "crypto_spot",
    market_type: "spot",
    base_asset: "ETH",
    quote_asset: "USDT",
    price_precision: 2,
    quantity_precision: 8,
    timezone: "UTC",
    calendar_kind: "always_open",
    trading_calendar: "crypto-24x7",
    metadata_version: 1,
    is_enabled: true,
  },
  {
    id: "00000000-0000-4000-8000-000000000003",
    slug: "xau-usd",
    symbol: "XAU/USD",
    display_name: "Золото",
    asset_class: "metal_fx_spot",
    market_type: "spot",
    base_asset: "XAU",
    quote_asset: "USD",
    price_precision: 2,
    quantity_precision: null,
    timezone: "UTC",
    calendar_kind: "provider_session",
    trading_calendar: "xau-usd-provider-session",
    metadata_version: 1,
    is_enabled: true,
  },
];

const priceBySlug = {
  "btc-usdt": 60350,
  "eth-usdt": 3325,
  "xau-usd": 2418,
};
const timeframeMilliseconds = {
  "1m": 60_000,
  "5m": 300_000,
  "15m": 900_000,
  "1h": 3_600_000,
  "4h": 14_400_000,
  "1d": 86_400_000,
};

function quote(slug, requestNumber) {
  const base = priceBySlug[slug];
  const price = base + requestNumber * 0.25;
  const observedAt = new Date(REFERENCE_TIME).toISOString();
  return {
    slug,
    price: price.toFixed(2),
    bid: null,
    ask: null,
    mid: null,
    open_24h: (price * 0.988).toFixed(2),
    high_24h: (price * 1.012).toFixed(2),
    low_24h: (price * 0.979).toFixed(2),
    change_24h: (price * 0.012).toFixed(2),
    change_percent_24h: "1.21",
    base_volume_24h: null,
    quote_volume_24h: null,
    market_status: "open",
    data_status: "fresh",
    observed_at: observedAt,
    received_at: observedAt,
    age_seconds: 0,
    provenance: {
      source_label: "Synthetic test source",
      venue_label: null,
      market_type: "spot",
      price_type: "last_trade",
      delay_class: "indicative",
    },
  };
}

function candles(slug, timeframe) {
  const duration = timeframeMilliseconds[timeframe];
  const now = REFERENCE_TIME;
  const latestOpen = Math.floor(now / duration) * duration - duration;
  const base = priceBySlug[slug];
  const instrumentSeed = slug === "btc-usdt" ? 0.35 : slug === "eth-usdt" ? 1.15 : 2.1;
  let previousClose = base * 0.975;
  return Array.from({ length: 120 }, (_, index) => {
    const openTime = latestOpen - (119 - index) * duration;
    const movement = Math.sin(index / 8 + instrumentSeed) * base * 0.0018
      + Math.cos(index / 19 + instrumentSeed) * base * 0.0011
      + base * 0.00022;
    const open = previousClose;
    const close = open + movement;
    const wick = base * (0.0007 + ((index * 7) % 5) * 0.00008);
    previousClose = close;
    return {
      open_time: new Date(openTime).toISOString(),
      close_time: new Date(openTime + duration).toISOString(),
      open: open.toFixed(8),
      high: (Math.max(open, close) + wick).toFixed(8),
      low: (Math.min(open, close) - wick).toFixed(8),
      close: close.toFixed(8),
      base_volume: null,
      quote_volume: null,
      trade_count: null,
      source_label: "Synthetic historical candle source",
      venue_label: null,
      received_at: new Date(openTime + duration).toISOString(),
    };
  });
}

async function resolveLaunchOptions() {
  try {
    await access(systemChromium);
    return { executablePath: systemChromium };
  } catch {
    return {};
  }
}

async function capture(page, filename) {
  await page.screenshot({ path: path.join(outputDirectory, filename), animations: "disabled" });
}

async function main() {
  await mkdir(outputDirectory, { recursive: true });
  const browser = await chromium.launch({
    ...(await resolveLaunchOptions()),
    headless: true,
    args: ["--disable-dev-shm-usage"],
  });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 1,
    locale: "ru-RU",
    reducedMotion: "reduce",
  });
  const page = await context.newPage();
  await page.clock.setFixedTime(REFERENCE_TIME);
  const runtimeErrors = [];
  const requestedSeries = new Set();
  let quoteRequestNumber = 0;

  page.on("pageerror", (error) => runtimeErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") runtimeErrors.push(message.text());
  });

  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/v1/users/me") {
      await route.fulfill({
        json: {
          id: "11111111-1111-4111-8111-111111111111",
          telegram_id: 1,
          first_name: "Stage 8",
          created_at: "2026-07-28T00:00:00Z",
          updated_at: "2026-07-28T00:00:00Z",
        },
      });
      return;
    }
    if (url.pathname === "/api/v1/assets") {
      await route.fulfill({ json: { items: assets, next_cursor: null } });
      return;
    }
    if (url.pathname === "/api/v1/assets/quotes") {
      quoteRequestNumber += 1;
      const slugs = url.searchParams.getAll("slug");
      await route.fulfill({
        json: {
          items: slugs.map((slug) => quote(slug, quoteRequestNumber)),
          unavailable: [],
          not_found: [],
        },
      });
      return;
    }
    const candleMatch = url.pathname.match(/^\/api\/v1\/market-data\/instruments\/([^/]+)\/candles$/);
    if (candleMatch) {
      const slug = decodeURIComponent(candleMatch[1]);
      const timeframe = url.searchParams.get("timeframe");
      requestedSeries.add(`${slug}:${timeframe}`);
      await route.fulfill({ json: { timeframe, items: candles(slug, timeframe) } });
      return;
    }
    await route.fulfill({ status: 404, json: { detail: "Not found" } });
  });

  async function waitForRequestedSeries(series) {
    for (let attempt = 0; attempt < 100; attempt += 1) {
      if (requestedSeries.has(series)) return;
      await page.waitForTimeout(25);
    }
    throw new Error(`Timed out waiting for safe mocked series ${series}`);
  }

  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByText("DEMO", { exact: true }).first().waitFor();
  await page.getByRole("img", { name: /График из 120 закрытых свечей/ }).waitFor();
  const scrollContainer = page.locator('main[class*="overflow-y-auto"]').first();

  const screenshots = [];
  await capture(page, "home-top-390x844.png");
  screenshots.push("home-top-390x844.png");

  await scrollContainer.evaluate((element) => element.scrollTo(0, element.scrollHeight));
  await page.waitForTimeout(100);
  await capture(page, "home-lower-390x844.png");
  screenshots.push("home-lower-390x844.png");

  await scrollContainer.evaluate((element) => element.scrollTo(0, 0));
  for (const [timeframe, filename] of [
    ["1m", "btc-1m-390x844.png"],
    ["1h", "btc-1h-390x844.png"],
    ["1d", "btc-1d-390x844.png"],
  ]) {
    await page.getByRole("button", { name: timeframe, exact: true }).click();
    await waitForRequestedSeries(`btc-usdt:${timeframe}`);
    await capture(page, filename);
    screenshots.push(filename);
  }

  for (const timeframe of ["5m", "15m", "4h"]) {
    await page.getByRole("button", { name: timeframe, exact: true }).click();
    await waitForRequestedSeries(`btc-usdt:${timeframe}`);
  }

  await page.getByRole("button", { name: "Выбрать Ethereum" }).click();
  await page.getByRole("button", { name: "1h", exact: true }).click();
  await waitForRequestedSeries("eth-usdt:1h");
  await capture(page, "eth-1h-390x844.png");
  screenshots.push("eth-1h-390x844.png");

  await page.getByRole("button", { name: "Выбрать Золото" }).click();
  await waitForRequestedSeries("xau-usd:1h");
  await capture(page, "xau-usd-1h-390x844.png");
  screenshots.push("xau-usd-1h-390x844.png");

  await page.getByRole("button", { name: "Выбрать Bitcoin" }).click();
  const overflow390 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  await page.setViewportSize({ width: 320, height: 844 });
  await capture(page, "home-320x844.png");
  screenshots.push("home-320x844.png");
  const overflow320 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);

  await page.setViewportSize({ width: 430, height: 932 });
  await capture(page, "home-430x932.png");
  screenshots.push("home-430x932.png");
  const overflow430 = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);

  await scrollContainer.evaluate((element) => element.scrollTo(0, element.scrollHeight));
  const navigationObscuresContent = await page.evaluate(() => {
    const navigation = document.querySelector("nav.bottom-nav-shell");
    const content = document.querySelector("main.market-home");
    if (!(navigation instanceof HTMLElement) || !(content instanceof HTMLElement)) return true;
    return content.getBoundingClientRect().bottom > navigation.getBoundingClientRect().top + 1;
  });

  const iconState = await page.evaluate(() => {
    const isLocalImage = (label) => {
      const image = document.querySelector(`img[aria-label="${label}"]`);
      if (!(image instanceof HTMLImageElement)) return false;
      return image.src.startsWith("data:image/svg+xml") || new URL(image.src).origin === window.location.origin;
    };
    return {
      bitcoin: isLocalImage("Bitcoin"),
      ethereum: isLocalImage("Ethereum"),
      gold: isLocalImage("Золото"),
      neutralStatus: Boolean(document.querySelector("svg.lucide-activity")),
      bottomNavigation: Boolean(document.querySelector("nav.bottom-nav-shell")),
    };
  });

  await page.getByRole("button", { name: "Открыть AI-поддержку" }).scrollIntoViewIfNeeded();
  await page.getByRole("button", { name: "Открыть AI-поддержку" }).click();
  const aiModalUsable = await page.getByRole("dialog").isVisible();
  await page.keyboard.press("Escape");

  const requiredSeries = [
    "btc-usdt:1m", "btc-usdt:5m", "btc-usdt:15m",
    "btc-usdt:1h", "btc-usdt:4h", "btc-usdt:1d",
    "eth-usdt:1h", "xau-usd:1h",
  ];
  const seriesVerified = requiredSeries.every((series) => requestedSeries.has(series));

  await browser.close();
  console.log(`screenshots=${screenshots.join(",")}`);
  console.log(`runtime_errors=${runtimeErrors.length}`);
  console.log(`series_verified=${seriesVerified}`);
  console.log(`overflow_390=${overflow390}`);
  console.log(`overflow_320=${overflow320}`);
  console.log(`overflow_430=${overflow430}`);
  console.log(`navigation_obscures_content=${navigationObscuresContent}`);
  console.log(`icon_state=${Object.entries(iconState).map(([name, state]) => `${name}:${state}`).join(",")}`);
  console.log(`icons_verified=${Object.values(iconState).every(Boolean)}`);
  console.log(`ai_modal_usable=${aiModalUsable}`);
  if (runtimeErrors.length || !seriesVerified || overflow320 || overflow390 || overflow430
    || navigationObscuresContent
    || !Object.values(iconState).every(Boolean) || !aiModalUsable) {
    process.exitCode = 1;
  }
}

await main();
