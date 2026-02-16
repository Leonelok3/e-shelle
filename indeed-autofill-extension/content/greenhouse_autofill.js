function getParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

function setValue(el, value) {
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

async function fetchAutofill(apiBaseUrl, leadId) {
  const url = `${String(apiBaseUrl || "").replace(/\/$/, "")}/jobs/api/indeed/autofill/${leadId}/`;
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new Error("API error " + res.status);
  return await res.json();
}

function highlightSubmitAndFile() {
  const submitBtn =
    document.querySelector('button[type="submit"]') ||
    document.querySelector('input[type="submit"]');

  if (submitBtn) {
    submitBtn.style.outline = "4px solid #16a34a";
    submitBtn.style.borderRadius = "12px";
    try { submitBtn.scrollIntoView({ behavior: "smooth", block: "center" }); } catch (e) {}
  }

  const fileInput = document.querySelector('input[type="file"]');
  if (fileInput) {
    fileInput.style.outline = "4px solid orange";
    fileInput.style.borderRadius = "12px";
  }
}

function fillGreenhouse(data) {
  const c = data.candidate || {};
  const a = data.application || {};
  let filled = 0;

  // Greenhouse a souvent ces name:
  // first_name, last_name, email, phone, location, linkedin, website
  const full = (c.full_name || "").trim();
  const parts = full.split(" ");
  const first = parts[0] || "";
  const last = parts.slice(1).join(" ") || "";

  filled += setValue(document.querySelector('input[name="first_name"]'), first) ? 1 : 0;
  filled += setValue(document.querySelector('input[name="last_name"]'), last) ? 1 : 0;
  filled += setValue(document.querySelector('input[name="email"]'), c.email) ? 1 : 0;
  filled += setValue(document.querySelector('input[name="phone"]'), c.phone) ? 1 : 0;

  // LinkedIn / Website
  filled += setValue(document.querySelector('input[name*="linkedin"]'), c.linkedin) ? 1 : 0;
  filled += setValue(document.querySelector('input[name*="website"]'), c.portfolio) ? 1 : 0;

  // Cover letter (textarea)
  const cover =
    document.querySelector('textarea[name*="cover"]') ||
    document.querySelector('textarea[name*="letter"]') ||
    document.querySelector("textarea");

  if (cover) filled += setValue(cover, a.cover_letter) ? 1 : 0;

  highlightSubmitAndFile();
  return filled;
}

function injectButton() {
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

  btn.addEventListener("click", async () => {
    try {
      const leadId = parseInt(getParam("imm97_lead") || "0", 10);
      const apiBaseUrl = getParam("imm97_api") || "http://127.0.0.1:8000";
      if (!leadId) return alert("Lead ID manquant (imm97_lead). Ouvre via ton bouton Django.");

      const data = await fetchAutofill(apiBaseUrl, leadId);
      const filled = fillGreenhouse(data);
      alert(`✅ AutoFill Greenhouse terminé. Champs remplis: ${filled}. Vérifie puis soumets.`);
    } catch (e) {
      alert("❌ AutoFill erreur: " + String(e?.message || e));
    }
  });

  document.body.appendChild(btn);
}

injectButton();
setTimeout(injectButton, 1500);
setTimeout(injectButton, 3000);
