export function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

export async function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      {
        apiBaseUrl: "http://127.0.0.1:8000",
        leadId: 1
      },
      resolve
    );
  });
}

export async function setSettings(obj) {
  return new Promise((resolve) => {
    chrome.storage.sync.set(obj, resolve);
  });
}
