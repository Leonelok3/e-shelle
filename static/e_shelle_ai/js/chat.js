/**
 * E-Shelle AI — chat.js
 * Gestion du chat IA : SSE streaming, markdown, images, quota, mémoire.
 */
"use strict";

// ─── État global ─────────────────────────────────────────────────────────────
const State = {
  currentConvId: DJANGO_DATA.activeConvId,
  isStreaming:   false,
  quotaMessages: DJANGO_DATA.quotaMessages,
  quotaMsgUsed:  DJANGO_DATA.quotaMsgUsed,
  quotaMsgLimit: DJANGO_DATA.quotaMsgLimit,
};

// ─── Sélecteurs DOM ──────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const messageInput    = $("message-input");
const sendBtn         = $("send-btn");
const messagesList    = $("messages-list");
const messagesZone    = $("messages-zone");
const typingIndicator = $("typing-indicator");
const welcomeScreen   = $("welcome-screen");
const quotaDisplay    = $("quota-display");
const quotaBadge      = $("quota-badge");
const quotaFill       = $("quota-fill");
const headerConvTitle = $("header-conv-title");
const convList        = $("conv-list");

// ─── Init ─────────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Rendre le markdown des messages existants
  document.querySelectorAll(".markdown-content").forEach(el => {
    const raw = el.dataset.raw || el.textContent;
    el.innerHTML = renderMarkdown(raw);
  });

  scrollToBottom();
  autoResizeTextarea();
  setupEventListeners();
  updateQuotaUI(State.quotaMessages, State.quotaMsgUsed, State.quotaMsgLimit);

  // Raccourci Ctrl+K global
  document.addEventListener("keydown", e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault();
      messageInput.focus();
    }
  });
});

// ─── Event Listeners ─────────────────────────────────────────────────────────
function setupEventListeners() {
  // Envoi par bouton
  sendBtn.addEventListener("click", handleSend);

  // Entrée pour envoyer, Shift+Entrée pour saut de ligne
  messageInput.addEventListener("keydown", e => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });

  // Auto-resize textarea
  messageInput.addEventListener("input", () => {
    messageInput.style.height = "auto";
    messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + "px";
  });

  // Nouvelle conversation
  $("btn-new-conv").addEventListener("click", createNewConversation);

  // Sidebar mobile
  $("burger-btn").addEventListener("click", toggleSidebar);
  $("sidebar-overlay").addEventListener("click", closeSidebar);

  // Effacer mémoire
  $("btn-clear-memory").addEventListener("click", clearMemory);

  // Supprimer conversations (délégation)
  document.addEventListener("click", e => {
    if (e.target.classList.contains("conv-delete")) {
      e.preventDefault();
      e.stopPropagation();
      deleteConversation(e.target.dataset.id);
    }
  });

  // Suggestions
  document.querySelectorAll(".suggestion-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      messageInput.value = btn.dataset.msg;
      messageInput.dispatchEvent(new Event("input"));
      handleSend();
    });
  });
}

// ─── Envoi message ────────────────────────────────────────────────────────────
async function handleSend() {
  const text = messageInput.value.trim();
  if (!text || State.isStreaming) return;
  if (State.quotaMessages <= 0) {
    showToast("⚠️ Quota épuisé. Passez au plan Pro pour continuer.", "error");
    return;
  }

  // UI
  messageInput.value = "";
  messageInput.style.height = "auto";
  sendBtn.disabled = true;
  State.isStreaming = true;

  // Cacher le welcome screen
  if (welcomeScreen) welcomeScreen.style.display = "none";

  // Ajouter le message utilisateur
  appendMessage("user", text);
  scrollToBottom();

  // Afficher l'indicateur de frappe
  typingIndicator.classList.remove("hidden");
  scrollToBottom();

  // Appel API streaming
  await sendMessageStream(text);

  typingIndicator.classList.add("hidden");
  sendBtn.disabled = false;
  State.isStreaming = false;
  messageInput.focus();
}

