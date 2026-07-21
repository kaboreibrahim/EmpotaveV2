from decimal import Decimal
from itertools import chain

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from weasyprint import HTML
from apps.audit.models import AuditLog
from apps.audit.services import log_action
from apps.conteneurs.models import Dossier, ISOTanks
from apps.notification.services import notifier, notifier_personnel


RAPPORT_TEMPLATE = 'DashboardAgentEmpotage/rapports/rapport_dossier.html'
EMAIL_TEMPLATE = 'DashboardAgentEmpotage/rapports/email_soumission.html'
DESTINATAIRES_SOUMISSION = ['infos@oils-of-africa.com', 'serge.debetou@oils-of-africa.com', 'ibrahimkabore025@gmail.com']

# Photos et plombs communs aux deux natures de conteneur, obligatoires avant
# soumission. Les plombs Oils (texte + photo) sont volontairement exclus :
# pas vraiment obligatoires en pratique.
CHAMPS_OBLIGATOIRES_COMMUNS = ['poids_net', 'photo_debut', 'photo_pendant', 'photo_fin']

CHAMPS_OBLIGATOIRES_ISO = CHAMPS_OBLIGATOIRES_COMMUNS + [
    'plombAmateur1', 'photoPlombAmateur1',
    'plombAmateur2', 'photoPlombAmateur2',
    'plombAmateur3', 'photoPlombAmateur3',
]

CHAMPS_OBLIGATOIRES_FLEXITANK = CHAMPS_OBLIGATOIRES_COMMUNS + [
    'numeroFlextank', 'photoFlextank',
    'Numeroheatingpad', 'Photoheatingpad',
    'plombs_amateur', 'plombs_amateur_photo',
]

LIBELLES_CHAMPS = {
    'poids_net': 'poids net',
    'photo_debut': 'photo début',
    'photo_pendant': 'photo pendant',
    'photo_fin': 'photo fin',
    'plombAmateur1': 'plomb amateur 1', 'photoPlombAmateur1': 'photo plomb amateur 1',
    'plombAmateur2': 'plomb amateur 2', 'photoPlombAmateur2': 'photo plomb amateur 2',
    'plombAmateur3': 'plomb amateur 3', 'photoPlombAmateur3': 'photo plomb amateur 3',
    'numeroFlextank': 'n° Flexitank', 'photoFlextank': 'photo Flexitank',
    'Numeroheatingpad': 'n° heating pad', 'Photoheatingpad': 'photo heating pad',
    'plombs_amateur': 'plombs amateur', 'plombs_amateur_photo': 'photo plombs amateur',
}


def _dossier_pret_pour_soumission(dossier):
    """Vérifie que chaque conteneur a bien toutes ses photos et tous ses plombs
    obligatoires renseignés (les plombs Oils, pas vraiment obligatoires, sont
    exclus du contrôle) avant d'autoriser la clôture du dossier."""
    conteneurs = list(chain(dossier.isotanks.all(), dossier.flexitanks.all()))
    if not conteneurs:
        return False, "Aucun conteneur n'a été ajouté à ce dossier."

    for conteneur in conteneurs:
        champs_requis = CHAMPS_OBLIGATOIRES_ISO if isinstance(conteneur, ISOTanks) else CHAMPS_OBLIGATOIRES_FLEXITANK
        manquants = [champ for champ in champs_requis if not getattr(conteneur, champ)]
        if manquants:
            libelles = ', '.join(LIBELLES_CHAMPS.get(champ, champ) for champ in manquants)
            return False, f"Le conteneur {conteneur.reference} n'est pas complet ({libelles})."

    return True, ""


def _conteneurs_pour_rapport(dossier):
    """Construit les lignes du tableau conteneurs.

    ISO Tanks et Flexitanks n'ont pas les mêmes champs propres (plombs
    amateurs numérotés 1 à 3 + plombs Oils 1/2 pour l'un, n° Flexitank /
    heating pad + poids brut/équipements pour l'autre) : chaque ligne ne
    porte donc que les champs pertinents pour sa nature, plutôt qu'un jeu de
    colonnes générique commun aux deux.
    """
    conteneurs = sorted(
        chain(dossier.isotanks.all(), dossier.flexitanks.all()),
        key=lambda c: c.reference,
    )
    lignes = []
    for conteneur in conteneurs:
        est_iso = isinstance(conteneur, ISOTanks)
        base = {
            'statut': conteneur.get_statut_display(),
            'reference': conteneur.reference,
            'temperature': conteneur.Temerature,
            'poids_net': conteneur.poids_net,
        }
        if est_iso:
            base.update({
                'plomb_amateur1': conteneur.plombAmateur1,
                'plomb_amateur2': conteneur.plombAmateur2,
                'plomb_amateur3': conteneur.plombAmateur3,
                'plombs_oils1': conteneur.Plombs_oils1,
                'plombs_oils2': conteneur.Plombs_oils2,
            })
        else:
            poids_equipements = conteneur.poids_equipements or Decimal('0.00')
            base.update({
                # Poids brute = poids net + poids équipements, calculé plutôt que lu depuis
                # le champ stocké, pour rester toujours cohérent avec la saisie d'empotage.
                'poids_brute': (conteneur.poids_net or Decimal('0.00')) + poids_equipements,
                'poids_equipements': conteneur.poids_equipements,
                'numero_flexitank': conteneur.numeroFlextank,
                'numero_heating_pad': conteneur.Numeroheatingpad,
                'plombs_amateur': conteneur.plombs_amateur,
                'plombs_oils': conteneur.Plombs_oils,
            })
        lignes.append(base)
    return lignes


