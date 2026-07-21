# import random
# from django.core.exceptions import ValidationError

# from django.core.mail import send_mail
# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Submit
# from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
# from django.forms import modelformset_factory
# from django import forms
# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML, Fieldset
# from .models import *
# from django.forms import  DateTimeInput

# #formulaire de connexion
# class LoginForm(AuthenticationForm): 
    
#     username = forms.CharField(
#         max_length=254,
#         widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom d\'utilisateur ou e-mail', 'id': 'username'})
#     )
#     password = forms.CharField(
#         label="Mot de passe",
#         widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe', 'id': 'password'})
#     )

# #formualaire de verification
# class VerificationForm(forms.Form):
 
#     code = forms.CharField(max_length=6)
    


# #formualire de creation de compte 
# class  PersonnelForm(UserCreationForm):
#     class Meta:
#         model = Personnel
#         fields = ('first_name','last_name','photos', 'email','Contact','username','Personnel_type','password1', 'password2')
        
#     def clean_email(self):
#         email = self.cleaned_data.get('email')
#         if Personnel.objects.filter(email=email).exists():
#             raise ValidationError("Un compte avec cet e-mail existe déjà.")
#         return email
    
#     def save(self, commit=True):
#         user = super().save(commit=False)
#         user.is_active = False  # Désactiver le compte jusqu'à la vérification
#         if commit:
#             user.save()
#             code = str(random.randint(100000, 999999))
#             VerificationCode.objects.create(user=user, code=code)
#             send_mail(
#                 'Votre code de vérification',
#                 f'Votre code de vérification est {code}',
#                 'kaboremessi@gmail.com',
#                 [user.email],
#                 fail_silently=False,
#             )
#         return user
    
# # form de site 
# class SiteForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(SiteForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
    
#     class Meta:
#         model=Site
#         fields='__all__'
#         labels={'nom_site':'Nom du Site '}


# # form de site 
# class SiteempotageForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(SiteempotageForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
    
#     class Meta:
#         model=Site_empotage
#         fields='__all__'
#         labels={'nom_site':'Nom du Site '}

# # form de commodite
# class CommoditeForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(CommoditeForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#     class Meta :
#         model=Commodite
#         fields='__all__'

# #orm de Port De Dechargement 
# class PODForm(forms.ModelForm):
    
#     def __init__(self, *args, **kwargs):
#         super(PODForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#     class Meta:
#         model=POD
#         fields='__all__'
#         labels={'nom_POD':'Nom du Port de Dechagement'}



# class POLForm(forms.ModelForm):
    
#     def __init__(self, *args, **kwargs):
#         super(POLForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#     class Meta:
#         model=POL
#         fields='__all__'
#         labels={'nom_POL':'Nom du Port de chagement'}
        
        
# class CompagnieMaritimeForm(forms.ModelForm):
    
#     def __init__(self, *args, **kwargs):
#         super(CompagnieMaritimeForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#     class Meta:
#         model=CompagnieMaritime
#         fields='__all__'
        



# class ClientForm(forms.ModelForm):
    
#     def __init__(self, *args, **kwargs):
#         super(ClientForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#     class Meta:
#         model=Client
#         fields='__all__'
        

# class DossiersForm(forms.ModelForm):
    
#     """
#     Formulaire pour la création et la modification des dossiers.
#     """
    
#     def __init__(self, *args, **kwargs):
#         super(DossiersForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#         self.fields['compagnie_maritime'].queryset = CompagnieMaritime.objects.filter(pays__nom='Côte d\'Ivoire')
#         self.fields['client'].queryset = Client.objects.filter(pays__nom='Côte d\'Ivoire')
#         self.fields['port_de_chargement'].queryset = POL.objects.filter(pays__nom='Côte d\'Ivoire')
#         self.fields['commodite'].queryset = Commodite.objects.filter(pays__nom='Côte d\'Ivoire')
#         self.fields['port_de_dechargement'].queryset = POD.objects.filter(pays__nom='Côte d\'Ivoire')
#         self.fields['site'].queryset = Site.objects.filter(pays__nom='Côte d\'Ivoire')
#         self.fields['Site_empotage'].queryset = Site_empotage.objects.filter(pays__nom='Côte d\'Ivoire')
#         self.fields['agent_selection'].queryset = Personnel.objects.filter(Personnel_pays='côte_ivoire',Personnel_type='agent_selection')
#         self.fields['agent_acconage'].queryset = Personnel.objects.filter(Personnel_pays='côte_ivoire',Personnel_type='agent_acconage')
        
       
#     class Meta:
#         model=Dossier
#         fields = ['projet', 'TRD', 'booking', 'type_conteneur', 'client', 'commodite', 'port_de_chargement', 'port_de_dechargement', 'compagnie_maritime', 'site', 'agent_selection', 'agent_acconage','Site_empotage']
       
