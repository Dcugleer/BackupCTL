# Makefile para backupctl

.PHONY: help install install-dev test lint format clean build docker run docker-build docker-run

# Variáveis
PYTHON := python3
PIP := pip3
PACKAGE_NAME := backupctl
VERSION := 1.0.0
DOCKER_IMAGE := backupctl:$(VERSION)

help: ## Mostra ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Instala o pacote
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

install-dev: ## Instala dependências de desenvolvimento
	$(PIP) install -r requirements.txt
	$(PIP) install -e ".[dev]"
	pre-commit install

test: ## Executa testes
	$(PYTHON) -m pytest tests/ -v --cov=$(PACKAGE_NAME) --cov-report=html --cov-report=term

test-fast: ## Executa testes rápidos (sem coverage)
	$(PYTHON) -m pytest tests/ -v

lint: ## Executa linting
	flake8 backupctl/ tests/
	mypy backupctl/
	black --check backupctl/ tests/
	isort --check-only backupctl/ tests/

format: ## Formata código
	black backupctl/ tests/
	isort backupctl/ tests/

clean: ## Limpa arquivos temporários
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build do pacote
	$(PYTHON) setup.py sdist bdist_wheel

docker-build: ## Build da imagem Docker
	docker build -t $(DOCKER_IMAGE) .
	docker tag $(DOCKER_IMAGE) backupctl:latest

docker-run: ## Executa container Docker
	docker run --rm -it \
		-e AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
		-e AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
		-e PG_HOST=$(PG_HOST) \
		-e PG_USER=$(PG_USER) \
		-e PG_PASSWORD=$(PG_PASSWORD) \
		-v $(PWD)/config:/etc/backupctl \
		backupctl:latest $(CMD)

docker-test: ## Testa no container Docker
	docker run --rm \
		-e AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
		-e AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
		-e PG_HOST=$(PG_HOST) \
		-e PG_USER=$(PG_USER) \
		-e PG_PASSWORD=$(PG_PASSWORD) \
		-v $(PWD)/config:/etc/backupctl \
		backupctl:latest test

demo: ## Demo do backupctl
	@echo "🚀 Iniciando demo do backupctl"
	@echo "1. Testando configuração..."
	backupctl config-show
	@echo "2. Testando conectividade..."
	backupctl test
	@echo "3. Criando backup completo..."
	backupctl backup full --label "demo-backup"
	@echo "4. Verificando status..."
	backupctl status --last 3
	@echo "✅ Demo concluída!"

dev-setup: install-dev ## Setup completo de desenvolvimento
	@echo "🛠️  Ambiente de desenvolvimento configurado!"
	@echo "Execute 'make test' para verificar instalação"

ci: lint test ## Pipeline de CI/CD
	@echo "✅ CI/CD pipeline concluído com sucesso!"

release: clean build ## Cria release
	@echo "📦 Pacote criado em dist/"
	@echo "Execute 'twine upload dist/*' para publicar"

all: clean install-dev lint test ## Executa todos os checks
	@echo "🎉 Todos os checks passaram!"