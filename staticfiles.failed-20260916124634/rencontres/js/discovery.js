/**
 * E-Shelle Love — Discovery Page JS
 * Gestion du swipe, des likes, et de la découverte de profils
 */

// Récupérer le cookie CSRF
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}

// ===== SWIPE MANAGER =====
class SwipeManager {
    constructor(cardElement, onLike, onPass, onSuperLike) {
        this.card = cardElement;
        this.onLike = onLike;
        this.onPass = onPass;
        this.onSuperLike = onSuperLike;
        this.startX = 0;
        this.startY = 0;
        this.currentX = 0;
        this.isDragging = false;
        this.threshold = 100;
        this.init();
    }

    init() {
        // Touch
        this.card.addEventListener('touchstart', e => this.onStart(e), { passive: true });
        this.card.addEventListener('touchmove', e => this.onMove(e), { passive: false });
        this.card.addEventListener('touchend', e => this.onEnd(e));

        // Mouse (desktop)
        this.card.addEventListener('mousedown', e => this.onStart(e));
        document.addEventListener('mousemove', e => this.onMove(e));
        document.addEventListener('mouseup', e => this.onEnd(e));
    }

    getX(e) {
        return e.touches ? e.touches[0].clientX : e.clientX;
    }

    getY(e) {
        return e.touches ? e.touches[0].clientY : e.clientY;
    }

    onStart(e) {
        this.isDragging = true;
        this.startX = this.getX(e);
        this.startY = this.getY(e);
        this.card.style.transition = 'none';
    }

    onMove(e) {
        if (!this.isDragging) return;

        const x = this.getX(e) - this.startX;
        const y = this.getY(e) - this.startY;

        // Empêcher le scroll vertical si swipe horizontal
        if (Math.abs(x) > Math.abs(y) && e.cancelable) {
            e.preventDefault();
        }

        this.currentX = x;
        const rotation = x * 0.08;
        this.card.style.transform = `translateX(${x}px) rotate(${rotation}deg)`;

        // Feedback visuel
        const likeOverlay = this.card.querySelector('.overlay-like');
        const passOverlay = this.card.querySelector('.overlay-pass');

        if (x > 40) {
            if (likeOverlay) likeOverlay.style.opacity = Math.min(1, (x - 40) / 60);
            if (passOverlay) passOverlay.style.opacity = 0;
        } else if (x < -40) {
            if (passOverlay) passOverlay.style.opacity = Math.min(1, (-x - 40) / 60);
            if (likeOverlay) likeOverlay.style.opacity = 0;
        } else {
            if (likeOverlay) likeOverlay.style.opacity = 0;
            if (passOverlay) passOverlay.style.opacity = 0;
        }
    }

    onEnd(e) {
        if (!this.isDragging) return;
        this.isDragging = false;

        const endX = e.changedTouches ? e.changedTouches[0].clientX : e.clientX;
        const x = endX - this.startX;

        if (Math.abs(x) > this.threshold) {
            if (x > 0) {
                this.animateExit('right');
                setTimeout(() => this.onLike && this.onLike(), 250);
            } else {
                this.animateExit('left');
                setTimeout(() => this.onPass && this.onPass(), 250);
            }
        } else {
            this.resetCard();
        }
    }

    animateExit(direction) {
        const x = direction === 'right' ? window.innerWidth + 100 : -window.innerWidth - 100;
        const rotation = direction === 'right' ? 20 : -20;
        this.card.style.transition = 'transform 0.4s ease';
        this.card.style.transform = `translateX(${x}px) rotate(${rotation}deg)`;
    }

    resetCard() {
        this.card.style.transition = 'transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275)';
        this.card.style.transform = 'translateX(0) rotate(0deg)';
        const likeOverlay = this.card.querySelector('.overlay-like');
        const passOverlay = this.card.querySelector('.overlay-pass');
        if (likeOverlay) likeOverlay.style.opacity = 0;
        if (passOverlay) passOverlay.style.opacity = 0;
    }

    destroy() {
        document.removeEventListener('mousemove', this.onMove);
        document.removeEventListener('mouseup', this.onEnd);
    }
}

// ===== GESTIONNAIRE DE PROFILS =====
class DiscoveryManager {
    constructor() {
        this.profils = JSON.parse(document.getElementById('profils-data')?.textContent || '[]');
        this.currentIndex = 0;
        this.swipeManager = null;
        this.isLoading = false;
        this.init();
    }

    init() {
        this.renderCurrentCard();
        this.bindButtons();
        this.startNotifPolling();
    }

    getCurrentProfil() {
        return this.profils[this.currentIndex] || null;
    }

