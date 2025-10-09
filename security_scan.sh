#!/bin/bash
# SCRIPT DE VERIFICAÇÃO DE SEGURANÇA - DETECÇÃO DE MALWARE
# Criado para detectar ataques como Kinsing e outros malwares
# Data: $(date)

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Função para log colorido
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[ALERTA]${NC} $1"
}

log_error() {
    echo -e "${RED}[PERIGO]${NC} $1"
}

log_title() {
    echo -e "${PURPLE}===============================================${NC}"
    echo -e "${PURPLE}$1${NC}"
    echo -e "${PURPLE}===============================================${NC}"
}

# Arquivo de relatório
REPORT_FILE="/root/security_scan_$(date +%Y%m%d_%H%M%S).txt"
echo "RELATÓRIO DE VERIFICAÇÃO DE SEGURANÇA - $(date)" > $REPORT_FILE
echo "=======================================================" >> $REPORT_FILE

log_title "🔍 VERIFICAÇÃO COMPLETA DE SEGURANÇA - DETECÇÃO DE MALWARE"
echo "📝 Relatório será salvo em: $REPORT_FILE"
echo ""

# 1. VERIFICAÇÃO DE PROCESSOS SUSPEITOS
log_title "1. 🔍 VERIFICAÇÃO DE PROCESSOS SUSPEITOS"
echo "" >> $REPORT_FILE
echo "=== PROCESSOS SUSPEITOS ===" >> $REPORT_FILE

SUSPICIOUS_PROCESSES=("kinsing" "xmrig" "monero" "crypto" "miner" "update.sh" "masscan" "zgrab" "zmap" "phpguard" "bioset" ".systemd-resolve" "systemd-network" "networkd-dispatcher")

FOUND_SUSPICIOUS=false
for process in "${SUSPICIOUS_PROCESSES[@]}"; do
    if pgrep -f "$process" > /dev/null 2>&1; then
        log_error "Processo suspeito encontrado: $process"
        echo "SUSPEITO: Processo $process encontrado" >> $REPORT_FILE
        ps aux | grep -i "$process" | grep -v grep >> $REPORT_FILE
        FOUND_SUSPICIOUS=true
    fi
done

# Verificação especial para kthreadd - só alertar se não for PID 2
if pgrep -f "kthreadd" > /dev/null 2>&1; then
    KTHREADD_PID=$(pgrep -f "kthreadd")
    if [ "$KTHREADD_PID" != "2" ]; then
        log_error "Processo kthreadd suspeito encontrado (PID não é 2): PID $KTHREADD_PID"
        echo "SUSPEITO: kthreadd malicioso com PID $KTHREADD_PID" >> $REPORT_FILE
        ps aux | grep kthreadd | grep -v grep >> $REPORT_FILE
        FOUND_SUSPICIOUS=true
    else
        log_info "kthreadd legítimo detectado (PID 2) - OK"
        echo "OK: kthreadd legítimo (PID 2)" >> $REPORT_FILE
    fi
fi

if [ "$FOUND_SUSPICIOUS" = false ]; then
    log_success "Nenhum processo suspeito encontrado"
    echo "OK: Nenhum processo suspeito encontrado" >> $REPORT_FILE
fi

# 2. VERIFICAÇÃO DE ARQUIVOS MALICIOSOS
log_title "2. 🗂️ VERIFICAÇÃO DE ARQUIVOS MALICIOSOS"
echo "" >> $REPORT_FILE
echo "=== ARQUIVOS MALICIOSOS ===" >> $REPORT_FILE

MALICIOUS_FILES=("/tmp/kinsing" "/tmp/kdevtmpfsi" "/tmp/update.sh" "/tmp/.systemd-resolve" "/var/tmp/kinsing" "/dev/shm/kinsing" "/usr/bin/kthreadd" "/usr/bin/bioset" "/tmp/masscan" "/tmp/zgrab" "/tmp/zmap" "/tmp/phpguard" "/tmp/.kinsing" "/tmp/.update.sh")

FOUND_MALICIOUS=false
for file in "${MALICIOUS_FILES[@]}"; do
    if [ -f "$file" ]; then
        log_error "Arquivo malicioso encontrado: $file"
        echo "MALICIOSO: $file" >> $REPORT_FILE
        ls -la "$file" >> $REPORT_FILE
        file "$file" >> $REPORT_FILE
        FOUND_MALICIOUS=true
    fi
done

if [ "$FOUND_MALICIOUS" = false ]; then
    log_success "Nenhum arquivo malicioso conhecido encontrado"
    echo "OK: Nenhum arquivo malicioso conhecido encontrado" >> $REPORT_FILE
fi

