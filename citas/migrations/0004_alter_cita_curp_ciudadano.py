# Generated manually — validación CURP con formato oficial

import citas.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('citas', '0003_alter_cita_estado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cita',
            name='curp_ciudadano',
            field=models.CharField(
                max_length=18,
                validators=[citas.validators.validador_curp],
                verbose_name='CURP',
            ),
        ),
    ]
