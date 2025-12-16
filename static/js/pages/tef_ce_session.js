/* =========================================================
   TEF – SESSION COMPRÉHENSION ÉCRITE (CE)
   Fichier JS séparé – Production Ready
   Dépend de :
   - const EXERCISES injecté depuis Django
========================================================= */

(function () {
  if (typeof EXERCISES === "undefined") {
    console.error("EXERCISES non défini (Django)");
    return;
  }

  let index = 0;
  let good = 0;
  let bad = 0;
  let answered = 0;
  let hasAnswered = false;

  // TIMER
  let timer = 0;
  let timerInterval = null;

  // DOM
  const qIndexEl = document.getElementById("q-index");
  const instructionEl = document.getElementById("instruction");
  const textEl = document.getElementById("text");
  const questionEl = document.getElementById("question");
  const optionsEl = document.getElementById("options");
  const explanationBox = document.getElementById("explanation");
  const explanationBody = document.getElementById("explanation-body");

  const goodEl = document.getElementById("good-count");
  const badEl = document.getElementById("bad-count");
  const answeredEl = document.getElementById("answered-count");
  const scoreBottomEl = document.getElementById("score-bottom");

  const timerEl = document.getElementById("timer");

  const nextBtn = document.getElementById("next-btn");
  const restartBtn = document.getElementById("restart-btn");

  /* =====================
     TIMER
  ===================== */
  function startTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      timer++;
      timerEl.textContent = formatTime(timer);
    }, 1000);
  }

  function resetTimer() {
    if (timerInterval) clearInterval(timerInterval);
    timer = 0;
    timerEl.textContent = "00:00";
  }

  function formatTime(sec) {
    const m = String(Math.floor(sec / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    return `${m}:${s}`;
  }

  /* =====================
     RENDER QUESTION
  ===================== */
  function renderQuestion() {
    if (!EXERCISES.length) {
      instructionEl.textContent =
        "Aucun exercice n’est encore configuré pour cette leçon.";
      return;
    }

    const ex = EXERCISES[index];
    hasAnswered = false;

    qIndexEl.textContent = index + 1;
    instructionEl.textContent =
      ex.instruction || "Lis le texte puis réponds à la question.";

    textEl.textContent = ex.text || "";
    questionEl.textContent = ex.question || "";

    explanationBox.style.display = "none";
    explanationBody.textContent = "";

    optionsEl.innerHTML = "";

    Object.entries(ex.options || {}).forEach(([key, label]) => {
      const row = document.createElement("div");
      row.className = "option-item";
      row.dataset.key = key;

      row.innerHTML = `
        <div>
          <strong>${key}.</strong> ${label}
        </div>
        <span class="option-mark"></span>
      `;

      row.addEventListener("click", () =>
        handleAnswer(row, key, ex)
      );

      optionsEl.appendChild(row);
    });

    updateStats();
  }

  /* =====================
     HANDLE ANSWER
  ===================== */
  function handleAnswer(row, key, ex) {
    if (hasAnswered) return;
    hasAnswered = true;

    const correct = ex.correct;
    const all = document.querySelectorAll(".option-item");

    all.forEach((opt) => (opt.style.pointerEvents = "none"));

    all.forEach((opt) => {
      const k = opt.dataset.key;
      const mark = opt.querySelector(".option-mark");

      if (k === correct) {
        opt.classList.add("correct");
        mark.textContent = "✔";
      }
    });

    const mark = row.querySelector(".option-mark");

    if (key === correct) {
      good++;
      row.classList.add("correct");
      mark.textContent = "✔";
    } else {
      bad++;
      row.classList.add("wrong");
      mark.textContent = "✖";
    }

    answered++;

    explanationBox.style.display = "block";
    explanationBody.textContent =
      ex.explanation ||
      "La bonne réponse est celle qui correspond exactement au sens du texte.";

    updateStats();
  }

  /* =====================
     STATS
  ===================== */
  function updateStats() {
    goodEl.textContent = good;
    badEl.textContent = bad;
    answeredEl.textContent = answered;
    scoreBottomEl.textContent = good;
  }

  /* =====================
     NAVIGATION
  ===================== */
  nextBtn.addEventListener("click", () => {
    if (index < EXERCISES.length - 1) {
      index++;
      renderQuestion();
    } else {
      explanationBox.style.display = "block";
      explanationBody.textContent =
        "🎉 Fin de la session. Analyse tes résultats et recommence pour progresser.";
    }
  });

  restartBtn.addEventListener("click", () => {
    index = 0;
    good = 0;
    bad = 0;
    answered = 0;
    resetTimer();
    startTimer();
    renderQuestion();
  });

  /* =====================
     INIT
  ===================== */
  resetTimer();
  startTimer();
  renderQuestion();
})();
