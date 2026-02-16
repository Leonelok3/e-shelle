async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ apiBaseUrl: "http://127.0.0.1:8000" }, resolve);
  });
}

async function setSettings(obj) {
  return new Promise((resolve) => chrome.storage.sync.set(obj, resolve));
}

document.addEventListener("DOMContentLoaded", async () => {
  const s = await getSettings();
  document.getElementById("apiBaseUrl").value = s.apiBaseUrl;

  document.getElementById("save").addEventListener("click", async () => {
    const apiBaseUrl = document.getElementById("apiBaseUrl").value.trim();
    await setSettings({ apiBaseUrl });
    document.getElementById("status").textContent = "✅ Enregistré";
  });
});
