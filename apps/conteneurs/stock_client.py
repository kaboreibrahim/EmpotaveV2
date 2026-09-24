"""
apps/conteneurs/stock_client.py
Client HTTP vers oils-stock-api (intégration flexitanks/heating pads — voir
apps.conteneurs.stock_client.StockServiceIndisponible pour la gestion
d'erreur). Authentification par clé API (X-API-Key), pas de JWT : voir
IsEmpotageService côté oils-stock-api.
"""
import requests
from django.conf import settings


class StockServiceIndisponible(Exception):
    """oils-stock-api est injoignable ou a répondu une erreur — à intercepter
    par l'appelant pour dégrader gracieusement (voir option a du dossier
    d'intégration : ne jamais bloquer EmpotaveV2 sur une panne réseau)."""


def _headers():
    return {"X-API-Key": settings.STOCK_API_KEY}


def _requete(methode, chemin, **kwargs):
    # `chemin` peut déjà être une URL absolue (le `next` renvoyé par la
    # pagination DRF dans lister_clients) — dans ce cas on ne re-préfixe pas.
    if chemin.startswith("http://") or chemin.startswith("https://"):
        url = chemin
    else:
        url = f"{settings.STOCK_API_BASE_URL.rstrip('/')}/{chemin.lstrip('/')}"
    try:
        reponse = requests.request(
            methode, url, headers=_headers(), timeout=settings.STOCK_API_TIMEOUT, **kwargs
        )
    except requests.RequestException as exc:
        raise StockServiceIndisponible(f"oils-stock-api injoignable ({exc}).") from exc
    if reponse.status_code >= 400:
        raise StockServiceIndisponible(
            f"oils-stock-api a répondu {reponse.status_code} sur {methode} {chemin} : {reponse.text[:300]}"
        )
    return reponse


def creer_sortie_brouillon(client_id, projet, trd, date_sortie) -> dict:
    reponse = _requete(
        "POST", "sorties/",
        json={
            "client": str(client_id),
            "projet": projet,
            "trd": trd,
            "date_sortie": date_sortie.isoformat(),
        },
    )
    return reponse.json()


def lister_lignes_sortie(sortie_id) -> list:
    reponse = _requete("GET", f"sorties/{sortie_id}/lignes/")
    return reponse.json()


def valider_sortie(sortie_id) -> dict:
    reponse = _requete("POST", f"sorties/{sortie_id}/valider/")
    return reponse.json()


def lister_clients(actif=True) -> list:
    resultats = []
    chemin = "clients/"
    params = {"actif": "true"} if actif else None
    while chemin:
        reponse = _requete("GET", chemin, params=params)
        params = None  # déjà encodés dans le `next` renvoyé par la pagination DRF
        corps = reponse.json()
        resultats.extend(corps.get("results", corps if isinstance(corps, list) else []))
        suivant = corps.get("next") if isinstance(corps, dict) else None
        chemin = suivant
    return resultats
