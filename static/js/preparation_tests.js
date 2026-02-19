(function () {
  "use strict";

  function closest(el, selector) {
    while (el && el !== document) {
      if (el.matches(selector)) return el;
      el = el.parentElement;
    }
    return null;
  }

  function setFeedback(form, msg, ok) {
    const p = form.querySelector(".pt-feedback");
    if (!p) return;

    p.hidden = false;
    p.textContent = msg;

    p.classList.remove("pt-feedback--ok", "pt-feedback--bad");
    p.classList.add(ok ? "pt-feedback--ok" : "pt-feedback--bad");
  }

  function lockForm(form) {
    const inputs = form.querySelectorAll('input[type="radio"]');
    inputs.forEach((i) => (i.disabled = true));

    const btn = form.querySelector(".pt-check-answer");
    if (btn) {
      btn.disabled = true;
      btn.classList.add("pt-btn--disabled");
    }
  }

  function getSelectedValue(form) {
    const checked = form.querySelector('input[type="radio"]:checked');
    return checked ? String(checked.value || "").toUpperCase() : "";
  }

  function getCorrectValue(form) {
    return String(form.dataset.correct || "").trim().toUpperCase();
  }

  function getCSRFToken() {
    const el = document.getElementById("csrf-token");
    return el ? el.value : "";
  }

  function updateProgressBar(data) {
    try {
      const doneEl = document.getElementById("ptProgressDone");
      const totalEl = document.getElementById("ptProgressTotal");
      const pctEl = document.getElementById("ptProgressPct");
      const fillEl = document.getElementById("ptProgressFill");

      if (doneEl) doneEl.textContent = String(data.completed_exercises ?? "");
      if (totalEl) totalEl.textContent = String(data.total_exercises ?? "");
      if (pctEl) pctEl.textContent = String(data.percent ?? "");

      if (fillEl && typeof data.percent === "number") {
        fillEl.style.width = `${data.percent}%`;
        const bar = fillEl.closest(".pt-progress-bar");
        if (bar) bar.setAttribute("aria-valuenow", String(data.percent));
      }
    } catch (e) {}
  }

  async function sendExerciseProgress({ exerciseId, selected, correct }) {
    const csrf = getCSRFToken();
    if (!csrf) return null;

    try {
      const res = await fetch("/prep/exercise-progress/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrf,
        },
        body: JSON.stringify({
          exercise_id: exerciseId,
          selected,
          correct,
        }),
      });

      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      return null;
    }
  }

  // ✅ UX: après validation, on propose de reload soft si besoin
  function softUnlockHint() {
    // Ici on ne fait rien de risqué.
    // Si tu veux ensuite : animation, scroll next, toast.
  }

  document.addEventListener("click", async function (e) {
    const btn = e.target.closest ? e.target.closest(".pt-check-answer") : null;
    if (!btn) return;

    const form = closest(btn, ".pt-exercise-form");
    if (!form) return;

    if (form.dataset.locked === "1") return;

    const selected = getSelectedValue(form);
    const correctVal = getCorrectValue(form);

    if (!selected) {
      setFeedback(form, "⚠️ Choisis une réponse avant de vérifier.", false);
      return;
    }

    if (!correctVal) {
      setFeedback(form, "⚠️ Erreur interne: data-correct manquant.", false);
      return;
    }

    const ok = selected === correctVal;

    if (ok) {
      setFeedback(form, "✅ Bonne réponse !", true);
    } else {
      setFeedback(form, `❌ Mauvaise réponse. La bonne réponse est : ${correctVal}.`, false);
    }

    form.dataset.locked = "1";
    lockForm(form);

    const exerciseId = parseInt(form.dataset.exerciseId || "0", 10);
    if (ok && exerciseId) {
      const data = await sendExerciseProgress({
        exerciseId,
        selected,
        correct: true,
      });

      if (data && data.ok) {
        updateProgressBar(data);
        softUnlockHint();
      }
    }
  });
})();
