"""Validadores reutilizables del sistema."""

import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

MENSAJE_CURP_FORMATO = (
    'La CURP no tiene un formato válido. Ejemplo: LOPE800101HDFRNN09. '
    'Debe coincidir con tu identificación oficial.'
)

PATRON_CURP = re.compile(r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$')

ENTIDADES_CURP = frozenset({
    'AS', 'BC', 'BS', 'CC', 'CL', 'CM', 'CS', 'CH', 'DF', 'DG',
    'GT', 'GR', 'HG', 'JC', 'MC', 'MN', 'MS', 'NT', 'NL', 'OC',
    'PL', 'QT', 'QR', 'SP', 'SL', 'SR', 'TC', 'TS', 'TL', 'VZ',
    'YN', 'ZS', 'NE',
})

validador_curp = RegexValidator(
    regex=r'^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d$',
    message=MENSAJE_CURP_FORMATO,
)


def validar_curp(valor):
    """Valida estructura oficial de CURP (18 caracteres)."""
    curp = (valor or '').strip().upper()
    if not PATRON_CURP.match(curp):
        raise ValidationError(MENSAJE_CURP_FORMATO, code='curp_formato')

    mes = int(curp[6:8])
    dia = int(curp[8:10])
    if not (1 <= mes <= 12 and 1 <= dia <= 31):
        raise ValidationError(
            'La fecha de nacimiento en la CURP no es válida.',
            code='curp_fecha',
        )

    if curp[11:13] not in ENTIDADES_CURP:
        raise ValidationError(
            'La entidad federativa en la CURP no es válida.',
            code='curp_entidad',
        )

    return curp
