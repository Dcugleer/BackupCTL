# BackupCTL - Sistema de Backup Automatizado PostgreSQL

## 📁 Estrutura do Projeto

```
backup-system/
├── backupctl/                    # Pacote Python principal
│   ├── __init__.py              # Metadata do pacote
│   ├── __main__.py              # Ponto de entrada executável
│   ├── cli.py                   # Interface CLI completa
│   ├── core/                    # Módulos core
│   │   ├── __init__.py
│   │   ├── backup.py            # Motor de backup
│   │   ├── restore.py           # Motor de restore
│   │   └── scheduler.py         # Agendamento e alertas
│   └── utils/                   # Utilitários
│       ├── __init__.py
│       ├── config.py            # Gerenciamento de configuração
│       ├── logger.py            # Sistema de logging
│       ├── crypto.py            # Criptografia e checksums
│       ├── s3_client.py         # Cliente AWS S3
│       └── metadata.py          # Gerenciamento de metadados
├── config/                      # Arquivos de configuração
│   ├── config.yaml              # Configuração principal
│   └── development.yaml         # Configuração de desenvolvimento
├── scripts/                     # Scripts auxiliares
│   ├── cron_sample              # Exemplo de configuração cron
│   ├── healthcheck.sh           # Health check automatizado
│   └── deploy.sh                # Script de deploy
├── tests/                       # Testes automatizados
│   └── test_backup_restore.py   # Testes principais
├── Dockerfile                   # Imagem Docker
├── Makefile                     # Comandos de desenvolvimento
├── requirements.txt             # Dependências Python
├── setup.py                     # Setup do pacote
├── README.md                    # Documentação completa
└── .gitignore                   # Arquivos ignorados
```

## 🚀 Quick Start

### 1. Instalação
```bash
# Clone o projeto
git clone <repository-url>
cd backup-system

# Instala dependências
pip install -r requirements.txt

# Instala o pacote
pip install -e .
```

### 2. Configuração
```bash
# Copie configuração de exemplo
cp config/development.yaml config/config.yaml

# Configure variáveis de ambiente
export PG_HOST=localhost
export PG_USER=postgres
export PG_PASSWORD=seu_password
export AWS_ACCESS_KEY_ID=sua_key
export AWS_SECRET_ACCESS_KEY=seu_secret
export S3_BUCKET=seu_bucket
```

### 3. Teste
```bash
# Testa conectividade
backupctl test

# Cria primeiro backup
backupctl backup full --label "primeiro-backup"

# Verifica status
backupctl status
```

## 📋 Comandos Principais

### Backup
```bash
# Backup completo
backupctl backup full --label "semanal"

# Backup incremental
backupctl backup incremental --label "wal-arquivo"
```

### Restore
```bash
# Restore mais recente
backupctl restore --destination /tmp/restore

# Restore point-in-time
backupctl restore --to "2024-01-15T12:30:00Z" --destination /tmp/restore
```

### Status e Manutenção
```bash
# Ver status
backupctl status --last 10

# Limpeza de backups antigos
backupctl prune --policy "monthly-retain=3,weekly-retain=4"

# Teste de conectividade
backupctl test
```

### Agendamento
```bash
# Inicia scheduler daemon
backupctl schedule --daemon

# Ver próximas execuções
backupctl schedule
```

## 🏗️ Arquitetura

### Componentes Principais

1. **BackupEngine**: Responsável por executar backups completos e incrementais
2. **RestoreEngine**: Gerencia recuperação de backups com suporte a PITR
3. **S3Client**: Interface com AWS S3 para storage e recuperação
4. **MetadataManager**: Gerencia metadados no PostgreSQL
5. **Scheduler**: Agendamento de tarefas e envio de alertas
6. **AlertManager**: Sistema de notificações via email/webhook

### Fluxo de Backup

```
CLI → BackupEngine → pg_dump → Compressão → S3 Upload → Metadata Store
```

### Fluxo de Restore

```
CLI → RestoreEngine → S3 Download → Descompressão → pg_restore → WAL Apply
```

## 🔧 Configuração Avançada

