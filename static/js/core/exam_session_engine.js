/* =========================================================
   EXAM SESSION ENGINE – CO / CE / EO
========================================================= */

window.ExamEngine = function (config) {
  const {
    exercises,
    selectors,
    withAudio = false,
    onFinish = null,
  } = config;

  let index = 0;
  let correct = 0;
  let answered = 0;
  let selected = null;
  let timer = 0;
  let timerHandle = null;

  const $ = (s) => document.querySelector(s);

  const audioEl = withAudio ? $(selectors.audio) : null;
  const questionEl = $(selectors.question);
  const optionsEl = $(selectors.options);
  const feedbackEl = $(selectors.feedback);
  const scoreEl = $(selectors.score);
  const progressEl = $(selectors.progress);

  function startTimer() {
    timerHandle = setInterval(() => timer++, 1000);
  }

  function stopTimer() {
    clearInterval(timerHandle);
  }

  function render() {
    const ex = exercises[index];
    selected = null;

    if (withAudio && audioEl) {
      audioEl.src = ex.audio_url || "";
    }

    questionEl.textContent = ex.question || "";
    optionsEl.innerHTML = "";
    feedbackEl.textContent = "";

    Object.entries(ex.options || {}).forEach(([key, label]) => {
      const div = document.createElement("div");
      div.className = "option-item";
      div.textContent = `${key}. ${label}`;
      div.onclick = () => {
        if (selected) return;
        selected = key;
        div.classList.add("selected");
      };
      optionsEl.appendChild(div);
    });

    scoreEl.textContent = correct;
    progressEl.style.width = `${(index / exercises.length) * 100}%`;
  }

  function validate() {
    if (!selected) return;

    const ex = exercises[index];
    answered++;

    if (selected === ex.correct) {
      correct++;
      feedbackEl.textContent = "✅ Bonne réponse";
    } else {
      feedbackEl.textContent = `❌ Mauvaise réponse (réponse : ${ex.correct})`;
    }

    scoreEl.textContent = correct;
  }

  function next() {
    if (index < exercises.length - 1) {
      index++;
      render();
    } else {
      stopTimer();
      if (onFinish) {
        onFinish({ correct, answered, timer });
      }
    }
  }

  function start() {
    if (!exercises.length) return;
    startTimer();
    render();
  }

  return {
    start,
    validate,
    next,
  };
};
