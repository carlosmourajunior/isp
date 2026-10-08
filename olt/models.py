from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
import ipaddress

from .fields import EncryptedCharField


class Olt(models.Model):
    """
    Uma OLT física cadastrada no sistema. Hoje só existe driver pra
    Nokia/Alcatel (AOS) - `vendor` já é o ponto de extensão pra outros
    fabricantes: ver olt/utils.py::build_connect_kwargs.
    """
    VENDOR_NOKIA_ALCATEL = 'nokia_alcatel'
    VENDOR_CHOICES = [
        (VENDOR_NOKIA_ALCATEL, 'Nokia / Alcatel (AOS)'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="Nome")
    vendor = models.CharField(max_length=30, choices=VENDOR_CHOICES, default=VENDOR_NOKIA_ALCATEL, verbose_name="Fabricante")
    device_type = models.CharField(max_length=50, default='alcatel_aos', verbose_name="Device type (netmiko)")
    host = models.CharField(max_length=255, verbose_name="Host/IP")
    username = models.CharField(max_length=100, verbose_name="Usuário SSH")
    password = EncryptedCharField(max_length=500, verbose_name="Senha SSH")
    ssh_port = models.IntegerField(default=22, verbose_name="Porta SSH")
    slot_count = models.PositiveSmallIntegerField(
        default=2, verbose_name="Quantidade de slots",
        help_text="Maior número de slot físico da OLT (mesmo que nem todos estejam instalados hoje) "
                   "- define até onde olt/utils.py varre a OLT via SSH."
    )
    global_delay_factor = models.IntegerField(default=2, verbose_name="Global delay factor (netmiko)")
    verbose = models.BooleanField(default=False, verbose_name="Verbose (netmiko)")
    is_active = models.BooleanField(default=True, verbose_name="Ativa")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criada em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizada em")

    class Meta:
        verbose_name = "OLT"
        verbose_name_plural = "OLTs"
        ordering = ['name']

    def __str__(self):
        return self.name


class OltUsers(models.Model):

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, related_name='olt_users', null=True, verbose_name="OLT")
    # Sem teto de negócio real aqui - cada OLT declara sua própria capacidade
    # em Olt.slot_count (varia por modelo de chassi/fabricante). 32 é só um
    # limite de sanidade.
    slot = models.IntegerField(verbose_name="Slot", validators=[MinValueValidator(1), MaxValueValidator(32)])
    port = models.IntegerField(verbose_name="Porta", validators=[MinValueValidator(1), MaxValueValidator(16)])

    users_connected = models.IntegerField(verbose_name="Usuários Aprovisionados")
    last_updated = models.DateTimeField(verbose_name="Última Atualização")

    class Meta:
        verbose_name = ("Porta")
        verbose_name_plural = ("Portas")

    def __str__(self):
        return f"1/1/{self.slot}/{self.port}"

class ONU(models.Model):

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, related_name='onus', null=True, verbose_name="OLT")
    pon = models.CharField(verbose_name="PON", max_length=20)
    position = models.IntegerField(verbose_name="Posição", validators=[MinValueValidator(1), MaxValueValidator(128)])
    mac = models.CharField(verbose_name="MAC", max_length=200)
    serial = models.CharField(verbose_name="Serial", max_length=30)
    oper_state = models.CharField(verbose_name="Status", max_length=30)
    admin_state = models.CharField(verbose_name="Status", max_length=30, default="up", null=True, blank=True)
    olt_rx_sig = models.FloatField(verbose_name="OLT RX Signal", default=0, null=True, blank=True)
    ont_rx_sig = models.FloatField(verbose_name="ONT RX Signal", null=True, blank=True)
    ont_tx_sig = models.FloatField(verbose_name="ONT TX Signal", null=True, blank=True)
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
        """Update the cliente_fibra field based on ClienteFibraIxc.

        Casa só por serial (ClienteFibraIxc.mac == ONU.serial) - desc1 é um
        campo livre digitado na OLT (às vezes nome do cliente, às vezes
        modelo do aparelho, às vezes "undefined") e nunca corresponde de
        fato ao nome cadastrado no IXC, então exigir os dois descartava
        vínculos que já existiam por serial.
        """
        existe = ClienteFibraIxc.objects.filter(mac=self.serial).exists()
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
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    id_contrato = models.CharField(max_length=50, blank=True, default='', verbose_name="ID do contrato (IXC)")
    vinculado = models.BooleanField(
        default=False,
        verbose_name="Vinculado a contrato",
        help_text="True quando id_contrato existe e foi encontrado em cliente_contrato/cliente no IXC "
                   "(nome/endereço são dados reais do cadastro). False = registro de provisionamento "
                   "(radpop_radio_cliente_fibra) sem contrato formal vinculado no IXC.",
    )

    class Meta:
        verbose_name = "Cliente Fibra"
        verbose_name_plural = "Clientes Fibra"

    def __str__(self) -> str:
        return f"{self.nome}"


