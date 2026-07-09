# Registro Civil 03

Sistema web para gestión de citas del Registro Civil (Oficialía 03), desarrollado con Django.

## Funcionalidades

- Portal ciudadano para agendar citas sin cuenta
- Validación de asistencia por código QR
- Paneles por rol: Administrador, Oficial y Capturista
- Catálogo de trámites, horarios y bitácora de auditoría
- Caja simulada con corte diario e historial financiero

## Requisitos

- Python 3.11+
- pip

## Instalación

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Estructura

- `citas/` — aplicación principal Django
- `autenticacion/` — usuarios y roles
- `mockups/` — maquetación estática de interfaces
- `core_rc/` — configuración del proyecto

## Despliegue en Render

El archivo `render.yaml` crea automáticamente:

- Base de datos PostgreSQL (`registro-civil-db`)
- Servicio web Django (`registro-civil-03`)

En [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint** → conecta el repositorio de GitHub y aplica el blueprint.

El build ejecuta migraciones y carga `fixtures/initial_data.json` (usuarios, trámites y citas de desarrollo).
