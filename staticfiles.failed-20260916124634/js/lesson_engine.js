/* ============================================================
   lesson_engine.js — E-Shelle 2026
   Moteur interactif : QCM, timer, progression, score
   ============================================================ */

'use strict';

/* ── Reading progress bar ────────────────────────────────── */
function initReadProgress() {
  const bar = document.getElementById('le-read-progress');
  if (!bar) return;
  const update = () => {
    const total = document.documentElement.scrollHeight - window.innerHeight;
    const pct   = total > 0 ? Math.min(100, (window.scrollY / total) * 100) : 0;
    bar.style.width = pct + '%';
  };
  window.addEventListener('scroll', update, { passive: true });
  update();
}

/* ── Score flottant ──────────────────────────────────────── */
let _scoreFloat = null;
function showScoreFloat(correct, total) {
  if (!_scoreFloat) {
    _scoreFloat = document.createElement('div');
    _scoreFloat.className = 'le-score-float';
    _scoreFloat.innerHTML = '<div class="le-score-float-num"></div><div class="le-score-float-label">Score</div>';
    document.body.appendChild(_scoreFloat);
  }
  const num = _scoreFloat.querySelector('.le-score-float-num');
  num.textContent = correct + '/' + total;
  num.classList.add('le-score-animate');
  setTimeout(() => num.classList.remove('le-score-animate'), 500);
  _scoreFloat.classList.add('visible');
}

/* ── Progress bar update ─────────────────────────────────── */
function updateProgress(answered, total) {
  const fill = document.getElementById('le-progress-fill');
  const val  = document.getElementById('le-progress-val');
  if (fill) fill.style.width = (total > 0 ? Math.round(answered / total * 100) : 0) + '%';
  if (val)  val.textContent = answered + '/' + total;
}

/* ── Timer countdown ─────────────────────────────────────── */
function initTimer(durationMinutes) {
  const el = document.getElementById('le-timer-val');
  if (!el || !durationMinutes) return;
  let remaining = durationMinutes * 60;
  const fmt = s => {
    const m = Math.floor(s / 60).toString().padStart(2, '0');
    const sec = (s % 60).toString().padStart(2, '0');
    return m + ':' + sec;
  };
  el.textContent = fmt(remaining);
  const tick = setInterval(() => {
    remaining--;
    if (remaining <= 0) {
      clearInterval(tick);
      el.textContent = '00:00';
      el.classList.add('urgent');
      // Auto-submit
      const form = document.getElementById('le-exam-form');
      if (form) {
        const notice = document.createElement('div');
        notice.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:1rem;background:rgba(239,68,68,.9);color:#fff;text-align:center;font-weight:700;z-index:9999';
        notice.textContent = '⏰ Temps écoulé — soumission automatique…';
        document.body.appendChild(notice);
        setTimeout(() => form.submit(), 1500);
      }
      return;
    }
    el.textContent = fmt(remaining);
    if (remaining <= 60) el.classList.add('urgent');
    else el.classList.remove('urgent');
  }, 1000);
}

/* ── Interactive QCM (client-side feedback) ──────────────── */
function initInteractiveQCM() {
  const cards = document.querySelectorAll('[data-qcm-card]');
  if (!cards.length) return;

  const wrapper     = document.querySelector('[data-qcm-mode]');
  const mode        = (wrapper && wrapper.dataset.qcmMode) || document.body.dataset.qcmMode || 'interactive'; // interactive | exam
  let   correct     = 0;
  let   answered    = 0;
  const total       = cards.length;
  const submitBtn   = document.getElementById('le-submit-btn');
  const answeredCnt = document.getElementById('le-answered-count');

  cards.forEach(card => {
    const options     = card.querySelectorAll('.le-option[data-value]');
    const correctVal  = card.dataset.correct || null;   // set if client-side check
    const explanation = card.querySelector('.le-q-explanation');
    let   cardDone    = false;

    options.forEach(opt => {
      opt.addEventListener('click', () => {
        if (cardDone) return;

        if (mode === 'exam') {
          // Exam mode: just highlight selected, no reveal
          options.forEach(o => {
            o.classList.remove('selected');
            // sync hidden radio/checkbox
            const inp = o.querySelector('input[type=radio]');
            if (inp) inp.checked = false;
          });
          opt.classList.add('selected');
          const inp = opt.querySelector('input[type=radio]');
          if (inp) { inp.checked = true; inp.dispatchEvent(new Event('change')); }
          // Count this card as answered if not already
          if (!card.dataset.answered) {
            card.dataset.answered = '1';
            answered++;
            updateProgress(answered, total);
            if (answeredCnt) answeredCnt.textContent = answered;
          }
          // Enable submit when all answered
          if (submitBtn && answered === total) {
            submitBtn.disabled = false;
            submitBtn.classList.add('le-btn-primary');
          }
          return;
        }

        // Interactive mode: immediate feedback
        cardDone = true;
        card.classList.add('answered');
        const chosen = opt.dataset.value;

        options.forEach(o => {
          o.classList.add('locked');
          const oVal  = o.dataset.value;
          const fbEl  = o.querySelector('.le-option-feedback');
          const inp   = o.querySelector('input[type=radio]');

          if (correctVal) {
            // We know the correct answer client-side
            if (oVal === correctVal) {
              o.classList.add('correct');
              if (fbEl) fbEl.textContent = '✓';
            } else if (oVal === chosen) {
              o.classList.add('wrong');
              if (fbEl) fbEl.textContent = '✗';
            }
          } else {
            // No client-side check — just mark selected
            if (oVal === chosen) {
              o.classList.add('selected');
            }
          }
          if (inp) inp.checked = (oVal === chosen);
        });

        if (correctVal) {
          if (chosen === correctVal) {
            correct++;
            showScoreFloat(correct, total);
          } else {
            showScoreFloat(correct, total);
          }
        }

        answered++;
        updateProgress(answered, total);
        if (answeredCnt) answeredCnt.textContent = answered;

        if (explanation) {
          explanation.classList.add('visible');
        }

        // Enable submit when all answered (interactive)
        if (submitBtn && answered === total) {
          submitBtn.disabled = false;
          submitBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      });
    });
  });

  // Disable submit until all answered (both modes)
  if (submitBtn && (mode === 'interactive' || mode === 'exam')) {
    submitBtn.disabled = true;
  }
}

/* ── Exam form — warn before leaving ────────────────────── */
function initExamGuard() {
  const form = document.getElementById('le-exam-form');
  if (!form) return;
  let submitted = false;
  form.addEventListener('submit', () => { submitted = true; });
  window.addEventListener('beforeunload', e => {
    if (!submitted) {
      e.preventDefault();
      e.returnValue = 'Votre examen est en cours. Voulez-vous vraiment quitter ?';
    }
  });
}

/* ── Score counter animation (result page) ───────────────── */
function animateScore() {
  document.querySelectorAll('[data-count-to]').forEach(el => {
    const target = parseInt(el.dataset.countTo, 10);
    const duration = parseInt(el.dataset.countDuration || '800', 10);
    const start = performance.now();
    const update = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      el.textContent = Math.round(eased * target);
      if (t < 1) requestAnimationFrame(update);
      else el.classList.add('le-score-animate');
    };
    requestAnimationFrame(update);
  });
}

