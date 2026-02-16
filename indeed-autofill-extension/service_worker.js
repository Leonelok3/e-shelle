chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // Juste un relais si besoin plus tard
  if (msg && msg.type === "PING") {
    sendResponse({ ok: true });
  }
});
