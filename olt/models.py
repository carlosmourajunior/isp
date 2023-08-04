from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator


class OltUsers(models.Model):

    SLOT_CHOICES = (
        1, 2
    )

    slot = models.IntegerField(verbose_name="Slot", validators=[MinValueValidator(1), MaxValueValidator(2)])
    port = models.IntegerField(verbose_name="Porta", validators=[MinValueValidator(1), MaxValueValidator(16)])

    users_connected = models.IntegerField(verbose_name="Usuários Aprovisionados")
    last_updated = models.DateTimeField(verbose_name="Última Atualização")

    class Meta:
        verbose_name = ("Porta")
        verbose_name_plural = ("Portas")

    def __str__(self):
        return f"1/1/{self.slot}/{self.port}"

class ONU(models.Model):
    
    pon = models.CharField(verbose_name="PON", max_length=20)
    position = models.IntegerField(verbose_name="Posição", validators=[MinValueValidator(1), MaxValueValidator(128)])
    mac = models.CharField(verbose_name="MAC", max_length=200)
    serial = models.CharField(verbose_name="Serial", max_length=30)
    oper_state = models.CharField(verbose_name="Status", max_length=30)
    pppoe = models.CharField(verbose_name="PPPoE", max_length=200)
    descricao = models.CharField(verbose_name="Descrição", max_length=300)

    class Meta:
        verbose_name = "ONU"
        verbose_name_plural = ("ONUs")
    
    def __str__(self) -> str:
        return f"{ self.serial }"
        

class PlacaOnu(models.Model):

    chassi = models.CharField(verbose_name="Chassi", max_length=20, default="1/1/1")
    position = models.IntegerField(verbose_name="Posição do Slot", validators=[MinValueValidator(1), MaxValueValidator(2)])

    class Meta:
        verbose_name = "Placa"
        verbose_name_plural = ("Placas")
    
    def __str__(self) -> str:
        return f"{self.chassi}/{self.position}"
