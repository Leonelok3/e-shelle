document.addEventListener("DOMContentLoaded", () => {
  const questions = document.querySelectorAll("[data-question]");
  const finishBtn = document.getElementById("finish-exam");
  const timerEl = document.getElementById("exam-timer");

  let duration = 40 * 60; // 40 minutes
  let timer = setInterval(() => {
    duration--;
    const min = String(Math.floor(duration / 60)).padStart(2, "0");
    const sec = String(duration % 60).padStart(2, "0");
    timerEl.textContent = `${min}:${sec}`;

    if (duration <= 0) {
      clearInterval(timer);
      finishExam();
    }
  }, 1000);

  finishBtn.addEventListener("click", finishExam);

  function finishExam() {
    clearInterval(timer);

    let score = 0;

    questions.forEach(q => {
      const correct = q.dataset.correct;
      const checked = q.querySelector("input[type=radio]:checked");
      if (checked && checked.value === correct) {
        score++;
      }
    });

    alert(`Examen terminé ✅\nScore : ${score} / ${questions.length}`);
    // PLUS TARD → sauvegarde DB
  }
});
