# templatetags/custom_filters.py
from django import template
register = template.Library()

@register.filter
def monthname(month_number):
    months = {
        1: 'Janvier', 2: 'Février', 3: 'Mars',
        4: 'Avril', 5: 'Mai', 6: 'Juin',
        7: 'Juillet', 8: 'Août', 9: 'Septembre',
        10: 'Octobre', 11: 'Novembre', 12: 'Décembre'
    }
    return months.get(int(month_number), '')


@register.filter(name='addclass')
def addclass(field, css):
    return field.as_widget(attrs={"class": css})