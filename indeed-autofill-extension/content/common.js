export function getParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

export async function fetchAutofill(apiBaseUrl, leadId) {
  const url = `${String(apiBaseUrl || "").replace(/\/$/, "")}/jobs/api/indeed/autofill/${leadId}/`;
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new Error("API error " + res.status);
  return await res.json();
}

export function setValue(el, value) {
  if (!el || value == null) return false;
  const v = String(value);
  try {
    el.focus();
    el.value = v;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return true;
  } catch (e) {
    return false;
  }
}

export function highlightSubmitAndFile() {
  const submitBtn =
    document.querySelector('button[type="submit"]') ||
    document.querySelector('input[type="submit"]') ||
    document.querySelector('button[aria-label*="Submit"]') ||
    document.querySelector('button[aria-label*="Soumettre"]');

  if (submitBtn) {
    submitBtn.style.outline = "4px solid #16a34a";
    submitBtn.style.borderRadius = "12px";
    try { submitBtn.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {}
  }

  const fileInput = document.querySelector('input[type="file"]');
  if (fileInput) {
    fileInput.style.outline = "4px solid orange";
    fileInput.style.borderRadius = "12px";
    try { fileInput.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {}
  }
}

export function injectFloatingButton(onClick) {
  if (document.getElementById("imm97-autofill-btn")) return;

  const btn = document.createElement("button");
  btn.id = "imm97-autofill-btn";
  btn.textContent = "AutoFill Immigration97";

  btn.style.position = "fixed";
  btn.style.bottom = "18px";
  btn.style.right = "18px";
  btn.style.zIndex = "999999";
  btn.style.padding = "10px 14px";
  btn.style.borderRadius = "12px";
  btn.style.border = "0";
  btn.style.cursor = "pointer";
  btn.style.fontWeight = "700";
  btn.style.background = "#16a34a";
  btn.style.color = "white";
  btn.style.boxShadow = "0 10px 22px rgba(0,0,0,.25)";

  btn.addEventListener("click", onClick);
  document.body.appendChild(btn);
}
