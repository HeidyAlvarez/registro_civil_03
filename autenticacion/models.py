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