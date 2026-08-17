/*
 * Temps reel d'une conversation : WebSocket (Channels) avec reconnexion
 * automatique en cas de coupure, et repli sur une actualisation periodique
 * (polling) si le WebSocket n'aboutit jamais — cas de l'hebergement actuel
 * (Passenger/WSGI classique, voir passenger_wsgi.py) qui ne sait pas encore
 * terminer de connexions WebSocket. Une seule route de rafraichissement
 * (`refreshMessages`) sert les deux cas : le WebSocket ne transporte aucune
 * donnee metier, juste un signal "quelque chose a change" — le rendu HTML
 * reste toujours cote Django (voir apps.messaging.views.MessagesFragmentView).
 */
(function () {
  const canvas = document.getElementById('messages-canvas');
  if (!canvas) return;

  const fragmentUrl = canvas.dataset.fragmentUrl;
  const wsUrl = canvas.dataset.wsUrl;
  const statusDot = document.getElementById('realtime-status');
  const typingIndicator = document.getElementById('typing-indicator');
  const composerForm = document.getElementById('composer-form');
  const composerInput = document.getElementById('composer-input');
  const banner = document.getElementById('reponse-banner');
  const bannerAuteur = document.getElementById('reponse-banner-auteur');
  const bannerContenu = document.getElementById('reponse-banner-contenu');
  const reponseInput = document.getElementById('reponse_a_input');
  const annulerBtn = document.getElementById('reponse-banner-annuler');

  function scrollToBottomIfNear(force) {
    const distance = canvas.scrollHeight - canvas.scrollTop - canvas.clientHeight;
    if (force || distance < 150) {
      canvas.scrollTop = canvas.scrollHeight;
    }
  }

  function bindMessageActions() {
    canvas.querySelectorAll('.msg-edit-toggle').forEach(function (btn) {
      btn.addEventListener('click', function () {
        const form = document.getElementById(btn.dataset.target);
        if (form) form.classList.toggle('hidden');
      });
    });
    canvas.querySelectorAll('.msg-reply-btn').forEach(function (btn) {
      btn.addEventListener('click', function () {
        reponseInput.value = btn.dataset.id;
        bannerAuteur.textContent = btn.dataset.auteur;
        bannerContenu.textContent = btn.dataset.contenu;
        banner.classList.remove('hidden');
        composerInput.focus();
      });
    });
  }

  if (annulerBtn) {
    annulerBtn.addEventListener('click', function () {
      reponseInput.value = '';
      banner.classList.add('hidden');
    });
  }

  bindMessageActions();
  scrollToBottomIfNear(true);

  // Edition/suppression : les formulaires sont recrees a chaque
  // refreshMessages() (innerHTML remplace), donc on ecoute sur `canvas`
  // (jamais remplace lui-meme) plutot que de re-attacher un listener par
  // fragment — la delegation survit naturellement aux rafraichissements.
  canvas.addEventListener('submit', function (event) {
    const form = event.target;
    if (form.classList.contains('msg-delete-form')) {
      event.preventDefault();
      if (!window.confirm('Supprimer ce message ?')) return;
      fetch(form.action, { method: 'POST', credentials: 'same-origin', body: new FormData(form) })
        .then(function () { refreshMessages(); })
        .catch(function () {});
    } else if (form.classList.contains('msg-edit-form')) {
      event.preventDefault();
      fetch(form.action, { method: 'POST', credentials: 'same-origin', body: new FormData(form) })
        .then(function () { refreshMessages(); })
        .catch(function () {});
    }
  });

  let refreshing = false;
  function refreshMessages() {
    if (refreshing || !fragmentUrl) return;
    refreshing = true;
    fetch(fragmentUrl, { credentials: 'same-origin' })
      .then(function (response) { return response.ok ? response.text() : null; })
      .then(function (html) {
        if (html === null) return;
        canvas.innerHTML = html;
        bindMessageActions();
        scrollToBottomIfNear(false);
      })
      .catch(function () {})
      .finally(function () { refreshing = false; });
  }

  // ---------------------------------------------------------------
  // WebSocket avec reconnexion automatique, repli sur polling au-dela
  // de MAX_RECONNECT_ATTEMPTS tentatives infructueuses.
  // ---------------------------------------------------------------
  let socket = null;
  let reconnectAttempts = 0;
  let reconnectTimer = null;
  let pollingTimer = null;
  const MAX_RECONNECT_ATTEMPTS = 4;
  const POLLING_INTERVAL_MS = 4000;

  function setStatus(state) {
    if (!statusDot) return;
    const classes = {
      connecte: 'w-2 h-2 rounded-full shrink-0 bg-secondary',
      polling: 'w-2 h-2 rounded-full shrink-0 bg-tertiary',
      deconnecte: 'w-2 h-2 rounded-full shrink-0 bg-outline-variant',
    };
    const titres = {
      connecte: 'Temps réel actif',
      polling: 'Mode actualisation périodique',
      deconnecte: 'Connexion en cours…',
    };
    statusDot.className = classes[state] || classes.deconnecte;
    statusDot.title = titres[state] || '';
  }

  function stopPolling() {
    if (pollingTimer) {
      window.clearInterval(pollingTimer);
      pollingTimer = null;
    }
  }

  function startPolling() {
    stopPolling();
    setStatus('polling');
    pollingTimer = window.setInterval(refreshMessages, POLLING_INTERVAL_MS);
  }

  function planifierReconnexion() {
    if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
      // Le WebSocket n'aboutit jamais (hebergement sans support WS) : on
      // arrete d'insister et on bascule sur l'actualisation periodique.
      startPolling();
      return;
    }
    reconnectAttempts += 1;
    const delai = Math.min(1000 * Math.pow(2, reconnectAttempts), 15000);
    reconnectTimer = window.setTimeout(connectSocket, delai);
  }

  function connectSocket() {
    if (!wsUrl || !('WebSocket' in window)) {
      startPolling();
      return;
    }
    try {
      socket = new WebSocket(wsUrl);
    } catch (erreur) {
      startPolling();
      return;
    }

    socket.addEventListener('open', function () {
      reconnectAttempts = 0;
      stopPolling();
      setStatus('connecte');
    });

    socket.addEventListener('message', function (event) {
      let data;
      try {
        data = JSON.parse(event.data);
      } catch (erreur) {
        return;
      }
      if (data.type === 'nouveau_message' || data.type === 'message_modifie' || data.type === 'message_supprime') {
        refreshMessages();
      } else if (data.type === 'typing') {
        afficherTyping(data);
      }
    });

    socket.addEventListener('close', function () {
      setStatus('deconnecte');
      planifierReconnexion();
    });

    socket.addEventListener('error', function () {
      socket.close();
    });
  }

  window.addEventListener('beforeunload', function () {
    if (socket) socket.close();
    stopPolling();
    if (reconnectTimer) window.clearTimeout(reconnectTimer);
  });

  connectSocket();

  // ---------------------------------------------------------------
  // Indicateur "en train d'ecrire"
  // ---------------------------------------------------------------
  let typingClearTimer = null;
  function afficherTyping(data) {
    if (!typingIndicator) return;
    if (!data.typing) {
      typingIndicator.classList.add('hidden');
      return;
    }
    typingIndicator.textContent = data.nom + ' est en train d’écrire…';
    typingIndicator.classList.remove('hidden');
    window.clearTimeout(typingClearTimer);
    typingClearTimer = window.setTimeout(function () {
      typingIndicator.classList.add('hidden');
    }, 4000);
  }

  let typingSentAt = 0;
  let typingStopTimer = null;
  function envoyerTyping(enTrainDecrire) {
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify({ type: 'typing', typing: enTrainDecrire }));
  }

  if (composerInput) {
    composerInput.addEventListener('input', function () {
      const maintenant = Date.now();
      if (maintenant - typingSentAt > 2000) {
        envoyerTyping(true);
        typingSentAt = maintenant;
      }
      window.clearTimeout(typingStopTimer);
      typingStopTimer = window.setTimeout(function () { envoyerTyping(false); }, 3000);
    });
  }

  if (composerForm) {
    composerForm.addEventListener('submit', function (event) {
      event.preventDefault();
      window.clearTimeout(typingStopTimer);
      envoyerTyping(false);

      const contenu = composerInput.value.trim();
      if (!contenu) return;

      // Snapshot avant de vider les champs : FormData lit les valeurs au
      // moment de la construction, pas au moment de l'envoi.
      const formData = new FormData(composerForm);
      composerInput.value = '';
      composerInput.focus();
      reponseInput.value = '';
      banner.classList.add('hidden');
      const emojiPickerEl = document.getElementById('emoji-picker');
      if (emojiPickerEl) emojiPickerEl.classList.add('hidden');

      fetch(composerForm.action, { method: 'POST', credentials: 'same-origin', body: formData })
        .then(function () { refreshMessages(); })
        .catch(function () { composerInput.value = contenu; });
    });
  }

  // ---------------------------------------------------------------
  // Pieces jointes : selection, apercu, upload avec barre de progression.
  // Validation cote serveur faisant foi (apps.messaging.attachments) — les
  // limites ci-dessous ne sont qu'un retour rapide, pas une garantie.
  // ---------------------------------------------------------------
  const attachmentInput = document.getElementById('attachment-input');
  const attachmentTrigger = document.getElementById('attachment-trigger');
  const uploadQueue = document.getElementById('upload-queue');
  const composerRow = document.getElementById('composer-row');
  const uploadUrl = composerForm ? composerForm.dataset.uploadUrl : null;
  const csrfToken = composerForm
    ? composerForm.querySelector('input[name="csrfmiddlewaretoken"]').value
    : null;

  const LIMITES_TAILLE_OCTETS = {
    image: 10 * 1024 * 1024,
    video: 100 * 1024 * 1024,
    document: 20 * 1024 * 1024,
    audio: 20 * 1024 * 1024,
  };
  const CATEGORIES_MIME = {
    'image/jpeg': 'image', 'image/png': 'image', 'image/webp': 'image',
    'video/mp4': 'video', 'video/webm': 'video', 'video/quicktime': 'video', 'video/ogg': 'video',
    'audio/webm': 'audio', 'audio/ogg': 'audio', 'audio/mp4': 'audio', 'audio/mpeg': 'audio',
    'audio/wav': 'audio', 'audio/aac': 'audio',
  };

  function categorieDeFichier(file) {
    // Les blobs MediaRecorder incluent parfois un parametre de codec
    // (ex. "audio/webm;codecs=opus") : on ne compare que le type de base.
    const type = (file.type || '').split(';')[0].trim();
    return CATEGORIES_MIME[type] || 'document';
  }

  function formaterTaille(octets) {
    if (octets > 1024 * 1024) return (octets / (1024 * 1024)).toFixed(1) + ' Mo';
    return Math.ceil(octets / 1024) + ' Ko';
  }

  if (attachmentTrigger && attachmentInput) {
    attachmentTrigger.addEventListener('click', function () {
      attachmentInput.click();
    });
    attachmentInput.addEventListener('change', function () {
      Array.from(attachmentInput.files).forEach(uploaderFichier);
      attachmentInput.value = '';
    });
  }

  function uploaderFichier(file, champsSupplementaires) {
    const categorie = categorieDeFichier(file);
    const limite = LIMITES_TAILLE_OCTETS[categorie] || LIMITES_TAILLE_OCTETS.document;

    const ligne = document.createElement('div');
    ligne.className = 'flex items-center gap-3 bg-surface-container-low rounded-xl p-2';
    uploadQueue.classList.remove('hidden');
    uploadQueue.appendChild(ligne);

    const icone = document.createElement('div');
    icone.className = 'w-10 h-10 rounded-lg overflow-hidden bg-surface-container-high flex items-center justify-center shrink-0';
    if (categorie === 'image') {
      const img = document.createElement('img');
      img.className = 'w-full h-full object-cover';
      img.src = URL.createObjectURL(file);
      icone.appendChild(img);
    } else {
      const span = document.createElement('span');
      span.className = 'material-symbols-outlined text-on-surface-variant';
      span.textContent = categorie === 'video' ? 'movie' : categorie === 'audio' ? 'mic' : 'description';
      icone.appendChild(span);
    }
    ligne.appendChild(icone);

    const info = document.createElement('div');
    info.className = 'flex-1 min-w-0';
    info.innerHTML =
      '<p class="text-label-sm font-bold text-on-surface truncate"></p>' +
      '<div class="flex items-center gap-2 mt-1">' +
      '<div class="flex-1 h-1.5 bg-surface-container-high rounded-full overflow-hidden"><div class="h-full bg-primary transition-all" style="width:0%"></div></div>' +
      '<span class="text-label-sm text-on-surface-variant shrink-0 statut">0%</span>' +
      '</div>';
    info.querySelector('p').textContent = file.name + ' · ' + formaterTaille(file.size);
    ligne.appendChild(info);

    const barre = info.querySelector('.h-full.bg-primary');
    const statut = info.querySelector('.statut');

    function retirerApresDelai(delai) {
      window.setTimeout(function () {
        ligne.remove();
        if (!uploadQueue.children.length) uploadQueue.classList.add('hidden');
      }, delai);
    }

    if (file.size > limite) {
      statut.textContent = 'Trop volumineux';
      statut.classList.add('text-error');
      retirerApresDelai(4000);
      return;
    }

    const xhr = new XMLHttpRequest();
    xhr.open('POST', uploadUrl);
    xhr.setRequestHeader('X-CSRFToken', csrfToken);

    xhr.upload.addEventListener('progress', function (event) {
      if (!event.lengthComputable) return;
      const pourcentage = Math.round((event.loaded / event.total) * 100);
      barre.style.width = pourcentage + '%';
      statut.textContent = pourcentage + '%';
    });

    xhr.addEventListener('load', function () {
      if (xhr.status === 200) {
        ligne.remove();
        if (!uploadQueue.children.length) uploadQueue.classList.add('hidden');
        refreshMessages();
        return;
      }
      let messageErreur = "Échec de l'envoi.";
      try {
        const reponse = JSON.parse(xhr.responseText);
        messageErreur = reponse.error || messageErreur;
      } catch (erreur) { /* reponse non-JSON, on garde le message par defaut */ }
      statut.textContent = messageErreur;
      statut.classList.add('text-error');
      barre.classList.replace('bg-primary', 'bg-error');
      retirerApresDelai(6000);
    });

    xhr.addEventListener('error', function () {
      statut.textContent = 'Erreur réseau';
      statut.classList.add('text-error');
      retirerApresDelai(6000);
    });

    const formData = new FormData();
    formData.append('fichier', file);
    if (champsSupplementaires) {
      Object.keys(champsSupplementaires).forEach(function (cle) {
        formData.append(cle, champsSupplementaires[cle]);
      });
    }
    xhr.send(formData);
  }

  // ---------------------------------------------------------------
  // Messages vocaux : MediaRecorder, une API native du navigateur (aucune
  // bibliotheque). Le bouton micro se desactive silencieusement si l'API
  // n'est pas disponible (navigateur trop ancien, contexte non securise) —
  // cf. cahier des charges : "utiliser les API natives lorsque disponibles".
  // ---------------------------------------------------------------
  const micButton = document.getElementById('mic-button');
  const voiceRecorderBar = document.getElementById('voice-recorder');
  const voiceTimer = document.getElementById('voice-timer');
  const voiceCancelBtn = document.getElementById('voice-cancel');
  const voiceStopBtn = document.getElementById('voice-stop');
  const voicePreviewBar = document.getElementById('voice-preview');
  const voicePreviewPlayer = document.getElementById('voice-preview-player');
  const voicePreviewDiscardBtn = document.getElementById('voice-preview-discard');
  const voicePreviewSendBtn = document.getElementById('voice-preview-send');
  const voicePreviewErreur = document.getElementById('voice-preview-erreur');

  function microDisponible() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && window.MediaRecorder);
  }

  if (micButton && !microDisponible()) {
    micButton.disabled = true;
    micButton.classList.add('opacity-40', 'cursor-not-allowed');
    micButton.title = 'Enregistrement vocal non disponible sur ce navigateur.';
  }

  let mediaRecorder = null;
  let audioStream = null;
  let audioChunks = [];
  let enregistrementAnnule = false;
  let debutEnregistrement = 0;
  let voiceTimerInterval = null;
  let dureeEnregistreeSecondes = 0;
  let blobEnregistre = null;
  let urlApercuVocal = null;

  function formaterChrono(secondes) {
    const m = Math.floor(secondes / 60);
    const s = secondes % 60;
    return m + ':' + String(s).padStart(2, '0');
  }

  function majChrono() {
    const ecoule = Math.floor((Date.now() - debutEnregistrement) / 1000);
    voiceTimer.textContent = formaterChrono(ecoule);
  }

  function afficherErreurVocal(message) {
    if (!voicePreviewErreur) return;
    voicePreviewErreur.textContent = message;
    voicePreviewErreur.classList.remove('hidden');
    window.setTimeout(function () { voicePreviewErreur.classList.add('hidden'); }, 4000);
  }

  function afficherComposerNormal() {
    if (composerRow) composerRow.classList.remove('hidden');
    if (voiceRecorderBar) voiceRecorderBar.classList.add('hidden');
    if (voicePreviewBar) voicePreviewBar.classList.add('hidden');
  }

  function extensionPourType(type) {
    if (type.indexOf('mp4') !== -1) return 'm4a';
    if (type.indexOf('ogg') !== -1) return 'ogg';
    if (type.indexOf('wav') !== -1) return 'wav';
    return 'webm';
  }

  async function demarrerEnregistrement() {
    if (!microDisponible()) return;
    try {
      audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (erreur) {
      afficherErreurVocal("Micro inaccessible — vérifiez l'autorisation du navigateur.");
      return;
    }

    audioChunks = [];
    enregistrementAnnule = false;
    try {
      mediaRecorder = new MediaRecorder(audioStream);
    } catch (erreur) {
      audioStream.getTracks().forEach(function (piste) { piste.stop(); });
      afficherErreurVocal("Enregistrement impossible sur ce navigateur.");
      return;
    }

    mediaRecorder.addEventListener('dataavailable', function (event) {
      if (event.data && event.data.size > 0) audioChunks.push(event.data);
    });

    mediaRecorder.addEventListener('stop', function () {
      audioStream.getTracks().forEach(function (piste) { piste.stop(); });
      window.clearInterval(voiceTimerInterval);

      if (enregistrementAnnule) {
        afficherComposerNormal();
        return;
      }
      dureeEnregistreeSecondes = Math.max(1, Math.round((Date.now() - debutEnregistrement) / 1000));
      blobEnregistre = new Blob(audioChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
      urlApercuVocal = URL.createObjectURL(blobEnregistre);
      voicePreviewPlayer.src = urlApercuVocal;
      voiceRecorderBar.classList.add('hidden');
      voicePreviewBar.classList.remove('hidden');
    });

    mediaRecorder.start();
    debutEnregistrement = Date.now();
    if (composerRow) composerRow.classList.add('hidden');
    voicePreviewBar.classList.add('hidden');
    voiceTimer.textContent = '0:00';
    voiceRecorderBar.classList.remove('hidden');
    voiceTimerInterval = window.setInterval(majChrono, 500);
  }

  function arreterEtPrevisualiser() {
    enregistrementAnnule = false;
    if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  }

  function annulerEnregistrement() {
    enregistrementAnnule = true;
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    } else {
      afficherComposerNormal();
    }
  }

  function annulerApercuVocal() {
    if (urlApercuVocal) URL.revokeObjectURL(urlApercuVocal);
    blobEnregistre = null;
    voicePreviewPlayer.src = '';
    afficherComposerNormal();
  }

  function envoyerVocal() {
    if (!blobEnregistre) return;
    const nomFichier = 'vocal.' + extensionPourType(blobEnregistre.type);
    const fichierVocal = new File([blobEnregistre], nomFichier, { type: blobEnregistre.type });
    uploaderFichier(fichierVocal, { duree_secondes: dureeEnregistreeSecondes });
    if (urlApercuVocal) URL.revokeObjectURL(urlApercuVocal);
    blobEnregistre = null;
    afficherComposerNormal();
  }

  if (micButton) micButton.addEventListener('click', demarrerEnregistrement);
  if (voiceStopBtn) voiceStopBtn.addEventListener('click', arreterEtPrevisualiser);
  if (voiceCancelBtn) voiceCancelBtn.addEventListener('click', annulerEnregistrement);
  if (voicePreviewDiscardBtn) voicePreviewDiscardBtn.addEventListener('click', annulerApercuVocal);
  if (voicePreviewSendBtn) voicePreviewSendBtn.addEventListener('click', envoyerVocal);

  // ---------------------------------------------------------------
  // Emoji : selecteur minimal en Unicode natif (pas d'image, pas de
  // dependance externe — fonctionne hors-ligne comme le reste de la PWA).
  // Insertion au niveau du curseur, pas juste en fin de champ.
  // ---------------------------------------------------------------
  const EMOJI_CATEGORIES = [
    { nom: 'Smileys', emojis: ['😀', '😃', '😄', '😁', '😆', '😅', '🤣', '😂', '🙂', '🙃', '😉', '😊', '😇', '🥰', '😍', '😘', '😋', '😛', '😜', '🤪', '🤑', '🤗', '🤭', '🤫', '🤔', '😐', '😑', '🙄', '😏', '😴', '😪', '😌', '😢', '😭', '😡', '🥳', '😎'] },
    { nom: 'Gestes', emojis: ['👍', '👎', '👌', '✌️', '🤞', '🤝', '👏', '🙌', '👐', '🙏', '💪', '👋', '✋', '👊', '✊', '👆', '👇', '👉', '👈', '☝️'] },
    { nom: 'Coeurs', emojis: ['❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '🤍', '🤎', '💔', '❣️', '💕', '💞', '💓', '💗', '💖', '💘', '💝'] },
    { nom: 'Nature', emojis: ['🐶', '🐱', '🐭', '🐹', '🐰', '🦊', '🐻', '🐼', '🐨', '🐯', '🦁', '🐮', '🐷', '🐸', '🐵', '🌸', '🌼', '🌻', '🌞', '🌧️', '❄️', '⭐', '🔥', '🌈'] },
    { nom: 'Nourriture', emojis: ['🍎', '🍌', '🍇', '🍉', '🍓', '🍕', '🍔', '🍟', '🌭', '🍿', '🍩', '🍪', '🎂', '🍰', '☕', '🍵', '🍺', '🍷', '🥤', '🍫'] },
    { nom: 'Objets', emojis: ['🎉', '🎊', '🎁', '🎈', '✅', '❌', '⚠️', '📌', '📎', '🔔', '💡', '⏰', '📅', '📞', '💬', '✏️', '📄', '📦', '🚀', '✈️'] },
  ];

  const emojiTrigger = document.getElementById('emoji-trigger');
  const emojiPicker = document.getElementById('emoji-picker');
  const emojiTabs = document.getElementById('emoji-picker-tabs');
  const emojiGrid = document.getElementById('emoji-picker-grid');

  function insererEmoji(emoji) {
    if (!composerInput) return;
    const debut = composerInput.selectionStart != null ? composerInput.selectionStart : composerInput.value.length;
    const fin = composerInput.selectionEnd != null ? composerInput.selectionEnd : composerInput.value.length;
    composerInput.value = composerInput.value.slice(0, debut) + emoji + composerInput.value.slice(fin);
    const position = debut + emoji.length;
    composerInput.focus();
    composerInput.setSelectionRange(position, position);
  }

  function afficherCategorieEmoji(index) {
    emojiGrid.innerHTML = '';
    EMOJI_CATEGORIES[index].emojis.forEach(function (emoji) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = emoji;
      btn.className = 'text-xl leading-none hover:bg-surface-container-low rounded-lg p-1.5 transition-colors';
      btn.addEventListener('click', function () { insererEmoji(emoji); });
      emojiGrid.appendChild(btn);
    });
    Array.prototype.forEach.call(emojiTabs.children, function (tab, i) {
      tab.classList.toggle('text-primary', i === index);
      tab.classList.toggle('border-primary', i === index);
      tab.classList.toggle('text-on-surface-variant', i !== index);
      tab.classList.toggle('border-transparent', i !== index);
    });
  }

  if (emojiTrigger && emojiPicker && emojiTabs && emojiGrid) {
    EMOJI_CATEGORIES.forEach(function (categorie, index) {
      const tab = document.createElement('button');
      tab.type = 'button';
      tab.textContent = categorie.emojis[0];
      tab.title = categorie.nom;
      tab.className = 'flex-1 py-2 text-lg border-b-2 transition-colors '
        + (index === 0 ? 'text-primary border-primary' : 'text-on-surface-variant border-transparent');
      tab.addEventListener('click', function () { afficherCategorieEmoji(index); });
      emojiTabs.appendChild(tab);
    });
    afficherCategorieEmoji(0);

    emojiTrigger.addEventListener('click', function (event) {
      event.stopPropagation();
      emojiPicker.classList.toggle('hidden');
    });
    document.addEventListener('click', function (event) {
      if (!emojiPicker.classList.contains('hidden')
        && !emojiPicker.contains(event.target) && event.target !== emojiTrigger) {
        emojiPicker.classList.add('hidden');
      }
    });
  }
})();
