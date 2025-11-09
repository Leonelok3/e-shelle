(function(window){
  function getCookie(name) {
    if (!document.cookie) return null;
    const match = document.cookie.split('; ').find(row => row.startsWith(name + '='));
    return match ? decodeURIComponent(match.split('=')[1]) : null;
  }

  function getCSRFFromMeta() {
    const meta = document.querySelector('meta[name="csrf-token"], meta[name="csrfmiddlewaretoken"]');
    return meta ? meta.getAttribute('content') : null;
  }

  function getCSRFFromForm() {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : null;
  }

  function getCSRF() {
    const fromCookie = getCookie('csrftoken');
    if (fromCookie) return fromCookie;
    const fromMeta = getCSRFFromMeta();
    if (fromMeta) return fromMeta;
    const fromForm = getCSRFFromForm();
    if (fromForm) return fromForm;
    return '';
  }

  // Expose global util
  window.getCSRF = getCSRF;
  window.csrftoken = getCSRF();
})(window);