async function sendMessageStream(text) {
  try {
    const body = JSON.stringify({
      message:         text,
      conversation_id: State.currentConvId,
    });

    const response = await fetch(DJANGO_DATA.chatApiUrl, {
      method: "POST",
      headers: {
        "Content-Type":      "application/json",
        "X-CSRFToken":       DJANGO_DATA.csrfToken,
        "Accept":            "text/event-stream",
      },
      body,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      if (response.status === 402) {
        showToast("⚠️ " + (err.error || "Quota dépassé."), "error");
        appendMessage("assistant", "❌ " + (err.error || "Quota dépassé. Passez au plan Pro."));
        return;
      }
      throw new Error(err.error || `Erreur HTTP ${response.status}`);
    }

    // Lecture du stream SSE
    const reader   = response.body.getReader();
    const decoder  = new TextDecoder();
    let   buffer   = "";
    let   aiMsgEl  = null;
    let   fullText = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // Garde le fragment incomplet

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const jsonStr = line.slice(6).trim();
        if (!jsonStr) continue;

        let data;
        try { data = JSON.parse(jsonStr); } catch { continue; }

        if (data.type === "meta") {
          // Mise à jour du conv ID
          if (data.conversation_id && !State.currentConvId) {
            State.currentConvId = data.conversation_id;
            // Mettre à jour l'URL sans rechargement
            history.replaceState({}, "", `/ai/c/${data.conversation_id}/`);
          }
        } else if (data.type === "chunk") {
          typingIndicator.classList.add("hidden");
          if (!aiMsgEl) {
            aiMsgEl = appendMessage("assistant", "", true);
          }
          fullText += data.text;
          updateStreamingMessage(aiMsgEl, fullText);
          scrollToBottom();
        } else if (data.type === "done") {
          // Mettre à jour le quota
          if (data.quota) {
            updateQuotaUI(data.quota.messages, data.quota.msg_used, data.quota.msg_limit);
            State.quotaMessages = data.quota.messages;
          }
          // Finaliser le markdown
          if (aiMsgEl) finalizeMessage(aiMsgEl, fullText);
        } else if (data.type === "error") {
          appendMessage("assistant", "⚠️ " + (data.text || "Erreur inattendue."));
        }
      }
    }

  } catch (err) {
    console.error("Stream error:", err);
    typingIndicator.classList.add("hidden");
    appendMessage("assistant", "⚠️ Une erreur est survenue. Veuillez réessayer.");
  }
}

// ─── DOM Messages ─────────────────────────────────────────────────────────────
function appendMessage(role, content, isStreaming = false) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const now = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });

  if (role === "user") {
    row.innerHTML = `
      <div class="message-bubble user">
        <div class="message-content">${escapeHtml(content)}</div>
        <div class="message-time">${now}</div>
      </div>`;
  } else {
    const contentHtml = isStreaming
      ? `<span class="stream-cursor">▌</span>`
      : renderMarkdown(content);
    row.innerHTML = `
      <div class="message-avatar">✦</div>
      <div class="message-bubble assistant">
        <div class="message-content markdown-content">${contentHtml}</div>
        <div class="message-actions">
          <span class="message-time">${now}</span>
          <button class="copy-btn" onclick="copyMessage(this)" title="Copier">⧉</button>
        </div>
      </div>`;
  }

  messagesList.appendChild(row);
  return role === "assistant" ? row.querySelector(".markdown-content") : null;
}

function updateStreamingMessage(el, text) {
  if (!el) return;
  // Affichage brut pendant le streaming + curseur
  el.innerHTML = renderMarkdown(text) + '<span class="stream-cursor" style="animation:blink 1s step-end infinite">▌</span>';
}

function finalizeMessage(el, fullText) {
  if (!el) return;
  el.innerHTML = renderMarkdown(fullText);
}

// ─── Markdown renderer ────────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return "";
  let html = escapeHtml(text);

  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm,  "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm,   "<h1>$1</h1>");

  // Bold & italic
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, "<strong><em>$1</em></strong>");
  html = html.replace(/\*\*(.+?)\*\*/g,     "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g,         "<em>$1</em>");

  // Code inline
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // Liens
  html = html.replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

  // Listes à puces
  html = html.replace(/^[\-\*] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/s, match =>
    "<ul>" + match + "</ul>"
  );

  // Listes numérotées
  html = html.replace(/^\d+\. (.+)$/gm, "<li>$1</li>");

  // Blockquote
  html = html.replace(/^&gt; (.+)$/gm, "<blockquote>$1</blockquote>");

  // HR
  html = html.replace(/^---$/gm, "<hr/>");

  // Highlight montants FCFA
  html = html.replace(/([\d\s,]+\s*FCFA)/g, '<span class="fcfa-highlight">$1</span>');
  html = html.replace(/([\d\s,]+\s*F CFA)/g, '<span class="fcfa-highlight">$1</span>');

  // Sauts de ligne → <br> (sauf dans les blocs déjà convertis)
  html = html.replace(/\n\n+/g, "</p><p>");
  html = html.replace(/\n/g, "<br/>");

  // Wrap dans paragraphes si pas déjà structuré
  if (!html.match(/^<(h[1-6]|ul|ol|blockquote|hr)/)) {
    html = `<p>${html}</p>`;
  }

  return html;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ─── Copier message ───────────────────────────────────────────────────────────
window.copyMessage = function(btn) {
  const bubble  = btn.closest(".message-bubble");
  const content = bubble.querySelector(".message-content");
  const text    = content.innerText || content.textContent;

  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "✓";
    setTimeout(() => btn.textContent = "⧉", 1500);
  });
};

