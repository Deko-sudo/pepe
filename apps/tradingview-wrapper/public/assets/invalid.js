(() => {
  "use strict";
  window.parent.postMessage({
    type: "pepe.tradingview-wrapper.lifecycle",
    version: 1,
    event: "wrapper-configuration-invalid",
  }, window.PEPE_TRADINGVIEW_WRAPPER_RUNTIME.harnessOrigin);
})();
