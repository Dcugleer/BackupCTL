#!/bin/bash

# Health check script para backupctl
# Verifica se os serviços estão funcionando corretamente

set -euo pipefail

# Configurações
LOG_FILE="/var/log/backupctl.log"
LOCK_FILE="/tmp/backupctl_healthcheck.lock"
MAX_AGE_HOURS=24  # Máximo idade do último backup completo

# Função de log
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Verifica se já está rodando
if [ -f "$LOCK_FILE" ]; then
    if [ $(($(date +%s) - $(stat -c %Y "$LOCK_FILE"))) -gt 3600 ]; then
        log "WARNING: Lock file antigo removido"
        rm -f "$LOCK_FILE"
    else
        log "WARNING: Health check já está rodando"
        exit 1
    fi
fi

# Cria lock file
touch "$LOCK_FILE"
trap "rm -f $LOCK_FILE" EXIT

log "Iniciando health check"

# Verifica se backupctl está instalado
if ! command -v backupctl &> /dev/null; then
    log "ERROR: backupctl não encontrado no PATH"
    exit 1
fi

# Verifica configuração
if ! backupctl config_show &> /dev/null; then
    log "ERROR: Falha na configuração do backupctl"
    exit 1
fi

# Verifica conectividade
if ! backupctl test &> /dev/null; then
    log "ERROR: Falha nos testes de conectividade"
    exit 1
fi

# Verifica último backup completo
LAST_BACKUP=$(backupctl status --type full --last 1 --json-output 2>/dev/null | jq -r '.backups[0].backup_id // empty')

if [ -z "$LAST_BACKUP" ]; then
    log "WARNING: Nenhum backup completo encontrado"
    exit 1
fi

# Verifica idade do último backup
BACKUP_AGE=$(backupctl status --type full --last 1 --json-output 2>/dev/null | jq -r '.backups[0].start_ts // empty')

if [ -n "$BACKUP_AGE" ]; then
    BACKUP_TIMESTAMP=$(date -d "$BACKUP_AGE" +%s 2>/dev/null || echo 0)
    CURRENT_TIMESTAMP=$(date +%s)
    AGE_HOURS=$(( (CURRENT_TIMESTAMP - BACKUP_TIMESTAMP) / 3600 ))
    
    if [ "$AGE_HOURS" -gt "$MAX_AGE_HOURS" ]; then
        log "WARNING: Último backup completo tem mais de ${MAX_AGE_HOURS} horas (${AGE_HOURS}h)"
        exit 1
    fi
fi

# Verifica espaço em disco
BACKUP_DIR=$(backupctl config_show 2>/dev/null | grep "backup_dir" | awk '{print $2}' || echo "/tmp")
DISK_USAGE=$(df "$BACKUP_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')

if [ "$DISK_USAGE" -gt 90 ]; then
    log "WARNING: Uso de disco alto em $BACKUP_DIR: ${DISK_USAGE}%"
fi

# Verifica se há backups falhados recentes
FAILED_BACKUPS=$(backupctl status --last 20 --json-output 2>/dev/null | jq '.backups[] | select(.status == "failed") | .backup_id' | wc -l)

if [ "$FAILED_BACKUPS" -gt 2 ]; then
    log "WARNING: Muitos backups falhados recentemente: $FAILED_BACKUPS"
    exit 1
fi

# Verifica se o scheduler está rodando (se configurado)
if pgrep -f "backupctl schedule" > /dev/null; then
    log "Scheduler está rodando"
else
    log "INFO: Scheduler não está rodando (pode ser normal se não configurado)"
fi

# Verifica logs de erro recentes
RECENT_ERRORS=$(grep -c "ERROR" "$LOG_FILE" 2>/dev/null | tail -100 || echo "0")

if [ "$RECENT_ERRORS" -gt 5 ]; then
    log "WARNING: Muitos erros recentes no log: $RECENT_ERRORS"
fi

log "Health check concluído com sucesso"

# Envia métricas para monitoring (opcional)
if command -v curl &> /dev/null && [ -n "${METRICS_ENDPOINT:-}" ]; then
    curl -s -X POST "$METRICS_ENDPOINT" \
        -H "Content-Type: application/json" \
        -d "{
            \"service\": \"backupctl\",
            \"status\": \"healthy\",
            \"last_backup\": \"$LAST_BACKUP\",
            \"disk_usage\": $DISK_USAGE,
            \"failed_backups\": $FAILED_BACKUPS,
            \"timestamp\": \"$(date -Iseconds)\"
        }" || true
fi

exit 0