# class BaseDossierForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         country = kwargs.pop('country')
#         super(BaseDossierForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#         self.fields['compagnie_maritime'].queryset = CompagnieMaritime.objects.filter(pays__nom=country)
#         self.fields['client'].queryset = Client.objects.filter(pays__nom=country)
#         self.fields['port_de_chargement'].queryset = POL.objects.filter(pays__nom=country)
#         self.fields['commodite'].queryset = Commodite.objects.filter(pays__nom=country)
#         self.fields['port_de_dechargement'].queryset = POD.objects.filter(pays__nom=country)
#         self.fields['site'].queryset = Site.objects.filter(pays__nom=country)
#         self.fields['Site_empotage'].queryset = Site_empotage.objects.filter(pays__nom=country)
#         self.fields['agent_selection'].queryset = Personnel.objects.filter(Personnel_pays=country, Personnel_type='agent_selection')
#         self.fields['agent_acconage'].queryset = Personnel.objects.filter(Personnel_pays=country, Personnel_type='agent_acconage')
#         self.initial['pays'] = Pays.objects.get(nom=country)

#     class Meta:
#         model = Dossier
#         fields = ['projet', 'TRD', 'booking', 'type_conteneur', 'client', 'commodite', 'port_de_chargement', 'port_de_dechargement', 'compagnie_maritime', 'site', 'agent_selection', 'agent_acconage', 'Site_empotage']

# class DossiersGabonForm(BaseDossierForm):
#     """
#     Un formulaire pour gérer les dossiers spécifiques au Gabon.

#     Ce formulaire hérite de BaseDossierForm et définit le pays par défaut sur 'Gabon'.

#     Méthodes:
#         __init__(*args, **kwargs): Initialise le formulaire avec 'Gabon' comme pays.
#     """
#     def __init__(self, *args, **kwargs):
#         kwargs['country'] = 'Gabon'
#         super(DossiersGabonForm, self).__init__(*args, **kwargs)
        


# class DossiersNigeriaForm(BaseDossierForm):
#     def __init__(self, *args, **kwargs):
#         kwargs['country'] = 'Nigeria'
#         super(DossiersNigeriaForm, self).__init__(*args, **kwargs)      

# class DossiersliberiaForm(BaseDossierForm):
#     def __init__(self, *args, **kwargs):
#         kwargs['country'] = 'liberia'
#         super(DossiersliberiaForm, self).__init__(*args, **kwargs)  


# class DossiersBeninForm(BaseDossierForm):
#     def __init__(self, *args, **kwargs):
#         kwargs['country'] = 'Benin'
#         super(DossiersBeninForm, self).__init__(*args, **kwargs)      


# class DossiersMauritanieForm(BaseDossierForm):
#     def __init__(self, *args, **kwargs):
#         kwargs['country'] = 'Mauritanie'
#         super(DossiersMauritanieForm, self).__init__(*args, **kwargs)

     
# class ConteneurForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ConteneurForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.layout = Layout(
#             Row(
#                 Column('reference', css_class='form-group col-md-6 mb-0'),
#                 Column('etat', css_class='form-group col-md-6 mb-0'),
#                 css_class='form-row'
#             ),
#             Row(
#                 Column('photo_devant', css_class='form-group col-md-4 mb-0'),
#                 Column('photo_lateral_droit', css_class='form-group col-md-4 mb-0'),
#                 Column('photo_derriere', css_class='form-group col-md-4 mb-0'),
#                 css_class='form-row'
#             ),
#             Row(
#                 Column('photo_lateral_gauche', css_class='form-group col-md-6 mb-0'),
#                 Column('photo_interieur', css_class='form-group col-md-6 mb-0'),
#                 css_class='form-row'
#             ),
#             Submit('submit', 'Enregistrer')
#         )

#     class Meta:
#         model = Conteneur
#         fields = ['reference', 'etat', 'photo_devant', 'photo_derriere', 'photo_interieur','photo_lateral_droit','photo_lateral_gauche']
        
# # Créez un FormSet pour le modèle Conteneur
# ConteneurFormSet = modelformset_factory(
#     Conteneur,
#     form=ConteneurForm,
#     extra=1,  # Nombre de formulaires supplémentaires à afficher
#     can_delete=True
# )

# from django import forms
# from crispy_forms.helper import FormHelper
# from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Div
# from django.core.validators import MinValueValidator
# from decimal import Decimal