# 3. VERIFICAÇÃO DE CONEXÕES SUSPEITAS
log_title "3. 🌐 VERIFICAÇÃO DE CONEXÕES DE REDE SUSPEITAS"
echo "" >> $REPORT_FILE
echo "=== CONEXÕES DE REDE ===" >> $REPORT_FILE

log_info "Verificando conexões ativas..."
netstat -tuln >> $REPORT_FILE
echo "" >> $REPORT_FILE

# Verificar portas expostas perigosas
DANGEROUS_PORTS=("5432" "6379" "27017" "3306" "1433" "5984" "6380" "11211")
EXPOSED_PORTS=false

for port in "${DANGEROUS_PORTS[@]}"; do
    if netstat -tuln | grep ":$port " | grep "0.0.0.0" > /dev/null; then
        log_error "Porta perigosa exposta externamente: $port"
        echo "PERIGO: Porta $port exposta externamente" >> $REPORT_FILE
        EXPOSED_PORTS=true
    fi
done

if [ "$EXPOSED_PORTS" = false ]; then
    log_success "Nenhuma porta de banco de dados exposta externamente"
    echo "OK: Portas de bancos protegidas" >> $REPORT_FILE
fi

# 4. VERIFICAÇÃO DE CRONTABS SUSPEITOS
log_title "4. ⏰ VERIFICAÇÃO DE CRONTABS SUSPEITOS"
echo "" >> $REPORT_FILE
echo "=== CRONTABS ===" >> $REPORT_FILE

log_info "Verificando crontabs do sistema..."
if [ -f "/etc/crontab" ]; then
    echo "Crontab do sistema:" >> $REPORT_FILE
    cat /etc/crontab >> $REPORT_FILE
fi

echo "" >> $REPORT_FILE
echo "Crontabs de usuários:" >> $REPORT_FILE
for user in $(cut -f1 -d: /etc/passwd); do
    if crontab -u $user -l > /dev/null 2>&1; then
        echo "=== Crontab do usuário $user ===" >> $REPORT_FILE
        crontab -u $user -l >> $REPORT_FILE
        echo "" >> $REPORT_FILE
    fi
done

# Verificar crontabs suspeitos
if grep -r "kinsing\|update\.sh\|masscan\|xmrig" /var/spool/cron/ /etc/cron* 2>/dev/null; then
    log_error "Crontab suspeito encontrado!"
    echo "SUSPEITO: Crontab malicioso encontrado" >> $REPORT_FILE
    grep -r "kinsing\|update\.sh\|masscan\|xmrig" /var/spool/cron/ /etc/cron* 2>/dev/null >> $REPORT_FILE
else
    log_success "Nenhum crontab suspeito encontrado"
    echo "OK: Nenhum crontab suspeito encontrado" >> $REPORT_FILE
fi

# 5. VERIFICAÇÃO DE USO DE CPU/MEMÓRIA
log_title "5. 📊 VERIFICAÇÃO DE USO DE RECURSOS"
echo "" >> $REPORT_FILE
echo "=== USO DE RECURSOS ===" >> $REPORT_FILE

log_info "Verificando processos com alto uso de CPU..."
echo "Top 10 processos por CPU:" >> $REPORT_FILE
ps aux --sort=-%cpu | head -10 >> $REPORT_FILE

echo "" >> $REPORT_FILE
echo "Top 10 processos por Memória:" >> $REPORT_FILE
ps aux --sort=-%mem | head -10 >> $REPORT_FILE

# Alertar se há processos usando muito CPU
HIGH_CPU=$(ps aux --sort=-%cpu | awk 'NR==2{print $3}' | cut -d'.' -f1)
if [ "$HIGH_CPU" -gt 80 ]; then
    log_warning "Processo usando CPU alta detectado: ${HIGH_CPU}%"
    echo "ALERTA: Uso de CPU alto: ${HIGH_CPU}%" >> $REPORT_FILE
fi

# 6. VERIFICAÇÃO DE MODIFICAÇÕES RECENTES
log_title "6. 📅 VERIFICAÇÃO DE MODIFICAÇÕES RECENTES"
echo "" >> $REPORT_FILE
echo "=== MODIFICAÇÕES RECENTES ===" >> $REPORT_FILE

log_info "Verificando arquivos modificados nas últimas 24 horas em /tmp..."
find /tmp -type f -mtime -1 -ls >> $REPORT_FILE 2>/dev/null

echo "" >> $REPORT_FILE
log_info "Verificando arquivos executáveis criados recentemente..."
find /tmp /var/tmp /dev/shm -type f -executable -mtime -7 -ls >> $REPORT_FILE 2>/dev/null

