/**
 * Counter Animations — Animate stat numbers from 0 to target on scroll
 */
(function(){
  if(!('IntersectionObserver' in window)) return;

  const counters = document.querySelectorAll('.stat-item__value');
  if(!counters.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if(entry.isIntersecting && !entry.target.classList.contains('counted')){
        animateCounter(entry.target);
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  function animateCounter(el){
    el.classList.add('counted');
    
    const text = el.textContent.trim();
    // Extract number from text like "12 000+" or "98%"
    const numStr = text.replace(/\D/g, '');
    const target = parseInt(numStr) || 0;
    const suffix = text.replace(/\d/g, '').trim();

    let current = 0;
    const duration = 1800; // ms
    const start = Date.now();

    function animate(){
      const now = Date.now();
      const progress = Math.min((now - start) / duration, 1);
      
      current = Math.floor(progress * target);
      
      // Format number with spaces (French style)
      let formattedNum = current.toString();
      if(current >= 1000){
        formattedNum = current.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
      }
      
      el.textContent = formattedNum + (suffix ? ' ' + suffix : '');
      
      if(progress < 1){
        requestAnimationFrame(animate);
      }
    }

    animate();
  }

  counters.forEach(counter => observer.observe(counter));
})();
