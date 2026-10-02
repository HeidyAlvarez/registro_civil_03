import json

from django.db import models

from core_rc.security import decrypt_text, encrypt_text, is_encrypted


class EncryptedTextField(models.TextField):
    """Persiste texto con AES-256-GCM y lo entrega descifrado a la aplicación."""

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        return decrypt_text(value)

    def to_python(self, value):
        if value is None or value == '' or not isinstance(value, str):
            return value
        if is_encrypted(value):
            return decrypt_text(value)
        return value

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == '':
            return value
        if is_encrypted(value):
            return value
        return encrypt_text(str(value))


class EncryptedJSONField(models.TextField):
    """Cifra objetos JSON completos porque el texto cifrado no es JSON válido."""

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return {}
        if not is_encrypted(value):
            raise ValueError('Se detectó un dato personal sin cifrar.')
        return self.to_python(decrypt_text(value))

    def to_python(self, value):
        if value is None or value == '':
            return {} if value == '' else value
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str) and is_encrypted(value):
            value = decrypt_text(value)
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, (dict, list)):
                raise ValueError('El JSON cifrado debe ser un objeto o una lista.')
            return parsed
        return value

    def get_prep_value(self, value):
        if value is None:
            return None
        if isinstance(value, str) and is_encrypted(value):
            return value
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        return encrypt_text(value)
