from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
import ipaddress


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
    is_active = models.BooleanField(default=True, verbose_name="Ativo")

    class Meta:
        verbose_name = "Cliente Fibra"
        verbose_name_plural = "Clientes Fibra"

    def __str__(self) -> str:
        return f"{self.nome}"


class OltSystemInfo(models.Model):
    """Model para armazenar informações do sistema OLT"""
    
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
    
    slot_name = models.CharField(max_length=20, verbose_name="Nome do Slot", unique=True)
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
        ordering = ['slot_name']
    
    def __str__(self):
        return f"{self.slot_name} - {self.actual_type}"
    
    @property
    def is_operational(self):
        """Verifica se o slot está operacional"""
        return self.enabled and self.availability == 'available' and self.error_status == 'no-error'


class OltTemperature(models.Model):
    """Model para armazenar informações de temperatura da OLT"""
    
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
        unique_together = ['slot_name', 'sensor_id']
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
    
    interface = models.CharField(max_length=50, verbose_name="Interface", unique=True)
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


class OltSystemStats(models.Model):
    """Model para armazenar histórico de estatísticas da OLT (CPU, memória)"""
    
    # Dados de performance
    cpu_percent = models.IntegerField(
        verbose_name="CPU (%)", 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    cpu_load = models.FloatField(
        verbose_name="CPU Load Average", 
        null=True, 
        blank=True
    )
    mem_percent = models.IntegerField(
        verbose_name="Memória (%)", 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # Informações do sistema (podem variar ao longo do tempo)
    model = models.CharField(max_length=50, verbose_name="Modelo", default="FX-4")
    uptime_days = models.IntegerField(verbose_name="Uptime (dias)", default=0)
    
    # Estatísticas dos slots
    total_slots = models.IntegerField(verbose_name="Total de Slots", default=0)
    operational_slots = models.IntegerField(verbose_name="Slots Operacionais", default=0)
    
    # Estatísticas de temperatura
    avg_temperature = models.FloatField(verbose_name="Temperatura Média (°C)", null=True, blank=True)
    max_temperature = models.FloatField(verbose_name="Temperatura Máxima (°C)", null=True, blank=True)
    critical_temps = models.IntegerField(verbose_name="Temperaturas Críticas", default=0)
    warning_temps = models.IntegerField(verbose_name="Temperaturas de Aviso", default=0)
    
    # Timestamp da medição
    measured_at = models.DateTimeField(auto_now_add=True, verbose_name="Medido em")
    
    class Meta:
        verbose_name = "Estatística da OLT"
        verbose_name_plural = "Estatísticas da OLT"
        ordering = ['-measured_at']
        indexes = [
            models.Index(fields=['measured_at']),
            models.Index(fields=['-measured_at']),
        ]
    
    def __str__(self):
        return f"OLT Stats {self.measured_at.strftime('%Y-%m-%d %H:%M')} - CPU: {self.cpu_percent}%, Mem: {self.mem_percent}%"
    
    @classmethod
    def cleanup_old_records(cls):
        """Remove registros mais antigos que 7 dias"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=7)
        deleted_count = cls.objects.filter(measured_at__lt=cutoff_date).delete()[0]
        return deleted_count
    
    @classmethod
    def get_latest(cls):
        """Retorna a última medição"""
        return cls.objects.first()
    
    @classmethod
    def get_last_24h(cls):
        """Retorna medições das últimas 24 horas"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(hours=24)
        return cls.objects.filter(measured_at__gte=cutoff_date)


class OltAlarm(models.Model):
    ALARM_TYPES = (
        ('current', 'Alarme Atual'),
        ('major', 'Alarme Major'),
        ('critical', 'Alarme Crítico'),
        ('log', 'Log de Alarmes'),
    )
    
    SEVERITY_CHOICES = (
        ('minor', 'Minor'),
        ('major', 'Major'),
        ('critical', 'Critical'),
        ('warning', 'Warning'),
        ('clear', 'Clear'),
    )
    
    alarm_type = models.CharField(max_length=20, choices=ALARM_TYPES, verbose_name="Tipo de Alarme")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, verbose_name="Severidade", null=True, blank=True)
    alarm_id = models.CharField(max_length=50, verbose_name="ID do Alarme", null=True, blank=True)
    entity = models.CharField(max_length=100, verbose_name="Entidade", null=True, blank=True)
    description = models.TextField(verbose_name="Descrição do Alarme")
    alarm_time = models.DateTimeField(verbose_name="Data/Hora do Alarme", null=True, blank=True)
    collected_at = models.DateTimeField(auto_now_add=True, verbose_name="Coletado em")
    is_active = models.BooleanField(default=True, verbose_name="Ativo")
    
    class Meta:
        verbose_name = "Alarme OLT"
        verbose_name_plural = "Alarmes OLT"
        ordering = ['-alarm_time', '-collected_at']
    
    def __str__(self):
        return f"{self.get_severity_display()} - {self.entity}: {self.description[:50]}"
    
    @classmethod
    def cleanup_old_records(cls):
        """Remove registros mais antigos que 30 dias"""
        from django.utils import timezone
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=30)
        deleted_count = cls.objects.filter(collected_at__lt=cutoff_date).delete()[0]
        return deleted_count


