# Makefile para Sistema ISP
SHELL:=/bin/bash
ARGS = $(filter-out $@,$(MAKECMDGOALS))
MAKEFLAGS += --silent
BASE_PATH=${PWD}
PYTHON_EXEC=python
DOCKER_COMPOSE_FILE=$(shell echo -f docker-compose.yml)

# Cores para output
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
WHITE := \033[37m
RESET := \033[0m

show_env:
	# Show wich DOCKER_COMPOSE_FILE and ENV the recipes will user
	# It should be referenced by all other recipes you want it to show.
	# It's only printed once even when more than a recipe executed uses it
	sh -c "if [ \"${ENV_PRINTED:-0}\" != \"1\" ]; \
	then \
		echo DOCKER_COMPOSE_FILE = \"${DOCKER_COMPOSE_FILE}\"; \
		echo OSFLAG = \"${OSFLAG}\"; \
	fi; \
	ENV_PRINTED=1;"

help: ## Mostrar esta ajuda
	@echo "$(CYAN)Sistema ISP - Comandos Disponíveis$(RESET)"
	@echo "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# ==================== SISTEMA COMPLETO ====================

install: ## Instalar e configurar sistema completo
	@echo "$(BLUE)🚀 Instalando Sistema ISP...$(RESET)"
	@python start_system.py

start: show_env ## Iniciar sistema completo
	@echo "$(GREEN)▶️  Iniciando sistema completo...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} up -d
	@echo "$(GREEN)✅ Sistema iniciado!$(RESET)"
	@make health

up: start ## Alias para start

stop: show_env ## Parar sistema completo
	@echo "$(YELLOW)⏹️  Parando sistema...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} down
	@echo "$(YELLOW)✅ Sistema parado!$(RESET)"

restart: show_env ## Reiniciar sistema completo
	@echo "$(CYAN)🔄 Reiniciando sistema...$(RESET)"
	@make stop
	@sleep 3
	@make start

_rebuild: show_env ## Rebuild completo dos containers
	@echo "$(BLUE)🔨 Rebuild completo...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} down
	@docker-compose ${DOCKER_COMPOSE_FILE} build --no-cache --force-rm
	@make start

build: show_env ## Construir imagens Docker
	@echo "$(BLUE)🔨 Construindo imagens...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} build --no-cache

# ==================== STATUS E LOGS ====================

status: show_env ## Mostrar status dos serviços
	@echo "$(CYAN)📊 Status dos serviços:$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} ps

logs: show_env ## Mostrar logs em tempo real
	@echo "$(CYAN)📋 Logs do sistema:$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200

log: show_env ## Logs apenas da aplicação web
	@docker-compose ${DOCKER_COMPOSE_FILE} logs -f --tail 200 web

logs-app: show_env ## Mostrar logs apenas da aplicação
	@echo "$(CYAN)📋 Logs da aplicação:$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} logs -f web rq_worker scheduler

logs-db: show_env ## Logs do banco de dados
	@docker-compose ${DOCKER_COMPOSE_FILE} logs -f db

logs-redis: show_env ## Logs do Redis
	@docker-compose ${DOCKER_COMPOSE_FILE} logs -f redis

# ==================== HEALTH CHECKS ====================

health: ## Verificar saúde dos serviços
	@echo "$(CYAN)🔍 Verificando saúde dos serviços...$(RESET)"
	@echo "$(WHITE)Aguardando serviços ficarem prontos...$(RESET)"
	@sleep 10
	@echo "$(GREEN)📱 Django App:$(RESET)"
	@curl -s http://localhost:8000/api/health/ | python -m json.tool 2>/dev/null || echo "❌ Não disponível"

test-health: ## Testar todos os endpoints de health
	@echo "$(CYAN)🔍 Testando endpoints de saúde...$(RESET)"
	@echo "$(WHITE)Basic Health:$(RESET)"
	@curl -s http://localhost:8000/api/health/ | python -m json.tool
	@echo "\n$(WHITE)Detailed Health:$(RESET)"
	@curl -s http://localhost:8000/api/health/detailed/ | python -m json.tool
	@echo "\n$(WHITE)Readiness:$(RESET)"
	@curl -s http://localhost:8000/api/health/readiness/ | python -m json.tool
	@echo "\n$(WHITE)Liveness:$(RESET)"
	@curl -s http://localhost:8000/api/health/liveness/ | python -m json.tool

# ==================== DJANGO MANAGEMENT ====================

sh: show_env ## Shell do container web
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web bash

shell_plus: show_env ## Django shell_plus
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} ./manage.py shell_plus

manage: show_env ## Executar comando Django manage.py
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py ${ARGS}

migrate: show_env ## Executar migrações do banco
	@echo "$(BLUE)💾 Executando migrações...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py migrate

makemigrations: show_env ## Criar migrações
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py makemigrations ${ARGS}
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py migrate

createsuperuser: show_env ## Criar superusuário
	@echo "$(BLUE)👤 Criando superusuário...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} ./manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@localhost', 'admin123'); print('Superuser: admin/admin123')"

collectstatic: show_env ## Coletar arquivos estáticos
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py collectstatic --no-input

# ==================== ACESSO ====================

urls: ## Mostrar URLs de acesso
	@echo "$(MAGENTA)🌐 URLs de Acesso:$(RESET)"
	@echo "$(WHITE)================================$(RESET)"
	@echo "$(GREEN)📱 Aplicação Principal:$(RESET)"
	@echo "  • Django:          http://localhost:8000"
	@echo "  • Admin:           http://localhost:8000/admin/ (admin/admin123)"
	@echo "  • API:             http://localhost:8000/api/"
	@echo "  • Health Check:    http://localhost:8000/api/health/"

# ==================== BACKUP E RESTORE ====================

backup: show_env ## Fazer backup do banco de dados
	@echo "$(YELLOW)💾 Fazendo backup do banco...$(RESET)"
	@mkdir -p backups
	@docker-compose ${DOCKER_COMPOSE_FILE} exec db pg_dump -U postgres postgres > backups/backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Backup salvo em backups/$(RESET)"

restore: show_env ## Restaurar backup do banco (use: make restore FILE=backup.sql)
	@echo "$(YELLOW)📥 Restaurando backup...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} exec -T db psql -U postgres -d postgres < $(FILE)
	@echo "$(GREEN)✅ Backup restaurado!$(RESET)"

# ==================== LIMPEZA ====================

clean: show_env ## Limpar containers e imagens (PRESERVA VOLUMES DE DADOS)
	@echo "$(RED)🧹 Limpando sistema (PRESERVANDO DADOS)...$(RESET)"
	@echo "$(YELLOW)⚠️  Parando containers mas MANTENDO volumes de dados...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} down
	@docker system prune -f
	@echo "$(GREEN)✅ Limpeza concluída! (Dados preservados)$(RESET)"

clean-all: show_env ## ⚠️ PERIGOSO: Limpar TUDO incluindo volumes de dados
	@echo "$(RED)⚠️ ⚠️ ⚠️  ATENÇÃO: ESTA OPERAÇÃO VAI APAGAR TODOS OS DADOS! ⚠️ ⚠️ ⚠️$(RESET)"
	@echo "$(RED)Pressione Ctrl+C nos próximos 10 segundos para cancelar...$(RESET)"
	@sleep 10
	@echo "$(RED)🧹 Limpando sistema INCLUINDO VOLUMES DE DADOS...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} down -v
	@docker system prune -f
	@echo "$(GREEN)✅ Limpeza COMPLETA concluída! (TODOS OS DADOS FORAM PERDIDOS)$(RESET)"

clean-logs: ## Limpar logs antigos
	@echo "$(YELLOW)🧹 Limpando logs antigos...$(RESET)"
	@find logs/ -name "*.log.*" -mtime +7 -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Logs limpos!$(RESET)"

chown_project: ## Corrigir permissões dos arquivos
	@sudo chown -R "${USER}:${USER}" ./

# ==================== DESENVOLVIMENTO ====================

dev-setup: ## Setup completo para desenvolvimento
	@echo "$(BLUE)🛠️  Configurando ambiente de desenvolvimento...$(RESET)"
	@make build
	@make start
	@sleep 20
	@make migrate
	@make createsuperuser
	@make health
	@make urls

dev-restart: show_env ## Restart rápido para desenvolvimento
	@docker-compose ${DOCKER_COMPOSE_FILE} restart web rq_worker

test: show_env ## Executar testes
	@echo "$(BLUE)🧪 Executando testes...$(RESET)"
	@docker-compose ${DOCKER_COMPOSE_FILE} exec web ${PYTHON_EXEC} manage.py test

# ==================== PRODUÇÃO ====================

production-check: ## Verificar configurações para produção
	@echo "$(RED)🔒 Verificando configurações de produção...$(RESET)"
	@echo "$(WHITE)Verificando .env...$(RESET)"
	@grep -q "DEBUG=False" .env && echo "✅ DEBUG=False" || echo "❌ DEBUG deve ser False"
	@grep -q "SECRET_KEY=" .env && echo "✅ SECRET_KEY configurado" || echo "❌ SECRET_KEY não configurado"
	@echo "$(WHITE)Verificando HTTPS...$(RESET)"
	@grep -q "SECURE_SSL_REDIRECT" .env && echo "✅ SSL configurado" || echo "⚠️  Configure SSL para produção"

# ==================== ALIASES ====================

down: stop ## Alias para stop
ps: status ## Alias para status
rebuild: _rebuild ## Alias para _rebuild

# Default target
.DEFAULT_GOAL := help