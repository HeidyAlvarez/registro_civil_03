"""Asistente del Registro Civil sobre la base de conocimientos institucional."""

from ia.servicios.texto import contiene_alguna, normalizar

ALIAS = (
    ('matrimonio', ('matrimonio', 'casar', 'casarme', 'boda', 'espos')),
    ('nacimiento', ('nacimiento', 'recien nacido', 'bebe', 'bebe', 'nacer')),
    ('defuncion', ('defuncion', 'fallec', 'defun')),
    ('divorcio', ('divorcio', 'divorciar')),
    ('copia', ('copia certificada', 'copia', 'certificada')),
)

RAMA_EDAD = ('matrimonio', 'nacimiento', 'divorcio')


def _alias_en_texto(texto, claves):
    return any(clave in texto for clave in claves)


def buscar_tramites(texto, tramites):
    plano = normalizar(texto)
    exactos = []
    por_alias = []
    vistos = set()
    for tramite in tramites:
        nombre = normalizar(tramite.nombre)
        seccion = normalizar(tramite.seccion.nombre) if getattr(tramite, 'seccion_id', None) else ''
        if nombre and nombre in plano and tramite.id not in vistos:
            vistos.add(tramite.id)
            exactos.append(tramite)
            continue
        if seccion and len(seccion) > 3 and seccion in plano and tramite.id not in vistos:
            vistos.add(tramite.id)
            exactos.append(tramite)
            continue
        for clave, alias in ALIAS:
            if (clave in nombre or clave in seccion) and _alias_en_texto(plano, alias):
                if tramite.id not in vistos:
                    vistos.add(tramite.id)
                    por_alias.append(tramite)
                break
    return exactos or por_alias


def _tramite_por_id(tramites, tramite_id):
    for tramite in tramites:
        if tramite.id == tramite_id:
            return tramite
    return None


def _costo(tramite):
    try:
        return f'${tramite.costo:,.2f}'
    except (TypeError, ValueError):
        return f'${tramite.costo}'


def _documentos(tramite):
    raw = (tramite.documentos_requeridos or '').strip()
    if not raw:
        return 'El catálogo no tiene documentos registrados para este trámite. Un funcionario puede confirmarlos.'
    partes = []
    for linea in raw.replace(',', '\n').splitlines():
        limpia = linea.strip(' -•\t')
        if limpia:
            partes.append(f'• {limpia}')
    return '\n'.join(partes)


def _requiere_edad(tramite):
    return contiene_alguna(tramite.nombre, RAMA_EDAD)


def _nota_edad(tramite, mayor_edad):
    if mayor_edad is None or not _requiere_edad(tramite):
        return ''
    if mayor_edad:
        return '\n\nLa orientación corresponde a una persona mayor de edad.'
    return (
        '\n\nIndicaste que la persona es menor de edad. Además de los requisitos del catálogo, '
        'normalmente debe acudir quien ejerce la patria potestad o la tutela, con identificación. '
        'Ese supuesto lo confirma un funcionario.'
    )


def _ficha(tramite, aspecto, oficina, mayor_edad):
    costo = _costo(tramite)
    docs = _documentos(tramite)
    duracion = f'{tramite.duracion_minutos} minutos'
    nota = _nota_edad(tramite, mayor_edad)
    bloques = {
        'costo': f'El costo configurado de «{tramite.nombre}» es {costo}, según el tabulador del catálogo.',
        'documentos': f'Documentos registrados para «{tramite.nombre}»:\n{docs}',
        'horario': (
            f'Horario de atención de {oficina["nombre"]}:\n'
            f'• {oficina["horario_semana"]}\n'
            f'• {oficina["horario_fin"]}'
        ),
        'oficina': (
            f'Puedes realizar «{tramite.nombre}» en {oficina["nombre"]}.\n'
            f'{oficina["direccion_linea1"]}\n{oficina["direccion_linea2"]}\n'
            f'Teléfono: {oficina["telefono"]}'
        ),
        'tiempo': f'El tiempo estimado configurado para «{tramite.nombre}» es de {duracion}.',
        'cita': (
            f'Sí. «{tramite.nombre}» se atiende con cita. '
            'Puedes agendarla en el portal, en la sección Agendar cita.'
        ),
        'pasos': (
            f'Guía para «{tramite.nombre}»:\n'
            '1. Revisar requisitos y costo.\n'
            '2. Confirmar que acudirás a la Oficialía 03.\n'
            '3. Elegir fecha y un horario de menor demanda.\n'
            '4. Confirmar la cita y guardar el comprobante con QR.'
        ),
    }
    if aspecto == 'todo':
        return (
            f'«{tramite.nombre}»\n'
            f'• Costo configurado: {costo}\n'
            f'• Duración estimada: {duracion}\n'
            f'• Cita: sí, se agenda en línea y se realiza en la oficina.\n'
            f'• Documentos:\n{docs}\n'
            f'• Horario: {oficina["horario_semana"]}'
            f'{nota}'
        )
    return bloques.get(aspecto, bloques['pasos']) + nota


