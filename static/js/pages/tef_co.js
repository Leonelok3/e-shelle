document.addEventListener("DOMContentLoaded", () => {

  document.querySelectorAll(".lesson-card").forEach(lesson => {

    const exercises = lesson.querySelectorAll(".exercise-card");
    const total = exercises.length;

    let score = 0;

    const scoreCurrent = lesson.querySelector(".score-current");
    const scoreTotal = lesson.querySelector(".score-total");
    const progressFill = lesson.querySelector(".progress-fill");

    if (scoreTotal) scoreTotal.textContent = total;

    exercises.forEach(card => {
      const btn = card.querySelector(".check-answer-btn");
      if (!btn) return;

      btn.addEventListener("click", () => {
        const selected = card.querySelector("input[type='radio']:checked");
        if (!selected) {
          alert("Veuillez choisir une réponse.");
          return;
        }

        const correct = selected.dataset.correct === "true";

        if (correct) {
          score += 1;
          card.classList.add("correct");
        } else {
          card.classList.add("wrong");
        }

        // Feedback texte
        const feedback = card.querySelector(".exercise-feedback");
        if (feedback) {
          feedback.textContent = correct
            ? "✅ Bonne réponse"
            : "❌ Mauvaise réponse";
          feedback.style.display = "block";
        }

        // Afficher la correction
        const summary = card.querySelector(".exercise-summary");
        if (summary) summary.open = true;

        // Désactiver l’exercice
        card.querySelectorAll("input").forEach(i => i.disabled = true);
        btn.disabled = true;

        // Mise à jour score
        if (scoreCurrent) scoreCurrent.textContent = score;

        const percent = Math.round((score / total) * 100);
        if (progressFill) progressFill.style.width = percent + "%";

        // Leçon validée
        if (score === total) {
          lesson.classList.add("lesson-complete");
        }
      });
    });
  });
});
