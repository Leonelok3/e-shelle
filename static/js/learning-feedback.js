(function (root) {
  "use strict";
  function escape(value) {
    return String(value == null ? "" : value).replace(/&/g, "&amp;").replace(/</g, "&lt;")
      .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  root.EShelleLearning = {
    render: function (data) {
      var coach = data.coaching;
      if (!coach || !coach.version) return "";
      var html = '<section class="learning-feedback"><h4>Ton plan de progression</h4>';
      html += '<p class="learning-note">' + escape(coach.assessment_note) + '</p>';
      if (coach.comparison) {
        html += '<p class="learning-comparison">Tentative précédente : ' + escape(coach.comparison.previous_score) +
          '/100 · Évolution : ' + (coach.comparison.change > 0 ? '+' : '') + escape(coach.comparison.change) +
          ' points. ' + escape(coach.comparison.note) + '</p>';
      }
      html += '<div class="learning-rubric">';
      (coach.rubric || []).forEach(function (criterion) {
        html += '<div><span>' + escape(criterion.label) + '</span><strong>' + escape(criterion.score) +
          '/100</strong><progress max="100" value="' + escape(criterion.score) + '" aria-label="' +
          escape(criterion.label) + '"></progress></div>';
      });
      html += '</div>';
      if ((coach.strengths || []).length) {
        html += '<h5>À conserver</h5><ul>';
        coach.strengths.forEach(function (strength) { html += '<li>' + escape(strength) + '</li>'; });
        html += '</ul>';
      }
      (coach.priorities || []).forEach(function (priority, index) {
        html += '<article class="learning-priority"><h5>Priorité ' + (index + 1) + ' · ' + escape(priority.diagnosis) + '</h5>';
        if (priority.evidence) html += '<blockquote>« ' + escape(priority.evidence) + ' »</blockquote>';
        html += '<p><strong>Technique :</strong> ' + escape(priority.action) + '</p><p><strong>À toi de jouer :</strong> ' +
          escape(priority.drill) + '</p><details><summary>Comment vérifier mon travail ?</summary><p>' +
          escape(priority.success_check) + '</p></details></article>';
      });
      if (coach.model_example) html += '<details class="learning-example"><summary>Analyser un exemple avancé</summary><p>' +
        escape(coach.model_example) + '</p><p>Repère la technique, puis reformule avec tes propres idées.</p></details>';
      html += '<p class="learning-next"><strong>Nouvelle tentative :</strong> ' + escape(coach.next_attempt) +
        '</p><a href="/prep/fr/mon-coach/" class="pt-btn-secondary">Voir mon carnet de progression</a></section>';
      return html;
    }
  };
})(window);