def _aspecto(texto):
    if contiene_alguna(texto, ('costo', 'cuesta', 'precio', 'cuanto vale', 'cuanto cuesta', 'tabulador')):
        return 'costo'
    if contiene_alguna(texto, ('documento', 'requisito', 'llevar', 'papel', 'falta un documento', 'me falta', 'necesito', 'que necesito')):
        return 'documentos'
    if contiene_alguna(texto, ('horario de atencion', 'horario', 'a que hora', 'que hora')):
        return 'horario'
    if contiene_alguna(texto, ('donde', 'ubicacion', 'direccion', 'oficina', 'mapa')):
        return 'oficina'
    if contiene_alguna(texto, ('cuanto tarda', 'tiempo', 'duracion', 'demora')):
        return 'tiempo'
    if contiene_alguna(texto, ('cita', 'agendar', 'sacar cita')):
        return 'cita'
    if contiene_alguna(texto, ('paso', 'guia', 'como hago', 'procedimiento')):
        return 'pasos'
    return 'todo'


def _respuesta_general(texto, oficina, tramites):
    if contiene_alguna(texto, ('sugerencia de horario', 'menor demanda', 'horario sugerido')):
        return (
            'En Sugerencia de horario elige el trámite y la fecha. '
            'Cada hora se marca en verde, amarillo o rojo según la demanda histórica y las citas ya agendadas, '
            'con una explicación de por qué se recomienda.'
        )
    if contiene_alguna(texto, ('en linea', 'internet', 'desde casa', 'sin ir')):
        nombres = ', '.join(t.nombre for t in tramites[:8]) or 'los trámites activos del catálogo'
        return (
            'En línea puedes agendar, consultar y cancelar una cita. '
            'El trámite se realiza en la oficina, con los documentos requeridos.\n\n'
            f'Trámites que puedes agendar: {nombres}.'
        )
    if contiene_alguna(texto, ('horario', 'a que hora abren', 'atencion')):
        return (
            f'Horario de {oficina["nombre"]}:\n'
            f'• {oficina["horario_semana"]}\n'
            f'• {oficina["horario_fin"]}\n\n'
            'Las citas se ofrecen dentro de ese horario, según la disponibilidad del calendario.'
        )
    if contiene_alguna(texto, ('donde', 'ubicacion', 'direccion', 'oficina')):
        return (
            f'{oficina["nombre"]}\n'
            f'{oficina["direccion_linea1"]}\n{oficina["direccion_linea2"]}\n'
            f'Teléfono: {oficina["telefono"]}\nCorreo: {oficina["correo"]}'
        )
    if contiene_alguna(texto, ('falta un documento', 'me falta', 'no tengo un documento')):
        return (
            'Si falta un documento, el trámite puede no iniciarse ese día. '
            'Revisa la lista del catálogo antes de acudir. '
            'Si el documento tiene una excepción, un funcionario debe revisarlo.\n\n'
            'Esta situación puede requerir revisión por parte de un funcionario. ¿Deseas solicitar atención?'
        )
    if contiene_alguna(texto, ('cita', 'agendar')):
        return (
            'Sí, la atención es con cita. En el portal eliges el trámite, tus datos, la fecha y la hora. '
            'Al confirmar recibes un comprobante con código QR. '
            'También puedo sugerirte horarios con menor demanda.'
        )
    return None


def _opciones_tramites(tramites):
    return [{'etiqueta': t.nombre, 'valor': t.nombre} for t in tramites[:8]]


