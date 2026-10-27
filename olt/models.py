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

        Só conta registro ainda presente no IXC (is_active): um cliente fibra
        apagado no IXC fica no banco como inativo e não pode manter o "Sim".
        """
        existe = ClienteFibraIxc.objects.filter(mac=self.serial, is_active=True).exists()
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
    # Login PPPoE do registro de cliente fibra (radpop_radio_cliente_fibra). Um mesmo
    # titular pode ter vários logins/ONUs, cada um numa caixa - o login é o que os separa.
    login = models.CharField(max_length=255, blank=True, default='', db_index=True)
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    id_caixa_ftth = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    id_contrato = models.CharField(max_length=50, blank=True, default='', verbose_name="ID do contrato (IXC)")
    # Status do contrato no IXC (cliente_contrato.status / status_internet), códigos crus.
    # Rótulos e a regra "ativo/bloqueado/inativo" em olt/contrato.py.
    status_contrato = models.CharField(max_length=5, blank=True, default='', verbose_name="Status do contrato (IXC)")
    status_internet = models.CharField(max_length=5, blank=True, default='', verbose_name="Status da internet (IXC)")
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



# ==================== OCUPAÇÃO DE CTO (histórico + eventos) ====================
# A tabela ONU é apagada e recriada a cada sync (utils.update_port), então
# sozinha ela não "lembra" quem já esteve em cada PON. Estes models guardam
# o histórico necessário para inferir CTOs e portas liberadas.

class OntSnapshot(models.Model):
    """Foto append-only de uma ONT a cada sync de ONUs. Nunca é sobrescrita."""

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, related_name='ont_snapshots', verbose_name="OLT")
    taken_at = models.DateTimeField(db_index=True, verbose_name="Coletado em")
    pon = models.CharField(max_length=20, verbose_name="PON")
    position = models.IntegerField(verbose_name="Posição")
    serial = models.CharField(max_length=30, db_index=True, verbose_name="Serial")
    admin_state = models.CharField(max_length=30, blank=True, default='', verbose_name="Admin")
    oper_state = models.CharField(max_length=30, blank=True, default='', verbose_name="Oper")
    olt_rx_sig = models.FloatField(null=True, blank=True, verbose_name="OLT RX (dBm)")
    # ont-olt-distance da OLT, em km (resolução de 0.1 km nesta release).
    distance_km = models.FloatField(null=True, blank=True, verbose_name="Distância (km)")

    class Meta:
        verbose_name = "Snapshot de ONT"
        verbose_name_plural = "Snapshots de ONT"
        indexes = [models.Index(fields=['olt', 'pon', 'taken_at'])]

    def __str__(self):
        return f"{self.serial} @ {self.pon}/{self.position} ({self.taken_at:%d/%m %H:%M})"


class OltSyslogMessage(models.Model):
    """Mensagem de syslog crua recebida da OLT. Guardada sempre, mesmo sem
    parse, para poder reprocessar quando o parser for ajustado."""

    olt = models.ForeignKey(Olt, on_delete=models.SET_NULL, null=True, blank=True, related_name='syslog_messages', verbose_name="OLT")
    source_ip = models.GenericIPAddressField(verbose_name="IP de origem")
    # Horário de recebimento é a referência: o relógio da OLT pode estar
    # errado (sem NTP ela reporta 1970).
    received_at = models.DateTimeField(db_index=True, verbose_name="Recebido em")
    raw = models.TextField(verbose_name="Mensagem crua")
    parsed = models.BooleanField(default=False, verbose_name="Gerou evento")

    class Meta:
        verbose_name = "Syslog da OLT"
        verbose_name_plural = "Syslogs da OLT"
        ordering = ['-received_at']

    def __str__(self):
        return f"{self.received_at:%d/%m %H:%M:%S} {self.raw[:80]}"


class OntEvent(models.Model):
    """Queda/retorno de uma ONT extraído do syslog. A base da correlação de
    quedas simultâneas (mesma CTO caem juntas por LOS)."""

    TYPE_LOS = 'los'
    TYPE_INATIVA = 'inativa'
    TYPE_DYING_GASP = 'dying_gasp'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_LOS, 'LOS (perda de sinal)'),
        # "ONT is inactive": o alarme de desconexão que a OLT (release 6.2) realmente manda.
        (TYPE_INATIVA, 'ONT inativa (saiu do ar)'),
        (TYPE_DYING_GASP, 'Dying gasp (falta de energia)'),
        (TYPE_OTHER, 'Outro (RDI, nível de sinal...)'),
    ]
    # Tipos que indicam a ONT desconectada - os únicos que servem para
    # inferir fibra em comum (RDI e alarmes de nível oscilam e são ruído).
    TYPES_QUEDA = (TYPE_LOS, TYPE_INATIVA)

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, null=True, blank=True, related_name='ont_events', verbose_name="OLT")
    message = models.ForeignKey(OltSyslogMessage, on_delete=models.SET_NULL, null=True, blank=True, related_name='events')
    occurred_at = models.DateTimeField(db_index=True, verbose_name="Ocorrido em")
    pon = models.CharField(max_length=20, verbose_name="PON")
    position = models.IntegerField(verbose_name="Posição")
    # Serial resolvido pela tabela ONU no momento do evento (a OLT só manda a posição).
    serial = models.CharField(max_length=30, blank=True, default='', db_index=True, verbose_name="Serial")
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Tipo")
    is_clear = models.BooleanField(default=False, verbose_name="Alarme encerrado (ONT voltou)")
    alarm_type = models.CharField(max_length=50, blank=True, default='', verbose_name="Tipo de alarme Nokia")

    class Meta:
        verbose_name = "Evento de ONT"
        verbose_name_plural = "Eventos de ONT"
        ordering = ['-occurred_at']
        indexes = [models.Index(fields=['olt', 'pon', 'occurred_at'])]

    def __str__(self):
        estado = 'fim' if self.is_clear else 'início'
        return f"{self.occurred_at:%d/%m %H:%M:%S} {self.pon}/{self.position} {self.event_type} ({estado})"


class SchedulerConfig(models.Model):
    """Configuração da atualização automática (registro único, editado no admin).

    Lida a cada minuto pelo processo do container `scheduler`
    (manage.py run_scheduler) - mudar aqui vale sem deploy nem restart.
    """

    enabled = models.BooleanField(default=False, verbose_name="Atualização automática ligada")
    interval_minutes = models.PositiveIntegerField(
        default=120, validators=[MinValueValidator(30)], verbose_name="Intervalo (minutos)",
        help_text="Tempo entre o início de uma atualização completa e a próxima. Mínimo 30. "
                  "Se a anterior ainda estiver na fila, a próxima é pulada.",
    )
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name="Última execução")
    last_run_summary = models.CharField(max_length=255, blank=True, default='', verbose_name="Resultado da última verificação")
    # IDs dos jobs RQ da última execução - para não enfileirar outra por cima.
    last_job_ids = models.JSONField(default=list, blank=True)
    # Atualizado a cada minuto pelo processo do scheduler: mostra se ele está vivo.
    heartbeat_at = models.DateTimeField(null=True, blank=True, verbose_name="Último sinal do scheduler")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Atualização automática"
        verbose_name_plural = "Atualização automática"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def next_run_at(self):
        if not self.last_run_at:
            return None
        from datetime import timedelta
        return self.last_run_at + timedelta(minutes=self.interval_minutes)

    def scheduler_alive(self, now=None, tolerance_seconds=180):
        from django.utils import timezone
        if not self.heartbeat_at:
            return False
        now = now or timezone.now()
        return (now - self.heartbeat_at).total_seconds() <= tolerance_seconds

    def __str__(self):
        estado = f"a cada {self.interval_minutes} min" if self.enabled else "desligada"
        return f"Atualização automática ({estado})"


class Cto(models.Model):
    """Caixa de atendimento (CTO). Base: cadastro do IXC (rad_caixa_ftth),
    enriquecido com o projeto da rede (KMZ): ramal, portas e splitter. Caixas
    que só existem no KMZ entram com origem='kmz'.

    ClienteFibraIxc.id_caixa_ftth guarda o id do IXC (ixc_id) - a ligação é
    por esse valor, sem FK, para não depender da ordem dos syncs.
    """

    ORIGEM_IXC = 'ixc'
    ORIGEM_KMZ = 'kmz'
    ORIGEM_CHOICES = [
        (ORIGEM_IXC, 'IXC'),
        # Caixa do projeto (KMZ) que não existe no cadastro do IXC - ainda
        # assim é candidata na inferência (clientes dela não têm como estar
        # cadastrados nela).
        (ORIGEM_KMZ, 'Só no KMZ'),
    ]

    ixc_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name="ID no IXC")
    origem = models.CharField(max_length=5, choices=ORIGEM_CHOICES, default=ORIGEM_IXC, db_index=True)
    # CA/CTO = atendimento; CD = distribuição/derivação (normalmente sem cliente direto).
    tipo = models.CharField(max_length=5, blank=True, default='', verbose_name="Tipo")
    descricao = models.CharField(max_length=100, db_index=True, verbose_name="Nome")
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    capacidade = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Capacidade (IXC)")
    status = models.CharField(max_length=5, blank=True, default='', verbose_name="Status IXC")
    id_projeto = models.CharField(max_length=20, blank=True, default='', verbose_name="Projeto IXC")
    is_active = models.BooleanField(default=True, verbose_name="Presente no último sync do IXC")

    # Preenchidos pela importação do KMZ (manage.py importar_kmz).
    olt = models.ForeignKey(Olt, on_delete=models.SET_NULL, null=True, blank=True, related_name='ctos', verbose_name="OLT")
    ramal = models.CharField(max_length=50, blank=True, default='', db_index=True, verbose_name="Ramal (KMZ)")
    kmz_nome = models.CharField(max_length=100, blank=True, default='', verbose_name="Nome no KMZ")
    kmz_portas = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Portas (KMZ)")
    kmz_splitter = models.CharField(max_length=20, blank=True, default='', verbose_name="Splitter (KMZ)")
    kmz_descricao = models.TextField(blank=True, default='', verbose_name="Descrição no KMZ")
    kmz_match = models.CharField(max_length=20, blank=True, default='', verbose_name="Como casou com o KMZ")
    # Topologia do projeto (olt/kmz_topologia.py): de qual 1:8 de distribuição a caixa sai.
    kmz_ceo = models.CharField(max_length=80, blank=True, default='', db_index=True,
                               verbose_name="Splitter de distribuição (CEO/CD)")
    kmz_ceo_saida = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Saída no splitter da CEO")
    kmz_alimentacao = models.CharField(max_length=80, blank=True, default='',
                                       verbose_name="Fibra de alimentação da CEO (backbone)")
    kmz_cabo = models.CharField(max_length=120, blank=True, default='', verbose_name="Cabo de distribuição")
    kmz_topologia = models.CharField(max_length=10, blank=True, default='',
                                     verbose_name="Como a topologia foi lida (texto/geometria)")

    # Ajustes feitos em campo (vistoria). Ampliar = instalar um splitter inteiro (4 ou 8
    # portas); inutilizar = porta que não pode ser usada (conector quebrado etc.).
    # Portas da caixa definidas à mão (painel da CTO); quando preenchido vale sobre KMZ e IXC.
    portas_manual = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name="Portas (ajuste manual)")
    splitters_extras = models.JSONField(default=list, blank=True, verbose_name="Splitters adicionados (portas de cada)")
    portas_inutilizadas = models.JSONField(default=list, blank=True, verbose_name="Portas inutilizadas")
    ajustado_em = models.DateTimeField(null=True, blank=True, verbose_name="Último ajuste em campo")
    ajustado_por = models.CharField(max_length=150, blank=True, default='')

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "CTO"
        verbose_name_plural = "CTOs"
        ordering = ['descricao']

    @property
    def portas_base(self):
        """Portas da caixa: ajuste manual > projeto (KMZ) > cadastro do IXC."""
        return self.portas_manual or self.kmz_portas or self.capacidade

    @property
    def portas(self):
        """Portas físicas: as do projeto mais os splitters adicionados em campo."""
        extras = sum(self.splitters_extras or [])
        if self.portas_base is None and not extras:
            return None
        return (self.portas_base or 0) + extras

    @property
    def portas_uteis(self):
        """Portas que podem receber cliente (físicas menos as inutilizadas)."""
        if self.portas is None:
            return None
        return max(0, self.portas - len(set(self.portas_inutilizadas or [])))

    def __str__(self):
        return self.descricao


class CtoInferencia(models.Model):
    """Resultado da inferência de CTO para cada ONT (olt/cto_inference.py).
    Recalculado inteiro a cada execução (manage.py inferir_ctos)."""

    STATUS_CONFIRMADO = 'confirmado'
    STATUS_PROVAVEL = 'provavel'
    STATUS_DIVERGENTE = 'divergente'
    STATUS_INCERTO = 'incerto'
    STATUS_SEM_CANDIDATA = 'sem_candidata'
    STATUS_VISTORIADO = 'vistoriado'
    STATUS_CHOICES = [
        (STATUS_VISTORIADO, 'Vistoriado (confirmado em campo)'),
        (STATUS_CONFIRMADO, 'Confirmado (cadastro bate com a rede)'),
        (STATUS_PROVAVEL, 'Provável (sem cadastro, evidência forte)'),
        (STATUS_DIVERGENTE, 'Divergente (rede aponta outra CTO que a do cadastro)'),
        (STATUS_INCERTO, 'Incerto'),
        (STATUS_SEM_CANDIDATA, 'Sem candidata'),
    ]

    olt = models.ForeignKey(Olt, on_delete=models.CASCADE, related_name='cto_inferencias')
    pon = models.CharField(max_length=20)
    position = models.IntegerField(verbose_name="Posição")
    serial = models.CharField(max_length=30, db_index=True)
    cliente_nome = models.CharField(max_length=255, blank=True, default='', verbose_name="Cliente")
    distance_km = models.FloatField(null=True, blank=True, verbose_name="Distância (km)")
    cto_cadastro = models.ForeignKey('Cto', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                                     verbose_name="CTO no cadastro IXC")
    cto_provavel = models.ForeignKey('Cto', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='inferencias', verbose_name="CTO provável")
    score = models.FloatField(null=True, blank=True)
    cto_alternativa = models.ForeignKey('Cto', on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
                                        verbose_name="2ª candidata")
    score_alternativa = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, db_index=True)
    # {'provavel': [...], 'alternativa': [...], 'cadastro': [...]} - por que cada CTO ganhou/perdeu pontos.
    motivos = models.JSONField(default=dict, blank=True)
    calculado_em = models.DateTimeField(verbose_name="Calculado em")

    class Meta:
        verbose_name = "Inferência de CTO"
        verbose_name_plural = "Inferências de CTO"
        unique_together = ['olt', 'pon', 'position']
        ordering = ['olt', 'pon', 'position']

    def __str__(self):
        return f"{self.pon}/{self.position} -> {self.cto_provavel or '?'} ({self.status})"


class Vistoria(models.Model):
    """Verificação de uma CTO em campo (técnico na caixa + bancada no sistema).
    Cada porta registrada vira verdade de campo para a inferência."""

    cto = models.ForeignKey('Cto', on_delete=models.CASCADE, related_name='vistorias')
    olt = models.ForeignKey(Olt, on_delete=models.SET_NULL, null=True, blank=True, related_name='vistorias')
    usuario = models.CharField(max_length=150, blank=True, default='', verbose_name="Registrada por")
    tecnico = models.CharField(max_length=150, blank=True, default='', verbose_name="Técnico em campo")
    observacao = models.TextField(blank=True, default='')
    iniciada_em = models.DateTimeField(auto_now_add=True)
    finalizada_em = models.DateTimeField(null=True, blank=True)
    # A vistoria é a ficha contínua da caixa: cada vez que é retomada começa uma sessão nova.
    # Registros anteriores a este momento vieram de sessões passadas (olt/ficha_cto.py).
    sessao_iniciada_em = models.DateTimeField(null=True, blank=True, verbose_name="Sessão atual iniciada em")

    class Meta:
        verbose_name = "Vistoria de CTO"
        verbose_name_plural = "Vistorias de CTO"
        ordering = ['-iniciada_em']

    def __str__(self):
        return f"Vistoria {self.cto} em {self.iniciada_em:%d/%m/%Y}"


class VistoriaPorta(models.Model):
    RESULTADO_CLIENTE = 'cliente'
    RESULTADO_VAZIA = 'vazia'
    RESULTADO_SEM_ONT_ATIVA = 'sem_ont_ativa'
    RESULTADO_NAO_IDENTIFICADO = 'nao_identificado'
    RESULTADO_CHOICES = [
        (RESULTADO_CLIENTE, 'Cliente identificado'),
        (RESULTADO_VAZIA, 'Porta vazia (sem drop)'),
        # Tem drop, mas desconectar não derrubou ninguém: fantasma - porta a liberar.
        (RESULTADO_SEM_ONT_ATIVA, 'Drop sem ONT ativa (fantasma)'),
        (RESULTADO_NAO_IDENTIFICADO, 'Não identificado'),
    ]
    METODO_CHOICES = [
        ('etiqueta', 'Etiqueta / nome informado'),
        ('desconexao', 'Desconexão (alarme da OLT)'),
        ('manual', 'Manual'),
    ]

    vistoria = models.ForeignKey(Vistoria, on_delete=models.CASCADE, related_name='portas')
    # Opcional: na identificação por desconexão o cliente é confirmado na caixa
    # mesmo sem saber em qual porta está.
    porta = models.PositiveSmallIntegerField(null=True, blank=True)
    resultado = models.CharField(max_length=20, choices=RESULTADO_CHOICES)
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES, default='manual')
    serial = models.CharField(max_length=30, blank=True, default='', db_index=True)
    pon = models.CharField(max_length=20, blank=True, default='')
    position = models.IntegerField(null=True, blank=True)
    cliente_nome = models.CharField(max_length=255, blank=True, default='')
    reconexao_confirmada = models.BooleanField(default=False, verbose_name="Reconexão confirmada pela OLT")
    # id_caixa_ftth do cliente no IXC quando foi registrado aqui. Se o IXC mudar
    # depois disso, o IXC volta a ser a verdade (ver olt/verdade.py).
    # None = registro antigo, de antes deste campo existir.
    caixa_ixc_no_registro = models.CharField(max_length=50, null=True, blank=True,
                                             verbose_name="Caixa no IXC na hora da vistoria")
    observacao = models.CharField(max_length=255, blank=True, default='')
    registrado_em = models.DateTimeField(auto_now=True)
    registrado_por = models.CharField(max_length=150, blank=True, default='')

    class Meta:
        verbose_name = "Porta vistoriada"
        verbose_name_plural = "Portas vistoriadas"
        unique_together = ['vistoria', 'porta']
        ordering = ['porta']

    def __str__(self):
        porta = f"porta {self.porta}" if self.porta else "sem porta"
        return f"{self.vistoria.cto} {porta}: {self.get_resultado_display()}"


class CorrecaoIxc(models.Model):
    """Alteração feita no IXC pelo sistema (hoje: CTO do cliente fibra). Guarda
    o registro antes/depois para auditoria e para restaurar se algo der errado."""

    STATUS_CHOICES = [
        ('ok', 'Aplicada'),
        ('alerta', 'Aplicada, mas outros campos mudaram'),
        ('erro', 'Falhou'),
    ]

    TIPO_CORRECAO = 'correcao'
    TIPO_REVERSAO = 'reversao'
    TIPO_CHOICES = [(TIPO_CORRECAO, 'Correção'), (TIPO_REVERSAO, 'Reversão')]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_CORRECAO)
    reverte = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversoes',
                                verbose_name="Correção desfeita por esta reversão")
    serial = models.CharField(max_length=30, db_index=True)
    cliente_nome = models.CharField(max_length=255, blank=True, default='')
    ixc_registro_id = models.CharField(max_length=50, blank=True, default='', verbose_name="ID em radpop_radio_cliente_fibra")
    caixa_antes = models.CharField(max_length=50, blank=True, default='', verbose_name="id_caixa_ftth antes")
    caixa_depois = models.CharField(max_length=50, blank=True, default='', verbose_name="id_caixa_ftth enviado")
    cto = models.ForeignKey('Cto', on_delete=models.SET_NULL, null=True, related_name='correcoes_ixc', verbose_name="CTO aplicada")
    vistoria_porta = models.ForeignKey('VistoriaPorta', on_delete=models.SET_NULL, null=True, blank=True)
    usuario = models.CharField(max_length=150)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    mensagem = models.TextField(blank=True, default='')
    registro_antes = models.JSONField(default=dict, blank=True)
    registro_depois = models.JSONField(default=dict, blank=True)
    outros_campos_alterados = models.JSONField(default=list, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Correção no IXC"
        verbose_name_plural = "Correções no IXC"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.serial}: {self.caixa_antes or '-'} -> {self.caixa_depois or self.cto} ({self.status})"


class CadastroCaixaIxc(models.Model):
    """Caixa do projeto (KMZ) cadastrada no IXC pelo sistema (olt/ixc_caixas.py).
    Guarda o que foi enviado e o que o IXC devolveu, para auditoria."""

    STATUS_CHOICES = [
        ('ok', 'Cadastrada'),
        ('alerta', 'Cadastrada, conferir'),
        ('erro', 'Falhou'),
    ]

    cto = models.ForeignKey('Cto', on_delete=models.SET_NULL, null=True, related_name='cadastros_ixc')
    descricao = models.CharField(max_length=100)
    ixc_id = models.CharField(max_length=50, blank=True, default='', verbose_name="id criado no IXC")
    modelo_ixc_id = models.CharField(max_length=50, blank=True, default='',
                                     verbose_name="Caixa do IXC usada como modelo (projeto, cidade...)")
    usuario = models.CharField(max_length=150)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    mensagem = models.TextField(blank=True, default='')
    registro_enviado = models.JSONField(default=dict, blank=True)
    registro_lido = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Caixa cadastrada no IXC"
        verbose_name_plural = "Caixas cadastradas no IXC"
        ordering = ['-criado_em']

    def __str__(self):
        return f"{self.descricao} -> IXC {self.ixc_id or '-'} ({self.status})"

