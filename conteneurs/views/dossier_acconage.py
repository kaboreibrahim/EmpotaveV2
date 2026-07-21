#from django.http import HttpRequest, HttpResponseRedirect
from django.db import IntegrityError
from django.views.generic import ListView, CreateView,UpdateView,DeleteView
from conteneurs.models import *
from conteneurs.forms import ConteneurAcconageForm,ConteneurISO20Form
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.edit import FormView
from django.forms import modelformset_factory
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Frame, PageTemplate
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from django.http import HttpResponse
from django.template.loader import get_template
from weasyprint import HTML
from django.templatetags.static import static
import os
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from django.contrib.auth.models import User
from datetime import datetime
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from urllib.parse import quote
from django.db.models import Q

class DossierAccoangeListView(LoginRequiredMixin, ListView):
    model = Dossier
    template_name = 'pages/Dossier_Acconage/dossier_list_Acconage.html'  # Template to be created
    context_object_name = 'Dossier_list'

    def get_context_data(self, **kwargs):
        """
        Adds additional context for dossiers in acconage process and awaiting acconage.
        """
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Filter dossiers based on status for the current user
        context['dossier_acconage_en_cours'] = Dossier.objects.filter(
            agent_acconage=user,
            statut='ACCONAGE_FAIT'
        ).order_by('-Date_ajout')
        context['dossier_en_attente_acconage'] = Dossier.objects.filter(
            agent_acconage=user,
            statut='Aconage_en_cours'
        ).order_by('-Date_ajout')

        # Check if the user is 'Responsable'
        if user.username in ['Responsable', 'kabore','DG']:
            # Add dossiers for 'Responsable'
            context['dossier_acconage_en_cours'] |= Dossier.objects.filter(
                statut='ACCONAGE_FAIT'
            ).order_by('-Date_ajout')
            context['dossier_en_attente_acconage'] |= Dossier.objects.filter(
                statut='Aconage_en_cours'
            ).order_by('-Date_ajout')

        return context
 
def manage_conteneurs_acconage(request, dossier_id, conteneur_id):
    print(f"dossier_id: {dossier_id}")  # Instruction de débogage
    print(f"conteneur_id: {conteneur_id}")  # Instruction de débogage

    conteneur = get_object_or_404(Conteneur, id=conteneur_id)
    dossier = conteneur.dossier  # Récupère le dossier associé au conteneur

    
    if dossier.type_conteneur == 'ISO_20_pieds':
        # Utilise un autre formulaire pour ISO 20 Pieds
        FormClass = ConteneurISO20Form
    else:
        # Formulaire par défaut
        FormClass = ConteneurAcconageForm
   
      
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=conteneur)
        if form.is_valid():
            conteneur = form.save(commit=False)
            conteneur.agent_acconage = request.user  # Assigne l'agent d'acconage
            conteneur.save()
            conteneur.dossier.marquer_comme_acconage_fait()

            # Met à jour le statut du dossier si nécessaire
            conteneur.verifier_et_changer_statut()
            return redirect('view_conteneurs', dossier_id=dossier_id)
        else:
            print(form.errors)  # Affiche les erreurs de validation pour le débogage
    else:
        form = FormClass(instance=conteneur)

    return render(request, 'pages/Dossier_Acconage/conteneur_ajout.html', {
        'form': form,
        'conteneur': conteneur,
        'dossier_id': dossier_id
    })



def afficher_detail_conteneur(request, conteneur_id):
    # Récupérer le conteneur ou renvoyer une erreur 404 s'il n'existe pas
    conteneur = get_object_or_404(Conteneur, id=conteneur_id)
    
    # Passer les détails du conteneur au template
    return render(request, 'pages/Dossier_Acconage/detail_conteneur.html', {'conteneur': conteneur})



