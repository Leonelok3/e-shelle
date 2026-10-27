/**
 * listener.js — Worker WhatsApp Baileys pour E-Shelle Immobilier
 * Écoute en continu le groupe "E-Shelle Immobilier", regroupe les photos
 * et les envoie automatiquement à Django sans aucune intervention manuelle.
 */
import makeWASocket, {
    useMultiFileAuthState,
    DisconnectReason,
    downloadMediaMessage,
    fetchLatestBaileysVersion
} from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcode from 'qrcode-terminal';
import axios from 'axios';
import FormData from 'form-data';
import dotenv from 'dotenv';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config();

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Configuration
const DJANGO_INGEST_URL = process.env.DJANGO_INGEST_URL || 'http://127.0.0.1:8000/immobilier/api/internal-ingest/';
const INTERNAL_SECRET = process.env.INTERNAL_WHATSAPP_SECRET || 'eshelle_immo_listener_secret_2026';
const TARGET_GROUP_KEYWORD = (process.env.TARGET_GROUP_KEYWORD || 'immobilier').toLowerCase();
const PHONE_NUMBER_FOR_PAIRING = process.env.PHONE_NUMBER || '237680625082'; // +237680625082
const USE_PAIRING_CODE = process.env.USE_PAIRING_CODE === 'true'; // Mettre à true pour recevoir un code à 8 chiffres

const logger = pino({ level: 'info' });

// Buffer temporaire pour regrouper les photos envoyées en rafale (fenêtre de 10s)
const pendingBatches = new Map();

async function sendBatchToDjango(batchKey, batchData) {
    try {
        console.log(`\n🚀 [Ingestion Django] Envoi annonce de ${batchData.senderPhone} (${batchData.images.length} photos)...`);
        
        const form = new FormData();
        form.append('secret', INTERNAL_SECRET);
        form.append('raw_text', batchData.text || '');
        form.append('source_name', batchData.senderName || 'Démarcheur WhatsApp');
        form.append('source_phone', batchData.senderPhone || '');
        form.append('whatsapp_group_name', batchData.groupName || 'E-Shelle Immobilier');

        batchData.images.forEach((imgBuffer, idx) => {
            form.append('photos', imgBuffer, {
                filename: `photo_${idx + 1}.jpg`,
                contentType: 'image/jpeg',
            });
        });

        const resp = await axios.post(DJANGO_INGEST_URL, form, {
            headers: {
                ...form.getHeaders(),
                'X-Internal-Secret': INTERNAL_SECRET,
            },
            timeout: 30000,
        });

        if (resp.data && resp.data.status === 'ok') {
            console.log(`✅ [Succès] Brouillon créé : « ${resp.data.titre} » (Score: ${resp.data.quality_score}/100)`);
            console.log(`🔗 Voir sur E-Shelle : https://e-shelle.com/immobilier/admin/whatsapp-drafts/`);
        } else {
            console.warn(`⚠️ [Réponse inattendue] :`, resp.data);
        }
    } catch (err) {
        console.error(`❌ [Erreur Ingestion Django] :`, err.response?.data || err.message);
    } finally {
        pendingBatches.delete(batchKey);
    }
}

