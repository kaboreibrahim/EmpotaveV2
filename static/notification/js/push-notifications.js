/*
 * Enregistrement automatique du Service Worker + abonnement Web Push.
 * Inclus dans chaque base template (voir data-attributes sur <body> ou sur
 * le script lui-même) : clé publique VAPID + URLs des endpoints Django.
 *
 * Comportement :
 *  - si un abonnement existe déjà côté navigateur, il est réutilisé
 *    (aucune nouvelle demande de permission, aucun nouvel abonnement créé) ;
 *  - sinon, la permission est demandée puis l'abonnement est créé et envoyé
 *    au serveur ;
 *  - si l'utilisateur refuse la permission ou que le navigateur ne supporte
 *    pas le Push, on abandonne silencieusement (aucune notification n'est
 *    critique au fonctionnement du site).
 */
(function () {
  const config = document.getElementById('push-notifications-config');
  if (!config) return;

  const VAPID_PUBLIC_KEY = config.dataset.vapidPublicKey;
  const SUBSCRIBE_URL = config.dataset.subscribeUrl;
  const CSRF_TOKEN = config.dataset.csrfToken;

  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
    return; // Navigateur non compatible : on n'affiche rien, on n'insiste pas.
  }
  if (!VAPID_PUBLIC_KEY) {
    return; // Clés VAPID non configurées (voir apps/notification/README.md).
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = window.atob(base64);
    return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
  }

  // Détecte un abonnement créé avec une ancienne clé VAPID (ex : clés
  // régénérées côté serveur) : le service de push le refuserait alors
  // définitivement avec une 403 "credentials do not correspond". Sans cette
  // vérification, un abonnement existant est toujours réutilisé tel quel
  // (voir initialiserPush) et resterait invalide indéfiniment.
  function abonnementCorrespondALaCleActuelle(subscription) {
    const cleAttendue = subscription.options && subscription.options.applicationServerKey;
    if (!cleAttendue) {
      return true; // Navigateur ne l'expose pas : on ne peut pas vérifier, on suppose que c'est bon.
    }
    const attendue = urlBase64ToUint8Array(VAPID_PUBLIC_KEY);
    const actuelle = new Uint8Array(cleAttendue);
    return (
      attendue.length === actuelle.length && attendue.every((octet, i) => octet === actuelle[i])
    );
  }

  function envoyerAbonnementAuServeur(subscription) {
    return fetch(SUBSCRIBE_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': CSRF_TOKEN,
      },
      body: JSON.stringify(subscription.toJSON()),
    }).catch((erreur) => {
      console.error('Impossible d’enregistrer l’abonnement Push côté serveur :', erreur);
    });
  }

  async function initialiserPush() {
    try {
      const registration = await navigator.serviceWorker.register('/sw.js');

      // Réutilise l'abonnement existant s'il y en a déjà un pour ce navigateur,
      // sauf s'il a été créé avec une clé VAPID différente de celle configurée
      // actuellement (rotation de clés côté serveur) : dans ce cas il faut le
      // remplacer, sans quoi le service de push le refusera indéfiniment.
      let subscription = await registration.pushManager.getSubscription();
      if (subscription && !abonnementCorrespondALaCleActuelle(subscription)) {
        await subscription.unsubscribe();
        subscription = null;
      }
      if (subscription) {
        await envoyerAbonnementAuServeur(subscription);
        return;
      }

      if (Notification.permission === 'denied') {
        return; // L'utilisateur a déjà refusé : ne pas re-solliciter.
      }

      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        return;
      }

      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });
      await envoyerAbonnementAuServeur(subscription);
    } catch (erreur) {
      console.error('Initialisation des notifications Push impossible :', erreur);
    }
  }

  initialiserPush();
})();
