/**
 * E-Shelle Love — Messaging JS
 * Gestion de la messagerie en temps réel (polling AJAX)
 */

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

class MessagingManager {
    constructor() {
        this.conversationId = document.getElementById('conversation-data')?.dataset.convId;
        this.monProfilId = parseInt(document.getElementById('conversation-data')?.dataset.monProfilId);
        this.lastMessageId = null;
        this.pollingInterval = null;
        this.isTyping = false;
        this.init();
    }

    init() {
        if (!this.conversationId) return;

        this.bindSendForm();
        this.scrollToBottom();
        this.setLastMessageId();
        this.startPolling();
        this.bindInputEvents();
    }

    setLastMessageId() {
        const msgs = document.querySelectorAll('.message-bubble');
        if (msgs.length > 0) {
            const last = msgs[msgs.length - 1];
            this.lastMessageId = parseInt(last.dataset.messageId) || 0;
        }
    }

    bindSendForm() {
        const form = document.getElementById('message-form');
        const input = document.getElementById('message-input');
        const btn = document.getElementById('btn-send');

        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const contenu = input.value.trim();
            if (!contenu) return;

            btn.disabled = true;
            input.value = '';

            await this.sendMessage(contenu);

            btn.disabled = false;
            input.focus();
        });

        // Envoyer avec Enter (Shift+Enter = nouvelle ligne)
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit'));
            }
        });
    }

    async sendMessage(contenu) {
        try {
            const resp = await fetch('/rencontres/ajax/envoyer-message/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    conversation_id: this.conversationId,
                    contenu,
                }),
            });
            const data = await resp.json();

            if (data.success) {
                this.appendMessage(data.message, true);
                this.updateMsgsCounter(data.msgs_restants);
            } else if (data.limite_atteinte) {
                showLimitModal(data.message);
            } else {
                showToast(data.error || 'Erreur lors de l\'envoi', 'error');
            }
        } catch (err) {
            showToast('Erreur réseau. Veuillez réessayer.', 'error');
        }
    }

    appendMessage(msg, isMine) {
        const container = document.getElementById('messages-container');
        if (!container) return;

        const bubble = document.createElement('div');
        bubble.className = `message-wrapper ${isMine ? 'sent-wrapper' : 'received-wrapper'}`;
        bubble.dataset.messageId = msg.id;

        const date = new Date(msg.date_envoi);
        const timeStr = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

        bubble.innerHTML = `
            <div class="message-bubble ${isMine ? 'sent' : 'received'}">
                ${escapeHtml(msg.contenu)}
                <div class="message-time">
                    ${timeStr}
                    ${isMine ? '<span class="read-tick">✓</span>' : ''}
                </div>
            </div>
        `;

        container.appendChild(bubble);
        this.scrollToBottom();

        if (msg.id) {
            this.lastMessageId = Math.max(this.lastMessageId || 0, msg.id);
        }
    }

    startPolling() {
        // Vérifier les nouveaux messages toutes les 5 secondes
        this.pollingInterval = setInterval(() => this.checkNewMessages(), 5000);
    }

    async checkNewMessages() {
        if (!this.lastMessageId) return;

        try {
            const resp = await fetch(
                `/rencontres/ajax/profils/?conv_id=${this.conversationId}&since=${this.lastMessageId}`
            );
            // Note: endpoint simplifié — en prod utiliser un endpoint dédié
        } catch (err) {
            // Silencieux
        }
    }

    scrollToBottom() {
        const container = document.getElementById('messages-container');
        if (container) {
            container.scrollTop = container.scrollHeight;
        }
    }

    bindInputEvents() {
        const input = document.getElementById('message-input');
        if (!input) return;

        // Auto-resize textarea si applicable
        input.addEventListener('input', () => {
            if (input.tagName === 'TEXTAREA') {
                input.style.height = 'auto';
                input.style.height = Math.min(120, input.scrollHeight) + 'px';
            }
        });
    }

    updateMsgsCounter(restants) {
        const el = document.getElementById('msgs-counter');
        if (el) {
            if (restants === -1) {
                el.textContent = '∞ messages';
            } else if (restants === 0) {
                el.textContent = 'Limite atteinte';
                el.style.color = 'var(--love-danger)';
                document.getElementById('message-input')?.setAttribute('disabled', true);
                document.getElementById('btn-send')?.setAttribute('disabled', true);
            } else {
                el.textContent = `${restants} messages restants aujourd'hui`;
            }
        }
    }

    destroy() {
        if (this.pollingInterval) clearInterval(this.pollingInterval);
    }
}

// ===== TOAST NOTIFICATIONS =====
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();

    const toast = document.createElement('div');
    toast.className = `toast-item toast-${type}`;
    toast.textContent = message;

    container.appendChild(toast);
    setTimeout(() => toast.classList.add('visible'), 10);
    setTimeout(() => {
        toast.classList.remove('visible');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
        position: fixed; top: 80px; right: 1rem; z-index: 9999;
        display: flex; flex-direction: column; gap: 0.5rem;
    `;
    document.body.appendChild(container);
    return container;
}

// ===== MODAL LIMITE =====
function showLimitModal(message) {
    const modal = document.createElement('div');
    modal.className = 'match-popup active';
    modal.innerHTML = `
        <div class="popup-content">
            <div style="font-size:2.5rem;margin-bottom:1rem">⚡</div>
            <h3 class="match-title" style="font-size:1.5rem">Limite atteinte</h3>
            <p style="color:var(--love-muted);margin-bottom:1.5rem">${escapeHtml(message)}</p>
            <a href="/rencontres/premium/" class="btn-premium">Passer en Premium</a>
            <button onclick="this.closest('.match-popup').remove()"
                style="background:none;border:none;color:var(--love-muted);margin-top:1rem;cursor:pointer;display:block;width:100%">
                Plus tard
            </button>
        </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('messages-container')) {
        window.messaging = new MessagingManager();
    }
});
