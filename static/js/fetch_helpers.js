(function(window){
  async function postJson(url, payload, opts = {}) {
    const token = window.getCSRF ? window.getCSRF() : (window.csrftoken || '');
    const res = await fetch(url, {
      method: opts.method || "POST",
      credentials: opts.credentials || 'same-origin',
      headers: Object.assign({
        "Content-Type": "application/json",
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest"
      }, opts.headers || {}),
      body: payload !== undefined ? JSON.stringify(payload) : undefined
    });
    // If response is not JSON or not OK, throw useful error
    if (!res.ok) {
      const text = await res.text().catch(()=>null);
      const err = new Error(`HTTP ${res.status} ${res.statusText}`);
      err.status = res.status;
      err.body = text;
      throw err;
    }
    // Try parse JSON safely
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      return res.json();
    } else {
      const text = await res.text();
      return text;
    }
  }

  window.postJson = postJson;
})(window);