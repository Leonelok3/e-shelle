/**
 * CV Generator – JS principal
 * Compatible prod / sans dépendance externe
 */

document.addEventListener("DOMContentLoaded", function () {
    console.log("cv_generator.js chargé ✅");

    // =========================
    // Helpers
    // =========================
    function qs(selector, scope = document) {
        return scope.querySelector(selector);
    }

    function qsa(selector, scope = document) {
        return scope.querySelectorAll(selector);
    }

    // =========================
    // Gestion des boutons "Suivant / Précédent"
    // =========================
    qsa("[data-cv-next]").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const target = btn.getAttribute("data-cv-next");
            if (target) {
                window.location.href = target;
            }
        });
    });

    qsa("[data-cv-prev]").forEach(btn => {
        btn.addEventListener("click", function (e) {
            e.preventDefault();
            const target = btn.getAttribute("data-cv-prev");
            if (target) {
                window.location.href = target;
            }
        });
    });

    // =========================
    // Validation simple des champs requis
    // =========================
    qsa("form").forEach(form => {
        form.addEventListener("submit", function (e) {
            let valid = true;

            qsa("[required]", form).forEach(input => {
                if (!input.value.trim()) {
                    valid = false;
                    input.classList.add("input-error");
                } else {
                    input.classList.remove("input-error");
                }
            });

            if (!valid) {
                e.preventDefault();
                alert("Veuillez remplir tous les champs obligatoires.");
            }
        });
    });

    // =========================
    // Toggle sections (expérience, compétences…)
    // =========================
    qsa("[data-toggle]").forEach(btn => {
        btn.addEventListener("click", function () {
            const targetId = btn.getAttribute("data-toggle");
            const target = document.getElementById(targetId);
            if (target) {
                target.classList.toggle("hidden");
            }
        });
    });
});