def _nom_fichier_rapport(dossier):
    prefixe = 'ISOTANKS' if dossier.type_conteneur == 'ISO_20_pieds' else 'Conteneurs'
    return f"Rapport_empotage_{prefixe}_{dossier.projet}.pdf".replace(' ', '_')


def _rendre_rapport_pdf(request, dossier):
    """Rend le template HTML du rapport avec le contexte du dossier et le convertit en PDF."""
    drapeau_url = None
    if dossier.Id_Pays.drapeau:
        drapeau_url = request.build_absolute_uri(dossier.Id_Pays.drapeau.url)

    contexte = {
        'dossier': dossier,
        'conteneurs': _conteneurs_pour_rapport(dossier),
        'nombre_conteneurs': dossier.isotanks.count() + dossier.flexitanks.count(),
        'date_generation': timezone.now(),
        'logo_url': request.build_absolute_uri(static('img/logo.jpg')),
        'otl_logo_url': request.build_absolute_uri(static('img/otl.webp')),
        'drapeau_url': drapeau_url,
    }
    html_string = render_to_string(RAPPORT_TEMPLATE, contexte)
    return HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()


@login_required
def generate_dossier_report(request, dossier_id):
    """Télécharge le rapport PDF d'empotage d'un dossier."""
    dossier = get_object_or_404(Dossier, id=dossier_id)
    pdf_bytes = _rendre_rapport_pdf(request, dossier)
    log_action(dossier, AuditLog.ACTION_DOWNLOAD, extra={'rapport': 'empotage'})

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{_nom_fichier_rapport(dossier)}"'
    return response


@login_required
def soumettre_dossier(request, dossier_id):
    """Clôture l'empotage : génère le rapport, termine le dossier et notifie l'équipe."""
    dossier = get_object_or_404(Dossier, id=dossier_id)

    if dossier.statut != 'empotage_en_cours':
        messages.error(request, "Le dossier n'est pas dans un état valide pour être soumis.")
        return redirect('DashboardAgentEmpotage:dossier-detail', dossier_id=dossier.id)

    pret, motif = _dossier_pret_pour_soumission(dossier)
    if not pret:
        messages.error(request, motif)
        return redirect('DashboardAgentEmpotage:dossier-detail', dossier_id=dossier.id)

    date_de_empotage = parse_datetime(request.POST.get('date_de_empotage', ''))
    if date_de_empotage is None:
        messages.error(request, "Veuillez renseigner une date d'empotage valide.")
        return redirect('DashboardAgentEmpotage:dossier-detail', dossier_id=dossier.id)
    if timezone.is_naive(date_de_empotage):
        date_de_empotage = timezone.make_aware(date_de_empotage)
    dossier.date_de_empotage = date_de_empotage

    copie = []
    if dossier.Id_Agent_selection and dossier.Id_Agent_selection.user.email:
        copie.append(dossier.Id_Agent_selection.user.email)
    if dossier.Id_Personnel and dossier.Id_Personnel.user.email:
        copie.append(dossier.Id_Personnel.user.email)

    pdf_bytes = _rendre_rapport_pdf(request, dossier)
    expediteur_nom = request.user.get_full_name() or request.user.username

    texte_body = (
        f"Le dossier {dossier.projet} (TRD : {dossier.TRD}) a été empoté et clôturé par l'agent "
        f"d'empotage {expediteur_nom}.\n\n"
        f"Client : {dossier.id_client}\n"
        f"Pays : {dossier.Id_Pays.nom}\n\n"
        "Le rapport PDF détaillant le dossier et ses conteneurs est joint à cet email.\n"
        "Pour plus de détails, connectez-vous à https://empotage-oils-of-africa.net/login/"
    )

    email = EmailMultiAlternatives(
        subject=f"Dossier {dossier.projet} - Empotage terminé",
        body=texte_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=DESTINATAIRES_SOUMISSION,
        cc=copie,
        reply_to=[request.user.email] if request.user.email else None,
    )
    email.attach_alternative(
        render_to_string(EMAIL_TEMPLATE, {
            'dossier': dossier,
            'expediteur': request.user,
            'logo_url': request.build_absolute_uri(static('img/logo.png')),
        }),
        'text/html',
    )
    email.attach(_nom_fichier_rapport(dossier), pdf_bytes, 'application/pdf')

    try:
        email.send()
    except Exception as exc:
        messages.error(request, f"Erreur lors de l'envoi de l'email : {exc}")
        return redirect('DashboardAgentEmpotage:dossier-detail', dossier_id=dossier.id)

    dossier.terminer()
    log_action(dossier, AuditLog.ACTION_SUBMIT, extra={'rapport': 'empotage'})

    message_cloture = (
        f"Le dossier {dossier.TRD} — {dossier.projet} a été empoté et clôturé par "
        f"{request.user.get_full_name() or request.user.username}."
    )
    notifier(
        [dossier.Id_Agent_selection.user if dossier.Id_Agent_selection else None],
        message_cloture,
    )
    notifier_personnel(message_cloture)
    notifier(
        dossier.id_client.user,
        f"Votre dossier {dossier.TRD} — {dossier.projet} est terminé : "
        "l'habillage & l'empotage sont achevés. Le rapport est disponible.",
    )

    messages.success(request, f"Dossier {dossier.projet} clôturé avec succès.")
    return redirect('DashboardAgentEmpotage:dossier-liste')
