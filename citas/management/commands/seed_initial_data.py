from django.core.management import call_command
from django.core.management.base import BaseCommand

from autenticacion.admin import sincronizar_rol_y_grupos
from autenticacion.models import UsuarioRegistroCivil
from citas.models import Tramite


class Command(BaseCommand):
    help = 'Carga datos iniciales del proyecto si la base está vacía.'

    def handle(self, *args, **options):
        if Tramite.objects.exists():
            self.stdout.write(self.style.WARNING('La base ya tiene datos; no se volvió a cargar.'))
            return

        call_command('loaddata', 'fixtures/initial_data.json')
        for usuario in UsuarioRegistroCivil.objects.all():
            sincronizar_rol_y_grupos(usuario)

        self.stdout.write(self.style.SUCCESS('Datos iniciales cargados correctamente.'))