# class ConteneurAcconageForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ConteneurAcconageForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.form_class = 'form-horizontal'
#         self.helper.label_class = 'col-lg-3'
#         self.helper.field_class = 'col-lg-9'
        
#         # Ajout des classes pour le style et la validation
#         for field_name, field in self.fields.items():
#             field.widget.attrs['class'] = 'form-control'
#             if 'photo' in field_name:
#                 field.widget.attrs.update({
#                     'accept': 'image/*',
#                     'class': 'form-control-file',
#                     'onchange': 'previewImage(this);'
#                 })
#             if 'poids' in field_name:
#                 field.widget.attrs.update({
#                     'step': '0.01',
#                     'min': '0'
#                 })

#         # Layout amélioré avec des sections et des prévisualisations
#         self.helper.layout = Layout(
#             HTML("""
#                 <div class="card mb-4">
#                     <div class="card-header bg-primary text-white">
#                         <h4 class="mb-0">Informations de poids</h4>
#                     </div>
#                     <div class="card-body">
#             """),
#             Row(
                
#                 Column('poids_equipements', css_class='form-group col-md-4 mb-3'),
#                 Column('poids_net', css_class='form-group col-md-4 mb-3'),
#                 css_class='form-row'
#             ),
#             HTML("</div></div>"),

#             HTML("""
#                 <div class="card mb-4">
#                     <div class="card-header bg-primary text-white">
#                         <h4 class="mb-0">Heating Pad</h4>
#                     </div>
#                     <div class="card-body">
#             """),
#             Row(
#                 Column('numero_heating_pad', css_class='form-group col-md-6 mb-3'),
#                 Column(
#                     Div(
#                         'photo_heating_pad',
#                         HTML("""<img id="preview_photo_heating_pad" class="img-preview mt-2 d-none" src="" alt="Aperçu">"""),
#                         css_class='form-group'
#                     ),
#                     css_class='col-md-6 mb-3'
#                 ),
#                 css_class='form-row'
#             ),
#             HTML("</div></div>"),

#             # Sections similaires pour Flexitank et Plombs...
#             HTML("""
#                 <div class="card mb-4">
#                     <div class="card-header bg-primary text-white">
#                         <h4 class="mb-0">Flexitank</h4>
#                     </div>
#                     <div class="card-body">
#             """),
#             Row(
#                 Column('numero_flexitank', css_class='form-group col-md-6 mb-3'),
#                 Column(
#                     Div(
#                         'photo_flexitank',
#                         HTML("""<img id="preview_photo_flexitank" class="img-preview mt-2 d-none" src="" alt="Aperçu">"""),
#                         css_class='form-group'
#                     ),
#                     css_class='col-md-6 mb-3'
#                 ),
#                 css_class='form-row'
#             ),
#             HTML("</div></div>"),

#             # Section pour les plombs
#             HTML("""
#                 <div class="card mb-4">
#                     <div class="card-header bg-primary text-white">
#                         <h4 class="mb-0">Plombs</h4>
#                     </div>
#                     <div class="card-body">
#             """),
#             Row(
#                 Column(
#                     Div(
#                         Div('numero_plomb', css_class='mb-2'),
#                         Div('photo_plomb', css_class='custom-file'),
#                         css_class='p-2 border rounded bg-light'
#                     ),
#                     css_class='form-group col-md-4 mb-3'
#                 ),
#                 Column(
#                     Div(
#                         Div('numero_plomb4', css_class='mb-2'),
#                         Div('photo_plomb4', css_class='custom-file'),
#                         css_class='p-2 border rounded bg-light'
#                     ),
#                     css_class='form-group col-md-4 mb-3'
#                 ),
                
#             ),
#             HTML("</div></div>"),

#             Div(
#                 Submit('submit', 'Enregistrer', css_class='btn btn-primary btn-lg'),
#                 css_class='text-center mt-4'
#             ),
#         )

#     def clean(self):
#         cleaned_data = super().clean()
#         poids_brute = cleaned_data.get('poids_brute')
#         poids_net = cleaned_data.get('poids_net')
#         poids_equipements = cleaned_data.get('poids_equipements')

#         if poids_net and poids_brute:
#             if poids_net > poids_brute:
#                 raise forms.ValidationError({
#                     'poids_net': "Le poids net ne peut pas être supérieur au poids brut."
#                 })
            
#             if poids_equipements and (poids_brute - poids_equipements) < poids_net:
#                 raise forms.ValidationError({
#                     'poids_net': "Le poids net ne peut pas être supérieur au poids brut moins le poids des équipements."
#                 })

#         return cleaned_data

