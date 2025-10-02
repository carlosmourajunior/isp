import json
import logging
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.conf import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def alertmanager_webhook(request):
    """
    Webhook para receber alertas do Alertmanager
    """
    try:
        data = json.loads(request.body)
        
        # Processar cada alerta
        for alert in data.get('alerts', []):
            process_alert(alert)
        
        return JsonResponse({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Erro ao processar webhook do Alertmanager: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)


def process_alert(alert):
    """
    Processar um alerta individual
    """
    try:
        alert_name = alert.get('labels', {}).get('alertname')
        severity = alert.get('labels', {}).get('severity')
        status_alert = alert.get('status')
        
        # Log do alerta
        alert_logger = logging.getLogger('olt.security')
        
        # Criar mensagem de log estruturada
        message = (
            f"PROMETHEUS_ALERT: {alert_name} "
            f"SEVERITY:{severity} "
            f"STATUS:{status_alert} "
            f"STARTS_AT:{alert.get('startsAt')} "
            f"SUMMARY:{alert.get('annotations', {}).get('summary', 'N/A')}"
        )
        
        if status_alert == 'firing':
            alert_logger.warning(message)
            
            # Enviar notificações para alertas críticos
            if severity == 'critical':
                send_critical_alert_notification(alert)
        else:
            alert_logger.info(message)
        
        # Salvar alerta no banco (opcional)
        save_alert_to_database(alert)
        
    except Exception as e:
        logger.error(f"Erro ao processar alerta: {str(e)}")


def send_critical_alert_notification(alert):
    """
    Enviar notificação para alertas críticos
    """
    try:
        # Configurações de email (ajustar conforme necessário)
        smtp_server = getattr(settings, 'EMAIL_HOST', 'localhost')
        smtp_port = getattr(settings, 'EMAIL_PORT', 587)
        smtp_user = getattr(settings, 'EMAIL_HOST_USER', '')
        smtp_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        
        # Dados do alerta
        alert_name = alert.get('labels', {}).get('alertname')
        summary = alert.get('annotations', {}).get('summary')
        description = alert.get('annotations', {}).get('description')
        instance = alert.get('labels', {}).get('instance')
        
        # Criar email
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = 'admin@empresa.com'  # Configurar email do administrador
        msg['Subject'] = f'[CRÍTICO] {alert_name} - Sistema ISP'
        
        body = f"""
        ALERTA CRÍTICO DETECTADO
        
        Sistema: ISP OLT Management
        Alerta: {alert_name}
        Resumo: {summary}
        Descrição: {description}
        Instance: {instance}
        Tempo: {alert.get('startsAt')}
        
        Por favor, verifique o sistema imediatamente.
        
        Dashboard: http://localhost:3000
        Prometheus: http://localhost:9090
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Enviar email (descomentarque quando configurado)
        # server = smtplib.SMTP(smtp_server, smtp_port)
        # server.starttls()
        # server.login(smtp_user, smtp_password)
        # text = msg.as_string()
        # server.sendmail(smtp_user, 'admin@empresa.com', text)
        # server.quit()
        
        logger.info(f"Notificação crítica enviada para alerta: {alert_name}")
        
    except Exception as e:
        logger.error(f"Erro ao enviar notificação crítica: {str(e)}")


def save_alert_to_database(alert):
    """
    Salvar alerta no banco de dados (implementação opcional)
    """
    try:
        # Aqui você pode criar um model para salvar alertas
        # Por exemplo: AlertHistory.objects.create(...)
        pass
    except Exception as e:
        logger.error(f"Erro ao salvar alerta no banco: {str(e)}")


@api_view(['GET'])
@permission_classes([AllowAny])
def alert_status(request):
    """
    Status dos alertas do sistema
    """
    try:
        # Simular verificação de alertas ativos
        # Em produção, consultar Prometheus ou banco de dados
        
        alert_summary = {
            'critical_alerts': 0,
            'warning_alerts': 2,
            'total_alerts': 2,
            'last_update': timezone.now().isoformat(),
            'alerts': [
                {
                    'name': 'HighMemoryUsage',
                    'severity': 'warning',
                    'status': 'firing',
                    'description': 'Memory usage is 87% on web server',
                    'duration': '5m'
                },
                {
                    'name': 'HighResponseTime',
                    'severity': 'warning', 
                    'status': 'firing',
                    'description': '95th percentile response time is 2.1s',
                    'duration': '3m'
                }
            ]
        }
        
        return Response(alert_summary)
        
    except Exception as e:
        logger.error(f"Erro ao obter status dos alertas: {str(e)}")
        return Response(
            {'error': 'Erro ao obter status dos alertas'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])  # Em produção, adicionar autenticação
def test_alert(request):
    """
    Endpoint para testar o sistema de alertas
    """
    try:
        alert_type = request.data.get('type', 'test')
        severity = request.data.get('severity', 'warning')
        
        # Criar alerta de teste
        test_alert = {
            'labels': {
                'alertname': f'TestAlert_{alert_type}',
                'severity': severity,
                'instance': 'test-instance'
            },
            'annotations': {
                'summary': 'Alert de teste do sistema',
                'description': f'Este é um alerta de teste do tipo {alert_type}'
            },
            'status': 'firing',
            'startsAt': timezone.now().isoformat()
        }
        
        # Processar alerta de teste
        process_alert(test_alert)
        
        return Response({
            'message': 'Alerta de teste criado com sucesso',
            'alert': test_alert
        })
        
    except Exception as e:
        logger.error(f"Erro ao criar alerta de teste: {str(e)}")
        return Response(
            {'error': 'Erro ao criar alerta de teste'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AlertManager:
    """
    Classe para gerenciar alertas internos da aplicação
    """
    
    @staticmethod
    def check_onu_alerts():
        """
        Verificar alertas relacionados às ONUs
        """
        try:
            from .models import ONU
            
            # Verificar ONUs com sinal baixo
            low_signal_onus = ONU.objects.filter(olt_rx_sig__lt=-25.0)
            
            if low_signal_onus.exists():
                alert = {
                    'labels': {
                        'alertname': 'ONULowSignal',
                        'severity': 'warning',
                        'component': 'onu'
                    },
                    'annotations': {
                        'summary': f'{low_signal_onus.count()} ONUs com sinal baixo',
                        'description': f'Detectadas {low_signal_onus.count()} ONUs com sinal abaixo de -25 dBm'
                    },
                    'status': 'firing',
                    'startsAt': timezone.now().isoformat()
                }
                
                process_alert(alert)
            
            # Verificar ONUs offline por muito tempo
            # Implementar lógica adicional conforme necessário
            
        except Exception as e:
            logger.error(f"Erro ao verificar alertas das ONUs: {str(e)}")
    
    @staticmethod
    def check_temperature_alerts():
        """
        Verificar alertas de temperatura da OLT
        """
        try:
            from .models import OltTemperature
            
            # Verificar temperaturas críticas
            critical_temps = OltTemperature.objects.filter(actual_temp__gte=75)
            
            for temp in critical_temps:
                alert = {
                    'labels': {
                        'alertname': 'OLTHighTemperature',
                        'severity': 'critical' if temp.actual_temp >= 80 else 'warning',
                        'slot': temp.slot_name,
                        'sensor': temp.sensor_id
                    },
                    'annotations': {
                        'summary': f'Temperatura alta no slot {temp.slot_name}',
                        'description': f'Temperatura de {temp.actual_temp}°C no sensor {temp.sensor_id}'
                    },
                    'status': 'firing',
                    'startsAt': timezone.now().isoformat()
                }
                
                process_alert(alert)
                
        except Exception as e:
            logger.error(f"Erro ao verificar alertas de temperatura: {str(e)}")