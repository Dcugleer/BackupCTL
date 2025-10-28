# Dockerfile para backupctl
FROM python:3.11-slim

# Labels
LABEL maintainer="backup-team@example.com"
LABEL version="1.0.0"
LABEL description="Sistema de Backup Automatizado PostgreSQL"

# Variáveis de ambiente
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV BACKUPCTL_CONFIG=/etc/backupctl/config.yaml

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    postgresql-client \
    postgresql-common \
    cron \
    curl \
    jq \
    gzip \
    && rm -rf /var/lib/apt/lists/*

# Cria usuário non-root
RUN groupadd -r backupctl && useradd -r -g backupctl backupctl

# Define work directory
WORKDIR /app

# Copia requirements e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código do aplicativo
COPY . .

# Instala o pacote
RUN pip install -e .

# Cria diretórios necessários
RUN mkdir -p /etc/backupctl /var/log/backupctl /tmp/postgres_backups /tmp/postgres_restore

# Copia configuração de exemplo
RUN cp config/config.yaml /etc/backupctl/config.yaml.example

# Muda ownership dos diretórios
RUN chown -R backupctl:backupctl /app /etc/backupctl /var/log/backupctl /tmp/postgres_backups /tmp/postgres_restore

# Copia scripts
RUN cp scripts/healthcheck.sh /usr/local/bin/healthcheck.sh && \
    chmod +x /usr/local/bin/healthcheck.sh

# Setup do cron
RUN echo "backupctl ALL=(ALL) NOPASSWD: /usr/local/bin/backupctl" >> /etc/sudoers

# Expõe volumes
VOLUME ["/etc/backupctl", "/var/log/backupctl", "/tmp/postgres_backups", "/tmp/postgres_restore"]

# Switch para usuário non-root
USER backupctl

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Comando padrão
ENTRYPOINT ["backupctl"]
CMD ["--help"]