#     class Meta:
#         model = Conteneur
#         fields = [
#             'poids_net',
#             'poids_equipements',
#             'numero_heating_pad',
#             'photo_heating_pad',
#             'numero_flexitank',
#             'photo_flexitank',
#             'numero_plomb',
#             'photo_plomb',
#             'numero_plomb4',
#             'photo_plomb4',
#             'temperature',
#             'photo_selection1',
#             'photo_selection2',
#             'photo_selection3'
#         ]
#         widgets = {
            
#             'poids_net': forms.NumberInput(attrs={'placeholder': 'Entrez le poids net'}),
#             'poids_equipements': forms.NumberInput(attrs={'placeholder': 'Entrez le poids des équipements'}),
#         }
        
#         labels={'numero_plomb':'plomb   ',
#                 'photo_plomb':'photo plomb   ',
#                 'numero_plomb4':' numero plomb oils',
#                 'photo_plomb4':'photo plomb oils ',
#                 'photo_selection1':'Photo avant empotage',
#                 'photo_selection2':'Photo pendant empotage',
#                 'photo_selection3':'Photo fin empotage',
#                 'temperature':'Température (°C)',
                
                
#         }
# class ConteneurISO20Form(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(ConteneurISO20Form, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.form_tag = True
#         self.helper.form_class = 'form-horizontal shadow rounded p-4 bg-white'
#         self.helper.label_class = 'col-md-3 text-md-right fw-bold'
#         self.helper.field_class = 'col-md-9'
#         self.helper.form_method = 'post'
#         self.helper.form_id = 'conteneur-form'
        
#         # Add Bootstrap styling to all fields
#         for field in self.fields:
#             self.fields[field].widget.attrs.update({
#                 'class': 'form-control',
#             })
            
#         # Custom styling for file upload fields
#         for field in ['photo_plomb', 'photo_plomb2', 'photo_plomb3', 'photo_plomb4', 'photo_plomb5', 
#                       'photo_selection1', 'photo_selection2', 'photo_selection3']:
#             if field in self.fields:
#                 self.fields[field].widget.attrs.update({
#                     'class': 'form-control-file border rounded p-2',
#                 })
        
#         self.helper.layout = Layout(
#             HTML('<h2 class="text-center mb-4 text-primary">Informations Conteneur ISO 20</h2>'),
            
#             Fieldset(
#                 'Informations de base',
#                 Row(
#                     Column('poids_net', css_class='form-group col-md-6 mb-3'),
#                     Column('temperature', css_class='form-group col-md-6 mb-3'),
#                     css_class='form-row'
#                 ),
#                 css_class='mb-4 pb-3 border-bottom'
#             ),
            
#             Fieldset(
#                 'Plombs standards',
#                 Row(
#                     Column('numero_plomb', css_class='form-group col-md-6 mb-2'),
#                     Column('photo_plomb', css_class='form-group col-md-6 mb-2'),
#                     css_class='form-row'
#                 ),
#                 Row(
#                     Column('numero_plomb2', css_class='form-group col-md-6 mb-2'),
#                     Column('photo_plomb2', css_class='form-group col-md-6 mb-2'),
#                     css_class='form-row'
#                 ),
#                 Row(
#                     Column('numero_plomb3', css_class='form-group col-md-6 mb-2'),
#                     Column('photo_plomb3', css_class='form-group col-md-6 mb-2'),
#                     css_class='form-row'
#                 ),
#                 css_class='mb-4 pb-3 border-bottom'
#             ),
            
#             Fieldset(
#                 'Plombs oils',
#                 Row(
#                     Column('numero_plomb4', css_class='form-group col-md-6 mb-2'),
#                     Column('photo_plomb4', css_class='form-group col-md-6 mb-2'),
#                     css_class='form-row'
#                 ),
#                 Row(
#                     Column('numero_plomb5', css_class='form-group col-md-6 mb-2'),
#                     Column('photo_plomb5', css_class='form-group col-md-6 mb-2'),
#                     css_class='form-row'
#                 ),
#                 css_class='mb-4 pb-3 border-bottom'
#             ),
            
#             Fieldset(
#                 'Photos d\'empotage',
#                 Row(
#                     Column('photo_selection1', css_class='form-group col-md-4 mb-3'),
#                     Column('photo_selection2', css_class='form-group col-md-4 mb-3'),
#                     Column('photo_selection3', css_class='form-group col-md-4 mb-3'),
#                     css_class='form-row'
#                 ),
#                 css_class='mb-4'
#             ),
            
