(() => {
  "use strict";
  const shell = document.querySelector(".tcf-daily-shell");
  if (!shell) return;
  const token = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
  const form = document.getElementById("daily-exam-form");
  const timer = document.getElementById("daily-timer");
  const text = document.getElementById("daily-production");
  const count = document.getElementById("daily-word-count");
  let submitted = false, recorder = null, recordingURL = null, stopRecording = null, recordingSaved = true;
  const recordingPlayer = document.getElementById("daily-recording");
  const recordingDownload = document.getElementById("daily-recording-download");
  function showRecording(blob) {
    if (!recordingPlayer) return;
    if (recordingURL) URL.revokeObjectURL(recordingURL);
    recordingURL = URL.createObjectURL(blob);
    recordingPlayer.src = recordingURL;
    recordingPlayer.hidden = false;
    if (recordingDownload) {
      recordingDownload.href = recordingURL;
      recordingDownload.download = `tcf-${shell.dataset.day}.${blob.type.includes("mp4") ? "m4a" : "webm"}`;
      recordingDownload.hidden = false;
      recordingDownload.onclick = () => { recordingSaved = true; };
    }
  }
  function recordingDB() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error("storage")); return; }
      const request = indexedDB.open("tcf-daily-local", 1);
      request.onupgradeneeded = () => request.result.createObjectStore("recording");
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }
  async function saveRecording(blob) {
    const db = await recordingDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction("recording", "readwrite");
      tx.objectStore("recording").put({day: shell.dataset.day, blob}, "latest");
      tx.oncomplete = () => { db.close(); resolve(); };
      tx.onerror = () => { db.close(); reject(tx.error); };
    });
  }
  if (recordingPlayer) recordingDB().then(db => {
    const request = db.transaction("recording", "readonly").objectStore("recording").get("latest");
    request.onsuccess = () => { if (request.result?.day === shell.dataset.day) showRecording(request.result.blob); db.close(); };
    request.onerror = () => db.close();
  }).catch(() => {});
  if (text && count) text.addEventListener("input", () => {
    const words = text.value.trim() ? text.value.trim().split(/\s+/).length : 0;
    const within = words >= Number(count.dataset.min) && words <= Number(count.dataset.max);
    count.textContent = `${words} mot${words === 1 ? "" : "s"} · ${within ? "dans la limite demandée" : "objectif : " + count.dataset.min + " à " + count.dataset.max}`;
  });
  if (form) form.addEventListener("submit", async event => {
    event.preventDefault();
    if (submitted) return;
    submitted = true;
    form.querySelector('button[type="submit"]').disabled = true;
    if (recorder?.state === "recording" && stopRecording) await stopRecording();
    if (!recordingSaved && recordingURL) {
      submitted = false;
      form.querySelector('button[type="submit"]').disabled = false;
      document.getElementById("daily-record-status").textContent = "Télécharge d'abord ton enregistrement ci-dessous, puis rends ta réponse.";
      return;
    }
    HTMLFormElement.prototype.submit.call(form);
  });
  if (timer && form) {
    const deadline = Date.now() + Number(timer.dataset.remaining) * 1000;
    const tick = () => {
      const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      timer.textContent = `${String(Math.floor(remaining / 60)).padStart(2, "0")}:${String(remaining % 60).padStart(2, "0")}`;
      if (!remaining && !submitted) {
        clearInterval(interval);
        document.getElementById("daily-time-note").textContent = "Temps écoulé : envoi de ta réponse.";
        form.requestSubmit();
      }
    };
    const interval = setInterval(tick, 250);
    tick();
  }
  const play = document.getElementById("daily-play");
  const audio = document.getElementById("daily-audio");
  const audioStatus = document.getElementById("daily-audio-status");
  if (play && audio) {
    if (play.dataset.used === "true") { play.disabled = true; audioStatus.textContent = "Document déjà lancé. Rends ta réponse pour consulter la transcription."; }
    let authorized = false;
    play.addEventListener("click", async () => {
      play.disabled = true;
      try {
        if (!authorized) {
          const payload = new URLSearchParams({action: "audio-play", day: shell.dataset.day});
          const response = await fetch(location.pathname, {method: "POST", headers: {"X-CSRFToken": token}, body: payload});
          const result = await response.json();
          if (!result.ok) { audioStatus.textContent = result.error; return; }
          authorized = true;
        }
        await audio.play();
        audioStatus.textContent = "Écoute en cours…";
      } catch (_) { play.disabled = false; play.textContent = "Réessayer de lancer le lecteur"; audioStatus.textContent = "Le lecteur n'a pas pu démarrer. Vérifie ta connexion et autorise la lecture audio."; }
    });
    audio.addEventListener("ended", () => { audioStatus.textContent = "Écoute terminée. Réponds aux questions."; });
    audio.addEventListener("error", () => { audioStatus.textContent = "Le fichier audio n'est pas accessible. Reviens à la préparation TCF et signale le problème."; });
  }
  const record = document.getElementById("daily-record");
  const stop = document.getElementById("daily-stop-record");
  const recordStatus = document.getElementById("daily-record-status");
  if (record) {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder || !window.indexedDB) {
      record.disabled = true; recordStatus.textContent = "Enregistrement indisponible dans ce navigateur. Tu peux parler à voix haute et saisir ta transcription.";
    } else record.addEventListener("click", async () => {
      record.disabled = true;
      let stream;
      try {
        await recordingDB().then(db => db.close());
        stream = await navigator.mediaDevices.getUserMedia({audio: true});
        const chunks = [];
        recorder = new MediaRecorder(stream);
        let finish;
        const finished = new Promise(resolve => { finish = resolve; });
        recorder.ondataavailable = event => { if (event.data.size) chunks.push(event.data); };
        recorder.onstop = async () => {
          stream.getTracks().forEach(track => track.stop());
          const blob = new Blob(chunks, {type: recorder.mimeType || "audio/webm"});
          showRecording(blob);
          try { await saveRecording(blob); recordingSaved = true; recordStatus.textContent = "Enregistrement conservé sur cet appareil. Tu peux le réécouter et le télécharger."; }
          catch (_) { recordingSaved = false; recordStatus.textContent = "Stockage indisponible : télécharge ton enregistrement avant de quitter cette page."; }
          stop.hidden = true;
          finish();
        };
        stopRecording = async () => { if (recorder.state === "recording") recorder.stop(); await finished; };
        stop.onclick = () => stopRecording();
        recorder.start(); stop.hidden = false; recordStatus.textContent = "Enregistrement en cours. Le microphone reste sur ton appareil.";
      } catch (_) { stream?.getTracks().forEach(track => track.stop()); record.disabled = false; recordStatus.textContent = "Accès au microphone ou au stockage refusé. Tu peux poursuivre sans enregistrement."; }
    });
  }
  const ai = document.getElementById("daily-ai");
  const feedback = document.getElementById("daily-ai-feedback");
  if (ai) ai.addEventListener("click", async () => {
    ai.disabled = true; feedback.textContent = "Analyse de ta réponse en cours…";
    try {
      const response = await fetch(ai.dataset.url, {method: "POST", headers: {"X-CSRFToken": token}});
      if (!response.headers.get("content-type")?.includes("application/json")) throw new Error("session");
      const data = await response.json();
      if (!data.ok) { feedback.textContent = data.error || data.message || "Correction indisponible."; return; }
      const result = data.result;
      const paragraphs = [result.feedback, result.coaching?.assessment_note];
      for (const priority of result.coaching?.priorities || []) {
        paragraphs.push(`À travailler : ${priority.diagnosis}\nConseil : ${priority.action}\nMini-exercice : ${priority.drill}`);
      }
      if (result.corrected_version) paragraphs.push("Version corrigée :\n" + result.corrected_version);
      feedback.textContent = paragraphs.filter(Boolean).join("\n\n");
    } catch (_) { feedback.textContent = "Connexion ou session indisponible. Ta réponse reste enregistrée dans cette séance."; }
    finally { ai.disabled = false; }
  });
})();
