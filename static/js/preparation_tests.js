/* ============================================================
   preparation_tests.js — E-Shelle 2026
   Correction des exercices QCM (CE / CO), enregistrement &
   soumission IA (EO / EE), progression live.
   ============================================================ */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var csrfInput = document.getElementById("csrf-token");
    if (!csrfInput) return;

    var csrfToken = csrfInput.value;
    var progressUrl = csrfInput.getAttribute("data-progress-url");
    var submitEoUrl = csrfInput.getAttribute("data-submit-eo-url");
    var submitEeUrl = csrfInput.getAttribute("data-submit-ee-url");
    var explainUrl = csrfInput.getAttribute("data-explain-url");
    var examCode = csrfInput.getAttribute("data-exam-code");
    var isAuthenticated = csrfInput.getAttribute("data-authenticated") === "1";

    function getCookie(name) {
      var match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
      return match ? decodeURIComponent(match[2]) : "";
    }

    function escapeHtml(str) {
      return String(str == null ? "" : str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
    }

    function readEvaluationResponse(res) {
      var message = "Le service de correction est temporairement indisponible. Réessaie dans un instant.";
      if (res.redirected || res.status === 401) {
        message = "Ta session a expiré. Reconnecte-toi avant de soumettre ta réponse.";
      } else if (res.status === 403) {
        message = "Recharge la page avant de soumettre à nouveau ta réponse.";
      }
      if (res.redirected || !res.ok) {
        return { httpOk: false, data: { message: message } };
      }
      return res.json().then(function (data) {
        return { httpOk: true, data: data };
      }).catch(function () {
        return { httpOk: false, data: { message: message } };
      });
    }

    function updateProgressBar(data) {
      var doneEl = document.getElementById("ptProgressDone");
      var totalEl = document.getElementById("ptProgressTotal");
      var pctEl = document.getElementById("ptProgressPct");
      var fillEl = document.getElementById("ptProgressFill");
      var barEl = fillEl ? fillEl.closest(".pt-progress-bar") : null;

      if (doneEl) doneEl.textContent = data.completed_exercises;
      if (totalEl) totalEl.textContent = data.total_exercises;
      if (pctEl) pctEl.textContent = data.percent;
      if (fillEl) fillEl.style.width = data.percent + "%";
      if (barEl) barEl.setAttribute("aria-valuenow", data.percent);
    }

    function sendProgress(exerciseId, selected, correct) {
      if (!progressUrl || !isAuthenticated) return;

      fetch(progressUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken || getCookie("csrftoken"),
        },
        body: JSON.stringify({
          exercise_id: exerciseId,
          selected: selected,
          correct: correct,
        }),
      })
        .then(function (res) {
          if (!res.ok) throw new Error("progress_request_failed");
          return res.json();
        })
        .then(function (data) {
          if (data && data.ok) updateProgressBar(data);
        })
        .catch(function () {
          /* Progression non enregistrée (hors-ligne, session expirée...) —
             la correction locale reste affichée à l'utilisateur. */
        });
    }

    function handleCheckAnswer(button) {
      var form = button.closest(".pt-exercise-form");
      if (!form) return;

      var feedback = form.querySelector(".pt-feedback");
      var exerciseId = form.getAttribute("data-exercise-id");
      var correctValue = (form.getAttribute("data-correct") || "").toUpperCase();
      var checkedInput = form.querySelector('input[type="radio"]:checked');

      if (!checkedInput) {
        if (feedback) {
          feedback.hidden = false;
          feedback.classList.remove("is-correct", "is-incorrect");
          feedback.classList.add("is-warning");
          feedback.textContent = "Sélectionne une réponse avant de vérifier.";
        }
        return;
      }

      var selectedValue = checkedInput.value.toUpperCase();
      var isCorrect = selectedValue === correctValue;

      form.querySelectorAll(".pt-option").forEach(function (label) {
        var input = label.querySelector('input[type="radio"]');
        label.classList.remove("is-correct", "is-incorrect");
        if (!input) return;
        if (input.value.toUpperCase() === correctValue) {
          label.classList.add("is-correct");
        } else if (input.checked) {
          label.classList.add("is-incorrect");
        }
        input.disabled = true;
      });

      button.disabled = true;

      if (feedback) {
        feedback.hidden = false;
        feedback.classList.remove("is-warning", "is-correct", "is-incorrect");
        feedback.classList.add(isCorrect ? "is-correct" : "is-incorrect");
        feedback.textContent = isCorrect
          ? "✅ Bonne réponse !"
          : "❌ Mauvaise réponse. La bonne réponse était " + correctValue + ".";
      }

      if (exerciseId) sendProgress(exerciseId, selectedValue, isCorrect);
      var explainButton = form.querySelector(".pt-explain-answer");
      if (explainButton) {
        explainButton.hidden = false;
        explainButton.onclick = function () {
          var output = form.querySelector(".learning-explanation");
          if (!output || !explainUrl) return;
          output.hidden = false;
          if (!isAuthenticated) { output.textContent = "Connecte-toi pour recevoir l'explication du coach."; return; }
          explainButton.disabled = true;
          output.textContent = "Le coach analyse le corrigé…";
          fetch(explainUrl, {method: "POST", credentials: "same-origin",
            headers: {"Content-Type": "application/json", "X-CSRFToken": csrfToken || getCookie("csrftoken")},
            body: JSON.stringify({exercise_id: exerciseId, selected: selectedValue})})
            .then(readEvaluationResponse).then(function (response) {
              output.textContent = response.httpOk && response.data.ok
                ? (response.data.mode === "reference" ? "Aide du corrigé (IA indisponible)\n" : "Explication du coach IA\n") + response.data.explanation
                : response.data.message || "L'explication est indisponible. Réessaie.";
            }).catch(function () { output.textContent = "Connexion interrompue. Réessaie."; })
            .finally(function () { explainButton.disabled = false; });
        };
      }
    }

    document.querySelectorAll(".pt-check-answer").forEach(function (button) {
      button.addEventListener("click", function () {
        handleCheckAnswer(button);
      });
    });

    /* ============================================================
       🎤 EO — Enregistrement micro + soumission évaluation IA
       ============================================================ */
    function formatTimer(ms) {
      var totalSec = Math.floor(ms / 1000);
      var m = String(Math.floor(totalSec / 60)).padStart(2, "0");
      var s = String(totalSec % 60).padStart(2, "0");
      return m + ":" + s;
    }

    function renderEoResult(data) {
      var scoreClass = data.score >= 60 ? "is-correct" : "is-incorrect";
      var html =
        '<div class="pt-result-score ' + scoreClass + '">Score : ' +
        Math.round(data.score) + '/100</div>';

      if (data.feedback) {
        html += '<p class="pt-result-feedback">' + escapeHtml(data.feedback) + "</p>";
      }
      if (data.points_covered && data.points_covered.length) {
        html += '<p class="pt-result-subtitle">✅ Points abordés</p><ul class="pt-result-list">';
        data.points_covered.forEach(function (p) {
          html += "<li>" + escapeHtml(p) + "</li>";
        });
        html += "</ul>";
      }
      if (data.suggestions && data.suggestions.length) {
        html += '<p class="pt-result-subtitle">💡 Suggestions</p><ul class="pt-result-list">';
        data.suggestions.forEach(function (s) {
          html += "<li>" + escapeHtml(s) + "</li>";
        });
        html += "</ul>";
      }
      if (data.transcript) {
        html +=
          '<details class="pt-result-details"><summary>📝 Voir la transcription</summary><p>' +
          escapeHtml(data.transcript) +
          "</p></details>";
      }
      return html + (typeof window !== "undefined" && window.EShelleLearning ? window.EShelleLearning.render(data) : "");
    }

    function initEoRecorders() {
      document.querySelectorAll(".pt-eo-card").forEach(function (card) {
        var recordBtn = card.querySelector(".pt-record-btn");
        var timerEl = card.querySelector(".pt-record-timer");
        var playback = card.querySelector(".pt-playback");
        var submitBtn = card.querySelector(".pt-submit-eo");
        var resultBox = card.querySelector(".pt-eo-result");
        var exerciseId = card.getAttribute("data-exercise-id");
        var savedFeedback = card.querySelector('script[type="application/json"]');
        if (savedFeedback && resultBox) {
          try { resultBox.innerHTML = renderEoResult(JSON.parse(savedFeedback.textContent)); resultBox.style.display = "block"; } catch (error) { /* A damaged old report must not block recording. */ }
        }

        if (!recordBtn) return;

        var mediaRecorder = null;
        var chunks = [];
        var activeStream = null;
        var recordedBlob = null;
        var timerInterval = null;
        var startTime = null;

        function stopTimer() {
          if (timerInterval) clearInterval(timerInterval);
          timerInterval = null;
        }

        recordBtn.addEventListener("click", function () {
          if (mediaRecorder && mediaRecorder.state === "recording") {
            mediaRecorder.stop();
            return;
          }

          if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            alert("Ton navigateur ne permet pas l'enregistrement audio.");
            return;
          }

          navigator.mediaDevices
            .getUserMedia({ audio: true })
            .then(function (stream) {
              activeStream = stream;
              chunks = [];

              var options = {};
              if (window.MediaRecorder && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported("audio/webm")) {
                options.mimeType = "audio/webm";
              }
              mediaRecorder = new MediaRecorder(stream, options);

              mediaRecorder.addEventListener("dataavailable", function (e) {
                if (e.data && e.data.size > 0) chunks.push(e.data);
              });

              mediaRecorder.addEventListener("stop", function () {
                recordedBlob = new Blob(chunks, {
                  type: mediaRecorder.mimeType || "audio/webm",
                });
                if (playback) {
                  playback.src = URL.createObjectURL(recordedBlob);
                  playback.style.display = "block";
                }
                if (submitBtn) submitBtn.disabled = false;
                activeStream.getTracks().forEach(function (track) {
                  track.stop();
                });
                stopTimer();
                recordBtn.textContent = "🎤 Recommencer l’enregistrement";
                recordBtn.classList.remove("is-recording");
              });

              mediaRecorder.start();
              startTime = Date.now();
              stopTimer();
              timerInterval = setInterval(function () {
                if (timerEl) timerEl.textContent = formatTimer(Date.now() - startTime);
              }, 250);

              recordBtn.textContent = "⏹ Arrêter l’enregistrement";
              recordBtn.classList.add("is-recording");
            })
            .catch(function () {
              alert("Impossible d'accéder au microphone. Vérifie les autorisations de ton navigateur.");
            });
        });

        if (submitBtn) {
          submitBtn.addEventListener("click", function () {
            if (!recordedBlob || !submitEoUrl) return;

            var formData = new FormData();
            formData.append("exercise_id", exerciseId);
            if (examCode) formData.append("exam", examCode);
            formData.append("audio", recordedBlob, "recording.webm");

            var originalLabel = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "⏳ Analyse en cours...";
            recordBtn.disabled = true;

            fetch(submitEoUrl, {
              method: "POST",
              credentials: "same-origin",
              headers: { "X-CSRFToken": csrfToken || getCookie("csrftoken") },
              body: formData,
            })
              .then(readEvaluationResponse)
              .then(function (result) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalLabel;
                recordBtn.disabled = false;

                if (!resultBox) return;
                resultBox.style.display = "block";

                if (!result.httpOk || !result.data || !result.data.ok) {
                  resultBox.innerHTML =
                    '<p class="pt-feedback is-incorrect">' + escapeHtml(result.data && result.data.message || "L’évaluation est indisponible. Réessaie.") + '</p>';
                  return;
                }

                resultBox.innerHTML = renderEoResult(result.data);
                if (isAuthenticated) updateProgressBar(result.data);
              })
              .catch(function () {
                submitBtn.disabled = false;
                submitBtn.textContent = originalLabel;
                recordBtn.disabled = false;
                if (resultBox) {
                  resultBox.style.display = "block";
                  resultBox.innerHTML =
                    '<p class="pt-feedback is-incorrect">Connexion impossible. Vérifie ta connexion internet.</p>';
                }
              });
          });
        }
      });
    }

    /* ============================================================
       ✍️ EE — Compteur de mots + soumission correction IA
       ============================================================ */
    function renderEeResult(data) {
      var scoreClass = data.score >= 60 ? "is-correct" : "is-incorrect";
      var html =
        '<div class="pt-result-score ' + scoreClass + '">Score : ' +
        Math.round(data.score) + "/100 · " + (data.word_count || 0) + " mot(s)</div>";

      if (data.feedback) {
        html += '<p class="pt-result-feedback">' + escapeHtml(data.feedback) + "</p>";
      }
      if (data.errors && data.errors.length) {
        html += '<p class="pt-result-subtitle">✏️ Corrections</p><ul class="pt-result-list">';
        data.errors.forEach(function (err) {
          if (err && typeof err === "object") {
            html +=
              "<li><s>" + escapeHtml(err.original) + "</s> → <strong>" +
              escapeHtml(err.correction) + "</strong>" +
              (err.kind === "style" ? " (suggestion de style)" : "") +
              (err.rule ? " — " + escapeHtml(err.rule) : "") +
              "</li>";
          } else {
            html += "<li>" + escapeHtml(err) + "</li>";
          }
        });
        html += "</ul>";
      }
      if (data.corrected_version) {
        html +=
          '<details class="pt-result-details"><summary>✅ Version corrigée</summary><p>' +
          escapeHtml(data.corrected_version) +
          "</p></details>";
      }
      return html + (typeof window !== "undefined" && window.EShelleLearning ? window.EShelleLearning.render(data) : "");
    }

    function initEeEditors() {
      document.querySelectorAll(".pt-ee-card").forEach(function (card) {
        var textarea = card.querySelector(".pt-ee-textarea");
        var counter = card.querySelector(".pt-word-count");
        var submitBtn = card.querySelector(".pt-submit-ee");
        var resultBox = card.querySelector(".pt-ee-result");
        var exerciseId = card.getAttribute("data-exercise-id");
        var savedFeedback = card.querySelector('script[type="application/json"]');
        if (savedFeedback && resultBox) {
          try { resultBox.innerHTML = renderEeResult(JSON.parse(savedFeedback.textContent)); resultBox.style.display = "block"; } catch (error) { /* The editor remains usable. */ }
        }
        if (textarea && counter) counter.textContent = textarea.value.trim() ? textarea.value.trim().split(/\s+/).length : 0;

        if (textarea && counter) {
          textarea.addEventListener("input", function () {
            var trimmed = textarea.value.trim();
            counter.textContent = trimmed ? trimmed.split(/\s+/).length : 0;
          });
        }

        if (submitBtn) {
          submitBtn.addEventListener("click", function () {
            var text = textarea ? textarea.value.trim() : "";

            if (!text) {
              if (resultBox) {
                resultBox.style.display = "block";
                resultBox.innerHTML =
                  '<p class="pt-feedback is-warning">Rédige ta réponse avant de soumettre.</p>';
              }
              return;
            }
            if (!submitEeUrl) return;

            var originalLabel = submitBtn.textContent;
            submitBtn.disabled = true;
            submitBtn.textContent = "⏳ Correction en cours...";

            fetch(submitEeUrl, {
              method: "POST",
              credentials: "same-origin",
              headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken || getCookie("csrftoken"),
              },
              body: JSON.stringify({ exercise_id: exerciseId, text: text, exam: examCode }),
            })
              .then(readEvaluationResponse)
              .then(function (result) {
                submitBtn.disabled = false;
                submitBtn.textContent = originalLabel;

                if (!resultBox) return;
                resultBox.style.display = "block";

                if (!result.httpOk || !result.data || !result.data.ok) {
                  resultBox.innerHTML =
                    '<p class="pt-feedback is-incorrect">' + escapeHtml(result.data && result.data.message || "La correction est indisponible. Réessaie.") + '</p>';
                  return;
                }

                resultBox.innerHTML = renderEeResult(result.data);
                if (isAuthenticated) updateProgressBar(result.data);
              })
              .catch(function () {
                submitBtn.disabled = false;
                submitBtn.textContent = originalLabel;
                if (resultBox) {
                  resultBox.style.display = "block";
                  resultBox.innerHTML =
                    '<p class="pt-feedback is-incorrect">Connexion impossible. Vérifie ta connexion internet.</p>';
                }
              });
          });
        }
      });
    }

    initEoRecorders();
    initEeEditors();
  });
})();
