import base64
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from citas.models import Cita, SeccionTramite, Tramite
from citas.servicios.cita import Cita as CitaNegocio
from core_rc.pii_migration import decrypt_citas, encrypt_citas, require_pii_keys
from core_rc.security import blind_index, clear_key_cache, encrypt_text
from ia.models import NotificacionInteligente
from ia.servicios.sincronizar import sincronizar_notificaciones

CURP = 'LOPE800101HDFRNN09'
OTRA_CURP = 'GARC800101MDFRRN08'


class CifradoAesTests(TestCase):
    def tearDown(self):
        clear_key_cache()

    def test_el_ciphertext_no_es_determinista_y_se_descifra(self):
        first = encrypt_text('Ana López')
        second = encrypt_text('Ana López')

        self.assertNotEqual(first, second)
        self.assertTrue(str(first).startswith('enc:v1:'))
        self.assertEqual(decrypt_text(first), 'Ana López')
        self.assertEqual(decrypt_text(second), 'Ana López')

    def test_rechaza_manipulacion_y_clave_incorrecta(self):
        token = encrypt_text('Ana López')
        altered = token[:-1] + ('A' if token[-1] != 'A' else 'B')
        with self.assertRaises(ValueError):
            decrypt_text(altered)

        other = base64.urlsafe_b64encode(b'\x33' * 32).decode('ascii')
        with override_settings(
            PII_ENCRYPTION_KEYS={'v1': other},
            PII_ACTIVE_KEY_VERSION='v1',
            PII_BLIND_INDEX_KEY=base64.urlsafe_b64encode(b'\x44' * 32).decode('ascii'),
        ):
            clear_key_cache()
            with self.assertRaises(ValueError):
                decrypt_text(token)
        clear_key_cache()

    def test_conserva_versiones_y_el_indice_ciego_es_estable(self):
        token = encrypt_text(CURP)
        version_two = base64.urlsafe_b64encode(b'\x55' * 32).decode('ascii')
        current = {
            'v1': base64.urlsafe_b64encode(b'\x11' * 32).decode('ascii'),
            'v2': version_two,
        }
        with override_settings(PII_ENCRYPTION_KEYS=current, PII_ACTIVE_KEY_VERSION='v2'):
            clear_key_cache()
            self.assertEqual(decrypt_text(token), CURP)
            renewed = encrypt_text(CURP)
            self.assertTrue(str(renewed).startswith('enc:v2:'))
        clear_key_cache()

        self.assertEqual(blind_index(CURP), blind_index(' lope800101hdfrnn09 '))
        self.assertNotEqual(blind_index(CURP), blind_index(OTRA_CURP))
        self.assertNotIn(CURP, blind_index(CURP))

    def test_aborta_si_faltan_claves_sin_tocar_datos(self):
        with override_settings(PII_ENCRYPTION_KEYS={}, PII_ACTIVE_KEY_VERSION='', PII_BLIND_INDEX_KEY=''):
            clear_key_cache()
            with self.assertRaises(ImproperlyConfigured):
                require_pii_keys()


