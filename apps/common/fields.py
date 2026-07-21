"""
apps/common/fields.py
Champs de modèle Django personnalisés.
"""
from django.db import models

from .imaging import convertir_en_webp


class WebPImageField(models.ImageField):
    """ImageField qui convertit automatiquement toute image uploadée en WebP.

    La conversion a lieu juste avant l'écriture dans le storage, donc elle
    s'applique à tous les points d'entrée (formulaires, admin, API) sans
    logique supplémentaire dans les vues.
    """

    def pre_save(self, model_instance, add):
        fichier = getattr(model_instance, self.attname)
        if fichier and not fichier._committed:
            converti = convertir_en_webp(fichier)
            if converti is not None:
                fichier.name = converti.name
                fichier.file = converti
        return super().pre_save(model_instance, add)