#             Div(
#                 Submit('submit', 'Enregistrer', css_class='btn btn-primary px-4 py-2'),
#                 HTML('<a class="btn btn-outline-secondary mx-2 px-4 py-2" href="{% url \'list_conteneurs\' %}">Annuler</a>'),
#                 css_class='d-flex justify-content-center mt-5'
#             )
#         )
   
#     class Meta:
#         model = Conteneur
#         fields = ['poids_net','numero_plomb','photo_plomb','numero_plomb2','photo_plomb2','numero_plomb3',
#                  'photo_plomb3','numero_plomb4','photo_plomb4','numero_plomb5','photo_plomb5', 
#                  'photo_selection1','photo_selection2','photo_selection3','temperature']
#         labels = {
#             'numero_plomb4': 'Plomb oils 1',
#             'photo_plomb4': 'Photo plomb oils 1',
#             'numero_plomb5': 'Plomb oils 2',
#             'photo_plomb5': 'Photo plomb oils 2',
#             'temperature': 'Température (°C)',
#             'photo_selection1': 'Photo avant empotage',
#             'photo_selection2': 'Photo pendant habillage',
#             'photo_selection3': 'Photo fin empotage',
#         }
#         widgets = {
#             'temperature': forms.NumberInput(attrs={'placeholder': 'Entrez la température', 'class': 'form-control'}),
#             'poids_net': forms.NumberInput(attrs={'placeholder': 'Entrez le poids net', 'class': 'form-control'}),
#         }    
        
# class Dossiers2Form(forms.ModelForm):
    
#     def __init__(self, *args, **kwargs):
#         super(Dossiers2Form, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
       
#     class Meta:
#         model=Dossier2
#         fields = ['projet', 'TRD', 'booking', 'type_conteneur', 'client', 'commodite', 'port_de_chargement', 'port_de_dechargement', 'compagnie_maritime', 'site', 'agent_selection', 'agent_acconage','Site_empotage','date_creation']
       
     

 
# class AgentForm(forms.ModelForm):
    
#     def __init__(self, *args, **kwargs):
#         super(AgentForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
#     class Meta:
#         model=Agent
#         fields='__all__'
        


# class DocumentFactureForm(forms.ModelForm):
#     class Meta:
#         model = Document_Facture
#         fields = ['document']
        

# class AutreDocumentForm(forms.ModelForm):
#     class Meta:
#         model = AutreDocument
#         fields = ['document']
        
        
# class ImagesForm(forms.ModelForm):
#     class Meta:
#         model = Images
#         fields = ['image']
       

# class FactureCommercialForm(forms.ModelForm):
#     def __init__(self, *args, **kwargs):
#         super(FactureCommercialForm, self).__init__(*args, **kwargs)
#         self.helper = FormHelper()
#         self.helper.add_input(Submit('submit', 'Enregistrer'))
       
#     class Meta:
#         model = FactureCommerciale
#         fields = ['fichier']
        
# class PackingListForm(forms.ModelForm):
#     class Meta:
#         model = PackingList
#         fields = ['fichier']
        
# class CertificatOrigineForm(forms.ModelForm):
#     class Meta:
#         model = CertificatOrigine
#         fields = ['fichier']
        
        
# class ConfirmationBookingForm(forms.ModelForm):
#     class Meta:
#         model = ConfirmationBooking
#         fields = ['fichier']
    
# class CertificatPhytosanitaireForm(forms.ModelForm):
#     class Meta:
#         model = CertificatPhytosanitaire
#         fields = ['fichier']
        
        
# class CopiesBLSForm(forms.ModelForm):
#     class Meta:
#         model = CopiesBLS
#         fields = ['fichier']
    
# class RapportEmpotageForm(forms.ModelForm):
#     class Meta:
#         model = RapportEmpotage
#         fields = ['fichier']        

# class RapportSelectionForm(forms.ModelForm):
#     class Meta:
#         model = RapportSelection
#         fields = ['fichier']
        
# class AutorisationExploitationForm(forms.ModelForm):
#     class Meta:
#         model = AutorisationExploitation
#         fields = ['fichier']
    
# class ECForm(forms.ModelForm):
#     class Meta:
#         model = EC
#         fields = ['fichier']


# class COAForm(forms.ModelForm):
#     class Meta:
#         model = COA
#         fields = ['fichier']
        
# class DeclarationForm(forms.ModelForm):
#     class Meta:
#         model = Declaration
#         fields = ['fichier']
        
# class IER_ENTREForm(forms.ModelForm):
#     class Meta:
#         model = IER_ENTRE
#         fields = ['fichier']
    
    
# class IER_SORTIEForm(forms.ModelForm):
#     class Meta:
#         model = IER_SORTIE
#         fields = ['fichier']
    