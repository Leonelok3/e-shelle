(() => {
    'use strict';
    const form = document.getElementById('chat-form');
    if (!form) return;
    const input = document.getElementById('chat-input');
    const picker = document.getElementById('wa-file-input');
    const attach = document.getElementById('wa-attach-button');
    const remove = document.getElementById('wa-remove-file');
    const preview = document.getElementById('wa-file-preview');
    const description = document.getElementById('wa-file-description');
    const feedback = document.getElementById('wa-send-feedback');
    const send = form.querySelector('[type=submit]');
    const history = document.getElementById('chat-messages-container');
    const token = form.querySelector('[name=csrfmiddlewaretoken]').value;
    let busy = false;
    let lastHistory = '';
    let refreshing = false;
    const statusLabels = {envoye: '✓ Accepté par WhatsApp', livre: '✓✓ Livré', lu: '✓✓ Lu',
        echec: '⚠ Échec', simulation: 'Simulation', en_attente: '⏱ En attente'};
    function showFeedback(text, error = false) {
        feedback.textContent = text;
        feedback.classList.toggle('wa-error', error);
    }
    function choose() {
        const file = picker.files[0];
        if (!file) { preview.hidden = true; return; }
        const extension = file.name.split('.').pop().toLowerCase();
        const limit = ['jpg', 'jpeg', 'png'].includes(extension) ? 5
            : ['mp3', 'm4a', 'aac', 'amr', 'ogg', 'mp4', '3gp'].includes(extension) ? 16 : 25;
        if (!file.size || file.size > limit * 1024 * 1024) {
            picker.value = ''; preview.hidden = true;
            showFeedback(`Fichier vide ou trop volumineux. Maximum ${limit} Mo pour ce format.`, true);
            return;
        }
        preview.hidden = false;
        description.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} Mo`;
        showFeedback(['mp3', 'm4a', 'aac', 'amr', 'ogg'].includes(extension)
            ? 'Audio sélectionné. Envoyez le texte séparément : WhatsApp ne prend pas en charge les légendes audio.'
            : 'Fichier prêt. Vous pouvez ajouter une légende avant de l’envoyer.');
    }
    attach.addEventListener('click', () => picker.click());
    picker.addEventListener('change', choose);
    remove.addEventListener('click', () => { picker.value = ''; preview.hidden = true; showFeedback(''); });
    function element(tag, className, text) {
        const node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
    }
    function mediaURL(value, download = false) {
        const url = new URL(value, window.location.origin);
        if (url.origin !== window.location.origin || !/^\/whatsapp\/media\/\d+\/$/.test(url.pathname)) return '';
        if (download) url.searchParams.set('download', '1');
        return url.href;
    }
    function renderMessage(message) {
        const wrapper = element('div', `wa-bubble-wrap ${message.direction === 'sortant' ? 'sortant' : 'entrant'}`);
        const bubble = element('div', 'wa-bubble-chat');
        const url = message.media_download_url ? mediaURL(message.media_download_url) : '';
        if (message.has_media && url) {
            const container = element('div', 'wa-media-container');
            if (message.is_image) {
                const link = element('a'); link.href = url; link.target = '_blank'; link.rel = 'noopener';
                const image = element('img', 'wa-bubble-img'); image.src = url; image.alt = message.display_filename || 'Image WhatsApp'; image.loading = 'lazy';
                image.addEventListener('error', () => { image.hidden = true; link.textContent = 'Image indisponible — réessayer'; });
                link.append(image); container.append(link);
            } else if (message.is_audio || message.is_video) {
                const player = element(message.is_audio ? 'audio' : 'video', message.is_audio ? 'wa-bubble-audio' : 'wa-bubble-video');
                player.controls = true; player.preload = 'none'; player.src = url; container.append(player);
            } else {
                const card = element('div', 'wa-bubble-doc-card');
                card.append(element('span', 'wa-doc-icon-wrap', '📄'));
                const details = element('div', 'wa-doc-details');
                details.append(element('span', 'wa-doc-title', message.display_filename || 'Document WhatsApp'));
                details.append(element('span', 'wa-doc-sub', message.media_size ? `${(message.media_size / 1024).toFixed(1)} Ko` : 'Pièce jointe WhatsApp'));
                card.append(details); container.append(card);
            }
            const link = element('a', 'wa-doc-btn wa-download-link', '↓ Télécharger');
            link.href = mediaURL(message.media_download_url, true); container.append(link); bubble.append(container);
        }
        if (message.texte && (!message.is_document || message.texte !== message.display_filename)) {
            bubble.append(element('div', 'wa-bubble-caption', message.texte));
        }
        if (message.erreur && message.statut === 'echec') bubble.append(element('div', 'wa-send-feedback wa-error', message.erreur));
        const footer = element('div', 'wa-bubble-footer');
        footer.append(element('span', '', `${message.date} · ${message.heure}`));
        if (message.direction === 'sortant') footer.append(element('span', 'wa-tick', statusLabels[message.statut] || '⏱'));
        wrapper.append(bubble, footer);
        return wrapper;
    }
    async function refresh() {
        if (refreshing || document.hidden || !navigator.onLine) return;
        if (Array.from(history.querySelectorAll('audio,video')).some(player => !player.paused)) return;
        refreshing = true;
        try {
            const response = await fetch(form.dataset.detailUrl, {credentials: 'same-origin'});
            if (!response.ok) return;
            const data = await response.json();
            const signature = JSON.stringify(data.messages);
            if (signature === lastHistory) return;
            const atBottom = history.scrollHeight - history.scrollTop - history.clientHeight < 90;
            const position = history.scrollTop;
            history.replaceChildren(...data.messages.map(renderMessage));
            lastHistory = signature;
            history.scrollTop = atBottom ? history.scrollHeight : position;
        } catch (_) { /* Preserve already loaded history during a connection failure. */ }
        finally { refreshing = false; }
    }
    form.addEventListener('submit', async event => {
        event.preventDefault();
        const text = input.value.trim();
        const file = picker.files[0];
        if (busy || (!text && !file)) return;
        busy = true;
        [send, attach, remove, picker, input].forEach(node => { node.disabled = true; });
        send.textContent = 'Envoi…';
        showFeedback(file ? 'Transfert du fichier vers WhatsApp…' : 'Envoi du message…');
        const data = new FormData();
        data.append('texte', text);
        if (file) data.append('fichier', file);
        try {
            const response = await fetch(form.dataset.sendUrl, {method: 'POST',
                headers: {'X-CSRFToken': token}, body: data, credentials: 'same-origin'});
            let result;
            try { result = await response.json(); }
            catch (_) { throw new Error(response.status === 413 ? 'Le serveur refuse ce fichier : taille trop importante.' : 'Réponse du serveur indisponible. Vérifiez l’historique avant de réessayer.'); }
            if (!response.ok || !result.success) throw new Error(result.erreur || result.error || 'Envoi refusé.');
            input.value = ''; picker.value = ''; preview.hidden = true;
            showFeedback(result.simulation ? 'Simulation : aucun fichier envoyé au client.' : 'Accepté par WhatsApp. La confirmation de livraison apparaît dans le fil.');
            await refresh(); history.scrollTop = history.scrollHeight;
        } catch (error) {
            showFeedback(`${error.message} Votre brouillon et votre fichier sont conservés.`, true);
            await refresh();
        } finally {
            busy = false;
            [send, attach, remove, picker, input].forEach(node => { node.disabled = false; });
            send.textContent = 'Envoyer ➤'; input.focus();
        }
    });
    input.addEventListener('keydown', event => {
        if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); form.requestSubmit(); }
    });
    refresh();
    setInterval(refresh, 4000);
    document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
})();
