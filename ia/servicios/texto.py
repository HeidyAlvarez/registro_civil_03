import unicodedata


def normalizar(texto):
    texto = (texto or '').lower().strip()
    descompuesto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in descompuesto if unicodedata.category(c) != 'Mn')


def contiene_alguna(texto, palabras):
    plano = normalizar(texto)
    return any(palabra in plano for palabra in palabras)


PALABRAS_SENSIBLES = ('defunc', 'matrimonio', 'divorcio')


def es_tramite_sensible(nombre):
    return contiene_alguna(nombre, PALABRAS_SENSIBLES)
