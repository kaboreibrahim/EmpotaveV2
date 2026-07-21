
import os
from django.core.exceptions import ValidationError


def validate_image_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = [
        '.jpg', '.jpeg', '.png', ]
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')


def validate_document_extension(value):
    ext = os.path.splitext(value.name)[1]  # [0] returns path+filename
    valid_extensions = [
        '.doc', '.docx', '.pdf', ]
    if not ext.lower() in valid_extensions:
        raise ValidationError('Unsupported file extension.')
