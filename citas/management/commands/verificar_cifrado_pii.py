from django.core.management.base import BaseCommand, CommandError

from core_rc.pii_migration import count_column

COLUMNAS = (
    ('citas_cita', ('curp_ciudadano', 'nombre_ciudadano', 'codigo_postal', 'direccion', 'datos_adicionales')),
    ('citas_bitacoraauditoria', ('descripcion',)),
    ('ia_conversacionasistente', ('contexto',)),
    ('ia_mensajeasistente', ('texto', 'metadatos')),
    ('ia_solicitudatencion', ('curp', 'nombre', 'motivo')),
    ('ia_notificacioninteligente', ('curp', 'titulo', 'mensaje')),
    ('ia_alertaurgente', ('titulo', 'detalle')),
    ('ia_anomalia', ('descripcion', 'evidencia')),
)


class Command(BaseCommand):
    help = 'Reporta conteos de cifrado. Nunca imprime datos personales.'

    def handle(self, *args, **options):
        plaintext = 0
        for table, columns in COLUMNAS:
            for column in columns:
                counts = count_column(table, column)
                plaintext += counts['texto_claro']
                self.stdout.write(
                    f"{table}.{column}: cifrados={counts['cifrados']} "
                    f"texto_claro={counts['texto_claro']} vacios={counts['vacios']}"
                )
        if plaintext:
            raise CommandError('Hay datos personales en texto claro. No se mostró ningún valor.')
        self.stdout.write(self.style.SUCCESS('No hay datos personales en texto claro.'))