// ─── Génération de médias IA ──────────────────────────────────────────────────
State.activeMediaType = "image";

window.openImageModal  = () => {
  $("image-modal").classList.remove("hidden");
  switchMediaTab("image");
};
window.closeImageModal = () => $("image-modal").classList.add("hidden");

window.switchMediaTab = function(type) {
  State.activeMediaType = type;
  const tabImage = $("tab-image");
  const tabVideo = $("tab-video");
  const imageOptions = $("image-options-row");
  const videoOptions = $("video-options-row");
  const btn = $("btn-generate-img");
  const input = $("img-prompt-input");
  
  if (type === "image") {
    tabImage.classList.add("active");
    tabImage.style.background = "var(--bg-glass)";
    tabImage.style.color = "#fff";
    tabVideo.classList.remove("active");
    tabVideo.style.background = "transparent";
    tabVideo.style.color = "var(--text-2)";
    imageOptions.classList.remove("hidden");
    videoOptions.classList.add("hidden");
    btn.textContent = "✦ Générer l'image";
    input.placeholder = "Décrivez votre image (ex: ndolé présenté sur assiette blanche...)";
  } else {
    tabVideo.classList.add("active");
    tabVideo.style.background = "var(--bg-glass)";
    tabVideo.style.color = "#fff";
    tabImage.classList.remove("active");
    tabImage.style.background = "transparent";
    tabImage.style.color = "var(--text-2)";
    imageOptions.classList.add("hidden");
    videoOptions.classList.remove("hidden");
    btn.textContent = "✦ Générer la vidéo";
    input.placeholder = "Décrivez votre vidéo (ex: un lion majestueux marchant dans la savane...)";
  }
};

window.generateMedia = async function() {
  const prompt = $("img-prompt-input").value.trim();
  if (!prompt) {
    showToast("Veuillez décrire le média souhaité.", "error");
    return;
  }

  if (State.activeMediaType === "image") {
    await runGenerateImage(prompt);
  } else {
    await runGenerateVideo(prompt);
  }
};

async function runGenerateImage(prompt) {
  const context = $("img-context-select").value;
  const btn = $("btn-generate-img");
  btn.disabled = true;
  btn.textContent = "⏳ Génération en cours…";

  if (welcomeScreen) welcomeScreen.style.display = "none";
  appendMessage("user", `📸 Génère une image : ${prompt}`);
  scrollToBottom();
  closeImageModal();
  $("img-prompt-input").value = "";

  try {
    const resp = await fetch(DJANGO_DATA.imageApiUrl, {
      method:  "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken":  DJANGO_DATA.csrfToken,
      },
      body: JSON.stringify({
        prompt,
        context,
        conversation_id: State.currentConvId,
      }),
    });

    const data = await resp.json();

    if (!resp.ok || data.error) {
      showToast("⚠️ " + (data.error || "Erreur génération image."), "error");
      const adgenHint = data.adgen_url ? `\n\n👉 Créer une pub avec AdGen : ${data.adgen_url}` : "";
      appendMessage("assistant", "⚠️ " + (data.error || "Impossible de générer l'image.") + adgenHint);
    } else {
      const row = document.createElement("div");
      row.className = "message-row assistant";
      row.innerHTML = `
        <div class="message-avatar">✦</div>
        <div class="message-bubble assistant">
          <div class="message-image-container">
            <img src="${data.image_url}" alt="Image générée" class="generated-image"/>
            <a href="${data.image_url}" download class="img-download-btn">⬇ Télécharger</a>
          </div>
          <div class="message-actions">
            <span class="message-time">${new Date().toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}</span>
          </div>
        </div>`;
      messagesList.appendChild(row);
      scrollToBottom();

      if (data.quota) updateQuotaUI(data.quota.messages, data.quota.msg_used, data.quota.msg_limit);
    }
  } catch (err) {
    showToast("Erreur réseau.", "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "✦ Générer l'image";
  }
}

