"""
apps/common/imaging.py
Conversion des images uploadées vers le format WebP.
"""
import io
import os

from django.core.files.base import ContentFile
from PIL import Image

WEBP_QUALITY = 85


def convertir_en_webp(fichier, quality=WEBP_QUALITY):
    """Convertit le contenu d'un fichier image en WebP.

    Retourne un ContentFile prêt à être stocké (nom en .webp), ou None si le
    fichier n'est pas une image exploitable (auquel cas l'upload d'origine
    est conservé tel quel).
    """
    try:
        fichier.seek(0)
        image = Image.open(fichier)
        image.load()
    except Exception:
        return None

    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        image = image.convert('RGBA')
    else:
        image = image.convert('RGB')

    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=quality)
    buffer.seek(0)

    nom_base = os.path.splitext(os.path.basename(fichier.name))[0]
    return ContentFile(buffer.read(), name=f'{nom_base}.webp')