class OltSystemInfo(models.Model):
    """Model para armazenar informações do sistema OLT (um registro por OLT)"""

    olt = models.OneToOneField(Olt, on_delete=models.CASCADE, related_name='system_info', null=True, verbose_name="OLT")

    # Informações de software
    isam_release = models.CharField(max_length=50, verbose_name="ISAM Release")
    
    # Informações de uptime
    uptime_days = models.IntegerField(verbose_name="Uptime (dias)", default=0)
    uptime_hours = models.IntegerField(verbose_name="Uptime (horas)", default=0)
    uptime_minutes = models.IntegerField(verbose_name="Uptime (minutos)", default=0)
    uptime_seconds = models.IntegerField(verbose_name="Uptime (segundos)", default=0)
    uptime_raw = models.CharField(max_length=255, verbose_name="Uptime Raw")
    
    # Timestamp da última atualização
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    
    class Meta:
        verbose_name = "Informação do Sistema OLT"
        verbose_name_plural = "Informações do Sistema OLT"
    
    def __str__(self):
        return f"OLT System Info - {self.isam_release}"
    
    @property
    def total_uptime_hours(self):
        """Retorna o uptime total em horas"""
        return (self.uptime_days * 24) + self.uptime_hours


class OltSlot(models.Model):
    """Model para armazenar informações dos slots da OLT"""

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, related_name='slots', null=True, verbose_name="OLT")
    slot_name = models.CharField(max_length=20, verbose_name="Nome do Slot")
    actual_type = models.CharField(max_length=50, verbose_name="Tipo Atual")
    enabled = models.BooleanField(verbose_name="Habilitado", default=False)
    error_status = models.CharField(max_length=100, verbose_name="Status de Erro")
    availability = models.CharField(max_length=50, verbose_name="Disponibilidade")
    restart_count = models.IntegerField(verbose_name="Contador de Reinicializações", default=0)
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    # Timestamp da última atualização
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")

    class Meta:
        verbose_name = "Slot OLT"
        verbose_name_plural = "Slots OLT"
        unique_together = ['olt', 'slot_name']
        ordering = ['slot_name']
    
    def __str__(self):
        return f"{self.slot_name} - {self.actual_type}"
    
    @property
    def is_operational(self):
        """Verifica se o slot está operacional"""
        return self.enabled and self.availability == 'available' and self.error_status == 'no-error'


