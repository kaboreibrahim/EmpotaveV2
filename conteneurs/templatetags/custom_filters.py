import os
from django import template

register = template.Library()

@register.filter
def basename(value):
    """Retourne le nom du fichier à partir d'un chemin"""
    return os.path.basename(value)


from django import template

register = template.Library()

@register.filter(name='addclass')
def addclass(value, arg):
    return f'{value} {arg}'

from django import template
import os

register = template.Library()

@register.filter
def basename(value):
    """Returns the base name of the file from a path"""
    return os.path.basename(value)
