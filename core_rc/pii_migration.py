"""Cifrado idempotente de columnas existentes. No imprime valores personales."""

import json

from django.core.exceptions import ImproperlyConfigured
from django.db import connection, transaction


BATCH_SIZE = 200


def require_pii_keys(apps=None, schema_editor=None):
    from django.conf import settings

    keys = getattr(settings, 'PII_ENCRYPTION_KEYS', {}) or {}
    version = getattr(settings, 'PII_ACTIVE_KEY_VERSION', '')
    blind = getattr(settings, 'PII_BLIND_INDEX_KEY', '')
    if not keys or version not in keys or not blind:
        raise ImproperlyConfigured(
            'Migración abortada: faltan PII_ENCRYPTION_KEYS, PII_ACTIVE_KEY_VERSION '
            'o PII_BLIND_INDEX_KEY. No se modificó ningún registro.'
        )


def _as_text(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    return str(value)


def _quote(name):
    return connection.ops.quote_name(name)


def transform_columns(table, columns, *, mode, hash_source=None, hash_column=None):
    """mode: encrypt, decrypt o rotate. hash_source es la columna CURP en claro o cifrada."""
    from core_rc.security import blind_index, decrypt_text, encrypt_text, is_encrypted

    require_pii_keys()
    selected = list(columns)
    if hash_source and hash_source not in selected:
        selected.append(hash_source)
    column_sql = ', '.join(_quote(column) for column in selected)
    pk = _quote('id')
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT {pk}, {column_sql} FROM {_quote(table)} ORDER BY {pk}')
        rows = cursor.fetchall()

    for start in range(0, len(rows), BATCH_SIZE):
        with transaction.atomic():
            with connection.cursor() as cursor:
                for row in rows[start:start + BATCH_SIZE]:
                    pk_value = row[0]
                    current = dict(zip(selected, row[1:]))
                    assignments = []
                    params = []
                    plain_curp = None
                    for column in columns:
                        value = current[column]
                        text = _as_text(value)
                        if text is None or text == '':
                            continue
                        if mode == 'encrypt':
                            if is_encrypted(text):
                                continue
                            stored = encrypt_text(text)
                        elif mode == 'decrypt':
                            if not is_encrypted(text):
                                continue
                            stored = decrypt_text(text)
                        elif mode == 'rotate':
                            if not is_encrypted(text):
                                stored = encrypt_text(text)
                            else:
                                stored = encrypt_text(decrypt_text(text))
                        else:
                            raise ValueError('Modo de migración no reconocido.')
                        assignments.append(f'{_quote(column)} = %s')
                        params.append(stored)
                    if hash_source and hash_column:
                        source = _as_text(current.get(hash_source))
                        if source:
                            plain_curp = decrypt_text(source) if is_encrypted(source) else source
                            assignments.append(f'{_quote(hash_column)} = %s')
                            params.append(blind_index(plain_curp))
                    if not assignments:
                        continue
                    params.append(pk_value)
                    cursor.execute(
                        f'UPDATE {_quote(table)} SET {", ".join(assignments)} WHERE {pk} = %s',
                        params,
                    )


def encrypt_citas(apps=None, schema_editor=None):
    transform_columns(
        'citas_cita',
        ['curp_ciudadano', 'nombre_ciudadano', 'codigo_postal', 'direccion', 'datos_adicionales'],
        mode='encrypt',
        hash_source='curp_ciudadano',
        hash_column='curp_hash',
    )
    transform_columns('citas_bitacoraauditoria', ['descripcion'], mode='encrypt')


def decrypt_citas(apps=None, schema_editor=None):
    transform_columns(
        'citas_cita',
        ['curp_ciudadano', 'nombre_ciudadano', 'codigo_postal', 'direccion', 'datos_adicionales'],
        mode='decrypt',
    )
    transform_columns('citas_bitacoraauditoria', ['descripcion'], mode='decrypt')


def encrypt_ia(apps=None, schema_editor=None):
    transform_columns('ia_conversacionasistente', ['contexto'], mode='encrypt')
    transform_columns('ia_mensajeasistente', ['texto', 'metadatos'], mode='encrypt')
    transform_columns('ia_solicitudatencion', ['curp', 'nombre', 'motivo'], mode='encrypt')
    transform_columns(
        'ia_notificacioninteligente',
        ['curp', 'titulo', 'mensaje'],
        mode='encrypt',
        hash_source='curp',
        hash_column='curp_hash',
    )
    transform_columns('ia_alertaurgente', ['titulo', 'detalle'], mode='encrypt')
    transform_columns('ia_anomalia', ['descripcion', 'evidencia'], mode='encrypt')


def decrypt_ia(apps=None, schema_editor=None):
    transform_columns('ia_conversacionasistente', ['contexto'], mode='decrypt')
    transform_columns('ia_mensajeasistente', ['texto', 'metadatos'], mode='decrypt')
    transform_columns('ia_solicitudatencion', ['curp', 'nombre', 'motivo'], mode='decrypt')
    transform_columns('ia_notificacioninteligente', ['curp', 'titulo', 'mensaje'], mode='decrypt')
    transform_columns('ia_alertaurgente', ['titulo', 'detalle'], mode='decrypt')
    transform_columns('ia_anomalia', ['descripcion', 'evidencia'], mode='decrypt')


def count_column(table, column):
    from core_rc.security import is_encrypted

    encrypted = plaintext = empty = 0
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT {_quote(column)} FROM {_quote(table)}',
        )
        for (value,) in cursor.fetchall():
            text = _as_text(value)
            if text is None or text == '' or text == '{}':
                empty += 1
            elif is_encrypted(text):
                encrypted += 1
            else:
                plaintext += 1
    return {'cifrados': encrypted, 'texto_claro': plaintext, 'vacios': empty}
