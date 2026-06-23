const root = document.querySelector('[data-status-url]');

function statusLabel(status) {
    return {
        draft: 'Brouillon',
        running: 'Génération en cours',
        done: 'Terminé',
        failed: 'Échec',
    }[status] || status;
}

async function pollStatus() {
    if (!root) return;
    const response = await fetch(root.dataset.statusUrl);
    const data = await response.json();

    document.getElementById('project-title').textContent = data.title || 'Génération en cours';
    document.getElementById('progress-bar').style.width = `${data.progress}%`;
    document.getElementById('current-step').textContent = data.current_step || '';
    document.getElementById('status').textContent = statusLabel(data.status);
    document.getElementById('error').textContent = data.error_message || '';

    if (data.status === 'done' && data.final_video_url) {
        const zone = document.getElementById('video-zone');
        if (!zone.querySelector('video')) {
            zone.innerHTML = `
                <div class="video-container-box">
                    <video controls class="video-player-premium" src="${data.final_video_url}"></video>
                    <div class="download-bar">
                        <a class="download-btn-premium" href="${data.final_video_url}" download>
                            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/></svg>
                            Télécharger le fichier MP4
                        </a>
                    </div>
                </div>
            `;
        }
        return;
    }
    if (data.status !== 'failed') {
        setTimeout(pollStatus, 2000);
    }
}

pollStatus();
