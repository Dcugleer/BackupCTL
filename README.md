# BackupCTL - Sistema de Backup Automatizado PostgreSQL

<div align="center">

![BackupCTL Logo](public/logo.svg)

**Sistema Enterprise de Backup e Recuperação para PostgreSQL**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js Version](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen)](https://nodejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-%3E%3D12-blue)](https://www.postgresql.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-blue)](https://www.typescriptlang.org/)

[Funcionalidades](#-funcionalidades) •
[Instalação](#-instalação) •
[Configuração](#-configuração) •
[Uso](#-uso) •
[API](#-api) •
[Contribuição](#-contribuição)

</div>

## 📋 Sobre

BackupCTL é uma solução enterprise de backup e recuperação para PostgreSQL, desenvolvida com foco em confiabilidade, performance e facilidade de uso. Oferece backup automatizado, recuperação avançada, monitoramento em tempo real e suporte multi-cloud.

### 🎯 Objetivos

- **Proteção de Dados**: Backup automatizado com múltiplas estratégias
- **Recuperação Rápida**: Opções avançadas de restore incluindo PITR
- **Monitoramento**: Dashboard em tempo real e alertas inteligentes
- **Multi-Cloud**: Suporte para AWS S3, Azure, GCP e FTP/SFTP
- **Segurança**: Criptografia ponta-a-ponta e controle de acesso

## ✨ Funcionalidades

### 🔄 Tipos de Backup

- **Backup Completo**: Backup full do banco de dados
- **Backup Diferencial**: Baseado no último backup completo
- **Backup Incremental**: Baseado no último backup qualquer
- **WAL Archiving**: Archiving contínuo de transaction logs

### 🛡️ Segurança

- **Criptografia AES-256**: Proteção ponta-a-ponta dos dados
- **Compressão Avançada**: GZIP, ZSTD, LZ4 para economia de espaço
- **Soft Delete**: Proteção contra exclusão acidental
- **Controle de Acesso**: Autenticação e permissões granulares

### ☁️ Storage Multi-Cloud

- **Local**: File system local
- **AWS S3**: Simple Storage Service
- **Azure Blob**: Blob Storage da Microsoft
- **GCP Cloud Storage**: Google Cloud Platform
- **FTP/SFTP**: Transferência de arquivos tradicional

### 📊 Monitoramento

- **Dashboard em Tempo Real**: Métricas e status atualizados via WebSocket
- **Análise de Tendências**: Gráficos de 7 dias com estatísticas
- **Alertas Inteligentes**: Notificações de falhas e avisos
- **Health Checks**: Verificação automática da integridade

### 🔄 Recuperação Avançada

- **Restore Completo**: Recuperação full do banco
- **Restore Seletivo**: Tabelas ou schemas específicos
- **Point-in-Time Recovery**: Recuperação até um momento específico
- **Testes Automáticos**: Validação da integridade dos backups

## 🚀 Instalação

### Pré-requisitos

- Node.js 18+ 
- PostgreSQL 12+
- NPM ou Yarn

### Passo 1: Clonar o Repositório

```bash
git clone https://github.com/seu-usuario/backupctl.git
cd backupctl
```

### Passo 2: Instalar Dependências

```bash
npm install
```

### Passo 3: Configurar Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:

```env
# Database
DATABASE_URL="postgresql://usuario:senha@localhost:5432/backupctl"

# NextAuth
NEXTAUTH_SECRET="seu-secret-aqui"
NEXTAUTH_URL="http://localhost:3000"

# AWS S3 (opcional)
AWS_ACCESS_KEY_ID="sua-access-key"
AWS_SECRET_ACCESS_KEY="seu-secret-key"
AWS_REGION="us-east-1"
AWS_S3_BUCKET="seu-bucket"

# Azure (opcional)
AZURE_STORAGE_ACCOUNT="sua-conta"
AZURE_STORAGE_KEY="sua-key"
AZURE_CONTAINER="seu-container"

# GCP (opcional)
GCP_PROJECT_ID="seu-project-id"
GCP_KEY_FILE="path/to/service-account.json"
GCP_BUCKET="seu-bucket"
```

### Passo 4: Configurar Banco de Dados

```bash
npm run db:push
```

### Passo 5: Iniciar a Aplicação

```bash
npm run dev
```

Acesse http://localhost:3000 no seu navegador.

## ⚙️ Configuração

### Configuração Básica

1. **Conexão PostgreSQL**: Configure as credenciais do banco a ser backupado
2. **Storage**: Escolha entre local, S3, Azure, GCP ou FTP/SFTP
3. **Agendamento**: Defina frequência e horários dos backups
4. **Retenção**: Configure políticas de retenção e rotação

### Configuração Avançada

```typescript
// src/lib/backup-config.ts
export const backupConfig = {
  // Tipos de backup habilitados
  enabledTypes: ['full', 'differential', 'incremental'],
  
  // Compressão
  compression: {
    algorithm: 'zstd', // 'gzip', 'zstd', 'lz4'
    level: 6
  },
  
  // Criptografia
  encryption: {
    enabled: true,
    algorithm: 'aes-256-gcm',
    keyRotationDays: 90
  },
  
  // Retenção
  retention: {
    full: 30,      // dias
    differential: 7, // dias
    incremental: 3,  // dias
    wal: 14        // dias
  }
}
```

## 📖 Uso

### Interface Web

1. **Dashboard**: Visão geral do status dos backups
2. **Backups**: Lista completa com filtros e ações
3. **Restauros**: Interface para recuperação de dados
4. **Configurações**: Gerenciamento do sistema
5. **Logs**: Histórico completo de operações

### Linha de Comando

```bash
# Criar backup completo
npm run backup:full

# Criar backup incremental
npm run backup:incremental

# Listar backups
npm run backup:list

# Restaurar backup
npm run restore:latest

# Testar integridade
npm run backup:test
```

### API REST

```bash
# Listar backups
curl -X GET http://localhost:3000/api/backups

# Criar backup
curl -X POST http://localhost:3000/api/backups \
  -H "Content-Type: application/json" \
  -d '{"type": "full", "compression": "zstd"}'

# Restaurar backup
curl -X POST http://localhost:3000/api/restores \
  -H "Content-Type: application/json" \
  -d '{"backupId": "backup_123", "targetTables": ["users"]}'
```

## 🔧 API Reference

### Endpoints Principais

#### Backups

```
GET    /api/backups           # Listar backups
POST   /api/backups           # Criar backup
GET    /api/backups/:id       # Detalhes do backup
DELETE /api/backups/:id       # Excluir backup
POST   /api/backups/:id/test  # Testar integridade
```

#### Restores

```
GET    /api/restores          # Listar restaurações
POST   /api/restores          # Iniciar restauração
GET    /api/restores/:id      # Status da restauração
```

#### Configuração

```
GET    /api/config            # Obter configuração
PUT    /api/config            # Atualizar configuração
GET    /api/config/storage    # Testar storage
```

#### Monitoramento

```
GET    /api/status            # Status do sistema
GET    /api/metrics           # Métricas e estatísticas
GET    /api/health            # Health check
```

### WebSocket Events

```javascript
// Conectar ao WebSocket
const socket = io('http://localhost:3000');

// Eventos disponíveis
socket.on('backup:started', (data) => {
  console.log('Backup iniciado:', data);
});

socket.on('backup:completed', (data) => {
  console.log('Backup concluído:', data);
});

socket.on('backup:failed', (data) => {
  console.error('Backup falhou:', data);
});

socket.on('system:status', (data) => {
  console.log('Status do sistema:', data);
});
```

## 🏗️ Arquitetura

```
backupctl/
├── src/
│   ├── app/                 # Next.js App Router
│   │   ├── api/            # API Routes
│   │   ├── dashboard/      # Dashboard pages
│   │   └── backups/        # Backup management
│   ├── components/         # React components
│   │   ├── ui/            # Shadcn UI components
│   │   └── charts/        # Chart components
│   ├── lib/               # Core libraries
│   │   ├── backup/        # Backup engine
│   │   ├── storage/       # Storage adapters
│   │   ├── crypto/        # Encryption utilities
│   │   └── db/           # Database client
│   └── types/             # TypeScript definitions
├── prisma/                # Database schema
├── public/               # Static assets
└── docs/                # Documentation
```

## 🔒 Segurança

### Criptografia

- **Dados em Trânsito**: TLS 1.3
- **Dados em Repouso**: AES-256-GCM
- **Chaves**: Rotação automática a cada 90 dias
- **Integridade**: HMAC-SHA256 verification

### Controle de Acesso

- **Autenticação**: NextAuth.js com múltiplos providers
- **Autorização**: RBAC (Role-Based Access Control)
- **Audit Trail**: Log completo de todas as operações
- **Session Management**: Configurações de sessão seguras

## 📊 Monitoramento

### Métricas Disponíveis

- **Taxa de Sucesso**: Percentual de backups concluídos
- **Duração Média**: Tempo médio dos backups
- **Economia de Storage**: Redução via compressão
- **Performance**: Velocidade de backup/restore
- **Disponibilidade**: Uptime do sistema

### Alertas

- **Backup Falhou**: Notificação imediata
- **Storage Baixo**: Aviso de espaço limitado
- **Performance Degradada**: Alerta de lentidão
- **Teste Falhou**: Problema na integridade

## 🧪 Testes

### Executar Testes

```bash
# Testes unitários
npm run test

# Testes de integração
npm run test:integration

# Testes E2E
npm run test:e2e

# Coverage
npm run test:coverage
```

### Testes Automáticos

- **Integridade de Backup**: Verificação pós-backup
- **Teste de Restore**: Validação automática
- **Performance Test**: Benchmark de velocidade
- **Security Scan**: Verificação de vulnerabilidades

## 🚀 Deploy

### Docker

```bash
# Build
docker build -t backupctl .

# Run
docker run -p 3000:3000 \
  -e DATABASE_URL="postgresql://..." \
  -e NEXTAUTH_SECRET="..." \
  backupctl
```

### Docker Compose

```yaml
version: '3.8'
services:
  backupctl:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/backupctl
      - NEXTAUTH_SECRET=your-secret
    depends_on:
      - db
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=backupctl
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Produção

```bash
# Build para produção
npm run build

# Iniciar em modo produção
npm start

# Com PM2
pm2 start ecosystem.config.js
```

## 🤝 Contribuição

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

### Diretrizes

- Siga o Code Style do projeto
- Adicione testes para novas funcionalidades
- Atualize a documentação
- Use commits semânticos

## 📝 Changelog

### v2.0.0 (2024-01-15)

- ✨ Multi-cloud support (AWS, Azure, GCP)
- 🔐 AES-256 encryption
- 📊 Real-time dashboard
- 🌐 Portuguese localization
- 🧪 Automated restore testing

### v1.5.0 (2023-12-01)

- ✨ Differential backups
- 📈 Performance metrics
- 🔔 Advanced alerts
- 🎨 UI improvements

### v1.0.0 (2023-10-01)

- 🎉 Initial release
- ✨ Full and incremental backups
- 📱 Web interface
- 🔧 Basic configuration

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.



## 🙏 Agradecimentos

- [PostgreSQL](https://www.postgresql.org/) - Banco de dados robusto
- [Next.js](https://nextjs.org/) - Framework React full-stack
- [Shadcn UI](https://ui.shadcn.com/) - Componentes UI modernos
- [Prisma](https://www.prisma.io/) - ORM moderno
- [Tailwind CSS](https://tailwindcss.com/) - Framework CSS utilitário

---

<div align="center">

**⭐ Se este projeto ajudou você, deixe uma star!**

📧 Contato do Autor

Nome: Denis Cugler

E-mail: deniscugler@gmail.com

GitHub: https://github.com/Dcugleer

LinkedIn: https://www.linkedin.com/in/denis-cugler/

Website / Portfólio: (https://denis-cugler.vercel.app/)

</div>