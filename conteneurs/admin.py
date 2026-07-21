# from django.contrib import admin
# from .models import *

# # Créer une Inline pour chaque type de document
# class FactureCommercialeInline(admin.TabularInline):  # Vous pouvez aussi utiliser StackedInline
#     model = FactureCommerciale
#     extra = 1  # Nombre de formulaires vides à afficher
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']  # Champs en lecture seule

# class PackingListInline(admin.TabularInline):
#     model = PackingList
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class CertificatOrigineInline(admin.TabularInline):
#     model = CertificatOrigine
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class ConfirmationBookingInline(admin.TabularInline):
#     model = ConfirmationBooking
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class CertificatPhytosanitaireInline(admin.TabularInline):
#     model = CertificatPhytosanitaire
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class CopiesBLSInline(admin.TabularInline):
#     model = CopiesBLS
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class RapportEmpotageInline(admin.TabularInline):
#     model = RapportEmpotage
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class RapportSelectionInline(admin.TabularInline):
#     model = RapportSelection
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class AutorisationExploitationInline(admin.TabularInline):
#     model = AutorisationExploitation
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class ECInline(admin.TabularInline):
#     model = EC
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']

# class DeclarationInline(admin.TabularInline):
#     model = Declaration
#     extra = 1
#     fields = ['fichier', 'statut', 'date_ajout', 'date_modification']
#     readonly_fields = ['date_ajout', 'date_modification']
 

# # Inline pour les conteneurs
# class ConteneurInline(admin.TabularInline):  # Vous pouvez aussi utiliser admin.StackedInline pour un affichage en blocs
#     model = Conteneur
#     extra = 1  # Nombre de conteneurs supplémentaires à afficher

# # Configuration pour le modèle Dossier
# @admin.register(Dossier)
# class DossierAdmin(admin.ModelAdmin):
#     list_display = ('date_creation', 'statut', 'projet','TRD', 'client', 'agent_selection', 'agent_acconage','port_de_chargement', 'port_de_dechargement','compagnie_maritime', 'site', 'commodite', 'secretaire')
#     search_fields = ('projet', 'statut', 'Personnel_type', 'client__nom')
#     list_filter = ('statut', 'projet', 'date_creation', 'secretaire')
#     date_hierarchy = 'date_creation'
#     inlines = [ConteneurInline,FactureCommercialeInline,
#         PackingListInline,
#         CertificatOrigineInline,
#         ConfirmationBookingInline,
#         CertificatPhytosanitaireInline,
#         CopiesBLSInline,
#         RapportEmpotageInline,
#         RapportSelectionInline,
#         AutorisationExploitationInline,
#         ECInline,
#         DeclarationInline]  # Ajout de l'inline pour les conteneurs

# # Autres configurations d'administration (comme avant)
# @admin.register(Personnel)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ('username', 'first_name', 'last_name', 'email', 'Personnel_type')
#     search_fields = ('username', 'first_name', 'last_name', 'Personnel_type')
#     list_filter = ('Personnel_type',)

# @admin.register(Client)
# class ClientAdmin(admin.ModelAdmin):
#     list_display = ('nom', 'adresse', 'contact', 'email')
#     search_fields = ('nom', 'adresse')

# @admin.register(Commodite)
# class CommoditeAdmin(admin.ModelAdmin):
#     list_display = ('nom_commodite',)
#     search_fields = ('nom_commodite',)

# @admin.register(Site)
# class SiteAdmin(admin.ModelAdmin):
#     list_display = ('nom_site',)
#     search_fields = ('nom_site',)

# @admin.register(Pays)
# class  PaysAdmin(admin.ModelAdmin):
#     list_display = ('nom',)
#     search_fields = ('nom',)


# @admin.register(Site_empotage)
# class Site_empotageAdmin(admin.ModelAdmin):
#     list_display = ('nom_site',)
#     search_fields = ('nom_site',)
# @admin.register(POD)
# class PortDeDechargementAdmin(admin.ModelAdmin):
#     list_display = ('nom_POD',)
#     search_fields = ('nom_POD',)

# @admin.register(POL)
# class PortDeChargementAdmin(admin.ModelAdmin):
#     list_display = ('nom_POL','Date_ajout')
#     search_fields = ('nom_POL',)

# @admin.register(CompagnieMaritime)
# class CompagnieMaritimeAdmin(admin.ModelAdmin):
#     list_display = ('nom_compagnie_maritime',)
#     search_fields = ('nom_compagnie_maritime',)

# @admin.register(Conteneur)
# class ConteneurAdmin(admin.ModelAdmin):
#     list_display = ('reference', 'etat', 'dossier', 'agent_selection', 'agent_acconage','Date_ajout')
#     list_filter = ('dossier', 'etat')
#     search_fields = ('reference', 'dossier__projet')

#     def save_model(self, request, obj, form, change):
#         if not change and not obj.agent_acconage:
#             obj.agent_selection = request.Personnel_type
#         elif change and 'agent_acconage' in form.changed_data:
#             obj.agent_acconage = request.Personnel_type
#         super().save_model(request, obj, form, change)

# @admin.register(FichierJoint)
# class FicherJointAdmin(admin.ModelAdmin):
    
#     pass
# class DocumentFactureInline(admin.TabularInline):
#     model = Document_Facture
#     extra = 1
#     readonly_fields = ('Date_ajout',)


# class AutreDocumentInline(admin.TabularInline):
#     model = AutreDocument
#     extra = 1
#     readonly_fields = ('Date_ajout',)

# class ImagesInline(admin.TabularInline):
#     model = Images
#     extra = 1
#     readonly_fields = ('Date_ajout',)

# @admin.register(Dossier2)
# class Dossier2Admin(admin.ModelAdmin):
#     list_display = ('projet', 'TRD', 'client', 'Date_ajout','date_creation')
#     search_fields = ('projet', 'TRD')
#     list_filter = ('client',)
#     inlines = [DocumentFactureInline, AutreDocumentInline, ImagesInline]


# @admin.register(FactureCommerciale)
# class FactureCommercialeAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut

# @admin.register(PackingList)
# class PackingListAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')
#     list_filter = ('statut',)

# # Répétez le même processus pour les autres modèles

# @admin.register(CertificatOrigine)
# class CertificatOrigineAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut



# @admin.register(ConfirmationBooking)
# class ConfirmationBookingAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut



# @admin.register(CertificatPhytosanitaire)
# class CertificatPhytosanitaireAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut



# @admin.register(CopiesBLS)
# class CopiesBLSAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut



# @admin.register(RapportEmpotage)
# class RapportEmpotageAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut



# @admin.register(RapportSelection)
# class RapportSelectionAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut



# @admin.register(AutorisationExploitation)
# class AutorisationExploitationAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification')
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut



# @admin.register(EC)
# class ECAdmin(admin.ModelAdmin):
#     list_display = ('dossier', 'statut', 'date_ajout', 'date_modification') 
#     search_fields = ('dossier__projet', 'dossier__TRD')  # Recherche par projet ou TRD
#     list_filter = ('statut',)  # Filtres par statut