class OrdemServicoIxc(models.Model):
    """
    Modelo para Ordens de Serviço do IXC
    """
    STATUS_CHOICES = (
        ('A', 'Aberta'),
        ('X', 'Executada'),
        ('F', 'Fechada'),
        ('C', 'Cancelada'),
        ('P', 'Pausada'),
        ('R', 'Reagendada'),
    )
    
    PRIORIDADE_CHOICES = (
        ('B', 'Baixa'),
        ('N', 'Normal'),
        ('A', 'Alta'),
        ('U', 'Urgente'),
    )
    
    TIPO_CHOICES = (
        ('I', 'Instalação'),
        ('M', 'Manutenção'),
        ('C', 'Corretiva'),
        ('R', 'Retirada'),
        ('V', 'Visita'),
        ('O', 'Outros'),
    )
    
    # Campos principais do IXC
    id_ixc = models.IntegerField(unique=True, verbose_name="ID IXC")
    protocolo = models.CharField(max_length=50, verbose_name="Protocolo", null=True, blank=True)
    tipo = models.CharField(max_length=1, choices=TIPO_CHOICES, verbose_name="Tipo", default='M')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, verbose_name="Status", default='A')
    prioridade = models.CharField(max_length=1, choices=PRIORIDADE_CHOICES, verbose_name="Prioridade", default='N')
    
    # Informações do cliente
    id_cliente = models.IntegerField(verbose_name="ID Cliente", null=True, blank=True)
    id_contrato = models.IntegerField(verbose_name="ID Contrato", null=True, blank=True)
    
    # Assunto/descrição
    id_assunto = models.IntegerField(verbose_name="ID Assunto", null=True, blank=True)
    assunto_nome = models.CharField(max_length=200, verbose_name="Nome do Assunto", null=True, blank=True)
    mensagem = models.TextField(verbose_name="Mensagem", null=True, blank=True)
    mensagem_resposta = models.TextField(verbose_name="Mensagem Resposta", null=True, blank=True)
    
    # Técnico
    id_tecnico = models.IntegerField(verbose_name="ID Técnico", null=True, blank=True)
    tecnico_nome = models.CharField(max_length=200, verbose_name="Nome do Técnico", null=True, blank=True)
    
    # Endereço
    endereco = models.CharField(max_length=300, verbose_name="Endereço", null=True, blank=True)
    bairro = models.CharField(max_length=100, verbose_name="Bairro", null=True, blank=True)
    cidade = models.CharField(max_length=100, verbose_name="Cidade", null=True, blank=True)
    referencia = models.CharField(max_length=200, verbose_name="Referência", null=True, blank=True)
    
    # Datas importantes
    data_abertura = models.DateTimeField(verbose_name="Data Abertura", null=True, blank=True)
    data_agenda = models.DateTimeField(verbose_name="Data Agendamento", null=True, blank=True)
    data_execucao = models.DateTimeField(verbose_name="Data Execução", null=True, blank=True)
    data_fechamento = models.DateTimeField(verbose_name="Data Fechamento", null=True, blank=True)
    data_prazo_limite = models.DateTimeField(verbose_name="Prazo Limite", null=True, blank=True)
    
    # Valores financeiros
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total", null=True, blank=True)
    valor_comissao = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Comissão", null=True, blank=True)
    
    # Controle interno
    sincronizado_em = models.DateTimeField(auto_now=True, verbose_name="Sincronizado em")
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")
    
    class Meta:
        verbose_name = "Ordem de Serviço IXC"
        verbose_name_plural = "Ordens de Serviço IXC"
        ordering = ['-data_abertura', '-id_ixc']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['data_abertura']),
            models.Index(fields=['id_assunto']),
            models.Index(fields=['id_tecnico']),
        ]
    
    def __str__(self):
        return f"OS #{self.protocolo or self.id_ixc} - {self.get_status_display()}"
    
    def get_mes_abertura(self):
        """Retorna mês/ano da abertura para agrupamento"""
        if self.data_abertura:
            return self.data_abertura.strftime('%Y-%m')
        return None