def responder(pregunta, contexto, tramites, oficina):
    """Devuelve texto, opciones, si ofrece derivación y el contexto actualizado."""
    contexto = dict(contexto or {})
    texto = normalizar(pregunta)
    derivar = False
    opciones = []

    if not texto or contiene_alguna(texto, ('hola', 'buenos dias', 'buenas tardes', 'ayuda')):
        return {
            'texto': (
                'Soy el asistente del Registro Civil. Puedo orientarte sobre requisitos, '
                'documentos, costos configurados, horarios, oficina, pasos y si necesitas cita. '
                'Escribe tu pregunta con tus propias palabras.'
            ),
            'opciones': [
                {'etiqueta': 'Registrar un matrimonio', 'valor': '¿Qué necesito para registrar un matrimonio?'},
                {'etiqueta': 'Costo de copia certificada', 'valor': '¿Cuánto cuesta una copia certificada?'},
                {'etiqueta': 'Horario de atención', 'valor': '¿Cuál es el horario de atención?'},
                {'etiqueta': 'Trámites en línea', 'valor': '¿Qué trámites puedo realizar en línea?'},
            ],
            'derivar': False,
            'contexto': contexto,
        }

    if contexto.get('esperando') == 'mayor_edad':
        tramite = _tramite_por_id(tramites, contexto.get('tramite_id'))
        if contiene_alguna(texto, ('no', 'menor')) and not contiene_alguna(texto, ('mayor',)):
            contexto['mayor_edad'] = False
        elif contiene_alguna(texto, ('si', 'mayor')):
            contexto['mayor_edad'] = True
        else:
            return {
                'texto': 'Para mostrarte los requisitos correspondientes, indica si la persona es mayor de edad.',
                'opciones': [
                    {'etiqueta': 'Sí, mayor de edad', 'valor': 'Sí, es mayor de edad'},
                    {'etiqueta': 'No, es menor de edad', 'valor': 'No, es menor de edad'},
                ],
                'derivar': False,
                'contexto': contexto,
            }
        contexto['esperando'] = None
        if tramite:
            return {
                'texto': _ficha(tramite, contexto.get('aspecto') or 'documentos', oficina, contexto.get('mayor_edad')),
                'opciones': [],
                'derivar': contexto.get('mayor_edad') is False,
                'contexto': contexto,
            }

    if contiene_alguna(texto, ('funcionario', 'persona real', 'no entiendes', 'hablar con alguien', 'solicitar atencion')):
        derivar = True
        return {
            'texto': (
                'Esta situación requiere revisión por parte de un funcionario. '
                '¿Deseas solicitar atención?'
            ),
            'opciones': [],
            'derivar': True,
            'contexto': contexto,
        }

    coincidencias_tempranas = buscar_tramites(pregunta, tramites)
    if len(coincidencias_tempranas) == 1:
        contexto['tramite_id'] = coincidencias_tempranas[0].id
        contexto['esperando'] = None

    if contexto.get('guia_paso'):
        if contiene_alguna(texto, ('cancelar guia', 'salir')):
            contexto['guia_paso'] = 0
        elif contiene_alguna(texto, ('siguiente', 'continuar', 'listo', 'ya')):
            contexto['guia_paso'] = min(int(contexto['guia_paso']) + 1, 4)

    if contiene_alguna(texto, ('guia paso', 'acompaname', 'paso a paso')) or contexto.get('guia_paso'):
        if not contexto.get('guia_paso'):
            contexto['guia_paso'] = 1
        paso = int(contexto['guia_paso'])
        tramite = _tramite_por_id(tramites, contexto.get('tramite_id'))
        if paso == 1 and not tramite:
            opciones = _opciones_tramites(tramites)
            return {
                'texto': 'Selecciona el trámite. Después revisaremos requisitos, oficina, fecha y confirmación.',
                'opciones': opciones,
                'derivar': False,
                'contexto': contexto,
            }
        if tramite and paso <= 2:
            contexto['guia_paso'] = 2
            return {
                'texto': 'Revisa los requisitos:\n' + _ficha(tramite, 'documentos', oficina, contexto.get('mayor_edad')) + '\n\nCuando termines, escribe «siguiente».',
                'opciones': [{'etiqueta': 'Siguiente', 'valor': 'siguiente'}],
                'derivar': False,
                'contexto': contexto,
            }
        if paso == 3 or (tramite and paso == 2 and contiene_alguna(texto, ('siguiente',))):
            contexto['guia_paso'] = 3
            return {
                'texto': _ficha(tramite, 'oficina', oficina, None) + '\n\nSiguiente: elige fecha y hora.',
                'opciones': [{'etiqueta': 'Siguiente', 'valor': 'siguiente'}],
                'derivar': False,
                'contexto': contexto,
            }
        if paso >= 4:
            contexto['guia_paso'] = 4
            return {
                'texto': (
                    'Elige la fecha en el portal y, si quieres, usa Sugerencia de horario '
                    'para ver la demanda estimada de cada hora. Al confirmar, guarda el comprobante con QR.'
                ),
                'opciones': [{'etiqueta': 'Ver horarios sugeridos', 'valor': 'quiero una sugerencia de horario'}],
                'derivar': False,
                'contexto': contexto,
            }

    coincidencias = buscar_tramites(pregunta, tramites)
    aspecto_mensaje = _aspecto(texto)
    if aspecto_mensaje != 'todo':
        contexto['aspecto'] = aspecto_mensaje
    if len(coincidencias) > 1 and not contexto.get('tramite_id'):
        contexto['esperando'] = 'elegir_tramite'
        return {
            'texto': 'Encontré más de un trámite relacionado. ¿Cuál necesitas?',
            'opciones': _opciones_tramites(coincidencias),
            'derivar': False,
            'contexto': contexto,
        }
    if len(coincidencias) == 1:
        contexto['tramite_id'] = coincidencias[0].id
        contexto['esperando'] = None

    if contiene_alguna(texto, ('sugerencia de horario', 'horarios sugeridos')):
        return {
            'texto': _respuesta_general(texto, oficina, tramites),
            'opciones': [],
            'derivar': False,
            'contexto': contexto,
        }

    tramite = _tramite_por_id(tramites, contexto.get('tramite_id'))
    aspecto = _aspecto(texto)
    if aspecto == 'todo':
        aspecto = contexto.get('aspecto') or 'todo'
    else:
        contexto['aspecto'] = aspecto

    if tramite and aspecto == 'documentos' and _requiere_edad(tramite) and contexto.get('mayor_edad') is None:
        contexto['esperando'] = 'mayor_edad'
        return {
            'texto': (
                f'Para «{tramite.nombre}» puedo afinar los requisitos.\n'
                '¿El trámite corresponde a una persona mayor de edad?'
            ),
            'opciones': [
                {'etiqueta': 'Sí, mayor de edad', 'valor': 'Sí, es mayor de edad'},
                {'etiqueta': 'No, es menor de edad', 'valor': 'No, es menor de edad'},
            ],
            'derivar': False,
            'contexto': contexto,
        }

    if tramite and (coincidencias or aspecto != 'todo' or contexto.get('tramite_id')):
        if coincidencias or aspecto != 'todo':
            texto_resp = _ficha(tramite, aspecto if coincidencias or aspecto != 'todo' else 'todo', oficina, contexto.get('mayor_edad'))
            if aspecto == 'documentos' and contiene_alguna(texto, ('falta',)):
                texto_resp += (
                    '\n\nSi te falta alguno, no completes el trámite hasta tenerlo o hasta que un funcionario revise la excepción.'
                )
                derivar = True
            return {'texto': texto_resp, 'opciones': [], 'derivar': derivar, 'contexto': contexto}

    general = _respuesta_general(texto, oficina, tramites)
    if general:
        derivar = contiene_alguna(texto, ('falta un documento', 'me falta'))
        return {'texto': general, 'opciones': [], 'derivar': derivar, 'contexto': contexto}

    if contiene_alguna(texto, ('pregunta frecuente', 'dudas', 'frecuente')):
        return {
            'texto': (
                'Preguntas frecuentes:\n'
                '• La cita se agenda en el portal y se presenta en la Oficialía 03.\n'
                '• El costo y los documentos salen del catálogo vigente.\n'
                '• Si falta un documento, el funcionario debe revisar el caso.\n'
                '• Puedes consultar o cancelar con folio y CURP.'
            ),
            'opciones': [],
            'derivar': False,
            'contexto': contexto,
        }

    listado = '\n'.join(f'• {t.nombre}' for t in tramites[:12]) or '• Aún no hay trámites activos.'
    return {
        'texto': (
            'No encontré una respuesta cerrada en la base de conocimientos del Registro Civil. '
            'Puedes preguntarme por un trámite del catálogo, su costo, documentos, horario o si requiere cita.\n\n'
            f'Trámites activos:\n{listado}\n\n'
            'Si tu caso no está en el catálogo, puedo canalizarte con un funcionario.'
        ),
        'opciones': [],
        'derivar': True,
        'contexto': contexto,
    }
