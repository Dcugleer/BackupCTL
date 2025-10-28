"""
Módulo principal de backup
"""

import os
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import uuid
import logging

from ..utils.s3_client import S3Client
from ..utils.metadata import MetadataManager
from ..utils.crypto import compress_file, calculate_checksum


class BackupEngine:
    """Motor principal de backup"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.pg_config = config.get('postgresql', {})
        self.backup_config = config.get('backup', {})
        self.aws_config = config.get('aws', {})
        
        # Inicializa componentes
        self.s3_client = S3Client(self.aws_config, logger)
        self.metadata_manager = MetadataManager(self.pg_config, logger)
        
        # Diretório de backup temporário
        self.temp_dir = tempfile.mkdtemp(prefix='backupctl_')
    
    def create_full_backup(self, label: Optional[str] = None,
                          description: Optional[str] = None) -> Tuple[bool, str]:
        """
        Cria backup completo do PostgreSQL
        
        Returns:
            Tuple[bool, str]: (sucesso, backup_id ou mensagem de erro)
        """
        backup_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(f"Iniciando backup completo: {backup_id}")
        
        # Cria registro inicial
        backup_data = {
            'backup_id': backup_id,
            'backup_type': 'full',
            'status': 'running',
            'start_ts': start_time,
            'label': label or f"full-backup-{start_time.strftime('%Y%m%d-%H%M%S')}",
            'description': description or "Backup completo automatizado",
            'metadata_json': {
                'hostname': os.uname().nodename,
                'pg_version': self._get_postgres_version(),
                'backup_method': 'pg_dump'
            }
        }
        
        try:
            # Insere registro no metadados
            self.metadata_manager.create_backup_record(backup_data)
            
            # Executa backup
            backup_file = self._execute_pg_dump(backup_id)
            
            if not backup_file:
                raise Exception("Falha ao executar pg_dump")
            
            # Comprime se configurado
            if self.backup_config.get('compression', {}).get('enabled', True):
                compressed_file = f"{backup_file}.gz"
                compression_level = self.backup_config.get('compression', {}).get('level', 6)
                
                if compress_file(backup_file, compressed_file, compression_level):
                    os.remove(backup_file)
                    backup_file = compressed_file
                else:
                    self.logger.warning("Falha na compressão, usando arquivo original")
            
            # Calcula checksum
            checksum = calculate_checksum(backup_file)
            file_size = os.path.getsize(backup_file)
            
            # Upload para S3
            filename = os.path.basename(backup_file)
            success, s3_key = self.s3_client.upload_file(
                backup_file, 'full', filename
            )
            
            if not success:
                raise Exception(f"Falha no upload para S3: {s3_key}")
            
            # Atualiza registro com sucesso
            end_time = datetime.now(timezone.utc)
            self.metadata_manager.update_backup_status(
                backup_id, 'completed', end_time,
                size_bytes=file_size,
                s3_key=s3_key,
                s3_bucket=self.aws_config.get('bucket'),
                checksum=checksum,
                compression='gzip' if backup_file.endswith('.gz') else None,
                encryption=self.aws_config.get('encryption', 'SSE-S3')
            )
            
            self.logger.info(f"Backup completo concluído: {backup_id}")
            return True, backup_id
            
        except Exception as e:
            self.logger.error(f"Erro no backup completo {backup_id}: {e}")
            
            # Atualiza registro com falha
            self.metadata_manager.update_backup_status(
                backup_id, 'failed', datetime.now(timezone.utc)
            )
            
            return False, str(e)
            
        finally:
            # Limpeza
            self._cleanup_temp_files()
    
    def create_incremental_backup(self, label: Optional[str] = None) -> Tuple[bool, str]:
        """
        Cria backup incremental (WAL archiving)
        
        Returns:
            Tuple[bool, str]: (sucesso, backup_id ou mensagem de erro)
        """
        backup_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(f"Iniciando backup incremental: {backup_id}")
        
        try:
            # Para backup incremental, vamos implementar WAL archiving
            # Na prática, isso seria integrado com archive_command do PostgreSQL
            
            # Obtém WAL files atuais
            wal_files = self._get_wal_files()
            
            if not wal_files:
                self.logger.warning("Nenhum WAL file encontrado para backup incremental")
                return False, "Nenhum WAL file disponível"
            
            # Processa cada WAL file
            uploaded_wals = []
            for wal_file in wal_files:
                try:
                    # Upload do WAL
                    filename = os.path.basename(wal_file)
                    success, s3_key = self.s3_client.upload_file(
                        wal_file, 'incremental', filename
                    )
                    
                    if success:
                        checksum = calculate_checksum(wal_file)
                        file_size = os.path.getsize(wal_file)
                        
                        # Registra WAL metadata
                        wal_data = {
                            'wal_name': filename,
                            'backup_id': backup_id,
                            'start_ts': start_time,
                            'end_ts': datetime.now(timezone.utc),
                            'size_bytes': file_size,
                            's3_key': s3_key,
                            'checksum': checksum,
                            'sequence_number': self._extract_wal_sequence(filename)
                        }
                        
                        self.metadata_manager.create_wal_record(wal_data)
                        uploaded_wals.append(filename)
                        
                except Exception as e:
                    self.logger.error(f"Erro ao processar WAL {wal_file}: {e}")
            
            if not uploaded_wals:
                raise Exception("Nenhum WAL file foi processado com sucesso")
            
            # Cria registro do backup incremental
            backup_data = {
                'backup_id': backup_id,
                'backup_type': 'incremental',
                'status': 'completed',
                'start_ts': start_time,
                'end_ts': datetime.now(timezone.utc),
                'label': label or f"incremental-backup-{start_time.strftime('%Y%m%d-%H%M%S')}",
                'description': f"Backup incremental com {len(uploaded_wals)} WAL files",
                'metadata_json': {
                    'wal_files': uploaded_wals,
                    'wal_count': len(uploaded_wals),
                    'backup_method': 'wal_archive'
                }
            }
            
            self.metadata_manager.create_backup_record(backup_data)
            
            self.logger.info(f"Backup incremental concluído: {backup_id}")
            return True, backup_id
            
        except Exception as e:
            self.logger.error(f"Erro no backup incremental {backup_id}: {e}")
            return False, str(e)
            
        finally:
            self._cleanup_temp_files()
    
    def _execute_pg_dump(self, backup_id: str) -> Optional[str]:
        """Executa pg_dump para criar backup"""
        try:
            backup_file = os.path.join(self.temp_dir, f"{backup_id}.sql")
            
            # Constrói comando pg_dump
            cmd = [
                'pg_dump',
                '-h', self.pg_config.get('host', 'localhost'),
                '-p', str(self.pg_config.get('port', 5432)),
                '-U', self.pg_config.get('user'),
                '-d', self.pg_config.get('database'),
                '-f', backup_file,
                '--verbose',
                '--no-password',
                '--format=custom',
                '--compress=9'
            ]
            
            # Configura variáveis de ambiente
            env = os.environ.copy()
            env['PGPASSWORD'] = self.pg_config.get('password', '')
            
            self.logger.info(f"Executando pg_dump: {' '.join(cmd)}")
            
            # Executa comando
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hora timeout
            )
            
            if result.returncode != 0:
                self.logger.error(f"pg_dump falhou: {result.stderr}")
                return None
            
            if os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
                self.logger.info(f"pg_dump concluído: {backup_file}")
                return backup_file
            else:
                self.logger.error("Arquivo de backup não foi criado ou está vazio")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("pg_dump timeout")
            return None
        except Exception as e:
            self.logger.error(f"Erro ao executar pg_dump: {e}")
            return None
    
    def _get_wal_files(self) -> list:
        """Obtém lista de WAL files para backup"""
        try:
            # Em um ambiente real, isso obteria WAL files do pg_wal directory
            # Por ora, vamos simular
            
            pg_wal_dir = self.pg_config.get('wal_directory', '/var/lib/postgresql/data/pg_wal')
            
            if not os.path.exists(pg_wal_dir):
                self.logger.warning(f"Diretório WAL não encontrado: {pg_wal_dir}")
                return []
            
            # Lista arquivos WAL (arquivos que começam com números hexadecimais)
            wal_files = []
            for file in os.listdir(pg_wal_dir):
                if file.startswith('0') and len(file) == 24 and file.endswith('.gz'):
                    full_path = os.path.join(pg_wal_dir, file)
                    if os.path.isfile(full_path):
                        wal_files.append(full_path)
            
            return sorted(wal_files)
            
        except Exception as e:
            self.logger.error(f"Erro ao obter WAL files: {e}")
            return []
    
    def _extract_wal_sequence(self, wal_filename: str) -> int:
        """Exai número de sequência do WAL filename"""
        try:
            # Remove extensão e converte de hexadecimal
            name_part = wal_filename.split('.')[0]
            return int(name_part, 16)
        except:
            return 0
    
    def _get_postgres_version(self) -> str:
        """Obtém versão do PostgreSQL"""
        try:
            cmd = [
                'psql',
                '-h', self.pg_config.get('host', 'localhost'),
                '-p', str(self.pg_config.get('port', 5432)),
                '-U', self.pg_config.get('user'),
                '-d', self.pg_config.get('database'),
                '-t',
                '-c', 'SELECT version();'
            ]
            
            env = os.environ.copy()
            env['PGPASSWORD'] = self.pg_config.get('password', '')
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return "Unknown"
                
        except Exception as e:
            self.logger.error(f"Erro ao obter versão do PostgreSQL: {e}")
            return "Unknown"
    
    def _cleanup_temp_files(self):
        """Limpa arquivos temporários"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"Arquivos temporários removidos: {self.temp_dir}")
        except Exception as e:
            self.logger.error(f"Erro na limpeza de arquivos temporários: {e}")
    
    def get_backup_status(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de um backup"""
        return self.metadata_manager.get_backup_by_id(backup_id)
    
    def list_recent_backups(self, limit: int = 10) -> list:
        """Lista backups recentes"""
        return self.metadata_manager.list_backups(limit=limit)
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas dos backups"""
        return self.metadata_manager.get_backup_statistics()
    
    def cleanup(self):
        """Limpa recursos"""
        try:
            self._cleanup_temp_files()
            self.metadata_manager.close()
        except Exception as e:
            self.logger.error(f"Erro no cleanup: {e}")