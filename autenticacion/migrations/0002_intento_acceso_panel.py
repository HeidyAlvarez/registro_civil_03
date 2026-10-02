from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autenticacion', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IntentoAccesoPanel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username_normalizado', models.CharField(max_length=300)),
                ('direccion_ip', models.CharField(max_length=45)),
                ('intentos_fallidos', models.PositiveSmallIntegerField(default=0)),
                ('bloqueado_hasta', models.DateTimeField(blank=True, null=True)),
                ('ultimo_intento', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'Intento de acceso al panel',
                'verbose_name_plural': 'Intentos de acceso al panel',
                'constraints': [
                    models.UniqueConstraint(
                        fields=('username_normalizado', 'direccion_ip'),
                        name='unico_intento_acceso_usuario_ip',
                    ),
                ],
            },
        ),
    ]