# 7. VERIFICAÇÃO DE LOGS SUSPEITOS
log_title "7. 📋 VERIFICAÇÃO DE LOGS SUSPEITOS"
echo "" >> $REPORT_FILE
echo "=== LOGS SUSPEITOS ===" >> $REPORT_FILE

log_info "Verificando logs de autenticação..."
if [ -f "/var/log/auth.log" ]; then
    grep -i "failed\|invalid\|illegal" /var/log/auth.log | tail -20 >> $REPORT_FILE
fi

log_info "Verificando logs do sistema..."
if [ -f "/var/log/syslog" ]; then
    grep -i "kinsing\|xmrig\|miner\|crypto" /var/log/syslog | tail -20 >> $REPORT_FILE
fi

# 8. VERIFICAÇÃO DE DOCKER
log_title "8. 🐳 VERIFICAÇÃO DE SEGURANÇA DOCKER"
echo "" >> $REPORT_FILE
echo "=== DOCKER SECURITY ===" >> $REPORT_FILE

log_info "Verificando containers em execução..."
docker ps >> $REPORT_FILE 2>/dev/null

echo "" >> $REPORT_FILE
log_info "Verificando portas expostas pelos containers..."
docker ps --format "table {{.Names}}\t{{.Ports}}" >> $REPORT_FILE 2>/dev/null

# 9. VERIFICAÇÃO DE USUÁRIOS SUSPEITOS
log_title "9. 👥 VERIFICAÇÃO DE USUÁRIOS SUSPEITOS"
echo "" >> $REPORT_FILE
echo "=== USUÁRIOS DO SISTEMA ===" >> $REPORT_FILE

log_info "Verificando usuários do sistema..."
cat /etc/passwd >> $REPORT_FILE

echo "" >> $REPORT_FILE
log_info "Verificando últimos logins..."
last -10 >> $REPORT_FILE

# 10. VERIFICAÇÃO DE INTEGRIDADE DE ARQUIVOS IMPORTANTES
log_title "10. 🛡️ VERIFICAÇÃO DE INTEGRIDADE"
echo "" >> $REPORT_FILE
echo "=== INTEGRIDADE DE ARQUIVOS ===" >> $REPORT_FILE

IMPORTANT_FILES=("/etc/passwd" "/etc/shadow" "/etc/hosts" "/etc/crontab" "/etc/ssh/sshd_config")

for file in "${IMPORTANT_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "Checksum de $file:" >> $REPORT_FILE
        md5sum "$file" >> $REPORT_FILE
    fi
done

# RESUMO FINAL
log_title "📊 RESUMO DA VERIFICAÇÃO"
echo "" >> $REPORT_FILE
echo "=== RESUMO FINAL ===" >> $REPORT_FILE

TOTAL_ISSUES=0

if [ "$FOUND_SUSPICIOUS" = true ]; then
    log_error "❌ Processos suspeitos encontrados!"
    echo "CRÍTICO: Processos suspeitos encontrados" >> $REPORT_FILE
    ((TOTAL_ISSUES++))
fi

if [ "$FOUND_MALICIOUS" = true ]; then
    log_error "❌ Arquivos maliciosos encontrados!"
    echo "CRÍTICO: Arquivos maliciosos encontrados" >> $REPORT_FILE
    ((TOTAL_ISSUES++))
fi

if [ "$EXPOSED_PORTS" = true ]; then
    log_error "❌ Portas perigosas expostas!"
    echo "CRÍTICO: Portas de banco expostas" >> $REPORT_FILE
    ((TOTAL_ISSUES++))
fi

if [ $TOTAL_ISSUES -eq 0 ]; then
    log_success "✅ Sistema aparenta estar seguro!"
    echo "RESULTADO: Sistema aparenta estar SEGURO" >> $REPORT_FILE
else
    log_error "❌ $TOTAL_ISSUES problemas críticos encontrados!"
    echo "RESULTADO: $TOTAL_ISSUES problemas críticos encontrados" >> $REPORT_FILE
fi

echo ""
echo "📝 Relatório completo salvo em: $REPORT_FILE"
echo "📧 Recomendação: Analise o relatório e tome as ações necessárias"
echo ""

# Sugestões de ação
if [ $TOTAL_ISSUES -gt 0 ]; then
    log_title "🚨 AÇÕES RECOMENDADAS"
    echo "1. 🔍 Analise os processos e arquivos suspeitos encontrados"
    echo "2. 🗑️ Remove arquivos maliciosos identificados"
    echo "3. 🔒 Feche portas expostas desnecessariamente"
    echo "4. 🔄 Reinicie o sistema após limpeza"
    echo "5. 🛡️ Execute este script novamente para verificar"
    echo "6. 📈 Configure monitoramento contínuo"
fi

echo ""
log_info "Verificação concluída em $(date)"