"""
CLI principal do backupctl
"""

import click
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional

from .utils.config import Config
from .utils.logger import get_logger
from .core.backup import BackupEngine
from .core.restore import RestoreEngine
from .core.scheduler import BackupScheduler


def load_config_and_logger():
    """Carrega configuração e logger"""
    try:
        config = Config()
        config.validate()
        
        logging_config = config.get_logging_config()
        logger = get_logger(logging_config)
        
        return config, logger
    except Exception as e:
        click.echo(f"Erro ao carregar configuração: {e}", err=True)
        sys.exit(1)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Sistema de Backup Automatizado PostgreSQL"""
    pass


@cli.group()
def backup():
    """Comandos de backup"""
    pass


@backup.command()
@click.option('--label', '-l', help='Label para o backup')
@click.option('--description', '-d', help='Descrição do backup')
@click.option('--json-output', is_flag=True, help='Output em formato JSON')
def full(label, description, json_output):
    """Cria backup completo"""
    config, logger = load_config_and_logger()
    
    try:
        backup_engine = BackupEngine(config.get_backup_config(), logger)
        
        click.echo("Iniciando backup completo...")
        success, result = backup_engine.create_full_backup(label, description)
        
        if json_output:
            output = {
                'success': success,
                'backup_id': result if success else None,
                'message': result if not success else "Backup completo concluído",
                'timestamp': datetime.now().isoformat()
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if success:
                click.echo(f"✅ Backup completo concluído: {result}")
            else:
                click.echo(f"❌ Falha no backup completo: {result}")
                sys.exit(1)
        
        backup_engine.cleanup()
        
    except Exception as e:
        error_msg = f"Erro no backup completo: {e}"
        logger.error(error_msg)
        click.echo(f"❌ {error_msg}", err=True)
        sys.exit(1)


@backup.command()
@click.option('--label', '-l', help='Label para o backup')
@click.option('--json-output', is_flag=True, help='Output em formato JSON')
def incremental(label, json_output):
    """Cria backup incremental (WAL)"""
    config, logger = load_config_and_logger()
    
    try:
        backup_engine = BackupEngine(config.get_backup_config(), logger)
        
        click.echo("Iniciando backup incremental...")
        success, result = backup_engine.create_incremental_backup(label)
        
        if json_output:
            output = {
                'success': success,
                'backup_id': result if success else None,
                'message': result if not success else "Backup incremental concluído",
                'timestamp': datetime.now().isoformat()
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if success:
                click.echo(f"✅ Backup incremental concluído: {result}")
            else:
                click.echo(f"❌ Falha no backup incremental: {result}")
                sys.exit(1)
        
        backup_engine.cleanup()
        
    except Exception as e:
        error_msg = f"Erro no backup incremental: {e}"
        logger.error(error_msg)
        click.echo(f"❌ {error_msg}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--backup-id', '-b', help='ID do backup para restaurar')
@click.option('--to', help='Timestamp target para restore (PITR)')
@click.option('--destination', '-d', help='Diretório de destino')
@click.option('--json-output', is_flag=True, help='Output em formato JSON')
def restore(backup_id, to, destination, json_output):
    """Restaura backup"""
    config, logger = load_config_and_logger()
    
    try:
        restore_engine = RestoreEngine(config.get_restore_config(), logger)
        
        click.echo("Iniciando restore...")
        success, result = restore_engine.restore_backup(backup_id, to, destination)
        
        if json_output:
            output = {
                'success': success,
                'restore_id': result if success else None,
                'message': result if not success else "Restore concluído",
                'timestamp': datetime.now().isoformat()
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if success:
                click.echo(f"✅ Restore concluído: {result}")
            else:
                click.echo(f"❌ Falha no restore: {result}")
                sys.exit(1)
        
        restore_engine.cleanup()
        
    except Exception as e:
        error_msg = f"Erro no restore: {e}"
        logger.error(error_msg)
        click.echo(f"❌ {error_msg}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--last', '-n', default=10, help='Número de backups recentes')
@click.option('--type', '-t', help='Tipo de backup (full/incremental)')
@click.option('--json-output', is_flag=True, help='Output em formato JSON')
def status(last, type, json_output):
    """Mostra status dos backups"""
    config, logger = load_config_and_logger()
    
    try:
        backup_engine = BackupEngine(config.get_backup_config(), logger)
        
        if type:
            backups = backup_engine.metadata_manager.list_backups(
                backup_type=type, limit=last
            )
        else:
            backups = backup_engine.list_recent_backups(last)
        
        if json_output:
            output = {
                'backups': backups,
                'count': len(backups),
                'timestamp': datetime.now().isoformat()
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if not backups:
                click.echo("Nenhum backup encontrado")
                return
            
            click.echo(f"\n📊 Últimos {len(backups)} backups:\n")
            click.echo(f"{'ID':<36} {'Tipo':<12} {'Status':<10} {'Início':<20} {'Tamanho':<10}")
            click.echo("-" * 90)
            
            for backup in backups:
                size_str = f"{backup['size_bytes']/1024/1024:.1f}MB" if backup['size_bytes'] else "N/A"
                start_time = backup['start_ts'].strftime('%Y-%m-%d %H:%M:%S') if backup['start_ts'] else "N/A"
                
                status_icon = {
                    'completed': '✅',
                    'running': '🔄',
                    'failed': '❌'
                }.get(backup['status'], '❓')
                
                click.echo(f"{backup['backup_id'][:36]:<36} {backup['backup_type']:<12} {status_icon} {backup['status']:<8} {start_time:<20} {size_str:<10}")
        
        backup_engine.cleanup()
        
    except Exception as e:
        error_msg = f"Erro ao obter status: {e}"
        logger.error(error_msg)
        click.echo(f"❌ {error_msg}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--policy', '-p', help='Política de retenção (ex: monthly-retain=3,weekly-retain=4,daily-retain=7)')
@click.option('--dry-run', is_flag=True, help='Simular remoção')
@click.option('--json-output', is_flag=True, help='Output em formato JSON')
def prune(policy, dry_run, json_output):
    """Remove backups antigos"""
    config, logger = load_config_and_logger()
    
    try:
        backup_engine = BackupEngine(config.get_backup_config(), logger)
        
        # Parse da política (simplificado)
        retention_config = config.get_backup_config().get('retention', {})
        
        if policy:
            # Parse da política passada por linha de comando
            for rule in policy.split(','):
                if '=' in rule:
                    key, value = rule.split('=', 1)
                    retention_config[key] = int(value)
        
        click.echo(f"Política de retenção: {retention_config}")
        
        if dry_run:
            click.echo("🔍 MODO SIMULAÇÃO - Nenhum arquivo será removido")
        
        # Implementação de prune
        old_backups = backup_engine.list_recent_backups(limit=1000)
        
        pruned_backups = []
        for backup in old_backups:
            backup_age = (datetime.now().replace(tzinfo=None) - 
                         backup['start_ts'].replace(tzinfo=None)).days
            
            should_prune = False
            if backup['backup_type'] == 'full':
                full_days = retention_config.get('full_days', 30)
                should_prune = backup_age > full_days
            elif backup['backup_type'] == 'incremental':
                inc_days = retention_config.get('incremental_days', 7)
                should_prune = backup_age > inc_days
            
            if should_prune:
                pruned_backups.append({
                    'backup_id': backup['backup_id'],
                    'type': backup['backup_type'],
                    'age_days': backup_age,
                    'size_bytes': backup['size_bytes']
                })
                
                if not dry_run:
                    # Implementar remoção real
                    if backup['s3_key']:
                        backup_engine.s3_client.delete_file(backup['s3_key'])
                    # Remover metadados
                    # backup_engine.metadata_manager.delete_backup(backup['backup_id'])
        
        if json_output:
            output = {
                'pruned_backups': pruned_backups,
                'pruned_count': len(pruned_backups),
                'dry_run': dry_run,
                'timestamp': datetime.now().isoformat()
            }
            click.echo(json.dumps(output, indent=2))
        else:
            if pruned_backups:
                click.echo(f"\n🗑️  {len(pruned_backups)} backups para remover:")
                for backup in pruned_backups:
                    size_str = f"{backup['size_bytes']/1024/1024:.1f}MB" if backup['size_bytes'] else "N/A"
                    click.echo(f"  • {backup['backup_id'][:36]} ({backup['type']}, {backup['age_days']} dias, {size_str})")
                
                if not dry_run:
                    click.echo("\n✅ Backups removidos com sucesso")
            else:
                click.echo("✅ Nenhum backup para remover")
        
        backup_engine.cleanup()
        
    except Exception as e:
        error_msg = f"Erro no prune: {e}"
        logger.error(error_msg)
        click.echo(f"❌ {error_msg}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--daemon', '-d', is_flag=True, help='Executar como daemon')
def schedule(daemon):
    """Inicia agendador de backups"""
    config, logger = load_config_and_logger()
    
    try:
        scheduler = BackupScheduler(config, logger)
        
        if daemon:
            click.echo("🚀 Iniciando scheduler em modo daemon...")
            scheduler.start()
            
            try:
                # Mantém o processo rodando
                while True:
                    import time
                    time.sleep(60)
            except KeyboardInterrupt:
                click.echo("\n🛑 Parando scheduler...")
                scheduler.stop()
        else:
            # Mostra próximas execuções
            scheduler.setup_schedule()
            next_runs = scheduler.get_next_runs()
            
            if next_runs:
                click.echo("\n📅 Próximas execuções agendadas:")
                for job, next_run in next_runs.items():
                    click.echo(f"  • {job}: {next_run}")
            else:
                click.echo("Nenhuma tarefa agendada")
        
        scheduler.cleanup()
        
    except Exception as e:
        error_msg = f"Erro no scheduler: {e}"
        logger.error(error_msg)
        click.echo(f"❌ {error_msg}", err=True)
        sys.exit(1)


@cli.command()
def config_show():
    """Mostra configuração atual"""
    try:
        config = Config()
        
        # Mostra configurações principais (sem senhas)
        pg_config = config.get_postgresql_config()
        aws_config = config.get_aws_config()
        backup_config = config.get_backup_config()
        
        click.echo("📋 Configuração Atual:\n")
        
        click.echo("PostgreSQL:")
        click.echo(f"  Host: {pg_config.get('host')}")
        click.echo(f"  Port: {pg_config.get('port')}")
        click.echo(f"  User: {pg_config.get('user')}")
        click.echo(f"  Database: {pg_config.get('database')}")
        
        click.echo("\nAWS S3:")
        click.echo(f"  Bucket: {aws_config.get('bucket')}")
        click.echo(f"  Region: {aws_config.get('region')}")
        click.echo(f"  Prefix: {aws_config.get('prefix')}")
        click.echo(f"  Encryption: {aws_config.get('encryption')}")
        
        click.echo("\nBackup:")
        retention = backup_config.get('retention', {})
        click.echo(f"  Full retention: {retention.get('full_days', 30)} days")
        click.echo(f"  Incremental retention: {retention.get('incremental_days', 7)} days")
        click.echo(f"  Compression: {backup_config.get('compression', {}).get('enabled', True)}")
        
    except Exception as e:
        click.echo(f"❌ Erro ao mostrar configuração: {e}", err=True)
        sys.exit(1)


@cli.command()
def test():
    """Executa testes de conectividade"""
    config, logger = load_config_and_logger()
    
    click.echo("🧪 Executando testes de conectividade...\n")
    
    tests_passed = 0
    total_tests = 4
    
    # Teste 1: PostgreSQL
    try:
        import psycopg2
        pg_config = config.get_postgresql_config()
        
        conn = psycopg2.connect(
            host=pg_config.get('host'),
            port=pg_config.get('port', 5432),
            user=pg_config.get('user'),
            password=pg_config.get('password'),
            database=pg_config.get('database'),
            connect_timeout=5
        )
        conn.close()
        
        click.echo("✅ PostgreSQL: Conexão bem-sucedida")
        tests_passed += 1
        
    except Exception as e:
        click.echo(f"❌ PostgreSQL: Falha na conexão - {e}")
    
    # Teste 2: AWS S3
    try:
        from .utils.s3_client import S3Client
        aws_config = config.get_aws_config()
        
        s3_client = S3Client(aws_config, logger)
        bucket_info = s3_client.get_bucket_info()
        
        if bucket_info:
            click.echo(f"✅ AWS S3: Bucket acessível ({bucket_info.get('total_files', 0)} arquivos)")
            tests_passed += 1
        else:
            click.echo("❌ AWS S3: Falha ao acessar bucket")
            
    except Exception as e:
        click.echo(f"❌ AWS S3: Falha na conexão - {e}")
    
    # Teste 3: Diretórios
    try:
        backup_dir = config.get('postgresql.backup_dir', '/tmp/postgres_backups')
        os.makedirs(backup_dir, exist_ok=True)
        
        if os.access(backup_dir, os.W_OK):
            click.echo(f"✅ Diretórios: {backup_dir} acessível")
            tests_passed += 1
        else:
            click.echo(f"❌ Diretórios: {backup_dir} não é gravável")
            
    except Exception as e:
        click.echo(f"❌ Diretórios: Erro - {e}")
    
    # Teste 4: Metadados
    try:
        from .utils.metadata import MetadataManager
        pg_config = config.get_postgresql_config()
        
        metadata_manager = MetadataManager(pg_config, logger)
        stats = metadata_manager.get_backup_statistics()
        
        click.echo("✅ Metadados: Schema acessível")
        tests_passed += 1
        metadata_manager.close()
        
    except Exception as e:
        click.echo(f"❌ Metadados: Falha - {e}")
    
    click.echo(f"\n📊 Testes concluídos: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        click.echo("🎉 Todos os testes passaram!")
    else:
        click.echo("⚠️  Alguns testes falharam - verifique a configuração")
        sys.exit(1)


def main():
    """Ponto de entrada principal"""
    cli()


if __name__ == '__main__':
    main()