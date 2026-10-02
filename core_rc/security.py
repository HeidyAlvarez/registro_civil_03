"""Cifrado autenticado de datos personales y generación de índices ciegos."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from functools import lru_cache

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


PREFIX = 'enc'
NONCE_BYTES = 12


def _decode_key(value: str, setting_name: str) -> bytes:
    try:
        key = base64.urlsafe_b64decode(value.encode('ascii'))
    except Exception as exc:
        raise ImproperlyConfigured(f'{setting_name} debe usar Base64 URL-safe.') from exc
    if len(key) != 32:
        raise ImproperlyConfigured(f'{setting_name} debe contener exactamente 32 bytes.')
    return key


@lru_cache(maxsize=1)
def encryption_keys() -> dict[str, bytes]:
    raw = getattr(settings, 'PII_ENCRYPTION_KEYS', {})
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ImproperlyConfigured('PII_ENCRYPTION_KEYS debe ser un objeto JSON.') from exc
    if not isinstance(raw, dict) or not raw:
        raise ImproperlyConfigured('Configura PII_ENCRYPTION_KEYS antes de acceder a datos personales.')
    return {str(version): _decode_key(str(value), f'PII_ENCRYPTION_KEYS[{version}]') for version, value in raw.items()}


def active_key_version() -> str:
    version = str(getattr(settings, 'PII_ACTIVE_KEY_VERSION', '') or '')
    if not version or version not in encryption_keys():
        raise ImproperlyConfigured('PII_ACTIVE_KEY_VERSION no corresponde a una clave configurada.')
    return version


@lru_cache(maxsize=1)
def blind_index_key() -> bytes:
    value = str(getattr(settings, 'PII_BLIND_INDEX_KEY', '') or '')
    if not value:
        raise ImproperlyConfigured('Configura PII_BLIND_INDEX_KEY antes de buscar datos personales.')
    return _decode_key(value, 'PII_BLIND_INDEX_KEY')


def is_encrypted(value: object) -> bool:
    return isinstance(value, str) and value.startswith(f'{PREFIX}:')


def encrypt_text(value: object) -> object:
    if value is None or value == '' or is_encrypted(value):
        return value
    version = active_key_version()
    nonce = os.urandom(NONCE_BYTES)
    plaintext = str(value).encode('utf-8')
    ciphertext = AESGCM(encryption_keys()[version]).encrypt(nonce, plaintext, version.encode('utf-8'))
    payload = base64.urlsafe_b64encode(nonce + ciphertext).decode('ascii')
    return f'{PREFIX}:{version}:{payload}'


def decrypt_text(value: object, *, allow_plaintext: bool = False) -> object:
    if value is None or value == '':
        return value
    if not is_encrypted(value):
        if allow_plaintext:
            return value
        raise ValueError('Se detectó un dato personal sin cifrar.')
    try:
        _, version, payload = str(value).split(':', 2)
        raw = base64.urlsafe_b64decode(payload.encode('ascii'))
        nonce, ciphertext = raw[:NONCE_BYTES], raw[NONCE_BYTES:]
        return AESGCM(encryption_keys()[version]).decrypt(
            nonce, ciphertext, version.encode('utf-8'),
        ).decode('utf-8')
    except (InvalidTag, KeyError, ValueError, TypeError) as exc:
        raise ValueError('No fue posible autenticar o descifrar el dato personal.') from exc


def normalize_curp(value: object) -> str:
    return ''.join(str(value or '').upper().split())


def blind_index(value: object, *, purpose: str = 'curp') -> str:
    normalized = normalize_curp(value)
    if not normalized:
        return ''
    message = f'{purpose}:{normalized}'.encode('utf-8')
    return hmac.new(blind_index_key(), message, hashlib.sha256).hexdigest()


def clear_key_cache() -> None:
    encryption_keys.cache_clear()
    blind_index_key.cache_clear()
