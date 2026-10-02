import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from autenticacion.servicios.login import Login


class BloqueoAccesoPanelTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.password = 'Safe-password-2026'
        self.oficial = user_model.objects.create_user(
            username='oficial-panel',
            password=self.password,
            rol='OFICIAL',
            is_staff=True,
        )
        self.otro = user_model.objects.create_user(
            username='capturista-panel',
            password=self.password,
            rol='CAPTURISTA',
            is_staff=True,
        )
        self.oficial.groups.add(Group.objects.create(name='oficial'))
        self.otro.groups.add(Group.objects.create(name='Capturista'))

    def _api(self, username, password, ip='203.0.113.10'):
        return self.client.post(
            reverse('api_v1_login'),
            data=json.dumps({'username': username, 'password': password}),
            content_type='application/json',
            REMOTE_ADDR=ip,
        )

    def test_mensaje_generico_no_revela_que_credencial_fallo(self):
        usuario_inexistente = self._api('nadie', 'clave-incorrecta')
        contrasena_incorrecta = self._api('oficial-panel', 'clave-incorrecta')

        self.assertEqual(usuario_inexistente.status_code, 400)
        self.assertEqual(contrasena_incorrecta.status_code, 400)
        self.assertEqual(
            usuario_inexistente.json()['error'],
            Login.MENSAJE_CREDENCIALES_INVALIDAS,
        )
        self.assertEqual(
            usuario_inexistente.json(),
            contrasena_incorrecta.json(),
        )

    def test_el_cuarto_fallo_bloquea_durante_quince_minutos(self):
        for _ in range(3):
            response = self._api(' OFICIAL-PANEL ', 'clave-incorrecta')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], Login.MENSAJE_CREDENCIALES_INVALIDAS)

        cuarto = self._api('oficial-panel', 'clave-incorrecta')

        self.assertEqual(cuarto.status_code, 429)
        self.assertEqual(cuarto.json()['error'], Login.MENSAJE_BLOQUEO)
        self.assertNotIn('usuario y/o', cuarto.json()['error'])

    def test_los_intentos_siguen_bloqueados_dentro_de_la_ventana(self):
        for _ in range(4):
            self._api('oficial-panel', 'clave-incorrecta')

        bloqueado = self._api('oficial-panel', self.password)

        self.assertEqual(bloqueado.status_code, 429)
        self.assertEqual(bloqueado.json()['error'], Login.MENSAJE_BLOQUEO)
        session = self.client.get(reverse('api_v1_session')).json()
        self.assertFalse(session['authenticated'])

    def test_el_contador_se_reinicia_tras_un_acceso_exitoso(self):
        for _ in range(3):
            self._api('oficial-panel', 'clave-incorrecta')

        acceso = self._api('oficial-panel', self.password)
        self.assertEqual(acceso.status_code, 200)
        self.client.logout()

        for _ in range(3):
            response = self._api('oficial-panel', 'clave-incorrecta')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['error'], Login.MENSAJE_CREDENCIALES_INVALIDAS)

    def test_el_contador_se_reinicia_cuando_vence_la_ventana(self):
        inicio = timezone.now()
        with patch('autenticacion.servicios.login.timezone.now', return_value=inicio):
            for _ in range(4):
                self._api('oficial-panel', 'clave-incorrecta')

        durante = inicio + timedelta(minutes=10)
        with patch('autenticacion.servicios.login.timezone.now', return_value=durante):
            sigue = self._api('oficial-panel', self.password)
        self.assertEqual(sigue.status_code, 429)
        self.assertEqual(sigue.json()['error'], Login.MENSAJE_BLOQUEO)

        vencido = inicio + timedelta(minutes=15)
        with patch('autenticacion.servicios.login.timezone.now', return_value=vencido):
            response = self._api('oficial-panel', 'clave-incorrecta')
            acceso = self._api('oficial-panel', self.password)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], Login.MENSAJE_CREDENCIALES_INVALIDAS)
        self.assertEqual(acceso.status_code, 200)

    def test_un_usuario_no_bloquea_otra_cuenta_ni_otra_ip(self):
        for _ in range(4):
            self._api('oficial-panel', 'clave-incorrecta', ip='203.0.113.10')

        otra_cuenta = self._api('capturista-panel', self.password, ip='203.0.113.10')
        otra_ip = self._api('oficial-panel', self.password, ip='203.0.113.20')

        self.assertEqual(otra_cuenta.status_code, 200)
        self.assertEqual(otra_ip.status_code, 200)

    def test_admin_y_auth_muestran_el_mismo_bloqueo(self):
        ip = '198.51.100.8'
        for numero in range(1, 5):
            response = self.client.post(
                reverse('admin:login'),
                {'username': 'oficial-panel', 'password': 'clave-incorrecta'},
                REMOTE_ADDR=ip,
            )
            esperado = (
                Login.MENSAJE_BLOQUEO if numero == 4 else Login.MENSAJE_CREDENCIALES_INVALIDAS
            )
            self.assertContains(response, esperado)
            self.assertNotContains(response, 'sensibles a mayúsculas')

        bloqueado = self.client.post(
            reverse('admin:login'),
            {'username': 'oficial-panel', 'password': self.password},
            REMOTE_ADDR=ip,
        )
        self.assertContains(bloqueado, Login.MENSAJE_BLOQUEO)

        auth = self.client.post(
            '/accounts/login/',
            {'username': 'capturista-panel', 'password': 'clave-incorrecta'},
            REMOTE_ADDR='198.51.100.9',
        )
        self.assertContains(auth, Login.MENSAJE_CREDENCIALES_INVALIDAS)
