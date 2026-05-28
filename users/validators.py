import re

from django.core.exceptions import ValidationError


class StrongPasswordValidator:
    def validate(self, password, user=None):
        errors = []
        if len(password) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")
        if not re.search(r'[A-Z]', password):
            errors.append("Debe contener al menos una letra mayúscula.")
        if not re.search(r'[a-z]', password):
            errors.append("Debe contener al menos una letra minúscula.")
        if not re.search(r'\d', password):
            errors.append("Debe contener al menos un número.")
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return "Mínimo 8 caracteres, 1 mayúscula, 1 minúscula, 1 número."
