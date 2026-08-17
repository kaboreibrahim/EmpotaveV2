"""
apps/messaging/attachments.py
Validation et traitement des pieces jointes de messages : images, videos,
documents (Phase 6) et vocaux enregistres depuis le navigateur (Phase 7,
MediaRecorder). Point de passage unique : aucune vue ne doit stocker un
fichier uploade sans passer par `creer_piece_jointe`.
"""
import io
import os

from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError

from apps.common.imaging import convertir_en_webp

from .models import MessageAttachment

TAILLE_MAX_OCTETS = {
    MessageAttachment.TYPE_IMAGE: 10 * 1024 * 1024,     # 10 Mo
    MessageAttachment.TYPE_VIDEO: 100 * 1024 * 1024,    # 100 Mo
    MessageAttachment.TYPE_DOCUMENT: 20 * 1024 * 1024,  # 20 Mo
    MessageAttachment.TYPE_AUDIO: 20 * 1024 * 1024,     # 20 Mo (vocaux courts)
}

# Formats produits par MediaRecorder selon le navigateur (webm/opus sur
# Chrome/Firefox, mp4/aac sur Safari) — voir static/messaging/js/realtime.js.
MIME_AUTORISES = {
    MessageAttachment.TYPE_IMAGE: {'image/jpeg', 'image/png', 'image/webp'},
    MessageAttachment.TYPE_VIDEO: {'video/mp4', 'video/webm', 'video/ogg', 'video/quicktime'},
    MessageAttachment.TYPE_DOCUMENT: {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain',
    },
    MessageAttachment.TYPE_AUDIO: {
        'audio/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav', 'audio/aac',
    },
}

MINIATURE_TAILLE_MAX = (480, 480)
MINIATURE_QUALITY = 80


class FichierInvalide(Exception):
    """Levee quand un fichier ne passe pas la validation (type ou taille) —
    a rattraper par la vue pour renvoyer un message d'erreur exploitable."""


def categorie_fichier(uploaded_file):
    # MediaRecorder envoie souvent un Content-Type avec parametre de codec
    # (ex. "audio/webm;codecs=opus") : on ne compare que le type de base.
    content_type = (uploaded_file.content_type or '').lower().split(';')[0].strip()
    for categorie, mimes in MIME_AUTORISES.items():
        if content_type in mimes:
            return categorie
    return None


def valider_fichier(uploaded_file):
    """Renvoie la categorie (image/video/document) d'un fichier uploade, ou
    leve FichierInvalide si le type n'est pas autorise ou la taille depassee."""
    categorie = categorie_fichier(uploaded_file)
    if categorie is None:
        raise FichierInvalide(
            f"Type de fichier non autorisé ({uploaded_file.content_type or 'inconnu'})."
        )

    limite = TAILLE_MAX_OCTETS[categorie]
    if uploaded_file.size > limite:
        raise FichierInvalide(
            f"Fichier trop volumineux ({uploaded_file.size // (1024 * 1024)} Mo, "
            f"limite {limite // (1024 * 1024)} Mo pour ce type de fichier)."
        )

    if categorie == MessageAttachment.TYPE_IMAGE:
        # Le Content-Type declare par le navigateur est facilement falsifie
        # (ex. un .exe renomme en .jpg) : on verifie le contenu reel.
        try:
            uploaded_file.seek(0)
            Image.open(uploaded_file).verify()
        except (UnidentifiedImageError, OSError):
            raise FichierInvalide("Le fichier n'est pas une image valide.")
        finally:
            uploaded_file.seek(0)

    return categorie


def _generer_miniature(uploaded_file):
    """Miniature WebP redimensionnee pour un affichage rapide (bulles,
    section fichiers). None si l'image n'est finalement pas exploitable —
    l'affichage retombera alors sur le fichier original."""
    try:
        uploaded_file.seek(0)
        image = Image.open(uploaded_file)
        image.load()
    except Exception:
        return None

    image = image.convert('RGB')
    image.thumbnail(MINIATURE_TAILLE_MAX)

    buffer = io.BytesIO()
    image.save(buffer, format='WEBP', quality=MINIATURE_QUALITY)
    buffer.seek(0)

    nom_base = os.path.splitext(os.path.basename(uploaded_file.name))[0]
    return ContentFile(buffer.read(), name=f'{nom_base}_miniature.webp')


def creer_piece_jointe(message, uploaded_file, duree_secondes=None):
    """Valide puis enregistre une piece jointe pour `message`. Les images
    sont converties en WebP (compression, coherent avec WebPImageField
    utilise ailleurs) et dotees d'une miniature. Leve FichierInvalide sans
    rien ecrire si le fichier est refuse.

    `duree_secondes` (vocaux) vient du chronometre cote navigateur au moment
    de l'enregistrement — aucune bibliotheque d'analyse audio cote serveur
    n'est necessaire pour obtenir cette valeur."""
    categorie = valider_fichier(uploaded_file)

    fichier_a_stocker = uploaded_file
    type_mime = uploaded_file.content_type or ''
    miniature = None

    if categorie == MessageAttachment.TYPE_IMAGE:
        converti = convertir_en_webp(uploaded_file)
        if converti is not None:
            fichier_a_stocker = converti
            type_mime = 'image/webp'
        uploaded_file.seek(0)
        miniature = _generer_miniature(uploaded_file)

    return MessageAttachment.objects.create(
        message=message,
        type_fichier=categorie,
        fichier=fichier_a_stocker,
        miniature=miniature,
        duree_secondes=duree_secondes if categorie == MessageAttachment.TYPE_AUDIO else None,
        nom_original=uploaded_file.name,
        taille_octets=fichier_a_stocker.size,
        type_mime=type_mime,
    )
