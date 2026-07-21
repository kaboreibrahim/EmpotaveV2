#from django.http import HttpRequest, HttpResponseRedirect
from django.db import IntegrityError
from django.views.generic import ListView, CreateView,UpdateView,DeleteView
from conteneurs.models import *
from conteneurs.forms import ConteneurForm, ConteneurFormSet
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.edit import FormView
from django.forms import modelformset_factory
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.templatetags.static import static
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from django.templatetags.static import static
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import landscape, letter  # Add this line
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
import os
from django.conf import settings
from urllib.parse import quote
from datetime import datetime
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
class DossierSelectionListView(LoginRequiredMixin, ListView):
    model = Dossier
    template_name = 'pages/Dossier_selection/dossier_list.html'
    context_object_name = 'dossiers'

    def get_queryset(self):
        """
        Retourne les dossiers où l'agent de sélection connecté est associé,
        excluant ceux en 'Aconage_en_cours'.
        """
        user = self.request.user
        if user.username == 'Responsable':
            return Dossier.objects.exclude(statut='Aconage_en_cours').order_by('-Date_ajout')
        else:
            return Dossier.objects.filter(agent_selection=user).exclude(statut='Aconage_en_cours').order_by('-Date_ajout')
    
    def get_context_data(self, **kwargs):
        """
        Ajoute les contextes supplémentaires pour les dossiers en attente et en cours de sélection.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.username == 'Responsable':
            context['dossiers_en_attente'] = Dossier.objects.filter(statut='en_attente').order_by('-Date_ajout')
            context['dossiers_en_cours'] = Dossier.objects.filter(statut='selection_en_cours').order_by('-Date_ajout')
        else:
            context['dossiers_en_attente'] = Dossier.objects.filter(agent_selection=user, statut='en_attente').order_by('-Date_ajout')
            context['dossiers_en_cours'] = Dossier.objects.filter(agent_selection=user, statut='selection_en_cours').order_by('-Date_ajout')

        return context

def view_conteneurs(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    conteneurs = Conteneur.objects.filter(dossier=dossier).order_by('-Date_ajout')

    return render(request, 'pages/Dossier_selection/view_conteneur.html', {
        'conteneurs': conteneurs,
        'dossier': dossier
    })


def manage_conteneurs(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)

    ConteneurFormSet = modelformset_factory(
        Conteneur,
        form=ConteneurForm,
        extra=1,
        can_delete=True
    )

    if request.method == 'POST':
        formset = ConteneurFormSet(request.POST, request.FILES, queryset=Conteneur.objects.filter(dossier=dossier))
        if formset.is_valid():
            conteneurs = formset.save(commit=False)
            for form in formset.deleted_forms:
                if form.instance.pk:
                    form.instance.delete()
            for conteneur in conteneurs:
                conteneur.dossier = dossier
                conteneur.agent_selection = request.user
                conteneur.save()
            dossier.envoyer_pour_selection()  # Met à jour le statut du dossier si nécessaire
            return redirect('view_conteneurs', dossier_id=dossier_id)
        else:
            print(formset.errors)  # Affiche les erreurs de validation pour le débogage
    else:
        # Assurez-vous d'obtenir uniquement les conteneurs qui ne sont pas liés au dossier
        formset = ConteneurFormSet(queryset=Conteneur.objects.none())


    return render(request, 'pages/Dossier_selection/conteneur_create.html', {
        'formset': formset,
        'dossier': dossier
    })



class ConteneurUpdateView(LoginRequiredMixin, UpdateView):
    model = Conteneur
    form_class = ConteneurForm
    template_name = 'pages/Dossier_selection/modifier_conteneur.html'

    def get_success_url(self):
        # Obtenir le conteneur mis à jour
        conteneur = self.object
        dossier_id = conteneur.dossier.id
        # Rediriger vers la vue des conteneurs du dossier
        return reverse_lazy('view_conteneurs', kwargs={'dossier_id': dossier_id})

    def get_object(self, queryset=None):
        return get_object_or_404(Conteneur, id=self.kwargs['pk'])
    

class ConteneurDeleteView(LoginRequiredMixin, DeleteView):
    model = Conteneur
    template_name = 'pages/Dossier_selection/conteneur_confirm_delete.html'
    success_url = reverse_lazy('dossier_list_selction')  # Ou une URL spécifique à ta vue
    
    def get_success_url(self):
        # Obtenir le conteneur mis à jour
        conteneur = self.object
        dossier_id = conteneur.dossier.id
        # Rediriger vers la vue des conteneurs du dossier
        return reverse_lazy('view_conteneurs', kwargs={'dossier_id': dossier_id})

    def get_object(self, queryset=None):
        return get_object_or_404(Conteneur, id=self.kwargs['pk'])




def generate_dossier_pdf(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    conteneurs = dossier.conteneurs.all()

    response = HttpResponse(content_type='application/pdf')

    # Condition pour le nom du fichier
    if dossier.type_conteneur == 'ISO_20_pieds':
        filename = f"Rapport de selection des ISOTANKS Du Dossier {dossier.projet}.pdf"
    else:
        filename = f"Rapport de selection des Conteneurs Du Dossier{dossier.projet}.pdf"

    response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"'

    doc = SimpleDocTemplate(response, pagesize=landscape(letter),
                            rightMargin=0.5*inch, leftMargin=0.5*inch,
                            topMargin=0.5*inch, bottomMargin=0.5*inch)

    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']

    elements = []

    # Logo
    logo_path = os.path.join(settings.STATIC_ROOT, 'img/logo.jpg')

    elements.append(Paragraph(f'<img src="{logo_path}" width="70" height="70" />', normal_style))


    # Titre et informations du dossier
    if dossier.type_conteneur == 'ISO_20_pieds':
        title_text = f"Rapport de sélection des ISO TANKS Du Dossier: {dossier.projet}({dossier.pays})"
    else:
        title_text = f"Rapport de sélection des Conteneurs Du Dossier: {dossier.projet}({dossier.pays})"

    elements.append(Paragraph(title_text, title_style))

    elements.append(Spacer(1, 0.1*inch))

    info_text = [
        f"Client: {dossier.client}",
        f"Reference: {dossier.TRD}",
        f"BOOKING: {dossier.booking}",
        f"Site de sélection: {dossier.site}",
        f"Site d'habillage & empotage: {dossier.Site_empotage}",
        f"Nom de l'agent de sélection: Mr {dossier.agent_selection} - tel :{dossier.agent_selection.Contact}",
        f"Nom de l'agent d'habillage et empotage: ({dossier.agent_acconage}) Mr {dossier.agent_acconage.first_name} {dossier.agent_acconage.last_name} - tel :{dossier.agent_acconage.Contact}",
        f"Compagnie maritime: {dossier.compagnie_maritime}",
        f"POD: {dossier.port_de_dechargement}",
        f"POL: {dossier.port_de_chargement}",
        f"Commodité: {dossier.commodite}",
        f"Date d'ajout: {dossier.Date_ajout.strftime('%Y-%m-%d %H:%M')}",
        f"Date de sélection: {dossier.Date_selection.strftime('%Y-%m-%d %H:%M')}",
        f"Nombre de conteneurs: {conteneurs.count()}"
    ]

    for line in info_text:
        elements.append(Paragraph(line, normal_style))
        elements.append(Spacer(1, 0.05*inch))

    elements.append(Spacer(1, 0.2*inch))

    # Tableau des conteneurs
    data = [["N°", "Réf", "État", "Type"]]
    for i, conteneur in enumerate(conteneurs, start=1):
        data.append([
            i,
            conteneur.reference or "N/A",
            conteneur.etat or "N/A",
            dossier.get_type_conteneur_display()
        ])

    table = Table(data, colWidths=[1*inch, 2*inch, 2*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Utilisation de la couleur du pays
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph('<br/>', normal_style))
    elements.append(table)

    doc.build(elements)

    return response
    
def generate_dossier_mauritanie_pdf(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    conteneurs = dossier.conteneurs.all()
    response = HttpResponse(content_type='application/pdf')
    
    # Condition pour le nom du fichier
    if dossier.type_conteneur == 'ISO_20_pieds':
        filename = f"Rapport_ISOTANKS_{dossier.projet}.pdf"
    else:
        filename = f"Rapport_Conteneurs_{dossier.projet}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"'
    
    doc = SimpleDocTemplate(
        response, 
        pagesize=landscape(letter),
        rightMargin=0.75*inch, 
        leftMargin=0.75*inch,
        topMargin=0.6*inch, 
        bottomMargin=0.6*inch
    )
    
    # Styles personnalisés épurés
    styles = getSampleStyleSheet()
    
    # Style pour le titre principal
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica-Bold'
    )
    
    # Style pour les sous-titres
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=12,
        textColor=colors.HexColor('#34495e'),
        fontName='Helvetica-Bold'
    )
    
    # Style pour le texte normal épuré
    clean_normal_style = ParagraphStyle(
        'CleanNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=colors.HexColor('#2c3e50'),
        fontName='Helvetica'
    )
    
    # Style pour les informations importantes
    highlight_style = ParagraphStyle(
        'Highlight',
        parent=clean_normal_style,
        fontSize=11,
        textColor=colors.HexColor('#2980b9'),
        fontName='Helvetica-Bold'
    )
    
    elements = []
    
    # === EN-TÊTE ÉPURÉ ===
    logo_mauritanie = os.path.join(settings.STATIC_ROOT, 'img/cropped.png')
    logo_oils = os.path.join(settings.STATIC_ROOT, 'img/logo.jpg')
    
    # Header avec logos et ligne de séparation
    header_data = [[
        Paragraph(f'<img src="{logo_oils}" width="60" height="60" />', clean_normal_style),
        "",
        Paragraph(f'<img src="{logo_mauritanie}" width="50" height="50" />', clean_normal_style)
    ]]
    
    page_width = landscape(letter)[0] - 1.5*inch
    header_table = Table(header_data, colWidths=[1*inch, page_width-2*inch, 1*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (2, 0), (2, 0), 0),
    ]))
    
    elements.append(header_table)
    
    # Ligne de séparation élégante
    line_data = [["", "", ""]]
    line_table = Table(line_data, colWidths=[page_width/3, page_width/3, page_width/3])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#bdc3c7')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # === TITRE PRINCIPAL AVEC DRAPEAU ===
    # Chemin vers le drapeau de la Mauritanie
    drapeau_mauritanie = os.path.join(settings.STATIC_ROOT, 'img/mauritanie.png')
    
    if dossier.type_conteneur == 'ISO_20_pieds':
        title_text = "RAPPORT DE SÉLECTION - ISO TANKS"
        subtitle_text = f"Dossier: {dossier.projet} ({dossier.pays})"
    else:
        title_text = "RAPPORT DE SÉLECTION - CONTENEURS"
        subtitle_text = f"Dossier: {dossier.projet} ({dossier.pays})"
    
    # Création d'un tableau pour aligner le titre et le drapeau
    title_with_flag_data = [[
        Paragraph(title_text, title_style),
        Paragraph(f'<img src="{drapeau_mauritanie}" width="30" height="20" />', clean_normal_style)
    ]]
    
    # Largeur pour centrer le titre avec le drapeau
    title_table = Table(title_with_flag_data, colWidths=[6.5*inch, 1*inch])
    title_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),    # Titre centré
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),      # Drapeau à gauche de sa cellule
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), # Alignement vertical au milieu
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(title_table)
    elements.append(Paragraph(subtitle_text, subtitle_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # === INFORMATIONS PRINCIPALES EN COLONNES ===
    # Informations organisées en deux colonnes - sans balises HTML
    col1_data = [
        ["Client:", dossier.client],
        ["Reference:", dossier.TRD],
        ["Booking:", dossier.booking],
        ["Site sélection:", dossier.site],
        ["Site empotage:", dossier.Site_empotage],
        ["Commodité:", dossier.commodite],
        ["Nombre conteneurs:", str(conteneurs.count())]
    ]
    
    col2_data = [
        ["Agent sélection:", f"Mr {dossier.agent_selection.first_name} {dossier.agent_selection.last_name}"],
        ["Téléphone:", dossier.agent_selection.Contact],
        ["Agent empotage:", f"Mr {dossier.agent_acconage.first_name} {dossier.agent_acconage.last_name}"],
        ["Téléphone:", dossier.agent_acconage.Contact],
        ["Compagnie maritime:", dossier.compagnie_maritime],
        ["POL:", dossier.port_de_chargement],
        ["POD:", dossier.port_de_dechargement]
    ]
    
    # Création des tableaux d'informations
    info_table1 = Table(col1_data, colWidths=[1.8*inch, 2.5*inch])
    info_table1.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels en gras
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),       # Valeurs en normal
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),   # Labels alignés à gauche
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),   # Valeurs alignées à gauche
    ]))
    
    info_table2 = Table(col2_data, colWidths=[1.8*inch, 2.5*inch])
    info_table2.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),  # Labels en gras
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),       # Valeurs en normal
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),   # Labels alignés à gauche
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),   # Valeurs alignées à gauche
    ]))
    
    # Tableau combiné pour les deux colonnes
    combined_data = [[info_table1, info_table2]]
    combined_table = Table(combined_data, colWidths=[4.8*inch, 4.8*inch])
    combined_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(combined_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Style spécial pour les dates avec Paragraph pour gérer le HTML
    dates_paragraph_style = ParagraphStyle(
        'DatesStyle',
        parent=highlight_style,
        alignment=TA_CENTER
    )
    
    # Informations de dates en ligne séparée - avec Paragraph pour interpréter le HTML
    dates_text = f"<b>Date d'ajout:</b> {dossier.Date_ajout.strftime('%d/%m/%Y à %H:%M')} | " \
                 f"<b>Date de sélection:</b> {dossier.Date_selection.strftime('%d/%m/%Y à %H:%M')}"
    elements.append(Paragraph(dates_text, dates_paragraph_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # === TABLEAU DES CONTENEURS ÉPURÉ ===
    elements.append(Paragraph("LISTE DES CONTENEURS SÉLECTIONNÉS", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Données du tableau avec style épuré
    data = [["N°", "RÉFÉRENCE", "ÉTAT", "TYPE"]]
    for i, conteneur in enumerate(conteneurs, start=1):
        data.append([
            str(i).zfill(2),  # Numérotation avec zéros
            conteneur.reference or "—",
            conteneur.etat or "—",
            dossier.get_type_conteneur_display()
        ])
    
    # Style moderne pour le tableau
    table = Table(data, colWidths=[0.8*inch, 2.5*inch, 2*inch, 2.5*inch])
    table.setStyle(TableStyle([
        # En-tête
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Corps du tableau
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
        
        # Alternance de couleurs pour les lignes
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        
        # Bordures subtiles
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#34495e')),
        
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(table)
    
    # === PIED DE PAGE ===
    elements.append(Spacer(1, 0.4*inch))
    footer_text = f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | " \
                  f"Total: {conteneurs.count()} conteneur(s)"
    footer_style = ParagraphStyle(
        'Footer',
        parent=clean_normal_style,
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#7f8c8d')
    )
    elements.append(Paragraph(footer_text, footer_style))
    
    doc.build(elements)
    return response
    
def soumettre_dossier(request, dossier_id):
    # Récupérer le dossier
    dossier = get_object_or_404(Dossier, id=dossier_id)

    # Vérifier le statut du dossier
    if dossier.statut == 'selection_en_cours':
        # Changer le statut du dossier
        dossier.statut = 'Aconage_en_cours'
        dossier.statut_date = timezone.now()
        dossier.save()

        # Récupérer les emails des personnes concernées
        emails = []
        if dossier.agent_acconage:
            emails.append(dossier.agent_acconage.email)
        if dossier.secretaire:
            emails.append(dossier.secretaire.email)

        # Récupérer les emails de tous les personnels ayant le statut 'chef'
        chefs_emails = [chef.email for chef in Personnel.objects.filter(Personnel_type='chef')]
        emails += chefs_emails

        # Emails à mettre en copie (CC)
        cc_emails = [
            'alice.tuo@oils-of-africa.com',
            'appro.stock@oils-of-africa.com',
            'nan.jose@oils-of-africa.com',
            'logistics@oils-of-africa.com'
        ]

        # Utiliser l'email de l'utilisateur connecté comme expéditeur
        from_email = request.user.email

        # Générer le PDF
        
        if dossier.pays=="Mauritanie":
            pdf_response = generate_dossier_mauritanie_pdf(request, dossier_id)
        else:
            pdf_response = generate_dossier_pdf(request, dossier_id)
       
        pdf_content = pdf_response.content

        # Créer et envoyer l'e-mail avec le PDF en pièce jointe
        email = EmailMultiAlternatives(
            subject=f"Dossier {dossier.projet} - Prêt pour l'habillage & l'empotage",
            body=(
                f"<html>"
                f"<body>"
                f"<p>Le dossier <strong>{dossier.projet}</strong> (TRD: {dossier.TRD}) a été envoyé par "
                f"l'agent de sélection : {request.user.username}. Veuillez trouver ci-joint le PDF avec les "
                f"détails du dossier et des conteneurs.</p>"
                f"<p>Pour plus de détails, veuillez visiter le lien suivant : "
                f"<a href='https://empotage-oils-of-africa.net/login/'>Cliquez ici pour vous connecter</a>.</p>"
                f"</body>"
                f"</html>"
            ),
            from_email=from_email,
            to=emails,
            cc=cc_emails
        )
        
        # Joindre le PDF
        email.attach('dossier_details.pdf', pdf_content, 'application/pdf')

        # Indiquer que l'email est en HTML
        email.content_subtype = 'html'

        # Envoyer l'email
        try:
            email.send()
            messages.success(request, f"Dossier {dossier.projet} soumis avec succès à l'agent d'empotage.")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")
    else:
        # Si le dossier n'est pas dans le bon état, afficher une erreur
        messages.error(request, "Le dossier n'est pas dans un état valide pour être soumis.")

    # Redirection vers la liste des dossiers
    return redirect('dossier_list_selction')
    
    
    
   
def soumettre_dossier_Mauritanie(request, dossier_id):
    # Récupérer le dossier
    dossier = get_object_or_404(Dossier, id=dossier_id)

    # Vérifier le statut du dossier
    if dossier.statut == 'selection_en_cours':
        # Changer le statut du dossier
        dossier.statut = 'Aconage_en_cours'
        dossier.statut_date = timezone.now()
        dossier.save()

        # Récupérer les emails des personnes concernées
        emails = []
        if dossier.agent_acconage:
            emails.append(dossier.agent_acconage.email)
        if dossier.secretaire:
            emails.append(dossier.secretaire.email)

        # Récupérer les emails de tous les personnels ayant le statut 'chef'
        chefs_emails = [chef.email for chef in Personnel.objects.filter(Personnel_type='chef')]
        emails += chefs_emails

        # Emails à mettre en copie (CC)
        cc_emails = [
            'alice.tuo@oils-of-africa.com',
            'appro.stock@oils-of-africa.com',
            'infos@smtla-sa.com',
            'logistics@oils-of-africa.com'
        ]

        # Utiliser l'email de l'utilisateur connecté comme expéditeur
        from_email = request.user.email

        # Générer le PDF
        
   
        pdf_response = generate_dossier_mauritanie_pdf(request, dossier_id)
   
        pdf_content = pdf_response.content

        # Créer et envoyer l'e-mail avec le PDF en pièce jointe
        email = EmailMultiAlternatives(
            subject=f"Dossier {dossier.projet} - Prêt pour l'habillage & l'empotage",
            body=(
                f"<html>"
                f"<body>"
                f"<p>Le dossier <strong>{dossier.projet}</strong> (TRD: {dossier.TRD}) a été envoyé par "
                f"l'agent de sélection : {request.user.username}. Veuillez trouver ci-joint le PDF avec les "
                f"détails du dossier et des conteneurs.</p>"
                f"<p>Pour plus de détails, veuillez visiter le lien suivant : "
                f"<a href='https://empotage-oils-of-africa.net/login/'>Cliquez ici pour vous connecter</a>.</p>"
                f"</body>"
                f"</html>"
            ),
            from_email=from_email,
            to=emails,
            cc=cc_emails
        )
        
        # Joindre le PDF
        email.attach('dossier_details.pdf', pdf_content, 'application/pdf')

        # Indiquer que l'email est en HTML
        email.content_subtype = 'html'

        # Envoyer l'email
        try:
            email.send()
            messages.success(request, f"Dossier {dossier.projet} soumis avec succès à l'agent d'empotage.")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")
    else:
        # Si le dossier n'est pas dans le bon état, afficher une erreur
        messages.error(request, "Le dossier n'est pas dans un état valide pour être soumis.")

    # Redirection vers la liste des dossiers
    return redirect('dossier_list_selction')