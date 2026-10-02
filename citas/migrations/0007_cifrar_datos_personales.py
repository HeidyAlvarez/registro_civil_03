import citas.validators
import core_rc.fields
import django.core.validators
from django.db import migrations, models

import core_rc.pii_migration as pii


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0006_cita_datos_adicionales'),
    ]

    operations = [
        migrations.RunPython(pii.require_pii_keys, migrations.RunPython.noop),
        migrations.AddField(
            model_name='cita',
            name='curp_hash',
            field=models.CharField(blank=True, db_index=True, default='', editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name='cita',
            name='codigo_postal',
            field=core_rc.fields.EncryptedTextField(
                validators=[
                    django.core.validators.RegexValidator(
                        message='El Código Postal debe ser de exactamente 5 números (ej. 50900).',
                        regex='^[0-9]{5}$',
                    ),
                ],
                verbose_name='Código Postal',
            ),
        ),
        migrations.AlterField(
            model_name='cita',
            name='curp_ciudadano',
            field=core_rc.fields.EncryptedTextField(
                validators=[citas.validators.validador_curp],
                verbose_name='CURP',
            ),
        ),
        migrations.AlterField(
            model_name='cita',
            name='datos_adicionales',
            field=core_rc.fields.EncryptedJSONField(
                blank=True,
                default=dict,
                help_text='Información específica según el trámite (ej. datos del recién nacido).',
                verbose_name='Datos adicionales del trámite',
            ),
        ),
        migrations.AlterField(
            model_name='cita',
            name='direccion',
            field=core_rc.fields.EncryptedTextField(verbose_name='Dirección Completa'),
        ),
        migrations.AlterField(
            model_name='cita',
            name='nombre_ciudadano',
            field=core_rc.fields.EncryptedTextField(verbose_name='Nombre Completo'),
        ),
        migrations.AlterField(
            model_name='bitacoraauditoria',
            name='descripcion',
            field=core_rc.fields.EncryptedTextField(verbose_name='Descripción Detallada del Cambio'),
        ),
        migrations.RunPython(pii.encrypt_citas, pii.decrypt_citas),
    ]
