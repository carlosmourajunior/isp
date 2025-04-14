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
    admin_state = models.CharField(verbose_name="Status", max_length=30, default="up", null=True, blank=True)
    olt_rx_sig = models.FloatField(verbose_name="OLT RX Signal", default=0, null=True, blank=True)
    ont_olt = models.CharField(verbose_name="Distancia", max_length=200, default="0", null=True, blank=True)
    desc1 = models.CharField(verbose_name="Descrição_1", max_length=200)
    desc2 = models.CharField(verbose_name="Descrição_2", max_length=300)
    cliente_fibra = models.BooleanField(verbose_name="Cliente Fibra", default=False)    

    class Meta:
        verbose_name = "ONU"
        verbose_name_plural = ("ONUs")
    
    def __str__(self) -> str:
        return f"{ self.serial }"

    def get_slot(self):
        """Get slot number from PON string"""
        parts = self.pon.split('/')
        if len(parts) >= 3:
            return parts[2]
        return ''

    def get_port(self):
        """Get port number from PON string"""
        parts = self.pon.split('/')
        if len(parts) >= 4:
            return parts[3]
        return ''

    def update_cliente_fibra_status(self):
        """Update the cliente_fibra field based on ClienteFibraIxc."""
        existe = ClienteFibraIxc.objects.filter(mac=self.serial, nome=self.desc1).exists()
        self.cliente_fibra = existe
        self.save()

class PlacaOnu(models.Model):

    chassi = models.CharField(verbose_name="Chassi", max_length=20, default="1/1/1")
    position = models.IntegerField(verbose_name="Posição do Slot", validators=[MinValueValidator(1), MaxValueValidator(2)])

    class Meta:
        verbose_name = "Placa"
        verbose_name_plural = ("Placas")
    
    def __str__(self) -> str:
        return f"{self.chassi}/{self.position}"
    
class ClienteFibraIxc(models.Model):
    mac = models.CharField(max_length=255)
    nome = models.CharField(max_length=255)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    id_caixa_ftth = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Cliente Fibra"
        verbose_name_plural = "Clientes Fibra"

    def __str__(self) -> str:
        return f"{self.nome}"

