"""
apps/conteneurs/services.py
Vérifications métier réutilisables sur Dossier.
"""
from django.core.exceptions import PermissionDenied


def verifier_paiement(dossier):
    """Bloque toute action métier tant que le paiement du dossier n'est pas validé."""
    if not dossier.est_paye:
        raise PermissionDenied("Le dossier est en attente de validation du paiement.")