    renderCurrentCard() {
        const container = document.getElementById('cards-container');
        if (!container) return;

        container.innerHTML = '';

        // Afficher jusqu'à 3 cartes (effet stack)
        for (let i = Math.min(this.currentIndex + 2, this.profils.length - 1); i >= this.currentIndex; i--) {
            const profil = this.profils[i];
            if (profil) {
                const card = this.createCard(profil);
                container.appendChild(card);
            }
        }

        // Attacher le swipe à la carte du dessus
        const topCard = container.querySelector('.profile-card');
        if (topCard) {
            const profil = this.getCurrentProfil();
            if (this.swipeManager) this.swipeManager.destroy();
            this.swipeManager = new SwipeManager(
                topCard,
                () => this.handleLike(profil.id),
                () => this.handlePass(profil.id),
                () => this.handleSuperLike(profil.id)
            );
        } else {
            this.showEmptyState();
        }
    }

    createCard(profil) {
        const card = document.createElement('div');
        card.className = 'profile-card slide-up';
        card.dataset.profilId = profil.id;

        const tone = Number(profil.id || 0) % 5;
        const initial = escapeHtml((profil.prenom || '?').charAt(0).toUpperCase());
        const photoHtml = profil.photo
            ? `<img src="${profil.photo}" alt="${profil.prenom}" class="card-photo" loading="lazy">`
            : `<div class="card-photo-placeholder avatar-tone-${tone}"><span>${initial}</span></div>`;

        const badgesHtml = [
            profil.badge_verifie ? '<span class="badge-verifie">✓ Vérifié</span>' : '',
            profil.est_premium ? '<span class="badge-premium-gold">⭐ Premium</span>' : '',
        ].filter(Boolean).join(' ');

        const tagsHtml = [
            profil.religion ? `<span class="tag">${profil.religion}</span>` : '',
            ...(profil.langues || []).map(l => `<span class="tag">${l}</span>`),
        ].filter(Boolean).slice(0, 3).join('');

        const scoreHtml = profil.score
            ? `<span class="compat-score">⭐ ${profil.score}% compatible</span>`
            : '';

        const distanceHtml = profil.distance_km && profil.distance_km < 9000
            ? `📍 ${profil.ville}${profil.distance_km < 5000 ? ` · ${profil.distance_km} km` : ''}`
            : `📍 ${profil.ville}, ${profil.pays}`;

        card.innerHTML = `
            ${photoHtml}
            <div class="overlay-like">LIKE ❤️</div>
            <div class="overlay-pass">SUIVANT →</div>
            <div class="card-overlay">
                <div class="card-name">${escapeHtml(profil.prenom)}, ${profil.age} ans</div>
                <div class="card-location">${distanceHtml}</div>
                ${profil.profession ? `<div class="card-profession">💼 ${escapeHtml(profil.profession)}</div>` : ''}
                ${badgesHtml ? `<div style="margin-bottom:0.5rem">${badgesHtml}</div>` : ''}
                ${tagsHtml ? `<div class="card-tags">${tagsHtml}</div>` : ''}
                ${scoreHtml}
            </div>
        `;

        // Clic pour voir le profil (non-drag)
        card.addEventListener('click', (e) => {
            if (Math.abs(this.swipeManager?.currentX || 0) < 5) {
                window.location.href = `/rencontres/profil/${profil.id}/`;
            }
        });

        return card;
    }

    async handleLike(profilId, type = 'like') {
        try {
            const response = await fetch(`/rencontres/ajax/like/${profilId}/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ type }),
            });
            const data = await response.json();

            if (data.limite_atteinte) {
                showPremiumModal(data.type_like === 'super_like' ? 'super_like' : 'likes');
                return;
            }

            if (data.est_match) {
                showMatchPopup(data.profil_info, data.match_id);
            }

            this.updateLikesCounter(data.likes_restants);
            this.nextProfil();
        } catch (err) {
            console.error('Erreur like:', err);
            this.nextProfil();
        }
    }

    async handlePass(profilId) {
        try {
            await fetch(`/rencontres/ajax/passer/${profilId}/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
            });
        } catch (err) {
            console.error('Erreur pass:', err);
        }
        this.nextProfil();
    }

    handleSuperLike(profilId) {
        this.handleLike(profilId, 'super_like');
    }

    nextProfil() {
        this.currentIndex++;
        if (this.currentIndex >= this.profils.length - 2 && !this.isLoading) {
            this.loadMoreProfils();
        }
        this.renderCurrentCard();
    }

    async loadMoreProfils() {
        this.isLoading = true;
        try {
            const resp = await fetch(`/rencontres/ajax/profils/?offset=${this.profils.length}`);
            const data = await resp.json();
            if (data.profils && data.profils.length > 0) {
                this.profils.push(...data.profils);
            }
        } catch (err) {
            console.error('Erreur chargement:', err);
        } finally {
            this.isLoading = false;
        }
    }

    bindButtons() {
        document.getElementById('btn-like')?.addEventListener('click', () => {
            const profil = this.getCurrentProfil();
            if (profil) {
                const card = document.querySelector('.cards-stack .profile-card:first-child');
                if (card && this.swipeManager) this.swipeManager.animateExit('right');
                setTimeout(() => this.handleLike(profil.id), 200);
            }
        });

        document.getElementById('btn-pass')?.addEventListener('click', () => {
            const profil = this.getCurrentProfil();
            if (profil) {
                const card = document.querySelector('.cards-stack .profile-card:first-child');
                if (card && this.swipeManager) this.swipeManager.animateExit('left');
                setTimeout(() => this.handlePass(profil.id), 200);
            }
        });

        document.getElementById('btn-super-like')?.addEventListener('click', () => {
            const profil = this.getCurrentProfil();
            if (profil) {
                this.handleSuperLike(profil.id);
            }
        });
    }

    updateLikesCounter(restants) {
        const el = document.getElementById('likes-counter');
        if (el) {
            if (restants === -1) {
                el.textContent = '∞';
            } else {
                el.textContent = restants;
                if (restants === 0) el.closest('.likes-info')?.classList.add('limite');
            }
        }
    }

    showEmptyState() {
        const container = document.getElementById('cards-container');
        if (container) {
            container.innerHTML = `
                <div class="empty-state" style="text-align:center;padding:3rem 1rem;color:var(--love-muted)">
                    <div style="font-size:4rem;margin-bottom:1rem">💔</div>
                    <h3 style="color:var(--love-text)">Plus de profils disponibles</h3>
                    <p>Revenez plus tard ou élargissez vos critères de recherche.</p>
                    <a href="/rencontres/filtres/" class="btn-love-outline" style="margin-top:1rem">
                        Modifier les filtres
                    </a>
                </div>
            `;
        }
    }

    startNotifPolling() {
        // Vérifier les notifications toutes les 30 secondes
        setInterval(async () => {
            try {
                const resp = await fetch('/rencontres/ajax/notifications/');
                const data = await resp.json();
                updateNotifBadges(data);
            } catch (err) {
                // Silencieux
            }
        }, 30000);
    }
}