def modifier_conteneur(request, conteneur_id, dossier_id):
    # Récupérer l'objet conteneur en utilisant l'ID fourni, ou renvoyer une erreur 404 s'il n'existe pas
    conteneur = get_object_or_404(Conteneur, id=conteneur_id)
    dossier = conteneur.dossier  # Récupère le dossier associé au conteneur

    if request.method == 'POST':
        # Si la méthode est POST, cela signifie que le formulaire est soumis
        if dossier.type_conteneur == 'ISO_20_pieds':
            # Utilise un autre formulaire pour ISO 20 Pieds
            form = ConteneurISO20Form(request.POST, request.FILES, instance=conteneur)
        else:
            # Formulaire par défaut pour d'autres types
            form = ConteneurAcconageForm(request.POST, request.FILES, instance=conteneur)

        if form.is_valid():
            form.save()
            messages.success(request, 'Conteneur mis à jour avec succès !')
            return redirect('view_conteneurs', dossier_id=dossier_id)

    else:
        # Si la méthode est GET, afficher le formulaire avec les données du conteneur existant
        if dossier.type_conteneur == 'ISO_20_pieds':
            # Utilise un autre formulaire pour ISO 20 Pieds
            form = ConteneurISO20Form(instance=conteneur)
        else:
            # Formulaire par défaut pour d'autres types
            form = ConteneurAcconageForm(instance=conteneur)

    context = {
        'form': form,
        'conteneur': conteneur,
        'dossier_id': dossier_id
    }

    return render(request, 'pages/Dossier_Acconage/modifier_conteneur.html', context)




"""def generate_dossier_aconage_pdf(request, dossier_id):
    dossier = Dossier.objects.get(id=dossier_id)
    conteneurs = dossier.conteneurs.all()

    # URL absolue du logo
    logo_url = request.build_absolute_uri(static('img/logo.jpg'))  # Utiliser une URL absolue

    # Charger le template HTML
    template = get_template('pages/Dossier_Acconage/pdf_selection_aconage.html')
    html_content = template.render({
        'projet': dossier.projet,
        'client': dossier.client,
        'TRD': dossier.TRD,
        'compagnie_maritime': dossier.compagnie_maritime,
        'port_de_dechargement': dossier.port_de_dechargement,
        'port_de_chargement': dossier.port_de_chargement,
        'commodite': dossier.commodite,
        'conteneurs': conteneurs,
        'site': dossier.site,
        'Site_empotage': dossier.Site_empotage,
        'agent_selection': dossier.agent_selection,
        'agent_acconage': dossier.agent_acconage,
        'Date_ajout': dossier.Date_ajout,
        'Date_selection': dossier.Date_selection,
        'Date_acconage': dossier.Date_acconage,
        'Date_terminer': dossier.Date_terminer,
        'logo_url': logo_url  # Passer l'URL absolue du logo au template
    })

    # Convertir en PDF
    pdf_file = HTML(string=html_content, base_url=request.build_absolute_uri()).write_pdf()

    # Retourner le fichier PDF en réponse HTTP
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Rapport habillage & empotage {dossier.projet}.pdf"'
    return response
    
""" 


def format_date(date):
    if date:
        return date.strftime("%Y-%m-%d %A %H:%M")
    return "N/A"


