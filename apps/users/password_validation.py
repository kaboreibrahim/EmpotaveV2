import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

FOUR_DIGIT_CODE_RE = re.compile(r'^\d{4}$')


class FourDigitPasswordValidator:
    """Enforce a 4-digit numeric PIN as the only allowed password format."""

    def validate(self, password, user=None):
        if not FOUR_DIGIT_CODE_RE.match(password):
            raise ValidationError(
                _('Le mot de passe doit être un code à exactement 4 chiffres.'),
                code='password_not_four_digits',
            )

    def get_help_text(self):
        return _('Votre mot de passe doit être un code à exactement 4 chiffres.')