class OltTemperature(models.Model):
    """Model para armazenar informações de temperatura da OLT"""

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, related_name='temperatures', null=True, verbose_name="OLT")
    slot_name = models.CharField(max_length=20, verbose_name="Nome do Slot")
    sensor_id = models.IntegerField(verbose_name="ID do Sensor")
    actual_temp = models.IntegerField(verbose_name="Temperatura Atual (°C)")
    tca_low = models.IntegerField(verbose_name="TCA Baixo (°C)")
    tca_high = models.IntegerField(verbose_name="TCA Alto (°C)")
    shutdown_low = models.IntegerField(verbose_name="Shutdown Baixo (°C)")
    shutdown_high = models.IntegerField(verbose_name="Shutdown Alto (°C)")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    # Timestamp da última atualização
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    
    class Meta:
        verbose_name = "Temperatura OLT"
        verbose_name_plural = "Temperaturas OLT"
        unique_together = ['olt', 'slot_name', 'sensor_id']
        ordering = ['slot_name', 'sensor_id']
    
    def __str__(self):
        return f"{self.slot_name} Sensor {self.sensor_id}: {self.actual_temp}°C"
    
    @property
    def is_critical(self):
        """Verifica se a temperatura está em nível crítico"""
        return self.actual_temp >= self.tca_high
    
    @property
    def is_warning(self):
        """Verifica se a temperatura está em nível de aviso"""
        return self.actual_temp >= (self.tca_high - 5)
    
    @property
    def status(self):
        """Retorna o status da temperatura"""
        if self.actual_temp >= self.shutdown_high:
            return "CRITICAL_HIGH"
        elif self.actual_temp <= self.shutdown_low:
            return "CRITICAL_LOW"
        elif self.actual_temp >= self.tca_high:
            return "WARNING_HIGH"
        elif self.actual_temp <= self.tca_low:
            return "WARNING_LOW"
        else:
            return "NORMAL"


class OltSfpDiagnostics(models.Model):
    """Model para armazenar diagnósticos SFP da OLT"""

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, related_name='sfp_diagnostics', null=True, verbose_name="OLT")
    interface = models.CharField(max_length=50, verbose_name="Interface")
    vendor_name = models.CharField(max_length=100, verbose_name="Fabricante", blank=True, null=True)
    part_number = models.CharField(max_length=100, verbose_name="Número da Peça", blank=True, null=True)
    serial_number = models.CharField(max_length=100, verbose_name="Número Serial", blank=True, null=True)
    temperature = models.FloatField(verbose_name="Temperatura (°C)", null=True, blank=True)
    voltage = models.FloatField(verbose_name="Voltagem (V)", null=True, blank=True)
    tx_power = models.FloatField(verbose_name="Potência TX (dBm)", null=True, blank=True)
    rx_power = models.FloatField(verbose_name="Potência RX (dBm)", null=True, blank=True)
    
    # Timestamp da última atualização
    last_updated = models.DateTimeField(auto_now=True, verbose_name="Última Atualização")
    
    class Meta:
        verbose_name = "Diagnóstico SFP"
        verbose_name_plural = "Diagnósticos SFP"
        unique_together = ['olt', 'interface']
        ordering = ['interface']
    
    def __str__(self):
        return f"SFP {self.interface}"


class AllowedIP(models.Model):
    """Model para gerenciar IPs permitidos no sistema"""
    
    ip_address = models.CharField(
        max_length=50, 
        verbose_name="IP/Range", 
        help_text="IP individual (ex: 192.168.1.1) ou range CIDR (ex: 192.168.1.0/24)",
        unique=True
    )
    description = models.CharField(
        max_length=200, 
        verbose_name="Descrição",
        help_text="Descrição do IP ou range (ex: Servidor, Rede local, etc.)"
    )
    is_active = models.BooleanField(
        default=True, 
        verbose_name="Ativo",
        help_text="Se marcado, este IP será permitido no sistema"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Atualizado em")
    
    class Meta:
        verbose_name = "IP Permitido"
        verbose_name_plural = "IPs Permitidos"
        ordering = ['ip_address']
    
    def clean(self):
        """Valida se o IP ou range está no formato correto"""
        super().clean()
        try:
            # Tenta validar como rede (CIDR) ou IP individual
            ipaddress.ip_network(self.ip_address, strict=False)
        except ValueError:
            raise ValidationError({'ip_address': 'Formato de IP ou range inválido. Use formatos como: 192.168.1.1 ou 192.168.1.0/24'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.ip_address} - {self.description}"

