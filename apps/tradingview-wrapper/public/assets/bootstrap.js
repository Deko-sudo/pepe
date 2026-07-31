(() => {
  "use strict";
  const TYPE = "pepe.tradingview-wrapper.lifecycle";
  const VERSION = 1;
  const ALLOWED = new Set([
    "wrapper-document-ready",
    "provider-script-load-failed",
    "provider-frame-created",
    "provider-frame-document-loaded",
    "provider-frame-timeout",
    "wrapper-configuration-invalid",
  ]);
  const SCRIPT_URL = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
  const timeoutMs = 12000;
  let emitted = new Set();
  let timerId = null;

  function emit(event) {
    if (!ALLOWED.has(event) || emitted.has(event)) return;
    emitted.add(event);
    window.parent.postMessage({ type: TYPE, version: VERSION, event }, "*");
  }

  function showError() {
    document.querySelector("[data-loading-state]")?.setAttribute("hidden", "");
    document.querySelector("[data-error-state]")?.removeAttribute("hidden");
  }

  function invalid() {
    emit("wrapper-configuration-invalid");
    showError();
  }

  function validConfig(config) {
    const mappings = {
      "btc-usdt": "BINANCE:BTCUSDT",
      "eth-usdt": "BINANCE:ETHUSDT",
      "xau-usd": "OANDA:XAUUSD",
    };
    const timeframeMappings = { "1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "D" };
    return config && config.scriptUrl === SCRIPT_URL &&
      mappings[config.slug] === config.symbol && timeframeMappings[config.timeframe] === config.interval;
  }

  function observeFrame(container) {
    const observer = new MutationObserver(() => {
      const frame = container.querySelector("iframe");
      if (!frame || emitted.has("provider-frame-created")) return;
      emit("provider-frame-created");
      frame.addEventListener("load", () => {
        emit("provider-frame-document-loaded");
        if (timerId !== null) window.clearTimeout(timerId);
      }, { once: true });
    });
    observer.observe(container, { childList: true, subtree: true });
  }

  function initialize() {
    emit("wrapper-document-ready");
    if (window.location.search || window.location.hash) return invalid();
    const configNode = document.getElementById("wrapper-config");
    let config;
    try { config = JSON.parse(configNode?.textContent ?? ""); } catch { return invalid(); }
    if (!validConfig(config)) return invalid();
    const container = document.querySelector("[data-chart-container]");
    if (!container) return invalid();
    observeFrame(container);
    timerId = window.setTimeout(() => {
      if (!emitted.has("provider-frame-document-loaded")) { emit("provider-frame-timeout"); showError(); }
    }, timeoutMs);
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.type = "text/javascript";
    script.text = JSON.stringify({
      autosize: true, symbol: config.symbol, interval: config.interval, theme: "dark", locale: "en",
      timezone: "Etc/UTC", allow_symbol_change: false, hide_side_toolbar: true,
      hide_top_toolbar: true, save_image: false, withdateranges: false, watchlist: [],
    });
    script.addEventListener("error", () => {
      if (timerId !== null) window.clearTimeout(timerId);
      emit("provider-script-load-failed");
      showError();
    }, { once: true });
    container.append(script);
  }

  document.addEventListener("DOMContentLoaded", initialize, { once: true });
})();