// ===== POPUP MATCH =====
function showMatchPopup(profilInfo, matchId) {
    if (!profilInfo) return;

    const popup = document.getElementById('match-popup');
    if (!popup) return;

    const nameEl = popup.querySelector('.match-name');
    const photoEl = popup.querySelector('.match-photo-other');
    const msgBtn = popup.querySelector('.btn-envoyer-message');

    if (nameEl) nameEl.textContent = profilInfo.prenom;
    if (photoEl && profilInfo.photo) photoEl.src = profilInfo.photo;
    if (msgBtn && matchId) {
        // Récupérer l'ID de conversation
        fetch(`/rencontres/match/nouveau/${matchId}/`)
            .then(r => r.json())
            .then(data => {
                if (data.conversation_url) {
                    msgBtn.href = data.conversation_url;
                }
            })
            .catch(() => {});
    }

    popup.classList.add('active');
    createConfetti();

    // Fermer automatiquement après 7 secondes
    setTimeout(() => popup.classList.remove('active'), 7000);

    popup.querySelector('.btn-close-popup')?.addEventListener('click', () => {
        popup.classList.remove('active');
    });
}

// ===== CONFETTI =====
function createConfetti() {
    const container = document.createElement('div');
    container.className = 'confetti-container';
    document.body.appendChild(container);

    const colors = ['#E8436A', '#FF8C42', '#6C63FF', '#FFD700', '#2ecc71', '#e74c3c'];

    for (let i = 0; i < 60; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = Math.random() * 100 + 'vw';
        piece.style.animationDelay = Math.random() * 1.5 + 's';
        piece.style.animationDuration = (2 + Math.random() * 2) + 's';
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.borderRadius = Math.random() > 0.5 ? '50%' : '0';
        piece.style.transform = `rotate(${Math.random() * 360}deg)`;
        container.appendChild(piece);
    }

    setTimeout(() => container.remove(), 4000);
}

// ===== MODAL PREMIUM =====
function showPremiumModal(raison) {
    const modal = document.getElementById('premium-modal');
    if (!modal) return;

    const messages = {
        'likes': "Vous avez utilisé vos 5 likes gratuits aujourd'hui. Premium débloque les likes illimités.",
        'messages': "Vous avez utilisé vos 5 messages gratuits aujourd'hui. Premium débloque les messages illimités.",
        'super_like': "Le super like gratuit du jour est utilisé. Premium débloque plus d'actions.",
        'filtres': "Les filtres avancés sont réservés aux membres premium.",
    };

    const msgEl = modal.querySelector('.premium-modal-message');
    if (msgEl) msgEl.textContent = messages[raison] || "Cette fonctionnalité est réservée aux membres premium.";

    modal.classList.add('active');

    modal.querySelector('.btn-close-premium')?.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
    });
}

// ===== NOTIFICATIONS =====
function updateNotifBadges(data) {
    const badges = {
        'notif-messages': data.nouveaux_messages,
        'notif-matchs': data.nouveaux_matchs,
        'notif-likes': data.nouveaux_likes,
        'notif-total': data.total,
    };

    Object.entries(badges).forEach(([id, count]) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = count;
            el.style.display = count > 0 ? 'flex' : 'none';
        }
    });
}

// ===== UTILS =====
function escapeHtml(str) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}

// ===== INIT =====
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('cards-container')) {
        window.discovery = new DiscoveryManager();
    }
});
