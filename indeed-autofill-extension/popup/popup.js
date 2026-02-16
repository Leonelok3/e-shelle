async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      { apiBaseUrl: "http://127.0.0.1:8000", leadId: 1 },
      resolve
    );
  });
}

async function setSettings(obj) {
  return new Promise((resolve) => chrome.storage.sync.set(obj, resolve));
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

document.addEventListener("DOMContentLoaded", async () => {
  const s = await getSettings();
  document.getElementById("leadId").value = s.leadId;

  document.getElementById("save").addEventListener("click", async () => {
    const leadId = parseInt(document.getElementById("leadId").value || "1", 10);
    await setSettings({ leadId });
    setStatus("✅ Lead ID enregistré");
  });

  document.getElementById("options").addEventListener("click", () => {
    chrome.runtime.openOptionsPage();
  });

  document.getElementById("fill").addEventListener("click", async () => {
    const tab = await getActiveTab();
    if (!tab || !tab.id) return;

    const s2 = await getSettings();
    if (!tab.url || !tab.url.includes("indeed")) {
      setStatus("⚠️ Ouvre une page Indeed d’abord.");
      return;
    }

    setStatus("⏳ Auto-remplissage…");
    chrome.tabs.sendMessage(
      tab.id,
      { type: "INDEED_AUTOFILL", apiBaseUrl: s2.apiBaseUrl, leadId: s2.leadId },
      (resp) => {
        if (chrome.runtime.lastError) {
          setStatus("❌ Impossible de contacter la page (reload Indeed).");
          return;
        }
        setStatus(resp?.ok ? "✅ Champs remplis (vérifie puis soumets)" : "⚠️ Partiel: " + (resp?.error || ""));
      }
    );
  });
});
