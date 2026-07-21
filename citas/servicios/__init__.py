"""
Capa de lógica de negocio orientada a objetos (tarjetas CRC 16, 22–27).

Las vistas HTTP delegan en estas clases; los modelos Django conservan la capa de datos.
"""

from .bitacora import Bitacora
from .calendario import Calendario
from .caja import Caja
from .cita import Cita as CitaNegocio
from .qr import QR
from .tramite import Tramite as TramiteNegocio

__all__ = [
    'Bitacora',
    'Calendario',
    'Caja',
    'CitaNegocio',
    'QR',
    'TramiteNegocio',
]
