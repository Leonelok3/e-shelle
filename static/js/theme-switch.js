(function(){
  const KEY = 'imm97_theme';
  const root = document.querySelector('body.home');
  if(!root) return;

  const btn = document.getElementById('theme-toggle');
  const label = document.getElementById('theme-label');

  function setTheme(t){
    if(t==='light'){
      root.setAttribute('data-theme','light');
      label && (label.textContent='Light');
    } else {
      root.removeAttribute('data-theme');
      label && (label.textContent='Dark');
    }
    try{ localStorage.setItem(KEY, t); }catch(e){}
  }

  // init from storage
  try{
    const stored = localStorage.getItem(KEY);
    if(stored) setTheme(stored);
  }catch(e){}

  if(btn){
    btn.addEventListener('click', function(){
      const cur = root.getAttribute('data-theme')==='light' ? 'light' : 'dark';
      const next = cur==='light' ? 'dark' : 'light';
      setTheme(next);
    });
  }
})();
