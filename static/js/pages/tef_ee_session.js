/* =========================================================
   TEF – SESSION EXPRESSION ÉCRITE (EE)
   Fichier JS séparé – Production Ready
========================================================= */

(function () {
  /* =====================
     HELPERS
  ===================== */
  const $ = (s, p = document) => p.querySelector(s);
  const $$ = (s, p = document) => Array.from(p.querySelectorAll(s));

  const textEl = $("#text");
  const previewEl = $("#preview");
  const wcBadge = $("#wcBadge");
  const lenBadge = $("#lenBadge");

  const eeWordsEl = $("#ee_words");
  const eeAvgEl = $("#ee_avg");
  const eeConnEl = $("#ee_conn");
  const eeTtrEl = $("#ee_ttr");
  const eeScoreEl = $("#ee_score");
  const eeTipsEl = $("#ee_tips");

  const topicEl = $("#topic");
  const typeEl = $("#type");
  const toneEl = $("#tone");

  const btnAnalyze = $("#btnAnalyze");
  const btnClear = $("#btnClear");
  const btnCopy = $("#btnCopy");
  const btnTemplate = $("#btnTemplate");
  const btnPdf = $("#btnPdf");

  /* =====================
     CONNECTEURS
  ===================== */
  const CONNECTORS = [
    "premièrement",
    "d’une part",
    "d'autre part",
    "cependant",
    "en outre",
    "ainsi",
    "en conclusion",
    "par ailleurs",
    "en revanche",
    "toutefois",
  ];

  function getWords(str) {
    if (!str) return [];
    return str.toLowerCase().match(/[a-zà-öø-ÿ]+/gi) || [];
  }

  /* =====================
     ANALYSE TEXTE
  ===================== */
  function analyzeText() {
    const raw = textEl.value || "";
    const words = getWords(raw);
    const wordCount = words.length;
    const charCount = raw.length;

    wcBadge.textContent = `Mots : ${wordCount}`;
    lenBadge.textContent = `Longueur : ${charCount} caractères`;
    previewEl.textContent = raw.trim() || "Prévisualisation…";

    if (!wordCount) {
      eeWordsEl.textContent = "—";
      eeAvgEl.textContent = "—";
      eeConnEl.textContent = "—";
      eeTtrEl.textContent = "—";
      eeScoreEl.textContent = "—";
      eeTipsEl.innerHTML = "";
      return;
    }

    // Longueur
    eeWordsEl.textContent = wordCount;

    // Phrases
    const sentences = raw.split(/[.!?]+/).filter(Boolean);
    const avgSentence = sentences.length
      ? (wordCount / sentences.length).toFixed(1)
      : wordCount;
    eeAvgEl.textContent = avgSentence;

    // Connecteurs
    let connCount = 0;
    CONNECTORS.forEach((c) => {
      const re = new RegExp(`\\b${c}\\b`, "gi");
      const m = raw.match(re);
      if (m) connCount += m.length;
    });
    eeConnEl.textContent = connCount;

    // Richesse lexicale
    const unique = new Set(words);
    const ttr = (unique.size / wordCount).toFixed(2);
    eeTtrEl.textContent = ttr;

    // SCORE
    let score = 50;

    if (wordCount >= 120 && wordCount <= 180) score += 20;
    else if (wordCount >= 90 && wordCount <= 210) score += 10;
    else score -= 10;

    if (connCount >= 4) score += 10;
    else if (connCount >= 2) score += 5;
    else score -= 5;

    if (ttr >= 0.55) score += 10;
    else if (ttr >= 0.4) score += 5;
    else score -= 5;

    if (avgSentence >= 10 && avgSentence <= 22) score += 10;
    else score -= 5;

    score = Math.max(0, Math.min(100, score));
    eeScoreEl.textContent = score;

    /* =====================
       CONSEILS
    ===================== */
    const tips = [];

    if (wordCount < 120) tips.push("🔸 Texte trop court (minimum 120 mots).");
    if (wordCount > 180) tips.push("🔸 Texte trop long (max conseillé 180 mots).");

    if (connCount < 2)
      tips.push("🧩 Ajoute plus de connecteurs logiques.");
    else tips.push("✅ Bonne utilisation des connecteurs.");

    if (ttr < 0.4)
      tips.push("💡 Varie davantage ton vocabulaire.");

    if (avgSentence < 8)
      tips.push("✏️ Phrases trop courtes.");
    if (avgSentence > 25)
      tips.push("✏️ Phrases trop longues.");

    if (tips.length === 0)
      tips.push("🎉 Production bien équilibrée pour le TEF.");

    eeTipsEl.innerHTML = tips.join("<br>");
  }

  /* =====================
     TEMPLATE AUTO
  ===================== */
  function buildTemplate() {
    const topic = (topicEl.value || "le sujet demandé").toLowerCase();
    const type = typeEl.value;
    const tone = toneEl.value;

    let start = "Madame, Monsieur,";
    let end =
      "Je vous prie d’agréer, Madame, Monsieur, l’expression de mes salutations distinguées.";

    if (tone === "neutre") {
      start = "Bonjour,";
      end = "Cordialement,";
    } else if (tone === "amical") {
      start = "Salut,";
      end = "À bientôt,";
    }

    return `${start}

Je me permets de vous écrire au sujet de ${topic}.

Premièrement, ...
En outre, ...
Cependant, ...

En conclusion, je vous remercie de votre attention.

${end}
`;
  }

  /* =====================
     EVENTS
  ===================== */
  textEl.addEventListener("input", analyzeText);

  btnAnalyze.addEventListener("click", analyzeText);

  btnClear.addEventListener("click", () => {
    textEl.value = "";
    analyzeText();
  });

  btnCopy.addEventListener("click", () => {
    navigator.clipboard.writeText(textEl.value || "");
  });

  btnTemplate.addEventListener("click", () => {
    textEl.value = buildTemplate();
    analyzeText();
  });

  btnPdf.addEventListener("click", () => window.print());

  /* =====================
     INIT
  ===================== */
  analyzeText();
})();
