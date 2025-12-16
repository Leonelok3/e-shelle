/* =====================================================
   TEF — SESSION CO (Compréhension Orale)
   Projet : Immigration97
   ===================================================== */

(function () {
  "use strict";

  // ------------------ DONNÉES ------------------
  if (typeof EXERCISES === "undefined") {
    console.error("EXERCISES non défini");
    return;
  }

  let currentIndex = 0;
  let selectedOption = null;
  let answeredCount = 0;
  let correctCount = 0;
  let timerSeconds = 0;
  let timerHandle = null;
  let sessionFinished = false;

  // ------------------ ELEMENTS DOM ------------------
  const audioEl = document.getElementById("audio");
  const instructionEl = document.getElementById("instruction-text");
  const questionEl = document.getElementById("question-text");
  const optionsEl = document.getElementById("options-grid");
  const feedbackEl = document.getElementById("feedback");
  const progressEl = document.getElementById("progress-bar");

  const statQuestionEl = document.getElementById("stat-question");
  const statScoreEl = document.getElementById("stat-score");
  const statTimeEl = document.getElementById("stat-time");

  const btnValidate = document.getElementById("btn-validate");
  const btnNext = document.getElementById("btn-next");
  const btnRestart = document.getElementById("btn-restart");

  const summaryCard = document.getElementById("summary");
  const sumScoreEl = document.getElementById("sum-score");
  const sumQuestionsEl = document.getElementById("sum-questions");
  const sumTimeEl = document.getElementById("sum-time");
  const sumMessageEl = document.getElementById("sum-message");

  // ------------------ TIMER ------------------
  function startTimer() {
    clearInterval(timerHandle);
    timerHandle = setInterval(() => {
      timerSeconds++;
      statTimeEl.textContent = formatTime(timerSeconds);
    }, 1000);
  }

  function resetTimer() {
    clearInterval(timerHandle);
    timerSeconds = 0;
    statTimeEl.textContent = "00:00";
  }

  function formatTime(sec) {
    const m = String(Math.floor(sec / 60)).padStart(2, "0");
    const s = String(sec % 60).padStart(2, "0");
    return `${m}:${s}`;
  }

  // ------------------ INIT ------------------
  function initSession() {
    currentIndex = 0;
    selectedOption = null;
    answeredCount = 0;
    correctCount = 0;
    sessionFinished = false;

    feedbackEl.textContent = "";
    summaryCard.style.display = "none";

    statScoreEl.textContent = "0";
    statQuestionEl.textContent = `0 / ${EXERCISES.length}`;
    progressEl.style.width = "0%";

    if (!EXERCISES.length) {
      questionEl.textContent =
        "Aucun exercice n'est configuré pour cette leçon.";
      instructionEl.textContent = "";
      btnValidate.disabled = true;
      btnNext.disabled = true;
      return;
    }

    loadExercise();
    resetTimer();
    startTimer();
  }

  // ------------------ CHARGEMENT EXERCICE ------------------
  function loadExercise() {
    const ex = EXERCISES[currentIndex];

    audioEl.src = ex.audio_url || "";
    instructionEl.textContent = ex.instruction || "";
    questionEl.textContent = ex.question || "";
    feedbackEl.textContent = "";
    selectedOption = null;

    statQuestionEl.textContent = `${currentIndex + 1} / ${EXERCISES.length}`;
    updateProgress();

    optionsEl.innerHTML = "";

    Object.entries(ex.options || {}).forEach(([key, label]) => {
      const div = document.createElement("div");
      div.className = "option-item";
      div.dataset.key = key;
      div.innerHTML = `<strong>${key}.</strong> ${label}`;

      div.addEventListener("click", () => {
        if (sessionFinished || !btnValidate.disabled) {
          selectedOption = key;
          document
            .querySelectorAll(".option-item")
            .forEach(o => o.classList.remove("selected"));
          div.classList.add("selected");
        }
      });

      optionsEl.appendChild(div);
    });

    btnValidate.disabled = false;
    btnNext.disabled = true;
  }

  function updateProgress() {
    const pct = (currentIndex / EXERCISES.length) * 100;
    progressEl.style.width = `${pct}%`;
  }

  // ------------------ VALIDATION ------------------
  function validateAnswer() {
    if (sessionFinished) return;

    const ex = EXERCISES[currentIndex];
    if (!selectedOption) {
      feedbackEl.textContent = "Choisis une option avant de valider.";
      return;
    }

    answeredCount++;

    document.querySelectorAll(".option-item").forEach(o => {
      const key = o.dataset.key;
      o.classList.remove("selected");

      if (key === ex.correct) o.classList.add("correct");
      if (key === selectedOption && key !== ex.correct)
        o.classList.add("wrong");
    });

    if (selectedOption === ex.correct) {
      correctCount++;
      feedbackEl.innerHTML = "✅ Bonne réponse. " + (ex.explanation || "");
    } else {
      feedbackEl.innerHTML =
        `❌ Mauvaise réponse. La bonne réponse était <strong>${ex.correct}</strong>. ` +
        (ex.explanation || "");
    }

    statScoreEl.textContent = correctCount.toString();

    btnValidate.disabled = true;
    btnNext.disabled = currentIndex >= EXERCISES.length - 1;

    if (currentIndex >= EXERCISES.length - 1) finishSession();
  }

  // ------------------ QUESTION SUIVANTE ------------------
  function nextQuestion() {
    if (sessionFinished) return;
    if (currentIndex < EXERCISES.length - 1) {
      currentIndex++;
      loadExercise();
    }
  }

  // ------------------ FIN SESSION ------------------
  function finishSession() {
    sessionFinished = true;
    clearInterval(timerHandle);
    progressEl.style.width = "100%";

    const total = EXERCISES.length;
    const pct = total ? Math.round((correctCount / total) * 100) : 0;

    sumScoreEl.textContent = `${correctCount} / ${total} (${pct}%)`;
    sumQuestionsEl.textContent = `${answeredCount} / ${total}`;
    sumTimeEl.textContent = formatTime(timerSeconds);

    if (pct >= 80) {
      sumMessageEl.textContent =
        "Excellent niveau. Passe à la leçon suivante.";
    } else if (pct >= 60) {
      sumMessageEl.textContent =
        "Bon niveau. Recommence pour viser 80 % ou plus.";
    } else {
      sumMessageEl.textContent =
        "Continue l’entraînement et concentre-toi sur les mots-clés.";
    }

    summaryCard.style.display = "block";
  }

  // ------------------ EVENTS ------------------
  btnValidate.addEventListener("click", validateAnswer);
  btnNext.addEventListener("click", nextQuestion);
  btnRestart.addEventListener("click", initSession);

  // ------------------ START ------------------
  initSession();
})();


const engine = new ExamEngine({
  exercises: EXERCISES,
  withAudio: true,
  selectors: {
    audio: "#audio",
    question: "#question-text",
    options: "#options-grid",
    feedback: "#feedback",
    score: "#stat-score",
    progress: "#progress-bar",
  },
  onFinish: (stats) => {
    console.log("Session CO terminée", stats);
  },
});

engine.start();

document.getElementById("btn-validate").onclick = engine.validate;
document.getElementById("btn-next").onclick = engine.next;


document.addEventListener("click", function (e) {
  if (!e.target.classList.contains("check-answer-btn")) return;

  const card = e.target.closest(".exercise-card");
  const radios = card.querySelectorAll("input[type=radio]");
  const feedback = card.querySelector(".exercise-feedback");

  let selected = null;
  radios.forEach(r => { if (r.checked) selected = r });

  if (!selected) {
    feedback.textContent = "❗ Choisissez une réponse.";
    feedback.className = "exercise-feedback bad";
    return;
  }

  if (selected.dataset.correct === "true") {
    feedback.textContent = "✅ Bonne réponse";
    feedback.className = "exercise-feedback good";
  } else {
    feedback.textContent = "❌ Mauvaise réponse";
    feedback.className = "exercise-feedback bad";
  }
});

