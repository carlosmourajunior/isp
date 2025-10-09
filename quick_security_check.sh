#!/bin/bash
# SCRIPT DE VERIFICAÇÃO RÁPIDA DE SEGURANÇA
# Versão mais leve para execução frequente

echo "🔍 Verificação Rápida de Segurança - $(date)"
echo "============================================"

# 1. Verificar processos suspeitos
echo "🔍 Processos suspeitos:"
if pgrep -f "kinsing|xmrig|miner|update\.sh" > /dev/null; then
    echo "❌ ALERTA: Processo suspeito encontrado!"
    ps aux | grep -E "kinsing|xmrig|miner|update\.sh" | grep -v grep
else
    echo "✅ OK: Nenhum processo suspeito"
fi

# Verificação especial para kthreadd
if pgrep -f "kthreadd" > /dev/null; then
    KTHREADD_PID=$(pgrep -f "kthreadd")
    if [ "$KTHREADD_PID" != "2" ]; then
        echo "❌ ALERTA: kthreadd malicioso detectado (PID $KTHREADD_PID)!"
    else
        echo "✅ OK: kthreadd legítimo (PID 2)"
    fi
fi

# 2. Verificar arquivos maliciosos
echo ""
echo "🗂️ Arquivos maliciosos:"
if ls /tmp/kinsing /tmp/update.sh /var/tmp/kinsing 2>/dev/null; then
    echo "❌ ALERTA: Arquivos maliciosos encontrados!"
else
    echo "✅ OK: Nenhum arquivo malicioso conhecido"
fi

# 3. Verificar portas expostas
echo ""
echo "🌐 Portas de banco expostas:"
if netstat -tuln | grep -E ":5432|:6379|:3306" | grep "0.0.0.0"; then
    echo "❌ ALERTA: Porta de banco exposta!"
    netstat -tuln | grep -E ":5432|:6379|:3306" | grep "0.0.0.0"
else
    echo "✅ OK: Portas de banco protegidas"
fi

# 4. Verificar uso de CPU
echo ""
echo "📊 Uso de CPU:"
HIGH_CPU=$(ps aux --sort=-%cpu | awk 'NR==2{print $3}' | cut -d'.' -f1)
if [ "$HIGH_CPU" -gt 80 ]; then
    echo "⚠️ ALERTA: CPU alta: ${HIGH_CPU}%"
    ps aux --sort=-%cpu | head -3
else
    echo "✅ OK: CPU normal: ${HIGH_CPU}%"
fi

# 5. Verificar containers Docker
echo ""
echo "🐳 Status Docker:"
if docker ps --format "{{.Names}}: {{.Status}}" | grep -v "Up"; then
    echo "⚠️ ALERTA: Container com problema!"
else
    echo "✅ OK: Todos containers funcionando"
fi

echo ""
echo "Verificação rápida concluída!"