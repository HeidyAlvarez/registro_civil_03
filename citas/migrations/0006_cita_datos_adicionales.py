from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0005_cortecajadiario'),
    ]

    operations = [
        migrations.AddField(
            model_name='cita',
            name='datos_adicionales',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Información específica según el trámite (ej. datos del recién nacido).',
                verbose_name='Datos adicionales del trámite',
            ),
        ),
    ]
