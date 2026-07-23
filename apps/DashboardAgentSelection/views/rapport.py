from itertools import chain
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles.finders import find as find_static
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
from apps.conteneurs.services import verifier_paiement
from apps.DashboardAgentSelection.forms import PHOTOS_OBLIGATOIRES
from apps.notification.services import notifier, notifier_personnel


RAPPORT_TEMPLATE = 'DashboardAgentSelection/rapports/rapport_dossier.html'
EMAIL_TEMPLATE = 'DashboardAgentSelection/rapports/email_soumission.html'
DESTINATAIRES_SOUMISSION = ['infos@oils-of-africa.com', 'serge.debetou@oils-of-africa.com','ibrahimkabore025@gmail.com']


def _dossier_pret_pour_soumission(dossier):
    """Vérifie que chaque conteneur a bien sa référence, son état et toutes
    ses photos obligatoires, avant d'autoriser la soumission."""
    conteneurs = list(chain(dossier.isotanks.all(), dossier.flexitanks.all()))
    if not conteneurs:
        return False, "Aucun conteneur n'a été ajouté à ce dossier."

    for conteneur in conteneurs:
        if not conteneur.reference:
            return False, "Un conteneur n'a pas de référence renseignée."
        if not conteneur.etat:
            return False, f"Le conteneur {conteneur.reference} n'a pas d'état renseigné."
        manquantes = [champ for champ in PHOTOS_OBLIGATOIRES if not getattr(conteneur, champ)]
        if manquantes:
            return False, (
                f"Le conteneur {conteneur.reference} n'a pas toutes ses photos obligatoires "
                f"({len(manquantes)} manquante(s))."
            )

    return True, ""

def _conteneurs_pour_rapport(dossier):
    """Construit les lignes du tableau conteneurs, en identifiant leur nature (ISO Tank / Flexitank)."""
    conteneurs = sorted(
        chain(dossier.isotanks.all(), dossier.flexitanks.all()),
        key=lambda c: c.reference,
    )
    lignes = []
    for conteneur in conteneurs:
        nature = 'ISO Tank' if isinstance(conteneur, ISOTanks) else 'Flexitank'
        lignes.append({
            'reference': conteneur.reference,
            'etat': conteneur.get_etat_display(),
            'statut': conteneur.get_statut_display(),
            'nature': nature,
        })
    return lignes


def _nom_fichier_rapport(dossier):
    prefixe = 'ISOTANKS' if dossier.type_conteneur == 'ISO_20_pieds' else 'Conteneurs'
    return f"Rapport_selection_{prefixe}_{dossier.projet}.pdf".replace(' ', '_')


def _uri_fichier_statique(chemin_relatif):
    """Chemin file:// vers un fichier static, pour que WeasyPrint le lise directement du
    disque plutôt que via une requête HTTP vers le serveur lui-même (source de blocages/
    timeouts en prod, notamment sur des hébergements à un seul worker comme cPanel)."""
    chemin = find_static(chemin_relatif)
    return Path(chemin).as_uri() if chemin else None


def _rendre_rapport_pdf(request, dossier):
    """Rend le template HTML du rapport avec le contexte du dossier et le convertit en PDF."""
    drapeau_url = None
    if dossier.Id_Pays.drapeau:
        drapeau_url = Path(dossier.Id_Pays.drapeau.path).as_uri()

    contexte = {
        'dossier': dossier,
        'conteneurs': _conteneurs_pour_rapport(dossier),
        'nombre_conteneurs': dossier.isotanks.count() + dossier.flexitanks.count(),
        'date_generation': timezone.now(),
        'otl_logo_url': _uri_fichier_statique('img/otl.webp'),
        'logo_url': _uri_fichier_statique('img/logo.png'),
        'drapeau_url': drapeau_url,
    }
    html_string = render_to_string(RAPPORT_TEMPLATE, contexte)
    return HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()


