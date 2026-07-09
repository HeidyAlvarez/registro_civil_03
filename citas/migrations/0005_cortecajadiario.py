from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('citas', '0004_alter_cita_curp_ciudadano'),
    ]

    operations = [
        migrations.CreateModel(
            name='CorteCajaDiario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fecha', models.DateField(unique=True, verbose_name='Fecha del corte')),
                ('total_recaudado', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('desglose_tramites', models.JSONField(default=dict, verbose_name='Desglose por trámite')),
                ('cantidad_pagos', models.PositiveIntegerField(default=0)),
                ('cerrado_el', models.DateTimeField(auto_now_add=True)),
                ('cerrado_por', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Corte de Caja Diario',
                'verbose_name_plural': 'Cortes de Caja Diarios',
                'ordering': ['-fecha'],
            },
        ),
    ]
