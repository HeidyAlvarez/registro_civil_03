import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse


class FrontendReactTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.official = user_model.objects.create_user(
            username='official-react',
            password='Safe-password-2026',
            rol='OFICIAL',
        )
        self.capturista = user_model.objects.create_user(
            username='capturista-react',
            password='Safe-password-2026',
            rol='CAPTURISTA',
        )
        self.official.groups.add(Group.objects.create(name='oficial'))
        self.capturista.groups.add(Group.objects.create(name='Capturista'))

    def test_portal_principal_entrega_la_aplicacion_react(self):
        response = self.client.get(reverse('portal_ciudadano'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="root"')
        self.assertContains(response, 'frontend/assets/app.js')

    def test_sesion_anonima_no_expone_permisos(self):
        response = self.client.get(reverse('api_v1_session'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['authenticated'])
        self.assertFalse(response.json()['permissions']['internal_ai'])

    def test_login_json_crea_sesion_para_personal(self):
        response = self.client.post(
            reverse('api_v1_login'),
            data=json.dumps({'username': 'official-react', 'password': 'Safe-password-2026'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        session = self.client.get(reverse('api_v1_session')).json()
        self.assertTrue(session['authenticated'])
        self.assertTrue(session['permissions']['internal_ai'])

    def test_capturista_no_recibe_acceso_a_ia_interna(self):
        self.client.force_login(self.capturista)

        session = self.client.get(reverse('api_v1_session')).json()

        self.assertTrue(session['permissions']['staff'])
        self.assertFalse(session['permissions']['internal_ai'])

    def test_api_interna_rechaza_usuario_anonimo(self):
        response = self.client.get(reverse('ia_api_internal_summary'))

        self.assertEqual(response.status_code, 401)