class SystemUpdateLog(models.Model):
    """
    Modelo para rastrear atualizações completas do sistema
    """
    TIPO_CHOICES = [
        ('manual', 'Manual'),
        ('automatico', 'Automático'),
        ('agendado', 'Agendado'),
    ]
    
    STATUS_CHOICES = [
        ('iniciado', 'Iniciado'),
        ('em_progresso', 'Em Progresso'),
        ('concluido', 'Concluído'),
        ('falhou', 'Falhou'),
        ('parcial', 'Parcialmente Concluído'),
    ]
    
    # Informações básicas
    tipo_atualizacao = models.CharField(max_length=20, choices=TIPO_CHOICES, verbose_name="Tipo de Atualização")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='iniciado', verbose_name="Status")
    usuario = models.CharField(max_length=100, verbose_name="Usuário", default="Sistema")
    job_id = models.CharField(max_length=100, null=True, blank=True, verbose_name="Job ID")
    
    # Timestamps
    iniciado_em = models.DateTimeField(auto_now_add=True, verbose_name="Iniciado em")
    concluido_em = models.DateTimeField(null=True, blank=True, verbose_name="Concluído em")
    duracao_segundos = models.IntegerField(null=True, blank=True, verbose_name="Duração (segundos)")
    
    # Resultados das etapas
    olt_system_ok = models.BooleanField(default=False, verbose_name="Sistema OLT OK")
    port_occupation_ok = models.BooleanField(default=False, verbose_name="Ocupação Portas OK")
    onus_ok = models.BooleanField(default=False, verbose_name="ONUs OK")
    macs_ok = models.BooleanField(default=False, verbose_name="MACs OK")
    clientes_ok = models.BooleanField(default=False, verbose_name="Clientes OK")
    
    # Contadores
    sucessos = models.IntegerField(default=0, verbose_name="Sucessos")
    total_etapas = models.IntegerField(default=5, verbose_name="Total de Etapas")
    
    # Observações e erros
    observacoes = models.TextField(null=True, blank=True, verbose_name="Observações")
    erros = models.JSONField(null=True, blank=True, verbose_name="Erros Detalhados")
    
    class Meta:
        verbose_name = "Log de Atualização do Sistema"
        verbose_name_plural = "Logs de Atualizações do Sistema"
        ordering = ['-iniciado_em']
        indexes = [
            models.Index(fields=['tipo_atualizacao']),
            models.Index(fields=['status']),
            models.Index(fields=['iniciado_em']),
        ]
    
    def __str__(self):
        return f"{self.get_tipo_atualizacao_display()} - {self.get_status_display()} ({self.iniciado_em.strftime('%d/%m/%Y %H:%M')})"
    
    @classmethod
    def get_ultima_atualizacao_completa(cls):
        """Retorna a última atualização completa bem-sucedida"""
        return cls.objects.filter(
            status__in=['concluido', 'parcial']
        ).first()
    
    @classmethod
    def get_estatisticas_hoje(cls):
        """Retorna estatísticas de atualizações de hoje"""
        from django.utils import timezone
        hoje = timezone.now().date()
        
        return cls.objects.filter(
            iniciado_em__date=hoje
        ).aggregate(
            total=models.Count('id'),
            sucessos=models.Count('id', filter=models.Q(status='concluido')),
            falhas=models.Count('id', filter=models.Q(status='falhou'))
        )
    
    def calcular_duracao(self):
        """Calcula e salva a duração se a atualização foi concluída"""
        if self.concluido_em and self.iniciado_em:
            delta = self.concluido_em - self.iniciado_em
            self.duracao_segundos = int(delta.total_seconds())
            return self.duracao_segundos
        return None
    
    def get_porcentagem_sucesso(self):
        """Retorna a porcentagem de sucesso das etapas"""
        if self.total_etapas > 0:
            return round((self.sucessos / self.total_etapas) * 100, 1)
        return 0

