from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from ia.models import ConversacionAsistente, MensajeAsistente, SolicitudAtencion
from ia.servicios.grok import interpretar_respuesta
from ia.servicios.analitica import clasificar_nivel
from ia.servicios.asistente import responder
from ia.servicios.texto import es_tramite_sensible, normalizar


class TramiteFalso:
    def __init__(self, id, nombre, costo='350.00', documentos='Identificación oficial\nActa de nacimiento'):
        self.id = id
        self.nombre = nombre
        self.costo = costo
        self.duracion_minutos = 30
        self.documentos_requeridos = documentos
        self.seccion_id = None
        self.activo = True


OFICINA = {
    'nombre': 'Registro Civil — Oficialía 03',
    'horario_semana': 'Lunes a viernes de 9:00 a 17:00',
    'horario_fin': 'Domingos: cerrado',
    'direccion_linea1': 'Calle conocida',
    'direccion_linea2': 'Villa Victoria',
    'telefono': '7260000000',
    'correo': 'rc@example.com',
}


class AsistenteTests(SimpleTestCase):
    def setUp(self):
        self.tramites = [
            TramiteFalso(1, 'Registro de matrimonio', '800.00', 'Identificación oficial\nActa de nacimiento'),
            TramiteFalso(2, 'Copia certificada', '120.00', 'Identificación oficial'),
        ]

    def test_horario_de_atencion(self):
        resultado = responder('¿Cuál es el horario de atención?', {}, self.tramites, OFICINA)
        self.assertIn('9:00', resultado['texto'])
        self.assertFalse(resultado['derivar'])

    def test_costo_de_copia(self):
        resultado = responder('¿Cuánto cuesta una copia certificada?', {}, self.tramites, OFICINA)
        self.assertIn('120.00', resultado['texto'])

    def test_elige_un_solo_tramite_cuando_el_nombre_es_exacto(self):
        tramites = self.tramites + [
            TramiteFalso(3, 'Matrimonio a domicilio'),
            TramiteFalso(4, 'Matrimonio en oficialía (lunes a viernes)'),
        ]
        resultado = responder('Matrimonio en oficialía (lunes a viernes)', {}, tramites, OFICINA)
        self.assertEqual(resultado['contexto']['tramite_id'], 4)
        self.assertNotIn('más de un trámite', resultado['texto'])

    def test_matrimonio_pregunta_edad_antes_de_requisitos(self):
        resultado = responder('¿Qué documentos necesito para registrar un matrimonio?', {}, self.tramites, OFICINA)
        self.assertIn('mayor de edad', resultado['texto'].lower())
        self.assertEqual(resultado['contexto']['esperando'], 'mayor_edad')
        self.assertEqual(resultado['contexto']['tramite_id'], 1)

    def test_respuesta_de_menor_ofrece_funcionario(self):
        contexto = {'esperando': 'mayor_edad', 'tramite_id': 1, 'aspecto': 'documentos'}
        resultado = responder('No, es menor de edad', contexto, self.tramites, OFICINA)
        self.assertIn('menor de edad', resultado['texto'].lower())
        self.assertTrue(resultado['derivar'])

    def test_en_linea(self):
        resultado = responder('¿Qué trámites puedo realizar en línea?', {}, self.tramites, OFICINA)
        self.assertIn('agendar', resultado['texto'].lower())

    def test_falta_documento_deriva(self):
        resultado = responder('¿Qué pasa si me falta un documento?', {}, self.tramites, OFICINA)
        self.assertTrue(resultado['derivar'])
        self.assertIn('funcionario', resultado['texto'].lower())


class GrokTests(SimpleTestCase):
    def test_interpreta_json_de_grok(self):
        datos = interpretar_respuesta(
            '{"texto": "El horario es de 9 a 17.", "derivar": false, "opciones": '
            '[{"etiqueta": "Ver ubicación", "valor": "¿Dónde está la oficina?"}]}'
        )
        self.assertIn('9 a 17', datos['texto'])
        self.assertFalse(datos['derivar'])
        self.assertEqual(datos['opciones'][0]['etiqueta'], 'Ver ubicación')


class AnaliticaTests(SimpleTestCase):
    def test_clasificar_nivel(self):
        self.assertEqual(clasificar_nivel(1, 2, 5), 'baja')
        self.assertEqual(clasificar_nivel(3, 2, 5), 'media')
        self.assertEqual(clasificar_nivel(5, 2, 5), 'alta')

    def test_tramite_sensible(self):
        self.assertTrue(es_tramite_sensible('Registro de defunción'))
        self.assertTrue(es_tramite_sensible('Matrimonio civil'))
        self.assertFalse(es_tramite_sensible('Copia certificada'))

    def test_normalizar(self):
        self.assertEqual(normalizar('Defunción'), 'defuncion')


