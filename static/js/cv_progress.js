// cv_progress.js — anime les barres de progression du dashboard CV
document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.progress[data-progress]').forEach(function (el) {
    var pct = parseInt(el.getAttribute('data-progress'), 10) || 0;
    var bar = el.querySelector('.bar span');
    if (bar) {
      bar.style.width = pct + '%';
      if (pct >= 100) bar.style.background = '#22c55e';
      else if (pct >= 50) bar.style.background = '#D4A843';
      else bar.style.background = '#6b7280';
    }
  });
});
