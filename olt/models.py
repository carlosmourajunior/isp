from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

class OltUsers(models.Model):

    SLOT_CHOICES = (
        1, 2
    )

    slot = models.IntegerField(verbose_name="Slot", validators=[MinValueValidator(1), MaxValueValidator(100)])
    port = models.IntegerField(verbose_name="Porta", validators=[MinValueValidator(1), MaxValueValidator(100)])

    users_connected = models.IntegerField(verbose_name="Usuários Aprovisionados")

    class Meta:
        verbose_name = ("Ocupação da OLT")
        verbose_name_plural = ("Ocupação da OLT")

    def __str__(self):
        return f"1/1/{self.slot}/{self.port}"
