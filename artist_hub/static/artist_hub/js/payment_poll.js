/**
 * artist_hub/static/artist_hub/js/payment_poll.js
 * Polling léger et non intrusif pour surveiller la confirmation d'un paiement en arrière-plan.
 * Sans dépendance externe (Vanilla JS).
 */
(function() {
  window.initPaymentPolling = function(reference, statusApiUrl, redirectUrl) {
    var maxAttempts = 100; // env. 5 minutes
    var attempts = 0;
    var intervalTime = 3500; // 3.5 secondes
    var pollTimer = null;

    function checkStatus() {
      attempts++;
      fetch(statusApiUrl + "?check=1", {
        headers: { "X-Requested-With": "XMLHttpRequest" }
      })
      .then(function(res) {
        if (!res.ok) throw new Error("Erreur réseau");
        return res.json();
      })
      .then(function(data) {
        if (data.is_paid || data.status === "SUCCESS") {
          clearInterval(pollTimer);
          var finalRedirect = data.redirect_url || redirectUrl;
          var statusEl = document.getElementById("poll-status-message");
          if (statusEl) {
            statusEl.innerHTML = '<span style="color:var(--hub-success); font-weight:bold;">Paiement validé ! Redirection...</span>';
          }
          setTimeout(function() {
            window.location.href = finalRedirect;
          }, 800);
        } else if (data.status === "FAILED") {
          clearInterval(pollTimer);
          window.location.href = data.redirect_url || "/artist-hub/payments/failed/" + reference + "/";
        }
      })
      .catch(function(err) {
        console.warn("Vérification statut en attente :", err);
      });

      if (attempts >= maxAttempts) {
        clearInterval(pollTimer);
        var statusEl = document.getElementById("poll-status-message");
        if (statusEl) {
          statusEl.innerText = "La vérification automatique est suspendue. Si vous avez effectué le versement, votre candidature reste enregistrée et sera validée dès confirmation.";
        }
      }
    }

    pollTimer = setInterval(checkStatus, intervalTime);
    checkStatus(); // premier appel immédiat
  };
})();
