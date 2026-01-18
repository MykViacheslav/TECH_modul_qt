// ===== 00_readyflag.js =====
// Must be FIRST in bundle:
(() => {
  try { window.__APP_READY__ = "BOOTING"; } catch(e) {}
})();
