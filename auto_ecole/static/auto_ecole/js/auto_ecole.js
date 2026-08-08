document.addEventListener('DOMContentLoaded', function(){
  // Initialize Leaflet map if available
  function initMap(){
    if(typeof L === 'undefined') return;
    var map = L.map('ae-map', {scrollWheelZoom:false}).setView([3.9, 11.5], 6);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{
      attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);

    // collect schools with coords
    var schoolEls = document.querySelectorAll('.ae-school');
    var bounds = [];
    schoolEls.forEach(function(el){
      var lat = parseFloat(el.getAttribute('data-lat'));
      var lon = parseFloat(el.getAttribute('data-lon'));
      if(!isNaN(lat) && !isNaN(lon)){
        var name = el.querySelector('.ae-school-info strong').innerText.trim();
        var marker = L.marker([lat, lon]).addTo(map).bindPopup('<strong>'+name+'</strong>');
        bounds.push([lat, lon]);
      }
    });
    if(bounds.length){
      map.fitBounds(bounds, {padding:[40,40]});
    }
  }

  // Simple search/filter for schools and courses
  function initSearch(){
    var input = document.getElementById('ae-search-input');
    if(!input) return;
    var schoolEls = Array.from(document.querySelectorAll('.ae-school'));
    var courseEls = Array.from(document.querySelectorAll('.ae-card'));

    function normalize(s){ return (s||'').toLowerCase(); }
    input.addEventListener('input', function(ev){
      var q = normalize(ev.target.value);
      // schools
      schoolEls.forEach(function(el){
        var name = normalize(el.querySelector('.ae-school-info strong').innerText);
        var city = normalize(el.querySelector('.ae-school-city').innerText);
        var show = q === '' || name.indexOf(q) !== -1 || city.indexOf(q) !== -1;
        el.style.display = show ? '' : 'none';
      });
      // courses: show card if school name or title matches
      courseEls.forEach(function(card){
        var title = normalize(card.querySelector('.ae-course-title').innerText);
        var meta = normalize((card.querySelector('.ae-course-meta')||{}).innerText);
        var summary = normalize((card.querySelector('.ae-course-summary')||{}).innerText);
        var show = q === '' || title.indexOf(q) !== -1 || meta.indexOf(q) !== -1 || summary.indexOf(q) !== -1;
        card.style.display = show ? '' : 'none';
      });
    });
  }

  initMap();
  initSearch();

});