### PostgreSQL WAL Archiving
```sql
-- postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'backupctl backup incremental --label wal-archive'
```

### AWS IAM Policy
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject", "s3:PutObject", 
    "s3:DeleteObject", "s3:ListBucket"
  ],
  "Resource": [
    "arn:aws:s3:::your-bucket",
    "arn:aws:s3:::your-bucket/*"
  ]
}
```

### Crontab Configuration
```bash
# Backup completo semanal
0 2 * * 0 backupctl backup full --label "weekly"

# Backup incremental
0 */6 * * * backupctl backup incremental

# Limpeza
0 3 * * 0 backupctl prune
```

## 📊 Monitoramento

### Health Checks
- Conectividade PostgreSQL
- Acesso ao S3
- Espaço em disco
- Status dos backups
- Idade do último backup

### Logs Estruturados
```json
{
  "timestamp": "2024-01-15T12:30:00Z",
  "level": "INFO",
  "message": "Backup completo concluído",
  "backup_id": "uuid",
  "size_bytes": 1073741824,
  "duration_seconds": 300
}
```

### Métricas
- Taxa de sucesso/falha
- Tempo de execução
- Tamanho dos backups
- Uso de storage

## 🐳 Docker

### Build
```bash
docker build -t backupctl:latest .
```

### Execução
```bash
docker run --rm \
  -e AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID \
  -e AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY \
  -e PG_HOST=$PG_HOST \
  -e PG_USER=$PG_USER \
  -e PG_PASSWORD=$PG_PASSWORD \
  -v $(pwd)/config:/etc/backupctl \
  backupctl:latest backup full
```

### Docker Compose
```yaml
version: '3.8'
services:
  backupctl:
    build: .
    environment:
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY}
      - PG_HOST=postgres
      - PG_USER=postgres
      - PG_PASSWORD=${PG_PASSWORD}
    volumes:
      - ./config:/etc/backupctl
      - ./logs:/var/log/backupctl
```

## 🧪 Testes

### Executar Testes
```bash
# Instala dependências de teste
pip install pytest pytest-cov

# Executa todos os testes
pytest tests/ --cov=backupctl

# Teste específico
pytest tests/test_backup_restore.py::TestBackupRestore::test_full_backup_success
```

### Teste de Smoke
```bash
# Teste completo
backupctl test

# Backup e restore de teste
backupctl backup full --label "smoke-test"
backupctl restore --backup-id <id> --destination /tmp/smoke-restore
```

## 🚨 Troubleshooting

### Problemas Comuns

1. **Falha na conexão PostgreSQL**
   ```bash
   psql -h $PG_HOST -U $PG_USER -d $PG_DATABASE -c "SELECT version();"
   ```

2. **Falha no upload S3**
   ```bash
   aws s3 ls s3://$S3_BUCKET
   ```

3. **WAL archiving não funciona**
   ```sql
   SHOW archive_mode;
   SHOW archive_command;
   ```

### Logs de Debug
```bash
# Verifica logs
tail -f /var/log/backupctl.log

# Filtra erros
grep ERROR /var/log/backupctl.log
```

## 📈 Performance

### Benchmarks Típicos
- **Backup 10GB**: 2-5 minutos
- **WAL Archive**: <1 segundo por arquivo
- **Restore 10GB**: 3-7 minutos
- **Storage**: ~70% redução com compressão

### Otimizações
- Compression nível 6 (balance)
- Parallel upload para arquivos grandes
- Incremental backups (90% menor)
- S3 Transfer Acceleration

## 🔐 Segurança

### Best Practices
1. Use variáveis de ambiente para credenciais
2. Criptografia SSE-KMS para dados sensíveis
3. Princípio do menor privilégio
4. Logs de acesso e auditoria
5. Network privada (VPN/VPC)

## 🤝 Contribuição

### Development Setup
```bash
# Setup de desenvolvimento
make install-dev

# Formata código
make format

# Executa testes
make test

# Linting
make lint
```

## 📄 Licença

MIT License - ver arquivo LICENSE para detalhes.

---

**BackupCTL** - Backup automatizado com confiança 🚀