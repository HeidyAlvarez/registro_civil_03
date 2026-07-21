"""Generación del comprobante de cita en PDF (datos primero, QR al final)."""
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from .office_info import OFICINA_REGISTRO_CIVIL

MESES = (
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
)


def _fecha_legible(fecha):
    return f'{fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}'


def _hora_legible(hora):
    return hora.strftime('%H:%M') if hora else ''


def _dibujar_fila(c, x_label, x_val, y, etiqueta, valor, ancho_valor):
    c.setFont('Helvetica-Bold', 10)
    c.drawString(x_label, y, etiqueta)
    c.setFont('Helvetica', 10)
    texto = str(valor or '—')
    lineas = []
    palabras = texto.split()
    linea = ''
    for palabra in palabras:
        prueba = (linea + ' ' + palabra).strip()
        if c.stringWidth(prueba, 'Helvetica', 10) <= ancho_valor:
            linea = prueba
        else:
            if linea:
                lineas.append(linea)
            linea = palabra
    if linea:
        lineas.append(linea)
    if not lineas:
        lineas = ['—']
    for i, ln in enumerate(lineas):
        c.drawString(x_val, y - (i * 12), ln)
    return y - max(16, len(lineas) * 12)


def generar_comprobante_pdf(cita):
    buffer = io.BytesIO()
    ancho, alto = letter
    margen = 18 * mm
    c = canvas.Canvas(buffer, pagesize=letter)
    y = alto - margen

    oficina = OFICINA_REGISTRO_CIVIL
    tramite = cita.tramite

    c.setFillColorRGB(0.06, 0.36, 0.24)
    c.setFont('Helvetica-Bold', 16)
    c.drawString(margen, y, 'Comprobante de cita')
    y -= 14

    c.setFillColorRGB(0.35, 0.35, 0.35)
    c.setFont('Helvetica', 10)
    c.drawString(margen, y, f'{oficina["nombre"]} · {oficina["municipio"]}, {oficina["estado"]}')
    y -= 18

    c.setFillColorRGB(0, 0, 0)
    c.setFont('Helvetica-Bold', 12)
    c.drawString(margen, y, f'Folio #{cita.id}')
    y -= 20

    x_label = margen
    x_val = margen + 42 * mm
    ancho_val = ancho - x_val - margen

    filas = [
        ('Trámite:', f'{tramite.nombre} ({tramite.duracion_minutos} min)'),
        ('Ciudadano:', cita.nombre_ciudadano),
        ('CURP:', cita.curp_ciudadano),
        ('Domicilio:', cita.direccion),
        ('C.P.:', cita.codigo_postal),
        ('Fecha:', _fecha_legible(cita.fecha)),
        ('Hora:', _hora_legible(cita.hora)),
        ('Costo a pagar:', f'${tramite.costo:,.2f} MXN'),
    ]

    for etiqueta, valor in filas:
        y = _dibujar_fila(c, x_label, x_val, y, etiqueta, valor, ancho_val)

    datos = cita.datos_adicionales or {}
    if datos.get('tipo_tramite') == 'registro_nacimiento':
        y -= 8
        c.setFont('Helvetica-Bold', 11)
        c.drawString(x_label, y, 'Datos del recién nacido')
        y -= 16
        c.setFont('Helvetica', 10)
        filas_rn = [
            ('Tipo de registro:', datos.get('tipo_registro_etiqueta', '—')),
            ('Nombre:', datos.get('nombre_completo', '—')),
            ('Sexo:', 'Hombre' if datos.get('sexo') == 'H' else 'Mujer'),
            ('Fecha de nacimiento:', _fecha_legible(
                datetime.strptime(datos['fecha_nacimiento'], '%Y-%m-%d').date()
            ) if datos.get('fecha_nacimiento') else '—'),
            ('Hora de nacimiento:', datos.get('hora_nacimiento') or '—'),
            ('Lugar:', f'{datos.get("lugar_tipo_etiqueta", "")} — {datos.get("lugar_nombre", "")}'.strip(' —')),
            ('Municipio:', datos.get('municipio_nacimiento', '—')),
        ]
        for etiqueta, valor in filas_rn:
            y = _dibujar_fila(c, x_label, x_val, y, etiqueta, valor, ancho_val)

    docs = []
    if tramite.documentos_requeridos:
        docs = [d.strip() for d in tramite.documentos_requeridos.replace(',', '\n').split('\n') if d.strip()]

    if docs:
        y -= 6
        c.setFont('Helvetica-Bold', 10)
        c.drawString(x_label, y, 'Documentos requeridos:')
        y -= 14
        c.setFont('Helvetica', 9)
        for doc in docs:
            for ln in _partir_texto(c, '• ' + doc, ancho - margen * 2, 'Helvetica', 9):
                c.drawString(x_label + 4, y, ln)
                y -= 11
            y -= 2

    y -= 10
    c.setFont('Helvetica-Bold', 11)
    c.drawString(x_label, y, 'Código QR')
    y -= 14
    c.setFont('Helvetica', 9)
    c.drawString(x_label, y, 'Preséntalo en ventanilla el día de tu cita.')
    y -= 8

    qr_size = 50 * mm
    if cita.codigo_qr and cita.codigo_qr.name:
        try:
            c.drawImage(
                ImageReader(cita.codigo_qr.path),
                (ancho - qr_size) / 2,
                y - qr_size,
                width=qr_size,
                height=qr_size,
                preserveAspectRatio=True,
                mask='auto',
            )
            y -= qr_size + 12
        except Exception:
            c.setFont('Helvetica-Oblique', 9)
            c.drawString(x_label, y - 10, '(QR no disponible en este momento)')
            y -= 24
    else:
        y -= 10

    c.setFillColorRGB(0.45, 0.45, 0.45)
    c.setFont('Helvetica-Oblique', 8)
    notas = [
        'Preséntate 10 minutos antes con identificación oficial y documentos requeridos.',
        'El pago se realiza en efectivo en ventanilla de caja.',
    ]
    for nota in notas:
        for ln in _partir_texto(c, nota, ancho - margen * 2, 'Helvetica-Oblique', 8):
            c.drawString(margen, y, ln)
            y -= 10

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def _partir_texto(c, texto, ancho_max, fuente, tam):
    palabras = texto.split()
    lineas = []
    linea = ''
    for palabra in palabras:
        prueba = (linea + ' ' + palabra).strip()
        if c.stringWidth(prueba, fuente, tam) <= ancho_max:
            linea = prueba
        else:
            if linea:
                lineas.append(linea)
            linea = palabra
    if linea:
        lineas.append(linea)
    return lineas or ['']
