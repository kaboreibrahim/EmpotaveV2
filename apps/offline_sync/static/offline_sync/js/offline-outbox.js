/*
 * Interception des formulaires "hors ligne capables" (voir l'attribut
 * data-offline-form sur les 3 formulaires du pilote : empotage d'un
 * conteneur, retrogradation de dossier, retour en selection) + petit widget
 * "actions en attente" a cote de la cloche de notifications existante.
 *
 * Comportement : on tente toujours un fetch() direct en premier (identique a
 * aujourd'hui quand il y a du reseau). Seul un echec reseau (fetch qui rejette
 * sa promesse) declenche la mise en file d'attente locale + l'enregistrement
 * d'une synchronisation en arriere-plan — jamais un code d'erreur HTTP
 * (409/400), qui est un vrai desaccord metier a traiter tout de suite, pas
 * hors ligne.
 */
(function () {
  function genererClientActionId() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  const STYLES_STATUT = {
    conflict: 'bg-error/10 border-error text-error',
    error: 'bg-error/10 border-error text-error',
    queued: 'bg-tertiary/10 border-tertiary text-tertiary',
  };
  const ICONES_STATUT = { conflict: 'error', error: 'error', queued: 'cloud_off' };

  function afficherStatutFormulaire(form, statut, message) {
    const el = form.querySelector('[data-offline-status]');
    if (!el) return;
    el.className = 'rounded-lg border p-3 mb-3 text-label-sm flex items-start gap-2 ' + (STYLES_STATUT[statut] || '');
    el.innerHTML =
      '<span class="material-symbols-outlined text-[18px]">' + (ICONES_STATUT[statut] || 'info') + '</span>' +
      '<span>' + message + '</span>';
    el.classList.remove('hidden');
  }

  function decomposerFormData(formData) {
    const fields = {};
    const files = {};
    for (const [cle, valeur] of formData.entries()) {
      if (valeur instanceof File) {
        if (valeur.size > 0) {
          files[cle] = { blob: valeur, name: valeur.name, type: valeur.type };
        }
      } else {
        fields[cle] = valeur;
      }
    }
    return { fields, files };
  }

  function mettreEnFileDattente(form, formData) {
    const { fields, files } = decomposerFormData(formData);
    return IdbOutbox.add({
      clientActionId: fields.client_action_id,
      kind: form.dataset.offlineKind,
      url: form.dataset.ajaxUrl,
      fields: fields,
      files: files,
      baseDateModifier: form.dataset.dateModifier,
      viewUrl: form.dataset.successRedirect,
      queuedAt: Date.now(),
      status: 'pending',
    }).then(function () {
      if ('serviceWorker' in navigator && 'SyncManager' in window) {
        return navigator.serviceWorker.ready
          .then(function (reg) { return reg.sync.register('outbox-sync'); })
          .catch(function () { /* Background Sync indisponible : la file reste, sera reprise a la prochaine ouverture. */ });
      }
    });
  }

  function attacherFormulaire(form) {
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      const boutonEnvoi = form.querySelector('button[type="submit"]');
      const formData = new FormData(form);
      formData.set('client_action_id', genererClientActionId());
      formData.set('client_date_modifier', form.dataset.dateModifier || '');
      if (boutonEnvoi) boutonEnvoi.disabled = true;

      fetch(form.dataset.ajaxUrl, { method: 'POST', body: formData })
        .then(function (reponse) {
          return reponse
            .json()
            .catch(function () { return {}; })
            .then(function (data) { return { reponse, data }; });
        })
        .then(function (resultat) {
          const { reponse, data } = resultat;
          if (reponse.ok && data.success) {
            window.location.href = form.dataset.successRedirect;
            return;
          }
          if (reponse.status === 409) {
            afficherStatutFormulaire(
              form, 'conflict',
              "Cet enregistrement a été modifié entretemps. Rechargez la page pour voir l'état actuel avant de recommencer."
            );
            if (boutonEnvoi) boutonEnvoi.disabled = false;
            return;
          }
          afficherStatutFormulaire(
            form, 'error',
            "Le formulaire contient des erreurs ou l'action n'a pas pu être appliquée. Vérifiez les champs et réessayez."
          );
          if (boutonEnvoi) boutonEnvoi.disabled = false;
        })
        .catch(function () {
          mettreEnFileDattente(form, formData).then(function () {
            afficherStatutFormulaire(
              form, 'queued',
              "Hors ligne — cette action a été mise en file d'attente et sera envoyée automatiquement dès que la connexion revient."
            );
            rafraichirBadge();
          });
        });
    });
  }

  // --- Widget "actions en attente" (conflits / echecs definitifs) ---

  function rafraichirBadge() {
    const badge = document.getElementById('offline-outbox-badge');
    if (!badge || typeof IdbOutbox === 'undefined') return;
    IdbOutbox.getNeedsAttention().then(function (lignes) {
      if (lignes.length > 0) {
        badge.textContent = String(lignes.length);
        badge.classList.remove('hidden');
      } else {
        badge.classList.add('hidden');
      }
    });
  }

  function libelleAction(kind) {
    if (kind === 'empotage_renseigner') return "Empotage d'un conteneur";
    if (kind === 'dossier_retrograder') return 'Rétrogradation de dossier';
    if (kind === 'dossier_retour_selection') return 'Retour en sélection';
    return kind;
  }

  function afficherPanneau() {
    const liste = document.getElementById('offline-outbox-list');
    if (!liste) return;
    IdbOutbox.getNeedsAttention().then(function (lignes) {
      if (lignes.length === 0) {
        liste.innerHTML =
          '<div class="p-8 text-center text-on-surface-variant">' +
          '<span class="material-symbols-outlined text-3xl block mb-2 opacity-40">cloud_done</span>' +
          '<p class="text-body-sm">Aucune action en attente.</p></div>';
        return;
      }
      liste.innerHTML = lignes
        .map(function (ligne) {
          const statutLabel = ligne.status === 'conflict' ? 'Conflit : état modifié entretemps' : 'Échec de synchronisation';
          return (
            '<div class="p-4 space-y-2">' +
            '<p class="text-label-sm font-bold text-on-surface">' + libelleAction(ligne.kind) + '</p>' +
            '<p class="text-label-sm text-error">' + statutLabel + (ligne.lastError ? ' — ' + ligne.lastError : '') + '</p>' +
            '<div class="flex gap-3">' +
            (ligne.viewUrl ? '<a href="' + ligne.viewUrl + '" class="text-label-sm text-primary hover:underline">Voir le dossier</a>' : '') +
            '<button type="button" data-discard="' + ligne.localId + '" class="text-label-sm text-on-surface-variant hover:underline">Rejeter</button>' +
            '</div></div>'
          );
        })
        .join('');
      liste.querySelectorAll('[data-discard]').forEach(function (bouton) {
        bouton.addEventListener('click', function () {
          IdbOutbox.remove(parseInt(bouton.dataset.discard, 10)).then(function () {
            rafraichirBadge();
            afficherPanneau();
          });
        });
      });
    });
  }

  function initialiserWidget() {
    const toggle = document.getElementById('offline-outbox-toggle');
    const panneau = document.getElementById('offline-outbox-panel');
    if (!toggle || !panneau || typeof IdbOutbox === 'undefined') return;

    rafraichirBadge();

    toggle.addEventListener('click', function (event) {
      event.stopPropagation();
      const estOuvert = !panneau.classList.contains('hidden');
      if (estOuvert) {
        panneau.classList.add('hidden');
      } else {
        afficherPanneau();
        panneau.classList.remove('hidden');
      }
    });
    document.addEventListener('click', function () { panneau.classList.add('hidden'); });
    panneau.addEventListener('click', function (event) { event.stopPropagation(); });

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('message', function (event) {
        if (event.data && event.data.type === 'offline-outbox-updated') {
          rafraichirBadge();
        }
      });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('form[data-offline-form]').forEach(attacherFormulaire);
    initialiserWidget();
  });
})();
