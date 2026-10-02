from django.core.management.base import BaseCommand, CommandError

from core_rc.pii_migration import transform_columns


class Command(BaseCommand):
    help = 'Vuelve a cifrar los datos personales con la clave activa. Conserva las claves anteriores en PII_ENCRYPTION_KEYS.'

    def handle(self, *args, **options):
        try:
            transform_columns(
                'citas_cita',
                ['curp_ciudadano', 'nombre_ciudadano', 'codigo_postal', 'direccion', 'datos_adicionales'],
                mode='rotate',
                hash_source='curp_ciudadano',
                hash_column='curp_hash',
            )
            transform_columns('citas_bitacoraauditoria', ['descripcion'], mode='rotate')
            transform_columns('ia_conversacionasistente', ['contexto'], mode='rotate')
            transform_columns('ia_mensajeasistente', ['texto', 'metadatos'], mode='rotate')
            transform_columns('ia_solicitudatencion', ['curp', 'nombre', 'motivo'], mode='rotate')
            transform_columns(
                'ia_notificacioninteligente',
                ['curp', 'titulo', 'mensaje'],
                mode='rotate',
                hash_source='curp',
                hash_column='curp_hash',
            )
            transform_columns('ia_alertaurgente', ['titulo', 'detalle'], mode='rotate')
            transform_columns('ia_anomalia', ['descripcion', 'evidencia'], mode='rotate')
        except Exception as exc:
            raise CommandError(
                'La rotación se detuvo sin mostrar datos personales: '
                + exc.__class__.__name__
            ) from exc
        self.stdout.write(self.style.SUCCESS('Datos personales recifrados con la clave activa.'))