async function startWhatsAppListener() {
    const authDir = path.join(__dirname, 'auth_info_baileys');
    const { state, saveCreds } = await useMultiFileAuthState(authDir);
    const { version } = await fetchLatestBaileysVersion();

    console.log(`=======================================================`);
    console.log(`📱 E-Shelle WhatsApp Immo Listener (Baileys v${version.join('.')})`);
    console.log(`📡 URL Django Ingest : ${DJANGO_INGEST_URL}`);
    console.log(`🎯 Filtre groupe : "${TARGET_GROUP_KEYWORD}"`);
    console.log(`=======================================================\n`);

    const sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        printQRInTerminal: !USE_PAIRING_CODE,
        auth: state,
        browser: ['E-Shelle Immo Bot', 'Chrome', '1.0.0'],
    });

    // Support du code de jumelage par notification (Pairing Code)
    if (USE_PAIRING_CODE && !sock.authState.creds.registered) {
        setTimeout(async () => {
            try {
                const code = await sock.requestPairingCode(PHONE_NUMBER_FOR_PAIRING);
                console.log(`\n🔑 CODE D'APPAIRAGE WHATSAPP : \x1b[32m\x1b[1m${code}\x1b[0m`);
                console.log(`👉 Sur votre téléphone : WhatsApp > Appareils connectés > Connecter un appareil > Se connecter avec un numéro de téléphone.\n`);
            } catch (err) {
                console.error("Erreur demande code d'appairage:", err.message);
            }
        }, 3000);
    }

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr && !USE_PAIRING_CODE) {
            console.log('📷 Scannez ce QR Code avec WhatsApp :');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
            console.log(`⚠️ Connexion fermée. Reconnexion automatique : ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(startWhatsAppListener, 5000);
            } else {
                console.log('🔴 Déconnecté définitivement. Supprimez auth_info_baileys et relancez.');
            }
        } else if (connection === 'open') {
            console.log('\n🟢 CONNECTÉ À WHATSAPP AVEC SUCCÈS !');
            console.log('👀 Écoute active des annonces du groupe...');
        }
    });

    // Réception des messages
    sock.ev.on('messages.upsert', async ({ messages: msgs, type }) => {
        if (type !== 'notify') return;

        for (const msg of msgs) {
            if (!msg.message || msg.key.fromMe) continue;

            const remoteJid = msg.key.remoteJid;
            const isGroup = remoteJid.endsWith('@g.us');
            if (!isGroup) continue; // On écoute uniquement les groupes

            // Vérifier le groupe
            let groupSubject = 'Groupe Inconnu';
            try {
                const meta = await sock.groupMetadata(remoteJid);
                groupSubject = meta.subject || '';
            } catch (e) {
                // Métadonnées non dispo en cache
            }

            if (!groupSubject.toLowerCase().includes(TARGET_GROUP_KEYWORD)) {
                continue; // Pas un groupe immobilier
            }

            // Extraction du contenu
            const messageType = Object.keys(msg.message)[0];
            const senderJid = msg.key.participant || remoteJid;
            const senderPhone = senderJid.split('@')[0];
            const senderName = msg.pushName || 'Démarcheur WhatsApp';

            let text = '';
            let imageBuffer = null;

            if (messageType === 'conversation') {
                text = msg.message.conversation;
            } else if (messageType === 'extendedTextMessage') {
                text = msg.message.extendedTextMessage.text;
            } else if (messageType === 'imageMessage') {
                text = msg.message.imageMessage.caption || '';
                try {
                    imageBuffer = await downloadMediaMessage(
                        msg,
                        'buffer',
                        {},
                        { logger, reuploadRequest: sock.updateMediaMessage }
                    );
                } catch (e) {
                    console.error('Erreur téléchargement image:', e.message);
                }
            }

            // Ignorer les messages très courts sans image (ex: "bonjour", "ok", "merci")
            if (!imageBuffer && (!text || text.trim().length < 20)) {
                continue;
            }

            console.log(`📩 [Nouveau message] de ${senderName} (${senderPhone}) dans "${groupSubject}"`);

            // Gestion du batching (regrouper les messages d'un même expéditeur dans un intervalle de 8s)
            const batchKey = `${remoteJid}_${senderJid}`;
            let currentBatch = pendingBatches.get(batchKey);

            if (!currentBatch) {
                currentBatch = {
                    groupName: groupSubject,
                    senderName,
                    senderPhone: `+${senderPhone}`,
                    text: text || '',
                    images: [],
                    timer: null,
                };
                pendingBatches.set(batchKey, currentBatch);
            }

            if (text && !currentBatch.text) {
                currentBatch.text = text;
            } else if (text && currentBatch.text && !currentBatch.text.includes(text)) {
                currentBatch.text += `\n${text}`;
            }

            if (imageBuffer) {
                currentBatch.images.push(imageBuffer);
            }

            // Réinitialiser le timer de 8 secondes
            if (currentBatch.timer) {
                clearTimeout(currentBatch.timer);
            }

            currentBatch.timer = setTimeout(() => {
                sendBatchToDjango(batchKey, currentBatch);
            }, 8000); // 8 secondes après la dernière photo reçue
        }
    });
}

startWhatsAppListener().catch(err => {
    console.error('Erreur fatale listener:', err);
});