async function runGenerateVideo(prompt) {
  const aspect_ratio = $("video-ratio-select").value;
  const btn = $("btn-generate-img");
  btn.disabled = true;
  btn.textContent = "⏳ Initialisation de la vidéo…";

  if (welcomeScreen) welcomeScreen.style.display = "none";
  appendMessage("user", `🎥 Génère une vidéo : ${prompt}`);
  scrollToBottom();
  closeImageModal();
  $("img-prompt-input").value = "";

  try {
    const resp = await fetch(DJANGO_DATA.videoStartApiUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken":  DJANGO_DATA.csrfToken,
      },
      body: JSON.stringify({
        prompt,
        aspect_ratio,
        conversation_id: State.currentConvId,
      }),
    });

    const data = await resp.json();

    if (!resp.ok || data.error) {
      showToast("⚠️ " + (data.error || "Erreur de démarrage."), "error");
      appendMessage("assistant", "⚠️ " + (data.error || "Impossible d'initialiser la génération de la vidéo."));
      btn.disabled = false;
      btn.textContent = "✦ Générer la vidéo";
      return;
    }

    // Afficher la bulle de progression
    const row = document.createElement("div");
    row.className = "message-row assistant";
    row.innerHTML = `
      <div class="message-avatar">✦</div>
      <div class="message-bubble assistant">
        <div class="video-loading-content" style="display: flex; align-items: center; gap: 12px; padding: 4px 0;">
          <div class="video-spinner" style="width: 22px; height: 22px; border: 3px solid rgba(0,212,170,0.15); border-top-color: var(--ai-1); border-radius: 50%; animation: spin 1s linear infinite; flex-shrink: 0;"></div>
          <div>
            <div style="font-weight: 700; color: #fff; font-size: 13px;">Génération de la vidéo IA en cours...</div>
            <div style="font-size: 11px; color: var(--text-2);">Google Veo prépare votre vidéo. Temps estimé : 40-70s</div>
          </div>
        </div>
        <div class="message-actions" style="margin-top: 4px;">
          <span class="message-time">${new Date().toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}</span>
        </div>
      </div>`;
    messagesList.appendChild(row);
    scrollToBottom();

    // Lancer le polling
    pollVideoStatus(data.operation_name, data.conversation_id, prompt, row, btn);

  } catch (err) {
    showToast("Erreur réseau.", "error");
    btn.disabled = false;
    btn.textContent = "✦ Générer la vidéo";
  }
}

function pollVideoStatus(operationName, conversationId, prompt, rowElement, btnElement) {
  const pollUrl = `${DJANGO_DATA.videoPollUrl}?operation_name=${encodeURIComponent(operationName)}&conversation_id=${conversationId || ""}&prompt=${encodeURIComponent(prompt)}`;
  
  let attempts = 0;
  const maxAttempts = 50; // 50 * 4s = 200s
  
  const interval = setInterval(async () => {
    attempts++;
    if (attempts > maxAttempts) {
      clearInterval(interval);
      rowElement.innerHTML = `
        <div class="message-avatar">✦</div>
        <div class="message-bubble assistant">
          <div style="color: #EF4444; font-weight: 700; font-size: 13px;">⚠️ Temps de génération vidéo dépassé.</div>
          <div style="font-size: 11px; color: var(--text-2); margin-top: 2px;">Google prend un peu trop de temps à répondre. Veuillez réessayer plus tard.</div>
        </div>`;
      btnElement.disabled = false;
      btnElement.textContent = "✦ Générer la vidéo";
      return;
    }

    try {
      const resp = await fetch(pollUrl);
      const data = await resp.json();

      if (data.error) {
        clearInterval(interval);
        rowElement.innerHTML = `
          <div class="message-avatar">✦</div>
          <div class="message-bubble assistant">
            <div style="color: #EF4444; font-weight: 700; font-size: 13px;">⚠️ Échec de la génération</div>
            <div style="font-size: 11px; color: var(--text-2); margin-top: 2px;">${data.error}</div>
          </div>`;
        btnElement.disabled = false;
        btnElement.textContent = "✦ Générer la vidéo";
        return;
      }

      if (data.done) {
        clearInterval(interval);
        rowElement.innerHTML = `
          <div class="message-avatar">✦</div>
          <div class="message-bubble assistant">
            <div class="message-video-container">
              <video src="${data.video_url}" controls class="generated-video" style="max-width:100%; border-radius:12px; margin-top:8px; border:1px solid rgba(255,255,255,0.1); display:block;"></video>
              <a href="${data.video_url}" download class="img-download-btn" style="margin-top:8px; display:inline-flex;">⬇ Télécharger la vidéo</a>
            </div>
            <div class="message-actions">
              <span class="message-time">${new Date().toLocaleTimeString("fr-FR",{hour:"2-digit",minute:"2-digit"})}</span>
            </div>
          </div>`;
        scrollToBottom();

        btnElement.disabled = false;
        btnElement.textContent = "✦ Générer la vidéo";

        if (data.quota) {
          updateQuotaUI(data.quota.messages, data.quota.msg_used, data.quota.msg_limit);
        }
      }
    } catch (err) {
      console.error("Error polling video:", err);
    }
  }, 4000);
}

