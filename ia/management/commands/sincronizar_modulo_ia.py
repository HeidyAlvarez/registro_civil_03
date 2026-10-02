from django.core.management.base import BaseCommand

from ia.servicios.sincronizar import sincronizar


class Command(BaseCommand):
    help = 'Actualiza notificaciones, casos urgentes, anomalías y propuestas del módulo de IA.'

    def handle(self, *args, **options):
        sincronizar()
        self.stdout.write(self.style.SUCCESS('Módulo de IA sincronizado.'))
