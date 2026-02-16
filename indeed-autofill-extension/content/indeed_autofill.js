// ===============================
// Immigration97 - Indeed AutoFill
// content/indeed_autofill.js
// ===============================

function getParam(name) {
  const url = new URL(window.location.href);
  return url.searchParams.get(name);
}

function byLabelText(labelText) {
  const labels = Array.from(document.querySelectorAll("label"));
  const label = labels.find(l =>
    (l.textContent || "").toLowerCase().includes(labelText.toLowerCase())
  );
  if (!label) return null;

  const forId = label.getAttribute("for");
  if (forId) return document.getElementById(forId);

  // sinon input dans le label
  return label.querySelector("input, textarea, select");
}

function byNameOrIdContains(parts) {
  const all = Array.from(document.querySelectorAll("input, textarea, select"));
  return (
    all.find(el => {
      const n = (el.getAttribute("name") || "").toLowerCase();
      const i = (el.getAttribute("id") || "").toLowerCase();
      const a = (el.getAttribute("aria-label") || "").toLowerCase();
      const p = (el.getAttribute("placeholder") || "").toLowerCase();
      return parts.some(x => n.includes(x) || i.includes(x) || a.includes(x) || p.includes(x));
    }) || null
  );
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
  const res = await fetch(url, { credentials: "include" }); // utilise la session Django (login)
  if (!res.ok) throw new Error("API error " + res.status);
  return await res.json();
}

