#!/bin/bash

# Script de deploy para backupctl
# Uso: ./scripts/deploy.sh [environment]

set -euo pipefail

# Configurações
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-production}"

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funções de log
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica pré-requisitos
check_prerequisites() {
    log_info "Verificando pré-requisitos..."
    
    # Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 não encontrado"
        exit 1
    fi
    
    # pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 não encontrado"
        exit 1
    fi
    
    # PostgreSQL client
    if ! command -v psql &> /dev/null; then
        log_warning "PostgreSQL client não encontrado - instalando..."
        sudo apt-get update && sudo apt-get install -y postgresql-client
    fi
    
    # AWS CLI (opcional)
    if ! command -v aws &> /dev/null; then
        log_warning "AWS CLI não encontrado - recomendado para testes"
    fi
    
    log_success "Pré-requisitos verificados"
}

# Configura ambiente
setup_environment() {
    log_info "Configurando ambiente: $ENVIRONMENT"
    
    # Cria diretórios
    sudo mkdir -p /etc/backupctl
    sudo mkdir -p /var/log/backupctl
    sudo mkdir -p /tmp/postgres_backups
    sudo mkdir -p /tmp/postgres_restore
    
    # Permissões
    sudo chown -R $USER:$USER /tmp/postgres_backups /tmp/postgres_restore
    sudo chown -R $USER:$USER /var/log/backupctl
    
    # Configuração
    if [ ! -f "/etc/backupctl/config.yaml" ]; then
        log_info "Copiando configuração de exemplo..."
        sudo cp "$PROJECT_DIR/config/config.yaml" "/etc/backupctl/config.yaml.example"
        
        log_warning "Edite /etc/backupctl/config.yaml com suas configurações"
        log_warning "Ou copie seu arquivo de configuração para /etc/backupctl/config.yaml"
    fi
    
    log_success "Ambiente configurado"
}

# Instala pacote
install_package() {
    log_info "Instalando backupctl..."
    
    cd "$PROJECT_DIR"
    
    # Virtual environment (recomendado)
    if [ ! -d "venv" ]; then
        log_info "Criando virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    # Instala dependências
    pip install -r requirements.txt
    
    # Instala pacote
    pip install -e .
    
    log_success "backupctl instalado"
}

# Configura variáveis de ambiente
setup_env_file() {
    log_info "Configurando variáveis de ambiente..."
    
    ENV_FILE="/etc/backupctl/environment"
    
    if [ ! -f "$ENV_FILE" ]; then
        cat > "$ENV_FILE" << EOF
# PostgreSQL Configuration
export PG_HOST=localhost
export PG_PORT=5432
export PG_USER=postgres
export PG_PASSWORD=your_password_here
export PG_DATABASE=postgres

# AWS Configuration
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_DEFAULT_REGION=us-east-1
export S3_BUCKET=your-backup-bucket
export S3_PREFIX=backups

# BackupCTL Configuration
export BACKUPCTL_CONFIG=/etc/backupctl/config.yaml
export LOG_LEVEL=INFO
EOF
        
        log_warning "Edite $ENV_FILE com suas credenciais"
    fi
    
    # Adiciona ao profile
    if ! grep -q "source $ENV_FILE" /etc/profile; then
        echo "source $ENV_FILE" | sudo tee -a /etc/profile
    fi
    
    log_success "Variáveis de ambiente configuradas"
}

# Configura cron
setup_cron() {
    log_info "Configurando agendamento via cron..."
    
    CRON_FILE="/etc/cron.d/backupctl"
    
    sudo tee "$CRON_FILE" > /dev/null << EOF
# BackupCTL - Agendamento automático
# Editar conforme necessário

# Backup completo todo domingo às 2AM
0 2 * * 0 $USER source /etc/backupctl/environment && /usr/local/bin/backupctl backup full --label "weekly-full" >> /var/log/backupctl.log 2>&1

# Backup incremental a cada 6 horas
0 */6 * * * $USER source /etc/backupctl/environment && /usr/local/bin/backupctl backup incremental --label "wal-archive" >> /var/log/backupctl.log 2>&1

# Limpeza todo domingo às 3AM
0 3 * * 0 $USER source /etc/backupctl/environment && /usr/local/bin/backupctl prune >> /var/log/backupctl.log 2>&1

# Health check a cada 30 minutos
*/30 * * * * $USER /usr/local/bin/backupctl/scripts/healthcheck.sh >> /var/log/backupctl.log 2>&1
EOF
    
    # Recarrega cron
    sudo service cron reload
    
    log_success "Cron configurado"
}

# Configura logrotate
setup_logrotate() {
    log_info "Configurando logrotate..."
    
    LOGROTATE_FILE="/etc/logrotate.d/backupctl"
    
    sudo tee "$LOGROTATE_FILE" > /dev/null << EOF
/var/log/backupctl.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        # Envia sinal para processos backupctl se necessário
        kill -USR1 \$(cat /var/run/backupctl.pid 2>/dev/null || echo 0) 2>/dev/null || true
    endscript
}
EOF
    
    log_success "Logrotate configurado"
}

# Executa testes
run_tests() {
    log_info "Executando testes de deploy..."
    
    source /etc/backupctl/environment
    
    # Testa configuração
    if ! backupctl config-show &> /dev/null; then
        log_error "Falha na configuração"
        exit 1
    fi
    
    # Testa conectividade
    if ! backupctl test &> /dev/null; then
        log_error "Falha nos testes de conectividade"
        exit 1
    fi
    
    log_success "Testes passaram"
}

# Cria serviço systemd (opcional)
setup_systemd() {
    log_info "Configurando serviço systemd..."
    
    SERVICE_FILE="/etc/systemd/system/backupctl.service"
    
    sudo tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=BackupCTL Scheduler Service
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=$USER
Environment=BACKUPCTL_CONFIG=/etc/backupctl/config.yaml
EnvironmentFile=/etc/backupctl/environment
ExecStart=/usr/local/bin/backupctl schedule --daemon
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    sudo systemctl daemon-reload
    sudo systemctl enable backupctl
    
    log_success "Serviço systemd configurado"
    log_info "Inicie com: sudo systemctl start backupctl"
}

# Função principal
main() {
    log_info "Iniciando deploy do backupctl para ambiente: $ENVIRONMENT"
    
    check_prerequisites
    setup_environment
    install_package
    setup_env_file
    setup_cron
    setup_logrotate
    run_tests
    
    if [ "$ENVIRONMENT" = "production" ]; then
        setup_systemd
    fi
    
    log_success "Deploy concluído com sucesso!"
    
    echo
    log_info "Próximos passos:"
    echo "1. Edite /etc/backupctl/config.yaml com suas configurações"
    echo "2. Edite /etc/backupctl/environment com suas credenciais"
    echo "3. Execute: source /etc/backupctl/environment"
    echo "4. Teste: backupctl test"
    echo "5. Crie primeiro backup: backupctl backup full --label 'first-backup'"
    
    if [ "$ENVIRONMENT" = "production" ]; then
        echo "6. Inicie serviço: sudo systemctl start backupctl"
        echo "7. Verifique status: sudo systemctl status backupctl"
    fi
    
    echo
    log_info "Logs disponíveis em: /var/log/backupctl.log"
}

# Executa main
main "$@"