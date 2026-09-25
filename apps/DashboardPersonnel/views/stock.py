from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.conteneurs.stock_client import (
    StockServiceIndisponible,
    stock_dormant,
    stock_previsions,
    stock_seuils_reappro,
    stock_sorties_mensuelles,
)

# Même palette que pages/accueil.html, pour rester visuellement cohérent.
PALETTE_GRAPHIQUES = ['#002046', '#505f76', '#87a0cd', '#f1bd81', '#321c00', '#ba1a1a', '#74777f']


@login_required
def DashboardStock(request):
    """Tableau de bord « Appro Stock » : vue en lecture seule sur le stock
    physique géré par oils-stock-api (seuils, prévisions, tendance, stock
    dormant). Ne bloque jamais si oils-stock-api est injoignable — affiche
    un bandeau d'indisponibilité plutôt qu'une 500 (même principe que le
    reste de l'intégration, voir apps.conteneurs.stock_client)."""
    stock_indisponible = False
    seuils, previsions, dormant = [], [], []
    sorties_mensuelles = {}

    try:
        seuils = stock_seuils_reappro()
        previsions = stock_previsions()
        sorties_mensuelles = stock_sorties_mensuelles()
        dormant = stock_dormant()
    except StockServiceIndisponible:
        stock_indisponible = True

    total_flexitank = sum(l['stock_actuel'] for l in seuils if l['type_article'] == 'FLEXITANK')
    total_heating_pad = sum(l['stock_actuel'] for l in seuils if l['type_article'] == 'HEATING_PAD')
    nb_en_alerte = sum(1 for l in seuils if l['en_alerte'])
    valeur_dormante_totale = sum(
        float(u['valeur_immobilisee']) for u in dormant if u.get('valeur_immobilisee') is not None
    )

    return render(request, 'DashboardPersonnel/pages/stock.html', {
        'stock_indisponible': stock_indisponible,
        'seuils': seuils,
        'previsions': previsions,
        'dormant': dormant,
        'total_flexitank': total_flexitank,
        'total_heating_pad': total_heating_pad,
        'nb_en_alerte': nb_en_alerte,
        'valeur_dormante_totale': valeur_dormante_totale,
        'labels_mois': sorties_mensuelles.get('mois', []),
        'flexitank_mois': sorties_mensuelles.get('flexitank', []),
        'heating_pad_mois': sorties_mensuelles.get('heating_pad', []),
        'flexitank_moyenne': sorties_mensuelles.get('flexitank_moyenne_mobile', []),
        'heating_pad_moyenne': sorties_mensuelles.get('heating_pad_moyenne_mobile', []),
        'palette': PALETTE_GRAPHIQUES,
    })
