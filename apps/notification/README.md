# Notifications Web Push

Système de notifications (in-app + Web Push navigateur) pour l'application de
gestion de dossiers de transit/logistique. Tout passe par
`NotificationService` (`apps/notification/services.py`) : les vues n'appellent
que ses méthodes, jamais directement `Notification`/`PushSubscription`.

## Architecture

- `models.py` — `Notification` (in-app, alimente la cloche de chaque dashboard)
  et `PushSubscription` (un abonnement navigateur par appareil/navigateur).
- `services.py` — `NotificationService` : création des notifications +
  déclenchement du Web Push. Méthodes métier : `notify_dossier_created`,
  `notify_payment_validated`, `notify_status_changed`, `notify_document_added`,
  `notify_return_selection`, `notify_return_empotage`.
- `utils.py` — envoi bas niveau via `pywebpush` ; supprime automatiquement les
  abonnements expirés/invalides (410/404) sans jamais lever d'exception vers
  l'appelant.
- `views.py` — `push_subscribe` / `push_unsubscribe` (endpoints POST classiques,
  pas une API REST) + `service_worker` (sert `/sw.js` à la racine du site).
- `static/notification/js/service-worker.js` — écoute les push, affiche la
  notification, ouvre le dossier concerné au clic.
- `static/notification/js/push-notifications.js` — enregistre le Service
  Worker, demande la permission et crée/réutilise l'abonnement Push.
- `templates/notification/_push_bootstrap.html` — partial inclus dans les 5
  base templates (`base_personnel.html`, `base_client.html`,
  `base_agent_selection.html`, `base_agent_empotage.html`,
  `base_comptabilite.html`), juste avant `</body>`.

## 1. Générer les clés VAPID

`py-vapid` est déjà dans `requirements.txt` (dépendance de `pywebpush`). Le
navigateur (`applicationServerKey`) et `pywebpush` (`VAPID_PRIVATE_KEY`)
attendent tous les deux des clés **brutes encodées en base64url**, pas des
fichiers `.pem` — `vapid --gen` seul ne suffit donc pas, il faut les
ré-exporter dans ce format avec le script ci-dessous :

```bash
python -c "
from py_vapid import Vapid02, b64urlencode
from py_vapid.utils import num_to_bytes
from cryptography.hazmat.primitives import serialization

v = Vapid02()
v.generate_keys()

pub_raw = v.public_key.public_bytes(
    serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
)
priv_raw = num_to_bytes(v.private_key.private_numbers().private_value, 32)

print(f'VAPID_PUBLIC_KEY={b64urlencode(pub_raw)}')
print(f'VAPID_PRIVATE_KEY={b64urlencode(priv_raw)}')
"
```

Ce script génère une paire de clés et affiche directement les deux valeurs au
format attendu (vérifié : `pywebpush.webpush(vapid_private_key=...)` accepte
cette chaîne brute via `Vapid02.from_string()`, qui redérive correctement la
clé publique correspondante). Copier les deux lignes affichées dans `.env` :

```
VAPID_PUBLIC_KEY=<clé publique base64url>
VAPID_PRIVATE_KEY=<clé privée base64url>
VAPID_ADMIN_EMAIL=infos@oils-of-africa.com
```

Ces trois variables sont lues dans `config/settings.py`. Ne jamais committer
les clés réelles dans `.env` (déjà exclu du dépôt).

## 2. Configuration pywebpush

`pywebpush==2.3.0` est dans `requirements.txt`. Aucune configuration
supplémentaire : `apps/notification/utils.py` construit les `vapid_claims`
(`{'sub': 'mailto:<VAPID_ADMIN_EMAIL>'}`) et appelle `webpush()` avec la clé
privée à chaque envoi.

## 3. Emplacement du Service Worker

Le fichier source vit dans `static/notification/js/service-worker.js` (avec
les autres statiques de l'app), mais il **doit être servi à la racine du
site** (`/sw.js`) pour pouvoir contrôler toutes les pages, quel que soit le
dashboard visité — une portée `/static/...` limiterait les notifications aux
pages sous ce préfixe. C'est le rôle de la vue `service_worker` (branchée sur
`path('sw.js', ...)` dans `config/urls.py`), qui lit le fichier sur disque et
répond avec l'en-tête `Service-Worker-Allowed: /`.

## 4. Enregistrement automatique du navigateur

`push-notifications.js` s'exécute sur chaque page (inclus dans les 5 base
templates). À l'arrivée sur une page :

1. il enregistre `/sw.js` ;
2. si un abonnement existe déjà pour ce navigateur (`getSubscription()`), il
   le réutilise et le renvoie simplement au serveur (`notification:push-subscribe`) ;
3. sinon, il demande la permission (`Notification.requestPermission()`) — si
   refusée, on abandonne silencieusement et on ne re-sollicite plus tant que
   `Notification.permission === 'denied'` ;
4. si accordée, il crée l'abonnement avec `VAPID_PUBLIC_KEY` (exposée à tous
   les templates via `apps/notification/context_processors.py`) et l'envoie
   au serveur, qui le stocke via `PushSubscription.objects.update_or_create`
   (clé : `endpoint`, donc pas de doublon si le navigateur ré-abonne).

## 5. Tester en développement

1. Renseigner `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` / `VAPID_ADMIN_EMAIL`
   dans `.env.dev`.
2. Lancer le serveur (`python manage.py runserver`) — **en HTTPS ou sur
   `localhost`** : la Push API du navigateur exige un contexte sécurisé, mais
   `localhost` est explicitement autorisé même en HTTP par tous les
   navigateurs modernes, donc `runserver` par défaut suffit.
3. Se connecter avec un compte de test, accepter la demande de permission de
   notification.
4. Vérifier dans `Admin Django > Abonnements Push` qu'un `PushSubscription`
   a bien été créé pour l'utilisateur.
5. Déclencher un événement (créer un dossier, valider un paiement, ajouter un
   document, changer de statut, rétrograder) et vérifier :
   - la notification apparaît dans la cloche (`Notification` créée en base) ;
   - une notification système apparaît même onglet fermé/en arrière-plan tant
     que le navigateur tourne.
6. Pour rejouer un envoi manuellement sans repasser par le flux métier :
   ```python
   from apps.notification.services import NotificationService
   from apps.conteneurs.models import Dossier
   NotificationService.notify_dossier_created(Dossier.objects.first())
   ```

## 6. Déploiement en production

- Générer une paire de clés VAPID **dédiée à la prod** (différente du dev) et
  la stocker uniquement dans les variables d'environnement du serveur
  (jamais dans le dépôt).
- Le site doit être servi en **HTTPS** (obligatoire pour la Push API hors
  `localhost`).
- `python manage.py collectstatic` doit inclure
  `static/notification/js/service-worker.js` et `push-notifications.js`
  (déjà sous `STATICFILES_DIRS`, aucune config supplémentaire nécessaire).
- Vérifier que `/sw.js` répond bien avec `Content-Type: application/javascript`
  et l'en-tête `Service-Worker-Allowed: /` (testable avec
  `curl -I https://<domaine>/sw.js`).
- `VAPID_ADMIN_EMAIL` doit être une adresse valide et surveillée : certains
  navigateurs (Mozilla Push Service en particulier) l'utilisent pour
  contacter l'éditeur en cas d'abus détecté.
- Les abonnements expirés/invalides sont nettoyés automatiquement à l'envoi
  (`utils.send_web_push`) : aucune tâche de purge planifiée n'est nécessaire.
