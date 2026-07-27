"""Utilitaires partages par les vues Ajax "rejouables" (voir apps/offline_sync/models.py::SyncedAction).

Chaque vue qui accepte une action potentiellement mise en file d'attente hors
ligne (voir static/notification/js/service-worker.js, evenement 'sync') doit :
  1. verifier l'idempotence via `action_deja_appliquee` avant tout traitement ;
  2. comparer `date_modifier` du modele avec l'horodatage connu du client via
     `date_modifier_correspond` avant d'appliquer quoi que ce soit ;
  3. enregistrer le resultat via `enregistrer_action_synchronisee` apres succes.
"""
from django.http import JsonResponse

from .models import SyncedAction


def action_deja_appliquee(client_action_id, user):
    """Retourne la SyncedAction existante si cette action a deja ete rejouee
    avec succes (redelivrance Background Sync dont la reponse precedente
    n'est jamais arrivee jusqu'au client), sinon None."""
    if not client_action_id:
        return None
    return SyncedAction.objects.filter(client_action_id=client_action_id, user=user).first()


def enregistrer_action_synchronisee(client_action_id, user, endpoint, result_snapshot):
    SyncedAction.objects.create(
        client_action_id=client_action_id,
        user=user,
        endpoint=endpoint,
        result_snapshot=result_snapshot,
    )


def date_modifier_correspond(instance, client_date_modifier):
    """Compare le `date_modifier` courant de l'instance (precision seconde,
    car transmis en epoch secondes cote client via le filtre `|date:'U'`) a
    l'horodatage connu du client au moment ou l'action a ete mise en file
    d'attente. Une non-correspondance signifie que l'etat a change entretemps
    (autre agent, ou action serveur) : le rejeu ne doit alors rien appliquer."""
    if not client_date_modifier:
        return False
    try:
        client_epoch = int(client_date_modifier)
    except (TypeError, ValueError):
        return False
    return int(instance.date_modifier.timestamp()) == client_epoch


def reponse_conflit(current_state):
    return JsonResponse({'success': False, 'conflict': True, 'current': current_state}, status=409)