// ─── Nouvelle conversation ────────────────────────────────────────────────────
async function createNewConversation() {
  try {
    const resp = await fetch(DJANGO_DATA.newConvUrl, {
      method: "POST",
      headers: { "X-CSRFToken": DJANGO_DATA.csrfToken },
    });
    const data = await resp.json();
    if (data.conversation_id) {
      State.currentConvId = data.conversation_id;
      history.pushState({}, "", `/ai/c/${data.conversation_id}/`);
      messagesList.innerHTML = "";
      if (welcomeScreen) welcomeScreen.style.display = "flex";
      headerConvTitle.textContent = "Nouvelle conversation";
    }
  } catch (err) {
    console.error("New conv error:", err);
  }
}

// ─── Supprimer conversation ───────────────────────────────────────────────────
async function deleteConversation(id) {
  if (!confirm("Supprimer cette conversation ?")) return;
  try {
    const url = DJANGO_DATA.deleteConvUrl.replace("{id}", id);
    await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": DJANGO_DATA.csrfToken },
    });
    const item = document.querySelector(`.conv-item[data-id="${id}"]`);
    if (item) item.remove();
    if (State.currentConvId == id) createNewConversation();
  } catch (err) {
    console.error("Delete conv error:", err);
  }
}

// ─── Effacer mémoire ─────────────────────────────────────────────────────────
async function clearMemory() {
  if (!confirm("Effacer votre mémoire IA ? Vos préférences seront perdues.")) return;
  try {
    await fetch(DJANGO_DATA.memClearUrl, {
      method: "POST",
      headers: { "X-CSRFToken": DJANGO_DATA.csrfToken },
    });
    showToast("🧠 Mémoire effacée.");
  } catch (err) {
    console.error("Clear memory error:", err);
  }
}

// ─── Sidebar mobile ───────────────────────────────────────────────────────────
function toggleSidebar() {
  const sidebar  = document.querySelector(".sidebar");
  const overlay  = $("sidebar-overlay");
  const isOpen   = sidebar.classList.toggle("open");
  overlay.classList.toggle("visible", isOpen);
}
function closeSidebar() {
  document.querySelector(".sidebar").classList.remove("open");
  $("sidebar-overlay").classList.remove("visible");
}

// ─── Quota UI ─────────────────────────────────────────────────────────────────
function updateQuotaUI(remaining, used, limit) {
  if (quotaDisplay) quotaDisplay.textContent = `${remaining} msg restants`;
  if (quotaBadge)   quotaBadge.textContent   = `${remaining} messages`;
  if (quotaFill && limit > 0) {
    const pct = Math.min((used / limit) * 100, 100);
    quotaFill.style.width = pct + "%";
    quotaFill.style.background = pct > 90
      ? "linear-gradient(135deg,#EF4444,#B91C1C)"
      : pct > 70
        ? "linear-gradient(135deg,#F59E0B,#D97706)"
        : "linear-gradient(135deg,#00d4aa,#0066ff)";
  }
}

// ─── Utilitaires ──────────────────────────────────────────────────────────────
function scrollToBottom() {
  if (messagesZone) {
    messagesZone.scrollTop = messagesZone.scrollHeight;
  }
}

function autoResizeTextarea() {
  messageInput.style.height = "auto";
}

function showToast(message, type = "info") {
  const existing = document.querySelector(".toast");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

// ─── Raccourci Ctrl+K global (depuis d'autres pages via inclusion) ────────────
// Ce script peut être inclus dans le layout global pour ouvrir le chat
window.EshelleAI = {
  open: () => window.location.href = "/ai/",
};
