/*
 * Service Worker — notifications Web Push + support PWA (installation,
 * page de secours hors-ligne, cache des fichiers statiques, rejeu des
 * actions hors ligne via Background Sync).
 * Servi à la racine du site (/sw.js, voir apps/notification/views.service_worker)
 * pour pouvoir recevoir des push même lorsque l'utilisateur n'a aucun onglet
 * de l'application ouvert (tant que le navigateur tourne et que la
 * permission a été accordée).
 */

importScripts('/static/offline_sync/js/idb-outbox.js');

const ICONE_PAR_DEFAUT = '/static/img/logo.png';

// Incrémenter ce numéro invalide les anciens caches (voir 'activate').
const CACHE_VERSION = 'v1';
const APP_SHELL_CACHE = `app-shell-${CACHE_VERSION}`;
const RUNTIME_CACHE = `runtime-${CACHE_VERSION}`;

// Le reste de l'application (Tailwind/Alpine/polices via CDN, contenu
// dynamique par utilisateur) ne peut pas raisonnablement fonctionner hors
// ligne : on ne met en cache qu'une page de secours minimale et quelques
// icônes, pas les pages du tableau de bord elles-mêmes.
const PRECACHE_URLS = ['/static/offline.html', '/static/img/icons/icon-192.png', '/static/img/logo.png'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(APP_SHELL_CACHE).then((cache) => cache.addAll(PRECACHE_URLS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((noms) =>
        Promise.all(
          noms
            .filter((nom) => nom !== APP_SHELL_CACHE && nom !== RUNTIME_CACHE)
            .map((nom) => caches.delete(nom))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') {
    return; // Formulaires, actions AJAX, etc. : toujours en direct, jamais depuis le cache.
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return; // CDN externes (Tailwind, polices) : gérés par le navigateur, pas par ce Service Worker.
  }

  if (request.mode === 'navigate') {
    // Pages HTML : toujours essayer le réseau en premier (contenu dynamique par
    // utilisateur), et n'afficher la page de secours qu'en dernier recours.
    event.respondWith(
      fetch(request).catch(() => caches.match('/static/offline.html'))
    );
    return;
  }

  if (url.pathname.startsWith('/static/')) {
    // Fichiers statiques : servis avec un nom de fichier haché par
    // WhiteNoise (immutables), donc sans risque en cache-first.
    event.respondWith(
      caches.match(request).then(
        (reponse) =>
          reponse ||
          fetch(request).then((reseauReponse) => {
            const copie = reseauReponse.clone();
            caches.open(RUNTIME_CACHE).then((cache) => cache.put(request, copie));
            return reseauReponse;
          })
      )
    );
  }
});

// =============================================================================
// Rejeu des actions hors ligne (voir apps/offline_sync et
// apps/offline_sync/static/offline_sync/js/offline-outbox.js, qui met les
// actions en file d'attente dans IndexedDB quand un fetch() echoue faute de
// reseau). Un seul tag partage : a chaque declenchement on vide toute la file
// plutot que d'enregistrer un tag par action (reenregistrer un tag deja en
// attente est un no-op cote navigateur, donc inutile de les distinguer).
// =============================================================================

self.addEventListener('sync', (event) => {
  if (event.tag === 'outbox-sync') {
    event.waitUntil(vidangerFileDattente());
  }
});

function reconstruireFormData(action) {
  const formData = new FormData();
  Object.keys(action.fields || {}).forEach((cle) => formData.append(cle, action.fields[cle]));
  Object.keys(action.files || {}).forEach((cle) => {
    const fichier = action.files[cle];
    formData.append(cle, new File([fichier.blob], fichier.name, { type: fichier.type }));
  });
  return formData;
}

async function rejouerAction(action) {
  // Le champ cache `csrfmiddlewaretoken` (rendu par {% csrf_token %} sur le
  // formulaire d'origine) fait deja partie de `action.fields` : pas besoin de
  // relire un cookie CSRF depuis ce contexte sans `document`, le token capture
  // au moment de la mise en file d'attente reste valide (meme secret de
  // session, pas de rotation par requete cote Django).
  const formData = reconstruireFormData(action);

  let reponse;
  try {
    reponse = await fetch(action.url, { method: 'POST', body: formData, credentials: 'same-origin' });
  } catch (erreurReseau) {
    // Toujours pas de reseau : on relance l'erreur pour que le navigateur
    // reessaie ce tag plus tard avec son propre backoff, sans toucher au statut.
    throw erreurReseau;
  }

  const typeContenu = reponse.headers.get('content-type') || '';
  if (!typeContenu.includes('application/json')) {
    // Redirection vers /login/ (session expiree) ou autre reponse inattendue :
    // Background Sync ne peut pas se reauthentifier lui-meme.
    await IdbOutbox.update(action.localId, { status: 'failed', lastError: 'session_expired' });
    return;
  }

  const donnees = await reponse.json().catch(() => ({}));

  if (reponse.ok && donnees.success) {
    await IdbOutbox.remove(action.localId);
    return;
  }
  if (reponse.status === 409) {
    // Conflit metier (etat modifie entretemps) : le serveur a deja notifie
    // l'utilisateur via NotificationService.notify_sync_conflict. On ne
    // rejouera plus cette action automatiquement, elle attend une decision.
    await IdbOutbox.update(action.localId, { status: 'conflict', lastError: null });
    return;
  }
  // 400 ou autre erreur definitive : ne sera plus rejouee automatiquement.
  await IdbOutbox.update(action.localId, { status: 'failed', lastError: `Erreur ${reponse.status}` });
}

async function vidangerFileDattente() {
  const enAttente = (await IdbOutbox.getByStatus('pending')).sort((a, b) => a.queuedAt - b.queuedAt);
  for (const action of enAttente) {
    await rejouerAction(action);
  }
  const clientsOuverts = await self.clients.matchAll({ type: 'window' });
  clientsOuverts.forEach((client) => client.postMessage({ type: 'offline-outbox-updated' }));
}

self.addEventListener('push', (event) => {
  let donnees = {};
  try {
    donnees = event.data ? event.data.json() : {};
  } catch (erreur) {
    donnees = { title: 'Notification', body: event.data ? event.data.text() : '' };
  }

  const titre = donnees.title || 'Nouvelle notification';
  const options = {
    body: donnees.body || '',
    icon: donnees.icon || ICONE_PAR_DEFAUT,
    badge: donnees.badge || ICONE_PAR_DEFAUT,
    tag: donnees.tag || 'notification',
    data: { url: donnees.url || '/' },
  };

  event.waitUntil(
    self.registration.showNotification(titre, options).catch((erreur) => {
      // N'interrompt jamais le Service Worker : on journalise et on continue.
      console.error('Erreur affichage notification Push :', erreur);
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientsList) => {
      for (const client of clientsList) {
        if (client.url === url && 'focus' in client) {
          return client.focus();
        }
      }
      if (self.clients.openWindow) {
        return self.clients.openWindow(url);
      }
    })
  );
});
