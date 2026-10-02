"""Asistente del Registro Civil mediante la API de Grok (xAI)."""

import json

import requests
from django.conf import settings


def _clave():
    for nombre in ('GROQ_API_KEY', 'GROK_API_KEY'):
        valor = str(getattr(settings, nombre, '') or '').strip()
        if valor:
            return valor
    return ''


def clave_configurada():
    return bool(_clave())


def _catalogo(tramites):
    lineas = []
    for tramite in tramites:
        seccion = tramite.seccion.nombre if getattr(tramite, 'seccion_id', None) else 'Sin sección'
        documentos = (tramite.documentos_requeridos or 'Sin documentos registrados en el catálogo').strip()
        lineas.append(
            f'- {tramite.nombre} ({seccion}). Costo configurado: ${tramite.costo}. '
            f'Duración estimada: {tramite.duracion_minutos} minutos. Documentos: {documentos}'
        )
    return '\n'.join(lineas) or '- No hay trámites activos en el catálogo.'


def _instrucciones(tramites, oficina):
    return (
        'Eres el asistente virtual del Registro Civil, Oficialía 03, en Villa Victoria, Estado de México. '
        'Respondes en español, con claridad, solo con la información de esta base de conocimientos. '
        'No inventes costos, documentos ni horarios. Si el dato no está aquí, dilo y ofrece canalizar '
        'al ciudadano con un funcionario.\n\n'
        f'Oficina: {oficina["nombre"]}\n'
        f'Dirección: {oficina["direccion_linea1"]}, {oficina["direccion_linea2"]}\n'
        f'Teléfono: {oficina["telefono"]}\n'
        f'Correo: {oficina["correo"]}\n'
        f'Horario: {oficina["horario_semana"]}. {oficina["horario_fin"]}\n'
        'La cita se agenda en el portal en línea y el trámite se realiza en la oficina.\n\n'
        f'Catálogo vigente:\n{_catalogo(tramites)}\n\n'
        'Responde únicamente con un objeto JSON con estas claves: '
        '"texto" (string), "derivar" (boolean, true solo si hace falta un funcionario) y '
        '"opciones" (lista de objetos con "etiqueta" y "valor", o lista vacía).'
    )


def interpretar_respuesta(contenido):
    bruto = (contenido or '').strip()
    if bruto.startswith('```'):
        bruto = bruto.strip('`')
        if bruto.lower().startswith('json'):
            bruto = bruto[4:]
        bruto = bruto.strip()
    try:
        datos = json.loads(bruto)
    except json.JSONDecodeError:
        inicio = bruto.find('{')
        fin = bruto.rfind('}')
        if inicio == -1 or fin <= inicio:
            return {'texto': contenido or '', 'derivar': False, 'opciones': []}
        try:
            datos = json.loads(bruto[inicio:fin + 1])
        except json.JSONDecodeError:
            return {'texto': contenido or '', 'derivar': False, 'opciones': []}

    opciones = []
    for opcion in datos.get('opciones') or []:
        if isinstance(opcion, dict) and opcion.get('etiqueta') and opcion.get('valor'):
            opciones.append({'etiqueta': str(opcion['etiqueta']), 'valor': str(opcion['valor'])})
    return {
        'texto': str(datos.get('texto') or contenido or '').strip(),
        'derivar': bool(datos.get('derivar')),
        'opciones': opciones[:6],
    }


def _destino():
    clave = _clave()
    url = getattr(settings, 'GROK_API_URL', '') or ''
    modelo = getattr(settings, 'GROK_MODEL', '') or ''
    if clave.startswith('gsk_'):
        if 'groq.com' not in url:
            url = 'https://api.groq.com/openai/v1/chat/completions'
        if not modelo or modelo == 'llama-3.3-70b-versatile':
            modelo = 'openai/gpt-oss-120b'
    else:
        url = url or 'https://api.x.ai/v1/chat/completions'
        modelo = modelo or 'grok-4'
    return url, modelo


def _completar(instrucciones, pregunta, historial, temperature):
    """Llama a Groq o Grok con la clave del entorno. None si no hay respuesta."""
    if not clave_configurada():
        return None

    url, modelo = _destino()
    mensajes = [{'role': 'system', 'content': instrucciones}]
    for mensaje in (historial or [])[-8:]:
        rol = 'assistant' if mensaje.get('rol') == 'asistente' else 'user'
        mensajes.append({'role': rol, 'content': mensaje.get('texto') or ''})
    mensajes.append({'role': 'user', 'content': pregunta})

    try:
        respuesta = requests.post(
            url,
            headers={
                'Authorization': f'Bearer {_clave()}',
                'Content-Type': 'application/json',
            },
            json={
                'model': modelo,
                'messages': mensajes,
                'temperature': temperature,
            },
            timeout=30,
        )
        if respuesta.status_code >= 400:
            detalle = ''
            try:
                detalle = respuesta.json().get('error', {}).get('message', '')
            except ValueError:
                detalle = ''
            return {
                'error_http': True,
                'status': respuesta.status_code,
                'detalle': detalle,
            }
        contenido = respuesta.json()['choices'][0]['message']['content']
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return None

    interpretada = interpretar_respuesta(contenido)
    interpretada['error_http'] = False
    return interpretada


def responder_con_grok(pregunta, historial, tramites, oficina, contexto=None):
    """Consulta la API configurada en GROK_API_KEY. Devuelve None si no responde."""
    resultado = _completar(_instrucciones(tramites, oficina), pregunta, historial, 0.2)
    if resultado is None:
        return None
    if resultado.get('error_http'):
        return {
            'texto': (
                'No pude consultar la API configurada. '
                + (resultado.get('detalle') or f'La API respondió con el código {resultado.get("status")}.')
            ),
            'opciones': [],
            'derivar': False,
            'contexto': dict(contexto or {}),
        }
    return {
        'texto': resultado['texto'],
        'opciones': resultado['opciones'],
        'derivar': resultado['derivar'],
        'contexto': dict(contexto or {}),
    }


def consultar_grok(instrucciones, pregunta, historial):
    """Consulta el modelo para el personal interno. None si no hay una respuesta útil."""
    resultado = _completar(instrucciones, pregunta, historial, 0.1)
    if not resultado or resultado.get('error_http'):
        return None
    return resultado