class CitasCifradasTests(TestCase):
    def setUp(self):
        section = SeccionTramite.objects.create(nombre='Civil de prueba')
        self.tramite = Tramite.objects.create(
            seccion=section,
            nombre='Acta de prueba',
            costo='10.00',
            duracion_minutos=15,
        )
        self.cita = self._crear(CURP, 'Persona Ejemplo', hour=9)

    def tearDown(self):
        clear_key_cache()

    def _crear(self, curp, nombre, hour):
        return Cita.objects.create(
            tramite=self.tramite,
            nombre_ciudadano=nombre,
            curp_ciudadano=curp,
            codigo_postal='50960',
            direccion='Calle Ejemplo 10',
            fecha=timezone.localdate() + timedelta(days=12),
            hora=f'{hour:02d}:00',
            datos_adicionales={'referencia': 'dato familiar'},
        )

    def _raw(self, cita_id):
        with connection.cursor() as cursor:
            cursor.execute(
                '''
                SELECT curp_ciudadano, nombre_ciudadano, codigo_postal, direccion,
                       datos_adicionales, curp_hash
                FROM citas_cita WHERE id = %s
                ''',
                [cita_id],
            )
            return cursor.fetchone()

    def test_la_base_guarda_ciphertext_y_la_aplicacion_lee_texto_claro(self):
        raw = self._raw(self.cita.id)
        joined = ' '.join(str(value) for value in raw)

        self.assertTrue(all(str(value).startswith('enc:v1:') for value in raw[:5]))
        self.assertNotIn('Persona', joined)
        self.assertNotIn(CURP, joined)
        self.assertNotIn('Calle Ejemplo', joined)
        self.assertEqual(raw[5], blind_index(CURP))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.nombre_ciudadano, 'Persona Ejemplo')
        self.assertEqual(self.cita.datos_adicionales['referencia'], 'dato familiar')

    def test_consulta_unicidad_y_cancelacion_usan_el_indice_ciego(self):
        self.assertIsNotNone(CitaNegocio.obtener_por_folio_curp(self.cita.id, CURP))
        self.assertIsNone(CitaNegocio.obtener_por_folio_curp(self.cita.id, OTRA_CURP))
        self.assertTrue(CitaNegocio.tiene_cita_activa_curp(CURP))

        ok, message = CitaNegocio.crear_desde_portal({
            'tramite_id': self.tramite.id,
            'nombre': 'Otra Persona',
            'curp': CURP,
            'cp': '50960',
            'direccion': 'Calle Ejemplo 11',
            'fecha': (timezone.localdate() + timedelta(days=20)).isoformat(),
            'hora': '11:00',
        })
        self.assertFalse(ok)
        self.assertIn('cita programada', message)

        ok, _message, extra = CitaNegocio.cancelar(self.cita, 'oficial-prueba')
        self.assertTrue(ok)
        self.assertNotIn('Persona', extra['log'])
        self.assertFalse(CitaNegocio.tiene_cita_activa_curp(CURP))

    def test_la_migracion_es_idempotente_y_reversible(self):
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE citas_cita SET direccion = %s WHERE id = %s',
                ['Calle Residual 1', self.cita.id],
            )
        encrypt_citas(None, None)
        encrypt_citas(None, None)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.direccion, 'Calle Residual 1')

        decrypt_citas(None, None)
        with connection.cursor() as cursor:
            cursor.execute('SELECT direccion FROM citas_cita WHERE id = %s', [self.cita.id])
            self.assertEqual(cursor.fetchone()[0], 'Calle Residual 1')
        encrypt_citas(None, None)

    def test_comprobante_y_qr_exigen_token_y_el_pdf_usa_texto_descifrado(self):
        from unittest.mock import patch

        from reportlab.pdfgen.canvas import Canvas

        from citas.comprobante_pdf import generar_comprobante_pdf

        drawn = []
        original = Canvas.drawString

        def spy(pdf_canvas, x, y, text, *args, **kwargs):
            drawn.append(text)
            return original(pdf_canvas, x, y, text, *args, **kwargs)

        with patch.object(Canvas, 'drawString', spy):
            pdf = generar_comprobante_pdf(self.cita).getvalue()
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertIn('Persona Ejemplo', drawn)
        self.assertIn(CURP, drawn)
        image = self.client.get(reverse('imagen_qr_cita', args=[self.cita.id, self.cita.qr_codigo]))
        document = self.client.get(
            reverse('descargar_comprobante_pdf', args=[self.cita.id, self.cita.qr_codigo]),
        )
        denied = self.client.get(reverse('imagen_qr_cita', args=[self.cita.id, 'token-invalido']))

        self.assertEqual(image.status_code, 200)
        self.assertEqual(image['Content-Type'], 'image/png')
        self.assertEqual(document.status_code, 200)
        self.assertEqual(document['Content-Type'], 'application/pdf')
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(self.client.get(f'/citas/qr/{self.cita.id}/').status_code, 404)

    def test_la_sincronizacion_de_ia_cifra_la_curp(self):
        self.cita.fecha = timezone.localdate() + timedelta(days=1)
        self.cita.save()
        sincronizar_notificaciones()
        notice = NotificacionInteligente.objects.get(clave=f'rec-{self.cita.id}')

        self.assertEqual(notice.curp, CURP)
        self.assertEqual(notice.curp_hash, blind_index(CURP))
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT curp, titulo, mensaje FROM ia_notificacioninteligente WHERE id = %s',
                [notice.id],
            )
            stored = ' '.join(cursor.fetchone())
        self.assertNotIn(CURP, stored)
        self.assertTrue(stored.split()[0].startswith('enc:'))

    def test_verificacion_solo_reporta_conteos(self):
        from io import StringIO

        output = StringIO()
        call_command('verificar_cifrado_pii', stdout=output)
        text = output.getvalue()

        self.assertIn('texto_claro=0', text)
        self.assertNotIn(CURP, text)
        self.assertNotIn('Persona', text)
