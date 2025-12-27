// =========================================================
// 🎧 TEF COMPRÉHENSION ORALE - VÉRIFICATION EXERCICES
// =========================================================

document.addEventListener('DOMContentLoaded', function() {
  console.log('🔥 Script TEF CO chargé avec succès');

  const checkButtons = document.querySelectorAll('.btn-check');
  
  checkButtons.forEach(btn => {
    btn.addEventListener('click', function(e) {
      e.preventDefault();
      
      console.log('✅ Bouton vérifier cliqué');
      
      const form = this.closest('form');
      const correct = form.dataset.correct.trim().toUpperCase();
      const checked = form.querySelector('input:checked');
      const feedback = form.querySelector('.feedback');
      const allLabels = form.querySelectorAll('.option');

      allLabels.forEach(label => {
        label.style.backgroundColor = '';
        label.style.border = '';
      });

      if (!checked) {
        feedback.textContent = '❗ Veuillez choisir une réponse';
        feedback.style.color = '#f59e0b';
        feedback.style.fontWeight = 'bold';
        feedback.style.marginTop = '12px';
        feedback.style.display = 'block';
        return;
      }

      const userAnswer = checked.value.trim().toUpperCase();
      console.log('Réponse:', userAnswer, '| Correct:', correct);

      form.querySelectorAll('input[type="radio"]').forEach(input => {
        input.disabled = true;
      });

      if (userAnswer === correct) {
        feedback.innerHTML = '✅ <strong>Bonne réponse !</strong>';
        feedback.style.color = '#22c55e';
        feedback.style.fontWeight = 'bold';
        feedback.style.marginTop = '12px';
        feedback.style.display = 'block';
        
        const parentLabel = checked.closest('.option');
        parentLabel.style.backgroundColor = 'rgba(34, 197, 94, 0.15)';
        parentLabel.style.border = '2px solid #22c55e';
        parentLabel.style.transition = 'all 0.3s ease';
      } else {
        feedback.innerHTML = '❌ Mauvaise réponse. Réponse correcte : <strong>' + correct + '</strong>';
        feedback.style.color = '#ef4444';
        feedback.style.fontWeight = 'bold';
        feedback.style.marginTop = '12px';
        feedback.style.display = 'block';
        
        const wrongLabel = checked.closest('.option');
        wrongLabel.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
        wrongLabel.style.border = '2px solid #ef4444';
        wrongLabel.style.transition = 'all 0.3s ease';
        
        allLabels.forEach(label => {
          const input = label.querySelector('input');
          if (input && input.value.trim().toUpperCase() === correct) {
            label.style.backgroundColor = 'rgba(34, 197, 94, 0.15)';
            label.style.border = '2px solid #22c55e';
            label.style.transition = 'all 0.3s ease';
          }
        });
      }

      this.style.opacity = '0';
      this.style.transform = 'scale(0.8)';
      this.style.transition = 'all 0.3s ease';
      setTimeout(() => {
        this.style.display = 'none';
      }, 300);
    });
  });
});