def generate_dossier_aconage_pdf(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    conteneurs = dossier.conteneurs.all()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Rapport habillage & empotage {dossier.projet}.pdf"'

    # Configure page size
    page_width, page_height = landscape(letter)
    
    # Create a custom canvas class that handles page numbering and signatures
    class FooterCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []
            self._on_last_page = False
            
        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()
            
        def save(self):
            page_count = len(self._saved_page_states)
            for i, state in enumerate(self._saved_page_states):
                self.__dict__.update(state)
                # Définir un indicateur indiquant s'il s'agit de la dernière page
                self._on_last_page = (i == page_count - 1)
                self.draw_page_number(page_count)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)
        
        def draw_page_number(self, page_count):
            # Ajouter des numéros de page à toutes les pages
            self.setFont("Helvetica", 8)
            self.drawRightString(page_width - 0.5*inch, 0.25*inch, 
                               f"Page {self._pageNumber} / {page_count}")
            
            # Dessiner le pied de page avec signatures uniquement sur la dernière page
            if self._on_last_page:
                self.saveState()
                self.setFont('Helvetica', 10)
                
                # Déplacer les signatures plus bas pour qu'elles ne se superposent pas avec le contenu
                signature_y = 0.75*inch  # Position plus basse pour les signatures
                
                self.drawString(0.75*inch, signature_y, "OPERATEUR OTL&BULK LIQUID")
                self.line(0.75*inch, signature_y + 0.35*inch, 3*inch, signature_y + 0.35*inch)
                
                # Signature de droite - DIRECTEUR D'EXPLOITATION
                self.drawString(page_width - 3.5*inch, signature_y, "DIRECTEUR D'EXPLOITATION")
                self.line(page_width - 3.5*inch, signature_y + 0.35*inch, page_width - 1.25*inch, signature_y + 0.35*inch)
                
                self.restoreState()
        
        
    # Create document with standard page template
    doc = SimpleDocTemplate(response, pagesize=landscape(letter),   
                      rightMargin=0.5*inch, leftMargin=0.5*inch,
                      topMargin=0.5*inch, bottomMargin=1.25*inch)  # Marge inférieure augmentée
                      
    # Create standard page template - footer will be handled by the canvas
    frame = Frame(doc.leftMargin, doc.bottomMargin, 
                doc.width, doc.height - 0.5*inch,  # Reduced height to accommodate footer
                id='normal')
    template = PageTemplate(id='default', frames=frame)
    doc.addPageTemplates([template])

    # Styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    # Define table_style here
    table_style2 = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])
    
    # Define table_style here
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Aligne le texte dans l'en-tête
        ('SPAN', (0, 0), (-1, 0)),  # Fusionne toutes les cellules de la première ligne
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFD580')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (-1, -1), 'CENTER'),  # Aligne le texte des autres cellules
    ])

    # Contenu du document
    elements = []

   
    logo_path = os.path.join(settings.STATIC_ROOT, 'img/logo.jpg')
    elements.append(Paragraph(f'<img src="{logo_path}" width="70" height="70" />', normal_style))
    elements.append(Spacer(1, 0.2*inch))


    # Titre et informations du dossier
    if dossier.type_conteneur == 'ISO_20_pieds':  # Condition pour type ISO
        title_text = f"Rapport d'empotage des ISOTANKS Du Dossier: {dossier.projet}({dossier.pays})"
    else:
        title_text = f"Rapport d'empotage des Conteneurs Du Dossier: {dossier.projet}({dossier.pays})"

    elements.append(Paragraph(title_text, title_style))

    elements.append(Spacer(1, 0.1*inch))
    # Section 1: Informations générales du dossier
    general_info_data = [
        ["INFORMATIONS GÉNÉRALES"],
        [f"Client: {dossier.client}", f"TRD: {dossier.TRD}", f"BOOKING: {dossier.booking}"],
        [f"Commodité: {dossier.commodite}", f"Type: {'ISOTANKS' if dossier.type_conteneur == 'ISO_20_pieds' else 'Conteneurs 20 pieds'}", f"Nombre: {dossier.conteneurs.count()}"]
    ]
    general_info = Table(general_info_data, colWidths=[doc.width/3.0]*3)
    general_info.setStyle(table_style)
    elements.append(general_info)
    elements.append(Spacer(1, 0.1*inch))
    
    # Section 2: Sites et agents
    sites_data = [
        ["SITES ET AGENTS"],
        [f"Site de sélection: {dossier.site}", f"Site d'habillage & empotage: {dossier.Site_empotage}"],
        [f"Agent de sélection: Mr {dossier.agent_selection} - tel: {dossier.agent_selection.Contact}"],
        [f"Agent d'habillage et empotage:  Mr {dossier.agent_acconage.first_name} {dossier.agent_acconage.last_name} - tel: {dossier.agent_acconage.Contact}"]
    ]
    sites_table = Table(sites_data, colWidths=[doc.width/2.0, doc.width/2.0])
    sites_table.setStyle(table_style)
    elements.append(sites_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Section 3: Informations de transport
    transport_data = [
        ["INFORMATIONS DE TRANSPORT"],
        [f"Compagnie maritime: {dossier.compagnie_maritime}", f"POL: {dossier.port_de_chargement}"],
        [f"POD: {dossier.port_de_dechargement}", f"Pays: {dossier.pays}"]
    ]
    transport_table = Table(transport_data, colWidths=[doc.width/2.0, doc.width/2.0])
    transport_table.setStyle(table_style)
    elements.append(transport_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Section 4: Dates importantes
    dates_data = [
        ["PLANNING ET DATES"],
        [f"Date d'ajout: {dossier.Date_ajout.strftime('%Y-%m-%d %H:%M')}", 
         f"Date de sélection: {dossier.Date_selection.strftime('%Y-%m-%d %H:%M') if dossier.Date_selection else 'Non défini'}"],
        [f"Date d'empotage: {dossier.Date_acconage.strftime('%Y-%m-%d %H:%M') if dossier.Date_acconage else 'Non défini'}", 
         f"Date de fin: {dossier.Date_terminer.strftime('%Y-%m-%d %H:%M') if dossier.Date_terminer else 'Non défini'}"]
    ]
    dates_table = Table(dates_data, colWidths=[doc.width/2.0, doc.width/2.0])
    dates_table.setStyle(table_style)
    elements.append(dates_table)

    # Initialize info_text list
    info_text = []
    
    # Add a conditional check for the type of container
    #if dossier.type_conteneur == 'ISO_20_pieds':
     #   info_text.append(f"Nombre d'iso tanks: {conteneurs.count()}")
    #else:
        #info_text.append(f"Nombre de conteneurs: {conteneurs.count()}")

    for line in info_text:
        elements.append(Paragraph(line, normal_style))
        elements.append(Spacer(1, 0.05*inch))

    elements.append(Spacer(1, 0.2*inch))

    # Tableau des conteneurs en fonction du type de conteneur
    if dossier.type_conteneur == 'ISO_20_pieds':
        # Tableau spécifique pour le type 'iso_tank_20'
        data = [["N°", "Réf", "État", "P.net", "plomb 1", "N°plomb 2", "N°plomb 3","Tem °C"]]
        for i, conteneur in enumerate(conteneurs, start=1):
            data.append([
                i,
                conteneur.reference or "N/A",
                conteneur.etat or "N/A",
                f"{conteneur.poids_net or 'N/A'} KG",
                conteneur.numero_plomb or "N/A",    # Nouvelle colonne pour numero_plomb 1
                conteneur.numero_plomb2 or "N/A",  # Nouvelle colonne pour numero_plomb2
                conteneur.numero_plomb3 or "N/A",   # Nouvelle colonne pour numero_plomb3
                #conteneur.numero_plomb4 or "N/A",  # Nouvelle colonne pour plomb oils 1
                #conteneur.numero_plomb5 or "N/A",# Nouvelle colonne pour plomb oils 2
                conteneur.temperature or "N/A"
            ])
    else:
        # Tableau par défaut pour d'autres types de conteneurs
        data = [["N°", "Réf", "État", "P.brute", "P.équipement", "P.net", "heating pad", "flexitank", "plomb ","Temp °C"]]
        for i, conteneur in enumerate(conteneurs, start=1):
            data.append([
                i,
                conteneur.reference or "N/A",
                conteneur.etat or "N/A",
                f"{conteneur.poids_brute or 'N/A'} KG",
                f"{conteneur.poids_equipements or 'N/A'} KG",
                f"{conteneur.poids_net or 'N/A'} KG",
                conteneur.numero_heating_pad or "N/A",
                conteneur.numero_flexitank or "N/A",
                conteneur.numero_plomb or "N/A",
                #conteneur.numero_plomb4 or "N/A",  # plomd oils
                conteneur.temperature or "N/A"   
            ])

    table = Table(data)
    table.setStyle(table_style2)  # Use the same table_style here

    elements.append(table)

    # Générer le PDF avec notre canvas personnalisé
    doc.build(elements, canvasmaker=FooterCanvas)

    return response

def generate_dossier_aconage_mauritanie_pdf(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    conteneurs = dossier.conteneurs.all()

    response = HttpResponse(content_type='application/pdf')
    
    # Nom de fichier simplifié
    if dossier.type_conteneur == 'ISO_20_pieds':
        filename = f"Rapport_Empotage_ISOTANKS_{dossier.projet}.pdf"
    else:
        filename = f"Rapport_Empotage_Conteneurs_{dossier.projet}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{quote(filename)}"'

    # Configure page size
    page_width, page_height = landscape(letter)
    
    # Create a custom canvas class that handles page numbering and signatures
    class FooterCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []
            self._on_last_page = False
            
        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()
            
        def save(self):
            page_count = len(self._saved_page_states)
            for i, state in enumerate(self._saved_page_states):
                self.__dict__.update(state)
                self._on_last_page = (i == page_count - 1)
                self.draw_page_number(page_count)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)
        
        def draw_page_number(self, page_count):
            # Numéros de page avec style épuré
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor('#7f8c8d'))
            self.drawRightString(page_width - 0.5*inch, 0.25*inch, 
                               f"Page {self._pageNumber} / {page_count}")
            
            # Signatures épurées sur la dernière page
            if self._on_last_page:
                self.saveState()
                self.setFont('Helvetica-Bold', 10)
                self.setFillColor(colors.HexColor('#2c3e50'))
                
                signature_y = 0.9*inch
                
                # Signature gauche
                self.drawString(0.75*inch, signature_y, "OPÉRATEUR SMTLA.SA")
                self.setStrokeColor(colors.HexColor('#34495e'))
                self.setLineWidth(1.5)
                self.line(0.75*inch, signature_y + 0.35*inch, 3*inch, signature_y + 0.35*inch)
                
                # Signature droite
                self.drawString(page_width - 3.5*inch, signature_y, "DIRECTEUR D'EXPLOITATION")
                self.line(page_width - 3.5*inch, signature_y + 0.35*inch, page_width - 1.25*inch, signature_y + 0.35*inch)
                
                self.restoreState()
        
    # Create document with standard page template
    doc = SimpleDocTemplate(
        response, 
        pagesize=landscape(letter),   
        rightMargin=0.75*inch, 
        leftMargin=0.75*inch,
        topMargin=0.6*inch, 
        bottomMargin=1.4*inch
    )
                      
    frame = Frame(doc.leftMargin, doc.bottomMargin, 
                doc.width, doc.height - 0.5*inch,
                id='normal')
    template = PageTemplate(id='default', frames=frame)
    doc.addPageTemplates([template])

    # Styles épurés personnalisés
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
    
    # Style pour les sous-titres de sections
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=8,
        spaceBefore=8,
        alignment=TA_CENTER,
        textColor=colors.white,
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
    
    # Style pour les sous-titres
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#34495e'),
        fontName='Helvetica-Bold'
    )
    
    # Styles de tableaux épurés
    section_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('SPAN', (0, 0), (-1, 0)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#34495e')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 1), (-1, -1), 12),
        ('RIGHTPADDING', (0, 1), (-1, -1), 12),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ])
    
    # Style pour le tableau principal des conteneurs
    main_table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#2c3e50')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#34495e')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ])

    # Contenu du document
    elements = []

    # === EN-TÊTE ÉPURÉ ===
    logo_oils = os.path.join(settings.STATIC_ROOT, 'img/logo.jpg')
    logo_mauritanie = os.path.join(settings.STATIC_ROOT, 'img/cropped.png')
    
    # Header avec logos et ligne de séparation
    header_data = [[
        Paragraph(f'<img src="{logo_oils}" width="60" height="60" />', clean_normal_style),
        "",
        Paragraph(f'<img src="{logo_mauritanie}" width="50" height="50" />', clean_normal_style)
    ]]
    
    page_width_available = landscape(letter)[0] - 1.5*inch
    header_table = Table(header_data, colWidths=[1*inch, page_width_available-2*inch, 1*inch])
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
    line_table = Table(line_data, colWidths=[page_width_available/3, page_width_available/3, page_width_available/3])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#bdc3c7')),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.3*inch))

    # === TITRE PRINCIPAL AVEC DRAPEAU ===
    drapeau_mauritanie = os.path.join(settings.STATIC_ROOT, 'img/mauritanie.png')
    
    if dossier.type_conteneur == 'ISO_20_pieds':
        title_text = "RAPPORT D'EMPOTAGE - ISO TANKS"
        subtitle_text = f"Dossier: {dossier.projet} ({dossier.pays})"
    else:
        title_text = "RAPPORT D'EMPOTAGE - CONTENEURS"
        subtitle_text = f"Dossier: {dossier.projet} ({dossier.pays})"
    
    # Création d'un tableau pour aligner le titre et le drapeau
    title_with_flag_data = [[
        Paragraph(title_text, title_style),
        Paragraph(f'<img src="{drapeau_mauritanie}" width="30" height="20" />', clean_normal_style)
    ]]
    
    title_table = Table(title_with_flag_data, colWidths=[6.5*inch, 1*inch])
    title_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(title_table)
    elements.append(Paragraph(subtitle_text, subtitle_style))
    elements.append(Spacer(1, 0.2*inch))

    # === SECTIONS D'INFORMATIONS ÉPURÉES ===
    
    # Section 1: Informations générales
    general_info_data = [
        ["INFORMATIONS GÉNÉRALES"],
        [f"Client: {dossier.client}", f"Référence: {dossier.TRD}", f"Booking: {dossier.booking}"],
        [f"Commodité: {dossier.commodite}", 
         f"Type: {'ISO TANKS' if dossier.type_conteneur == 'ISO_20_pieds' else 'Conteneurs 20 pieds'}", 
         f"Nombre: {dossier.conteneurs.count()}"]
    ]
    general_info = Table(general_info_data, colWidths=[doc.width/3.0]*3)
    general_info.setStyle(section_table_style)
    elements.append(general_info)
    elements.append(Spacer(1, 0.15*inch))
    
    # Section 2: Sites et agents
    sites_data = [
        ["SITES ET AGENTS"],
        [f"Site de sélection: {dossier.site}", f"Site d'empotage: {dossier.Site_empotage}"],
        [f"Agent de sélection: Mr {dossier.agent_selection.first_name} {dossier.agent_selection.last_name}"],
        [f"Téléphone: {dossier.agent_selection.Contact}", ""],
        [f"Agent d'empotage: Mr {dossier.agent_acconage.first_name} {dossier.agent_acconage.last_name}"],
        [f"Téléphone: {dossier.agent_acconage.Contact}", ""]
    ]
    sites_table = Table(sites_data, colWidths=[doc.width/2.0, doc.width/2.0])
    sites_table.setStyle(section_table_style)
    elements.append(sites_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Section 3: Informations de transport
    transport_data = [
        ["INFORMATIONS DE TRANSPORT"],
        [f"Compagnie maritime: {dossier.compagnie_maritime}", f"Pays: {dossier.pays}"],
        [f"Port de chargement (POL): {dossier.port_de_chargement}", f"Port de déchargement (POD): {dossier.port_de_dechargement}"]
    ]
    transport_table = Table(transport_data, colWidths=[doc.width/2.0, doc.width/2.0])
    transport_table.setStyle(section_table_style)
    elements.append(transport_table)
    elements.append(Spacer(1, 0.15*inch))
    
    # Section 4: Planning et dates
    dates_data = [
        ["PLANNING ET DATES"],
        [f"Date d'ajout: {dossier.Date_ajout.strftime('%d/%m/%Y à %H:%M')}", 
         f"Date de sélection: {dossier.Date_selection.strftime('%d/%m/%Y à %H:%M') if dossier.Date_selection else 'Non définie'}"],
        [f"Date d'empotage: {dossier.Date_acconage.strftime('%d/%m/%Y à %H:%M') if dossier.Date_acconage else 'Non définie'}", 
         f"Date de fin: {dossier.Date_terminer.strftime('%d/%m/%Y à %H:%M') if dossier.Date_terminer else 'Non définie'}"]
    ]
    dates_table = Table(dates_data, colWidths=[doc.width/2.0, doc.width/2.0])
    dates_table.setStyle(section_table_style)
    elements.append(dates_table)
    elements.append(Spacer(1, 0.3*inch))

    # === TABLEAU PRINCIPAL DES CONTENEURS ===
    elements.append(Paragraph("DÉTAIL DES CONTENEURS EMPOTÉS", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))

    # Tableau adapté selon le type de conteneur
    if dossier.type_conteneur == 'ISO_20_pieds':
        data = [["N°", "RÉFÉRENCE", "ÉTAT", "POIDS NET", "PLOMB 1", "PLOMB 2", "PLOMB 3", "TEMP. °C"]]
        col_widths = [0.6*inch, 1.5*inch, 1*inch, 1.2*inch, 1*inch, 1*inch, 1*inch, 1*inch]
        for i, conteneur in enumerate(conteneurs, start=1):
            data.append([
                str(i).zfill(2),
                conteneur.reference or "—",
                conteneur.etat or "—",
                f"{conteneur.poids_net or '—'} KG" if conteneur.poids_net else "—",
                conteneur.numero_plomb or "—",
                conteneur.numero_plomb2 or "—",
                conteneur.numero_plomb3 or "—",
                f"{conteneur.temperature}°C" if conteneur.temperature else "—"
            ])
    else:
        data = [["N°", "RÉFÉRENCE", "ÉTAT", "P.BRUTE", "P.ÉQUIP.", "P.NET", "HEATING PAD", "FLEXITANK", "PLOMB", "TEMP.°C"]]
        col_widths = [0.5*inch, 1.2*inch, 0.8*inch, 1*inch, 1*inch, 1*inch, 1*inch, 1*inch, 0.8*inch, 0.8*inch]
        for i, conteneur in enumerate(conteneurs, start=1):
            data.append([
                str(i).zfill(2),
                conteneur.reference or "—",
                conteneur.etat or "—",
                f"{conteneur.poids_brute} KG" if conteneur.poids_brute else "—",
                f"{conteneur.poids_equipements} KG" if conteneur.poids_equipements else "—",
                f"{conteneur.poids_net} KG" if conteneur.poids_net else "—",
                conteneur.numero_heating_pad or "—",
                conteneur.numero_flexitank or "—",
                conteneur.numero_plomb or "—",
                f"{conteneur.temperature}°C" if conteneur.temperature else "—"
            ])

    table = Table(data, colWidths=col_widths)
    table.setStyle(main_table_style)
    elements.append(table)
    
    # Footer avec informations de génération
    elements.append(Spacer(1, 0.3*inch))
    footer_text = f"Document généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} | " \
                  f"Total: {conteneurs.count()} conteneur(s) empoté(s)"
    footer_style = ParagraphStyle(
        'Footer',
        parent=clean_normal_style,
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#7f8c8d')
    )
    elements.append(Paragraph(footer_text, footer_style))

    # Générer le PDF avec notre canvas personnalisé
    doc.build(elements, canvasmaker=FooterCanvas)

    return response

def soumettre_dossier_acconage(request, dossier_id):
    # Récupérer le dossier
    dossier = get_object_or_404(Dossier, id=dossier_id)

    # Vérifier si tous les conteneurs du dossier ont le statut 'acconé'
    conteneurs = Conteneur.objects.filter(dossier=dossier)

    if not conteneurs.exists():
        messages.error(request, "Aucun conteneur n'est associé à ce dossier.")
        return redirect('dossier_list_Accoange')

    # Vérifier que tous les conteneurs ont le statut 'acconé'
    conteneurs_non_accones = conteneurs.exclude(statut='aconer')
    if conteneurs_non_accones.exists():
        messages.error(request, "Tous les conteneurs doivent avoir le statut 'habillage et empotage' avant de soumettre le dossier.")
        return redirect('view_conteneurs', dossier_id=dossier_id)

    # Si le dossier a déjà été soumis (statut 'ACCONAGE_FAIT'), le soumettre
    if dossier.statut == 'ACCONAGE_FAIT':
        # Changer le statut du dossier
        dossier.terminer_dossier()
        dossier.Date_terminer = timezone.now()
        dossier.save()

        # Récupérer les emails des personnes concernées
        emails = []
        if dossier.agent_acconage:
            emails.append(dossier.agent_acconage.email)
        if dossier.secretaire:
            emails.append(dossier.secretaire.email)

        # Récupérer les emails de tous les chefs
        chefs = Personnel.objects.filter(Personnel_type='chef')
        chefs_emails = [chef.email for chef in chefs]

        # Ajouter les emails des chefs à la liste des destinataires
        emails += chefs_emails

        # Emails à mettre en copie (CC)
        cc_emails = [
            'alice.tuo@oils-of-africa.ci',
            'appro.stock@oils-of-africa.ci',
            'ops@oils-of-africa.ci',
            'operations@otlog.ci',
            'infos@smtla-sa.com',
            'logistics@oils-of-africa.com'
        ]

        # Utiliser l'email de l'agent d'acconage connecté comme expéditeur
        from_email = request.user.email

        # Générer le PDF
        pdf_response = generate_dossier_aconage_pdf(request, dossier_id)
        pdf_content = pdf_response.content

        # Créer et envoyer l'e-mail avec le PDF en pièce jointe
        email = EmailMultiAlternatives(
            subject=f"Dossier {dossier.projet} - Habillage & empotage Terminé",
            body=(
                f"<html>"
                f"<body>"
                f"<p>Le dossier <strong>{dossier.projet}</strong> (TRD: {dossier.TRD}) a terminé Habillage & empotage, "
                f"transmis par l'agent de sélection {request.user.username}.</p>"
                f"<p>Veuillez trouver ci-joint le PDF avec les détails du dossier et des conteneurs.</p>"
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
            messages.success(request, f"Dossier {dossier.projet} soumis avec succès.")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")
    else:
        # Si le dossier n'est pas dans le bon état, afficher une erreur
        messages.error(request, "Le dossier n'est pas dans un état valide pour être soumis.")

    # Redirection vers la liste des dossiers
    return redirect('dossier_list_Accoange')

 
 
def soumettre_dossier_acconage_mauritanie(request, dossier_id):
    # Récupérer le dossier
    dossier = get_object_or_404(Dossier, id=dossier_id)

    # Vérifier si tous les conteneurs du dossier ont le statut 'acconé'
    conteneurs = Conteneur.objects.filter(dossier=dossier)

    if not conteneurs.exists():
        messages.error(request, "Aucun conteneur n'est associé à ce dossier.")
        return redirect('dossier_list_Accoange')

    # Vérifier que tous les conteneurs ont le statut 'acconé'
    conteneurs_non_accones = conteneurs.exclude(statut='aconer')
    if conteneurs_non_accones.exists():
        messages.error(request, "Tous les conteneurs doivent avoir le statut 'habillage et empotage' avant de soumettre le dossier.")
        return redirect('view_conteneurs', dossier_id=dossier_id)

    # Si le dossier a déjà été soumis (statut 'ACCONAGE_FAIT'), le soumettre
    if dossier.statut == 'ACCONAGE_FAIT':
        # Changer le statut du dossier
        dossier.terminer_dossier()
        dossier.Date_terminer = timezone.now()
        dossier.save()

        # Récupérer les emails des personnes concernées
        emails = []
        if dossier.agent_acconage:
            emails.append(dossier.agent_acconage.email)
        if dossier.secretaire:
            emails.append(dossier.secretaire.email)

        # Récupérer les emails de tous les chefs
        chefs = Personnel.objects.filter(Personnel_type='chef')
        chefs_emails = [chef.email for chef in chefs]

        # Ajouter les emails des chefs à la liste des destinataires
        emails += chefs_emails

        # Emails à mettre en copie (CC)
        cc_emails = [
            'alice.tuo@oils-of-africa.ci',
            'appro.stock@oils-of-africa.ci',
            'ops@oils-of-africa.ci',
            'operations@otlog.ci',
            'infos@smtla-sa.com',
            'logistics@oils-of-africa.com'
        ]

        # Utiliser l'email de l'agent d'acconage connecté comme expéditeur
        from_email = request.user.email

        # Générer le PDF
        pdf_response = generate_dossier_aconage_mauritanie_pdf(request, dossier_id)
        pdf_content = pdf_response.content

        # Créer et envoyer l'e-mail avec le PDF en pièce jointe
        email = EmailMultiAlternatives(
            subject=f"Dossier {dossier.projet} - Habillage & empotage Terminé",
            body=(
                f"<html>"
                f"<body>"
                f"<p>Le dossier <strong>{dossier.projet}</strong> (TRD: {dossier.TRD}) a terminé Habillage & empotage, "
                f"transmis par l'agent de sélection {request.user.username}.</p>"
                f"<p>Veuillez trouver ci-joint le PDF avec les détails du dossier et des conteneurs.</p>"
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
            messages.success(request, f"Dossier {dossier.projet} soumis avec succès.")
        except Exception as e:
            messages.error(request, f"Erreur lors de l'envoi de l'email : {str(e)}")
    else:
        # Si le dossier n'est pas dans le bon état, afficher une erreur
        messages.error(request, "Le dossier n'est pas dans un état valide pour être soumis.")

    # Redirection vers la liste des dossiers
    return redirect('dossier_list_Accoange')
    
def retrograder_dossier (request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
        
    dossier.retrograder_en_selection()
    messages.success(request, f"Le dossier {dossier.projet} a été rétrogradé avec succès.")
    return redirect('dossier_list_Accoange')