@login_required
def generate_dossier_report(request, dossier_id):
    """Télécharge le rapport PDF de sélection d'un dossier."""
    dossier = get_object_or_404(Dossier, id=dossier_id)
    pdf_bytes = _rendre_rapport_pdf(request, dossier)
    log_action(dossier, AuditLog.ACTION_DOWNLOAD, extra={'rapport': 'selection'})

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{_nom_fichier_rapport(dossier)}"'
    return response


@login_required
def soumettre_dossier(request, dossier_id):
    """Clôture la sélection : génère le rapport et l'envoie par email à l'agent d'empotage."""
    dossier = get_object_or_404(Dossier, id=dossier_id)
    verifier_paiement(dossier)

    if dossier.statut != 'selection_en_cours':
        messages.error(request, "Le dossier n'est pas dans un état valide pour être soumis.")
        return redirect('DashboardAgentSelection:dossier-detail', dossier_id=dossier.id)

    pret, motif = _dossier_pret_pour_soumission(dossier)
    if not pret:
        messages.error(request, motif)
        return redirect('DashboardAgentSelection:dossier-detail', dossier_id=dossier.id)

    date_de_selection = parse_datetime(request.POST.get('date_de_selection', ''))
    if date_de_selection is None:
        messages.error(request, "Veuillez renseigner une date de sélection valide.")
        return redirect('DashboardAgentSelection:dossier-detail', dossier_id=dossier.id)
    if timezone.is_naive(date_de_selection):
        date_de_selection = timezone.make_aware(date_de_selection)
    dossier.date_de_selection = date_de_selection

    commentaire = request.POST.get('commentaire_soumission', '').strip()
    if not commentaire:
        messages.error(request, "Veuillez renseigner un commentaire de soumission.")
        return redirect('DashboardAgentSelection:dossier-detail', dossier_id=dossier.id)

    copie = []
    if dossier.Id_Agent_empotage and dossier.Id_Agent_empotage.user.email:
        copie.append(dossier.Id_Agent_empotage.user.email)
    if dossier.Id_Personnel and dossier.Id_Personnel.user.email:
        copie.append(dossier.Id_Personnel.user.email)

    pdf_bytes = _rendre_rapport_pdf(request, dossier)
    expediteur_nom = request.user.get_full_name() or request.user.username

    texte_body = (
        f"Le dossier {dossier.projet} (TRD : {dossier.TRD}) a été soumis par l'agent de sélection "
        f"{expediteur_nom} et est prêt pour l'habillage & l'empotage.\n\n"
        f"Client : {dossier.id_client}\n"
        f"Pays : {dossier.Id_Pays.nom}\n\n"
        + (f"Commentaire de l'agent de sélection :\n{commentaire}\n\n" if commentaire else "")
        + "Le rapport PDF détaillant le dossier et ses conteneurs est joint à cet email.\n"
        "Pour plus de détails, connectez-vous à https://empotage-oils-of-africa.net/login/"
    )

    email = EmailMultiAlternatives(
        subject=f"Dossier {dossier.projet} - Prêt pour l'habillage & l'empotage",
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
        return redirect('DashboardAgentSelection:dossier-detail', dossier_id=dossier.id)

    dossier.demarrer_empotage()
    dossier.soumettre_rapport(commentaire=commentaire)
    log_action(dossier, AuditLog.ACTION_SUBMIT, extra={'rapport': 'selection'})

    message_soumission = (
        f"Le dossier {dossier.TRD} — {dossier.projet} a été soumis par "
        f"{request.user.get_full_name() or request.user.username} et est prêt pour l'habillage & l'empotage."
    )
    notifier(
        [dossier.Id_Agent_empotage.user if dossier.Id_Agent_empotage else None],
        message_soumission,
    )
    notifier_personnel(message_soumission)
    notifier(
        dossier.id_client.user,
        f"La sélection de votre dossier {dossier.TRD} — {dossier.projet} est terminée : "
        "l'habillage & l'empotage démarrent.",
    )

    messages.success(request, f"Dossier {dossier.projet} soumis avec succès.")
    return redirect('DashboardAgentSelection:dossier-liste')
