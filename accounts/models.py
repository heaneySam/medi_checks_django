from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    class UserType(models.TextChoices):
        ADMIN = 'ADMIN', _('Administrator')
        DOCTOR = 'DOCTOR', _('Doctor')
        PHARMACIST = 'PHARMACIST', _('Pharmacist')
        NURSE = 'NURSE', _('Nurse')

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        default=UserType.NURSE,
    )
    department = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'auth_user'
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_user_type_display()})"

    @property
    def is_admin(self):
        return self.user_type == self.UserType.ADMIN

    @property
    def is_doctor(self):
        return self.user_type == self.UserType.DOCTOR

    @property
    def is_pharmacist(self):
        return self.user_type == self.UserType.PHARMACIST

    @property
    def is_nurse(self):
        return self.user_type == self.UserType.NURSE
