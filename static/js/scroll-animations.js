/**
 * Scroll-triggered fade-in animations
 * Applies .animate-in class when elements enter viewport
 */
(function(){
  if(!('IntersectionObserver' in window)) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if(entry.isIntersecting){
        entry.target.classList.add('animate-in');
        observer.unobserve(entry.target);
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });

  // Observe all service cards, why items, and section headers
  document.querySelectorAll('.service-card, .why-item, .section-header, .stat-item__value').forEach(el => {
    observer.observe(el);
  });
})();
