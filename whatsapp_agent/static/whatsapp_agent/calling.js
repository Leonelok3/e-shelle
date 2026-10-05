(() => {
  const status = document.getElementById('whatsapp-call-status');
  const startButton = document.getElementById('btn-start-whatsapp-call');
  const permissionButton = document.getElementById('btn-request-call-permission');
  const endButton = document.getElementById('btn-end-whatsapp-call');
  const remoteAudio = document.getElementById('whatsapp-call-audio');
  if (!status || !startButton || !permissionButton || !endButton || !remoteAudio) return;

  const csrf = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
  const peers = new Map();
  const handledCalls = new Set();
  const iceServers = [{urls: 'stun:stun.l.google.com:19302'}];
  let activeCallId = null;
  let polling = false;

  function showStatus(text, error = false) {
    status.textContent = text;
    status.dataset.error = error ? 'true' : 'false';
  }

  async function postJson(url, payload = {}) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf},
      body: JSON.stringify(payload),
      credentials: 'same-origin'
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `Erreur HTTP ${response.status}`);
    return result;
  }

  async function waitForIceGathering(peer) {
    if (peer.iceGatheringState === 'complete') return;
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('La connexion WebRTC n’a pas terminé la négociation ICE.')), 12000);
      peer.addEventListener('icegatheringstatechange', () => {
        if (peer.iceGatheringState === 'complete') {
          clearTimeout(timeout);
          resolve();
        }
      }, {once: false});
    });
  }

  async function waitForConnection(peer) {
    if (peer.connectionState === 'connected') return;
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => reject(new Error('La connexion audio n’a pas abouti.')), 20000);
      const checkState = () => {
        if (peer.connectionState === 'connected') {
          clearTimeout(timeout);
          resolve();
        } else if (['failed', 'closed'].includes(peer.connectionState)) {
          clearTimeout(timeout);
          reject(new Error('La connexion audio a échoué.'));
        }
      };
      peer.addEventListener('connectionstatechange', checkState);
      checkState();
    });
  }

  async function makePeer() {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true, video: false});
    const peer = new RTCPeerConnection({iceServers});
    stream.getTracks().forEach(track => peer.addTrack(track, stream));
    peer.ontrack = event => {
      remoteAudio.srcObject = event.streams[0];
      remoteAudio.play().catch(() => showStatus('Clique dans la page pour activer le son.'));
    };
    peer.onconnectionstatechange = () => {
      if (peer.connectionState === 'connected') showStatus('Appel connecté.');
      if (['failed', 'disconnected'].includes(peer.connectionState)) showStatus('Connexion audio interrompue.', true);
    };
    return peer;
  }

  async function acceptIncoming(call) {
    const peer = await makePeer();
    peers.set(call.id, peer);
    activeCallId = call.id;
    endButton.hidden = false;
    await peer.setRemoteDescription({type: 'offer', sdp: call.sdp_offer});
    const answer = await peer.createAnswer();
    await peer.setLocalDescription(answer);
    await waitForIceGathering(peer);
    const sdpAnswer = peer.localDescription.sdp;
    await postJson(`/whatsapp/api/calls/${call.id}/action/`, {action: 'pre_accept', sdp_answer: sdpAnswer});
    await waitForConnection(peer);
    await postJson(`/whatsapp/api/calls/${call.id}/action/`, {action: 'accept', sdp_answer: sdpAnswer});
    showStatus(`Appel avec ${call.contact_name}.`);
  }

  async function rejectIncoming(call) {
    try {
      await postJson(`/whatsapp/api/calls/${call.id}/action/`, {action: 'reject'});
      handledCalls.add(call.id);
    } catch (error) {
      showStatus(error.message, true);
    }
  }

  permissionButton.addEventListener('click', async () => {
    permissionButton.disabled = true;
    showStatus('Envoi de la demande de permission…');
    try {
      await postJson(permissionButton.dataset.url, {
        context: 'E-Shelle souhaite vous appeler sur WhatsApp afin de répondre à votre demande. Autorisez l’appel si cela vous convient.'
      });
      showStatus('Demande envoyée. Le contact doit accepter avant que tu puisses l’appeler.');
    } catch (error) {
      showStatus(error.message, true);
    } finally {
      permissionButton.disabled = false;
    }
  });

  startButton.addEventListener('click', async () => {
    if (!navigator.mediaDevices?.getUserMedia || !window.RTCPeerConnection) {
      showStatus('Ce navigateur ne prend pas en charge les appels WebRTC.', true);
      return;
    }
    startButton.disabled = true;
    showStatus('Vérification de la permission et préparation du microphone…');
    try {
      const peer = await makePeer();
      const offer = await peer.createOffer();
      await peer.setLocalDescription(offer);
      await waitForIceGathering(peer);
      const result = await postJson(startButton.dataset.url, {sdp_offer: peer.localDescription.sdp});
      activeCallId = result.call_id;
      peers.set(result.call_id, peer);
      endButton.hidden = false;
      showStatus('Appel WhatsApp en cours de connexion…');
    } catch (error) {
      showStatus(error.message, true);
      startButton.disabled = false;
    }
  });

  endButton.addEventListener('click', async () => {
    if (!activeCallId) return;
    endButton.disabled = true;
    try {
      await postJson(`/whatsapp/api/calls/${activeCallId}/action/`, {action: 'terminate'});
      closePeer(activeCallId);
      showStatus('Appel terminé.');
    } catch (error) {
      showStatus(error.message, true);
    } finally {
      endButton.disabled = false;
    }
  });

  function closePeer(callId) {
    const peer = peers.get(callId);
    if (peer) {
      peer.getSenders().forEach(sender => sender.track?.stop());
      peer.close();
      peers.delete(callId);
    }
    if (activeCallId === callId) {
      activeCallId = null;
      endButton.hidden = true;
      startButton.disabled = false;
      remoteAudio.srcObject = null;
    }
  }

  async function pollCalls() {
    if (polling) return;
    polling = true;
    try {
      const response = await fetch('/whatsapp/api/calls/pending/', {credentials: 'same-origin'});
      if (!response.ok) return;
      const data = await response.json();
      for (const call of data.calls || []) {
        if (call.direction === 'outbound' && call.sdp_answer && peers.has(call.id)) {
          const peer = peers.get(call.id);
          if (!peer.currentRemoteDescription) {
            await peer.setRemoteDescription({type: 'answer', sdp: call.sdp_answer});
            showStatus('Appel WhatsApp en sonnerie…');
            await waitForConnection(peer);
            await postJson(`/whatsapp/api/calls/${call.id}/action/`, {action: 'media_connected'});
          }
        }
        if (call.direction === 'inbound' && call.status === 'ringing' && call.sdp_offer && !handledCalls.has(call.id)) {
          handledCalls.add(call.id);
          const accepted = window.confirm(`Appel WhatsApp entrant de ${call.contact_name} (${call.number}). Répondre ?`);
          if (accepted) {
            showStatus(`Connexion à ${call.contact_name}…`);
            try {
              await acceptIncoming(call);
            } catch (error) {
              showStatus(error.message, true);
              await rejectIncoming(call);
              closePeer(call.id);
            }
          } else {
            await rejectIncoming(call);
          }
        }
        if (['ended', 'rejected', 'failed'].includes(call.status) && peers.has(call.id)) {
          closePeer(call.id);
          showStatus(call.status === 'failed' ? (call.error || 'Échec de l’appel.') : 'Appel terminé.');
        }
      }
    } catch (error) {
      showStatus(error.message, true);
    } finally {
      polling = false;
    }
  }

  pollCalls();
  window.setInterval(pollCalls, 2500);
})();
