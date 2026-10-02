import base64
import json
import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Imprime claves nuevas de cifrado. No escribe archivos ni las guarda en el repositorio.'

    def handle(self, *args, **options):
        def key():
            return base64.urlsafe_b64encode(os.urandom(32)).decode('ascii')

        payload = {'v1': key()}
        self.stdout.write('PII_ENCRYPTION_KEYS=' + json.dumps(payload, separators=(',', ':')))
        self.stdout.write('PII_ACTIVE_KEY_VERSION=v1')
        self.stdout.write('PII_BLIND_INDEX_KEY=' + key())
        self.stdout.write('Conserva estas claves fuera del repositorio y de los respaldos públicos.')