class AccesoModuloIATests(TestCase):
    def setUp(self):
        usuario = get_user_model()
        self.oficial = usuario.objects.create_user(username='oficial-ia', password='prueba-segura')
        self.admin = usuario.objects.create_user(username='admin-ia', password='prueba-segura')
        self.capturista = usuario.objects.create_user(username='capturista-ia', password='prueba-segura')
        self.usuario_comun = usuario.objects.create_user(username='ciudadano-ia', password='prueba-segura')
        self.oficial.groups.add(Group.objects.create(name='oficial'))
        self.admin.groups.add(Group.objects.create(name='Administrador'))
        self.capturista.groups.add(Group.objects.create(name='Capturista'))

    def test_anonimo_es_redirigido_al_portal_ciudadano(self):
        respuesta = self.client.get(reverse('ia_interno'))

        self.assertRedirects(respuesta, reverse('portal_ciudadano'))

    def test_oficial_y_administrador_pueden_entrar(self):
        for usuario in (self.oficial, self.admin):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                with patch('ia.views.sincronizar_si_hace_falta'):
                    respuesta = self.client.get(reverse('ia_interno'))
                self.assertEqual(respuesta.status_code, 200)
                self.client.logout()

    def test_capturista_y_usuario_comun_no_pueden_entrar(self):
        for usuario in (self.capturista, self.usuario_comun):
            with self.subTest(usuario=usuario.username):
                self.client.force_login(usuario)
                respuesta = self.client.get(reverse('ia_interno'))
                self.assertRedirects(respuesta, reverse('portal_ciudadano'))
                self.client.logout()

    def test_paginas_ciudadanas_no_exponen_enlaces_internos(self):
        rutas = (
            'ia_ciudadano',
            'ia_asistente',
            'ia_dias',
            'ia_sugerencia',
            'ia_notificaciones',
        )
        for ruta in rutas:
            with self.subTest(ruta=ruta):
                respuesta = self.client.get(reverse(ruta))
                self.assertEqual(respuesta.status_code, 200)
                self.assertNotContains(respuesta, reverse('ia_interno'))
                self.assertNotContains(respuesta, '/admin/')


class ConversacionTemporalTests(TestCase):
    RESPUESTA_API = {
        'texto': 'Respuesta temporal de prueba.',
        'opciones': [],
        'derivar': False,
        'contexto': {},
    }

    @patch('ia.views.responder_con_grok', return_value=RESPUESTA_API)
    def test_post_conserva_el_chat_despues_de_redirigir(self, _api):
        respuesta = self.client.post(
            reverse('ia_asistente'),
            {'pregunta': '¿Cuál es el horario?'},
            follow=True,
        )

        self.assertContains(respuesta, '¿Cuál es el horario?')
        self.assertContains(respuesta, 'Respuesta temporal de prueba.')
        self.assertEqual(MensajeAsistente.objects.count(), 2)

    @patch('ia.views.responder_con_grok', return_value=RESPUESTA_API)
    def test_un_nuevo_get_limpia_la_conversacion_anterior(self, _api):
        self.client.post(reverse('ia_asistente'), {'pregunta': 'Mensaje anterior'}, follow=True)
        self.client.get(reverse('ia_asistente'))

        self.assertEqual(MensajeAsistente.objects.count(), 0)
        self.assertEqual(ConversacionAsistente.objects.count(), 1)

    def test_solicitud_permanece_al_limpiar_su_conversacion(self):
        conversacion = ConversacionAsistente.objects.create(clave='chat-que-se-cierra')
        solicitud = SolicitudAtencion.objects.create(
            conversacion=conversacion,
            motivo='Necesita atención de una persona.',
        )
        sesion = self.client.session
        sesion['ia_conversacion'] = conversacion.clave
        sesion.save()

        self.client.get(reverse('ia_ciudadano'))

        solicitud.refresh_from_db()
        self.assertIsNone(solicitud.conversacion)
        self.assertFalse(ConversacionAsistente.objects.filter(pk=conversacion.pk).exists())


class ContratosDeFormulariosTests(SimpleTestCase):
    def test_acciones_de_investigacion_se_conservan(self):
        contenido = (
            __import__('pathlib').Path(__file__).parent
            / 'templates'
            / 'ia'
            / 'anomalia_detalle.html'
        ).read_text(encoding='utf-8')
        for accion in (
            'CONSULTAR_REGISTROS',
            'CONSULTAR_HISTORIAL',
            'MARCAR_REVISADO',
            'CLASIFICAR',
            'SOLICITAR_INVESTIGACION',
            'GENERAR_REPORTE',
        ):
            self.assertIn(f'value="{accion}"', contenido)