/* ── Skill bars animation (result page) ─────────────────── */
function animateSkillBars() {
  const bars = document.querySelectorAll('.le-skill-bar-fill[data-pct]');
  if (!bars.length) return;
  setTimeout(() => {
    bars.forEach(b => {
      b.style.width = b.dataset.pct + '%';
      // Color coding
      const pct = parseInt(b.dataset.pct, 10);
      if (pct >= 75)      b.style.background = 'linear-gradient(90deg,#2E7D32,#4CAF50)';
      else if (pct >= 50) b.style.background = 'linear-gradient(90deg,#E65100,#FF9800)';
      else                b.style.background = 'linear-gradient(90deg,#b91c1c,#ef4444)';
    });
  }, 200);
}

/* ── Search filter (lesson list) ─────────────────────────── */
function initLessonFilter() {
  const input = document.getElementById('le-search');
  if (!input) return;
  input.addEventListener('input', () => {
    const q = input.value.toLowerCase().trim();
    document.querySelectorAll('.le-lesson-card').forEach(card => {
      const name = card.querySelector('.le-lesson-name');
      const match = !q || (name && name.textContent.toLowerCase().includes(q));
      card.style.display = match ? '' : 'none';
    });
  });
}

/* ── Global progress (lesson list) ──────────────────────── */
function initGlobalProgress() {
  const bar   = document.getElementById('le-global-fill');
  const label = document.getElementById('le-global-label');
  const pctEl = document.getElementById('le-global-pct');
  if (!bar) return;
  const total = document.querySelectorAll('.le-lesson-card').length;
  const done  = document.querySelectorAll('.le-lesson-card.done').length;
  const pct   = total ? Math.round(done / total * 100) : 0;
  setTimeout(() => { bar.style.width = pct + '%'; }, 100);
  if (label) label.textContent = done + '/' + total + ' leçons terminées';
  if (pctEl) pctEl.textContent = pct + '%';
}

/* ── Tooltips on skill badges ────────────────────────────── */
function initSkillTooltips() {
  const tips = {
    READING:        'Compréhension écrite',
    LISTENING:      'Compréhension orale',
    WRITING:        'Expression écrite',
    SPEAKING:       'Expression orale',
    USE_OF_ENGLISH: 'Grammaire / Vocabulaire',
    GRAMMATIK:      'Grammaire',
    WORTSCHATZ:     'Vocabulaire',
    HOREN:          'Compréhension orale',
    LESEN:          'Lecture',
    SPRECHEN:       'Expression orale',
    SCHREIBEN:      'Expression écrite',
  };
  document.querySelectorAll('[data-skill]').forEach(el => {
    const key = el.dataset.skill;
    if (tips[key]) el.title = tips[key];
  });
}

/* ── Smooth scroll to quiz on CTA click ─────────────────── */
function initQuizScroll() {
  document.querySelectorAll('[data-scroll-to]').forEach(btn => {
    btn.addEventListener('click', e => {
      const target = document.getElementById(btn.dataset.scrollTo);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });
}

/* ── Confirm submit (exam mode) ──────────────────────────── */
function initSubmitConfirm() {
  const form = document.getElementById('le-exam-form');
  if (!form) return;
  form.addEventListener('submit', e => {
    const answered = parseInt(document.getElementById('le-answered-count')?.textContent || '0', 10);
    const total    = document.querySelectorAll('[data-qcm-card]').length;
    if (answered < total) {
      if (!confirm(`Vous avez répondu à ${answered}/${total} questions. Soumettre quand même ?`)) {
        e.preventDefault();
      }
    }
  });
}

/* ── Init all ────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  initReadProgress();
  initInteractiveQCM();
  initExamGuard();
  animateScore();
  animateSkillBars();
  initLessonFilter();
  initGlobalProgress();
  initSkillTooltips();
  initQuizScroll();
  initSubmitConfirm();

  // Timer: read from data attribute on body
  const timerMin = parseInt(document.body.dataset.timerMinutes || '0', 10);
  if (timerMin > 0) initTimer(timerMin);
});
