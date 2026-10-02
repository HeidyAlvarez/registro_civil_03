import core_rc.fields
from django.db import migrations, models

import core_rc.pii_migration as pii


class Migration(migrations.Migration):

    dependencies = [
        ('ia', '0001_modulo_ia'),
    ]

    operations = [
        migrations.RunPython(pii.require_pii_keys, migrations.RunPython.noop),
        migrations.AddField(
            model_name='notificacioninteligente',
            name='curp_hash',
            field=models.CharField(blank=True, db_index=True, default='', editable=False, max_length=64),
        ),
        migrations.AlterField(
            model_name='conversacionasistente',
            name='contexto',
            field=core_rc.fields.EncryptedJSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='mensajeasistente',
            name='metadatos',
            field=core_rc.fields.EncryptedJSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='mensajeasistente',
            name='texto',
            field=core_rc.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='solicitudatencion',
            name='curp',
            field=core_rc.fields.EncryptedTextField(blank=True),
        ),
        migrations.AlterField(
            model_name='solicitudatencion',
            name='motivo',
            field=core_rc.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='solicitudatencion',
            name='nombre',
            field=core_rc.fields.EncryptedTextField(blank=True),
        ),
        migrations.AlterField(
            model_name='notificacioninteligente',
            name='curp',
            field=core_rc.fields.EncryptedTextField(blank=True),
        ),
        migrations.AlterField(
            model_name='notificacioninteligente',
            name='mensaje',
            field=core_rc.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='notificacioninteligente',
            name='titulo',
            field=core_rc.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='alertaurgente',
            name='detalle',
            field=core_rc.fields.EncryptedTextField(blank=True),
        ),
        migrations.AlterField(
            model_name='alertaurgente',
            name='titulo',
            field=core_rc.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='anomalia',
            name='descripcion',
            field=core_rc.fields.EncryptedTextField(),
        ),
        migrations.AlterField(
            model_name='anomalia',
            name='evidencia',
            field=core_rc.fields.EncryptedJSONField(blank=True, default=dict),
        ),
        migrations.RunPython(pii.encrypt_ia, pii.decrypt_ia),
    ]