function highlightSubmitAndFile() {
  // ✅ Highlight submit
  const submitBtn =
    document.querySelector('button[type="submit"]') ||
    document.querySelector('button[aria-label*="Soumettre"]') ||
    document.querySelector('button[aria-label*="soumettre"]') ||
    document.querySelector('button[aria-label*="Submit"]') ||
    document.querySelector('button[aria-label*="submit"]');

  if (submitBtn) {
    submitBtn.style.outline = "4px solid #16a34a";
    submitBtn.style.borderRadius = "12px";
    try {
      submitBtn.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (e) {}
  }

  // ✅ Highlight file input (CV upload)
  const fileInput = document.querySelector('input[type="file"]');
  if (fileInput) {
    fileInput.style.outline = "4px solid orange";
    fileInput.style.borderRadius = "12px";
    try {
      fileInput.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (e) {}
  }
}

function assistCvUpload(candidate) {
  const fileInput = document.querySelector('input[type="file"]');
  if (!fileInput) return;

  // 1) mettre en évidence
  fileInput.style.outline = "4px solid orange";
  fileInput.style.borderRadius = "12px";

  // 2) essayer d'ouvrir le sélecteur (marche uniquement si appelé depuis un clic utilisateur)
  try {
    fileInput.click();
  } catch (e) {}

  // 3) si on a une URL CV, afficher un petit panneau “Télécharger”
  const cvUrl = (candidate && candidate.cv_file_url) ? String(candidate.cv_file_url) : "";
  if (!cvUrl) return;

  if (document.getElementById("imm97-cv-panel")) return;

  const panel = document.createElement("div");
  panel.id = "imm97-cv-panel";
  panel.style.position = "fixed";
  panel.style.bottom = "70px";
  panel.style.right = "18px";
  panel.style.zIndex = "999999";
  panel.style.background = "white";
  panel.style.border = "1px solid #e5e7eb";
  panel.style.borderRadius = "12px";
  panel.style.padding = "10px 12px";
  panel.style.boxShadow = "0 10px 22px rgba(0,0,0,.18)";
  panel.style.maxWidth = "260px";
  panel.style.fontFamily = "Arial, sans-serif";
  panel.style.fontSize = "12px";

  panel.innerHTML = `
    <div style="font-weight:700;margin-bottom:6px;">CV (Upload assisté)</div>
    <div style="color:#374151;margin-bottom:8px;">
      Si tu n'as pas ton fichier sous la main, télécharge-le puis upload sur Indeed.
    </div>
    <a id="imm97-cv-download" href="${cvUrl}" target="_blank" rel="noopener"
       style="display:inline-block;padding:8px 10px;border-radius:10px;background:#111827;color:#fff;text-decoration:none;">
      Télécharger mon CV
    </a>
    <button id="imm97-cv-close"
       style="margin-left:8px;padding:8px 10px;border-radius:10px;border:1px solid #e5e7eb;background:#fff;cursor:pointer;">
      Fermer
    </button>
  `;

  document.body.appendChild(panel);

  document.getElementById("imm97-cv-close")?.addEventListener("click", () => {
    panel.remove();
  });
}


function fillIndeed(data) {
  const c = data.candidate || {};
  const a = data.application || {};

  let filled = 0;

  // Nom
  filled += setValue(
    byLabelText("Nom") || byNameOrIdContains(["name", "fullname", "full name"]),
    c.full_name
  )
    ? 1
    : 0;

  // Email
  filled += setValue(byLabelText("Email") || byNameOrIdContains(["email"]), c.email) ? 1 : 0;

  // Téléphone
  filled += setValue(
    byLabelText("Téléphone") || byNameOrIdContains(["phone", "mobile", "tel"]),
    c.phone
  )
    ? 1
    : 0;

  // Ville / Localisation
  filled += setValue(
    byLabelText("Ville") || byNameOrIdContains(["city", "location"]),
    c.city
  )
    ? 1
    : 0;

  // LinkedIn / Portfolio
  filled += setValue(byLabelText("LinkedIn") || byNameOrIdContains(["linkedin"]), c.linkedin)
    ? 1
    : 0;

  // ⚠️ "url" est très large => on le garde mais ça peut remplir un champ non voulu
  // si tu veux être plus strict plus tard, on réduira à ["portfolio","website"]
  filled += setValue(
    byLabelText("Portfolio") || byNameOrIdContains(["portfolio", "website", "url"]),
    c.portfolio
  )
    ? 1
    : 0;

  // Lettre / Cover letter (textarea)
  const cover =
    byLabelText("Lettre") ||
    byLabelText("Cover") ||
    byNameOrIdContains(["cover", "letter", "motivation", "message"]);

  if (cover && cover.tagName.toLowerCase() === "textarea") {
    filled += setValue(cover, a.cover_letter) ? 1 : 0;
  }

  // Réponses génériques (si tu as “salaire”, “disponibilité”, etc.)
  const answers = a.answers || {};
  for (const [k, v] of Object.entries(answers)) {
    const key = String(k).toLowerCase();
    const field = byNameOrIdContains([key]);
    if (field) {
      if (setValue(field, v)) filled += 1;
    }
  }

  // ✅ On guide l’utilisateur vers Submit et Upload
  highlightSubmitAndFile();
  assistCvUpload(c);


  return filled;
}

// ==================================
// ✅ Étape 3 : bouton flottant Indeed
// ==================================
function injectFloatingButton() {
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

      if (!leadId) {
        alert("Lead ID manquant. Ouvre Indeed depuis ton bouton Django (Postuler AutoFill).");
        return;
      }

      const data = await fetchAutofill(apiBaseUrl, leadId);
      const filled = fillIndeed(data);

      alert(`✅ AutoFill terminé. Champs remplis: ${filled}. Vérifie puis clique Soumettre.`);
    } catch (e) {
      alert("❌ AutoFill erreur: " + String(e?.message || e));
    }
  });

  document.body.appendChild(btn);
}

// Inject direct + aussi après chargements dynamiques
injectFloatingButton();
setTimeout(injectFloatingButton, 1500);
setTimeout(injectFloatingButton, 3000);

// ==================================
// ✅ Toujours compatible popup (étape 2)
// ==================================
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  (async () => {
    if (!msg || msg.type !== "INDEED_AUTOFILL") return;

    try {
      // ✅ Étape 2 : si msg.leadId/apiBaseUrl manquants, on prend depuis l’URL
      const leadId =
        msg.leadId ||
        parseInt(getParam("imm97_lead") || "0", 10);

      const apiBaseUrl =
        msg.apiBaseUrl ||
        getParam("imm97_api") ||
        "http://127.0.0.1:8000";

      if (!leadId) {
        sendResponse({ ok: false, error: "Lead ID manquant (imm97_lead)." });
        return;
      }

      const data = await fetchAutofill(apiBaseUrl, leadId);
      const filled = fillIndeed(data);

      sendResponse({ ok: true, filled });
    } catch (e) {
      sendResponse({ ok: false, error: String(e?.message || e) });
    }
  })();

  return true; // async
});
