# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models

class UsuarioRegistroCivil(AbstractUser):
    # Definición de los Roles como constantes del objeto (POO)
    ADMINISTRADOR = 'ADMIN'
    OFICIAL_PRINCIPAL = 'OFICIAL'
    CAPTURISTA = 'CAPTURISTA'
    
    ROLES_CHOICES = [
        (ADMINISTRADOR, 'Administrador del Sistema'),
        (OFICIAL_PRINCIPAL, 'Oficial Principal'),
        (CAPTURISTA, 'Capturista de Ventanilla'),
    ]
    
    # Atributo personalizado para saber qué rol tiene cada usuario
    rol = models.CharField(
        max_length=15,
        choices=ROLES_CHOICES,
        default=CAPTURISTA,
        help_text="Rol operativo dentro del Registro Civil"
    )

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"


class IntentoAccesoPanel(models.Model):
    """Intentos fallidos de acceso a paneles, separados por usuario e IP."""

    username_normalizado = models.CharField(max_length=300)
    direccion_ip = models.CharField(max_length=45)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ultimo_intento = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Intento de acceso al panel'
        verbose_name_plural = 'Intentos de acceso al panel'
        constraints = [
            models.UniqueConstraint(
                fields=['username_normalizado', 'direccion_ip'],
                name='unico_intento_acceso_usuario_ip',
            ),
        ]

    def __str__(self):
        return f'{self.username_normalizado} @ {self.direccion_ip}'