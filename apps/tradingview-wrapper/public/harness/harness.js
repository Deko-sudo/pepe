const wrapperOrigin = "http://127.0.0.1:4173";
const allowedEvents = new Set([
  "wrapper-document-ready",
  "provider-script-load-failed",
  "provider-frame-created",
  "provider-frame-document-loaded",
  "provider-frame-timeout",
  "wrapper-configuration-invalid",
]);
const frame = document.querySelector("[data-wrapper-frame]");
const result = document.querySelector("[data-result]");
const received = [];

function acceptsLifecycle(event) {
  const payload = event.data;
  return event.origin === wrapperOrigin && event.source === frame.contentWindow &&
    payload && typeof payload === "object" && Object.keys(payload).length === 3 &&
    payload.type === "pepe.tradingview-wrapper.lifecycle" && payload.version === 1 &&
    typeof payload.event === "string" && allowedEvents.has(payload.event);
}

window.addEventListener("message", (event) => {
  if (!acceptsLifecycle(event)) return;
  received.push(event.data.event);
  result.textContent = `Accepted lifecycle: ${event.data.event}`;
});

window.wrapperHarness = Object.freeze({
  received,
  acceptsLifecycle,
  mount(path) { frame.src = `${wrapperOrigin}${path}`; },
});
