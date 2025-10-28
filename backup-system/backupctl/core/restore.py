"""
Módulo de restore/recuperação
"""

import os
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List
import uuid
import logging

from ..utils.s3_client import S3Client
from ..utils.metadata import MetadataManager
from ..utils.crypto import decompress_file, verify_checksum


class RestoreEngine:
    """Motor principal de restore"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.pg_config = config.get('postgresql', {})
        self.restore_config = config.get('restore', {})
        self.aws_config = config.get('aws', {})
        
        # Inicializa componentes
        self.s3_client = S3Client(self.aws_config, logger)
        self.metadata_manager = MetadataManager(self.pg_config, logger)
        
        # Diretório temporário
        self.temp_dir = tempfile.mkdtemp(prefix='restorectl_')
    
    def restore_backup(self, backup_id: Optional[str] = None,
                      target_time: Optional[str] = None,
                      destination: Optional[str] = None) -> Tuple[bool, str]:
        """
        Restaura backup completo + WALs até target_time
        
        Returns:
            Tuple[bool, str]: (sucesso, restore_id ou mensagem de erro)
        """
        restore_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)
        
        self.logger.info(f"Iniciando restore: {restore_id}")
        
        try:
            # Determina backup para restore
            if not backup_id:
                backup_id = self._find_latest_full_backup()
                if not backup_id:
                    raise Exception("Nenhum backup completo encontrado")
            
            # Obtém metadados do backup
            backup_metadata = self.metadata_manager.get_backup_by_id(backup_id)
            if not backup_metadata:
                raise Exception(f"Backup {backup_id} não encontrado")
            
            if backup_metadata['status'] != 'completed':
                raise Exception(f"Backup {backup_id} não está concluído")
            
            # Prepara diretório de destino
            if not destination:
                destination = self.restore_config.get('temp_dir', '/tmp/postgres_restore')
            
            os.makedirs(destination, exist_ok=True)
            
            # Cria registro de restore
            restore_data = {
                'restore_id': restore_id,
                'backup_id': backup_id,
                'target_time': datetime.fromisoformat(target_time) if target_time else None,
                'status': 'running',
                'start_ts': start_time,
                'destination_path': destination
            }
            
            self.metadata_manager.create_restore_record(restore_data)
            
            # Download do backup principal
            backup_file = self._download_backup_file(backup_metadata)
            if not backup_file:
                raise Exception("Falha no download do backup principal")
            
            # Descomprime se necessário
            if backup_file.endswith('.gz'):
                decompressed_file = backup_file[:-3]
                if decompress_file(backup_file, decompressed_file):
                    os.remove(backup_file)
                    backup_file = decompressed_file
                else:
                    raise Exception("Falha na descompressão do backup")
            
            # Restaura backup principal
            if not self._restore_base_backup(backup_file, destination):
                raise Exception("Falha na restauração do backup principal")
            
            # Se especificado target_time, aplica WALs
            if target_time:
                if not self._apply_wal_files(backup_id, target_time, destination):
                    self.logger.warning("Falha na aplicação de WALs, restore parcial")
            
            # Configura recovery
            self._setup_recovery_config(destination, target_time)
            
            # Atualiza registro com sucesso
            end_time = datetime.now(timezone.utc)
            self._update_restore_status(restore_id, 'completed', end_time)
            
            self.logger.info(f"Restore concluído: {restore_id}")
            return True, restore_id
            
        except Exception as e:
            self.logger.error(f"Erro no restore {restore_id}: {e}")
            
            # Atualiza registro com falha
            self._update_restore_status(
                restore_id, 'failed', datetime.now(timezone.utc),
                error_message=str(e)
            )
            
            return False, str(e)
            
        finally:
            self._cleanup_temp_files()
    
    def _find_latest_full_backup(self) -> Optional[str]:
        """Encontra o backup completo mais recente"""
        try:
            latest_backup = self.metadata_manager.get_latest_backup('full')
            if latest_backup:
                return latest_backup['backup_id']
            return None
        except Exception as e:
            self.logger.error(f"Erro ao encontrar backup completo: {e}")
            return None
    
    def _download_backup_file(self, backup_metadata: Dict[str, Any]) -> Optional[str]:
        """Baixa arquivo de backup do S3"""
        try:
            s3_key = backup_metadata['s3_key']
            if not s3_key:
                raise Exception("Backup não possui S3 key")
            
            # Nome do arquivo local
            filename = os.path.basename(s3_key)
            local_path = os.path.join(self.temp_dir, filename)
            
            # Download
            success, message = self.s3_client.download_file(s3_key, local_path)
            if not success:
                raise Exception(f"Falha no download: {message}")
            
            # Verifica integridade se tiver checksum
            expected_checksum = backup_metadata.get('checksum')
            if expected_checksum:
                if not verify_checksum(local_path, expected_checksum):
                    os.remove(local_path)
                    raise Exception("Checksum inválido")
            
            self.logger.info(f"Backup baixado: {local_path}")
            return local_path
            
        except Exception as e:
            self.logger.error(f"Erro no download do backup: {e}")
            return None
    
    def _restore_base_backup(self, backup_file: str, destination: str) -> bool:
        """Restaura backup base usando pg_restore"""
        try:
            # Para restore, precisamos de um PostgreSQL rodando no destino
            # Por ora, vamos apenas extrair o arquivo no destino
            
            self.logger.info(f"Restaurando backup base para: {destination}")
            
            # Se for formato custom, usa pg_restore
            if backup_file.endswith('.dump') or backup_file.endswith('.backup'):
                cmd = [
                    'pg_restore',
                    '-h', 'localhost',  # Assume restore local
                    '-p', '5433',       # Porta diferente para restore
                    '-U', 'postgres',
                    '-d', 'postgres_restore',  # Database de restore
                    '--verbose',
                    '--clean',
                    '--if-exists',
                    '--no-password',
                    backup_file
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = self.pg_config.get('password', '')
                
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=3600
                )
                
                if result.returncode != 0:
                    self.logger.error(f"pg_restore falhou: {result.stderr}")
                    return False
                
            else:
                # Se for SQL, usa psql
                cmd = [
                    'psql',
                    '-h', 'localhost',
                    '-p', '5433',
                    '-U', 'postgres',
                    '-d', 'postgres_restore',
                    '-f', backup_file
                ]
                
                env = os.environ.copy()
                env['PGPASSWORD'] = self.pg_config.get('password', '')
                
                result = subprocess.run(
                    cmd,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=3600
                )
                
                if result.returncode != 0:
                    self.logger.error(f"psql restore falhou: {result.stderr}")
                    return False
            
            self.logger.info("Backup base restaurado com sucesso")
            return True
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout no restore do backup base")
            return False
        except Exception as e:
            self.logger.error(f"Erro no restore do backup base: {e}")
            return False
    
    def _apply_wal_files(self, backup_id: str, target_time: str, destination: str) -> bool:
        """Aplica WAL files até target_time"""
        try:
            self.logger.info(f"Aplicando WALs até {target_time}")
            
            # Obtém WALs associados ao backup
            wal_files = self.metadata_manager.get_wals_for_backup(backup_id)
            
            if not wal_files:
                self.logger.info("Nenhum WAL file encontrado para aplicar")
                return True
            
            target_dt = datetime.fromisoformat(target_time)
            applied_wals = []
            
            for wal_metadata in wal_files:
                try:
                    # Download do WAL
                    s3_key = wal_metadata['s3_key']
                    wal_filename = os.path.basename(s3_key)
                    local_wal_path = os.path.join(self.temp_dir, wal_filename)
                    
                    success, _ = self.s3_client.download_file(s3_key, local_wal_path)
                    if not success:
                        continue
                    
                    # Verifica se WAL deve ser aplicado (baseado no tempo)
                    wal_time = wal_metadata['end_ts']
                    if wal_time > target_dt:
                        break
                    
                    # Aplica WAL usando pg_walfile ou similar
                    if self._apply_single_wal(local_wal_path, destination):
                        applied_wals.append(wal_filename)
                    
                except Exception as e:
                    self.logger.error(f"Erro ao aplicar WAL {wal_metadata['wal_name']}: {e}")
                    continue
            
            self.logger.info(f"Aplicados {len(applied_wals)} WAL files")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro na aplicação de WALs: {e}")
            return False
    
    def _apply_single_wal(self, wal_file: str, destination: str) -> bool:
        """Aplica um único WAL file"""
        try:
            # Em um ambiente real, isso usaria pg_walfile ou ferramenta similar
            # Por ora, vamos simular
            
            cmd = [
                'pg_walfile',
                '--path', destination,
                wal_file
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return result.returncode == 0
            
        except Exception as e:
            self.logger.error(f"Erro ao aplicar WAL {wal_file}: {e}")
            return False
    
    def _setup_recovery_config(self, destination: str, target_time: Optional[str]) -> None:
        """Configura arquivos de recovery"""
        try:
            # Cria recovery.conf (PostgreSQL < 12) ou postgresql.auto.conf (>= 12)
            recovery_conf_path = os.path.join(destination, 'recovery.conf')
            
            with open(recovery_conf_path, 'w') as f:
                f.write("restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'\n")
                
                if target_time:
                    f.write(f"recovery_target_time = '{target_time}'\n")
                    f.write("recovery_target_inclusive = true\n")
                
                f.write("standby_mode = on\n")
            
            self.logger.info("Arquivo de recovery configurado")
            
        except Exception as e:
            self.logger.error(f"Erro na configuração de recovery: {e}")
    
    def _update_restore_status(self, restore_id: str, status: str,
                             end_time: Optional[datetime] = None,
                             **kwargs) -> bool:
        """Atualiza status do restore"""
        try:
            conn = self.metadata_manager._get_connection()
            cursor = conn.cursor()
            
            update_fields = ["status = %s"]
            params = [status]
            
            if end_time:
                update_fields.append("end_ts = %s")
                params.append(end_time)
            
            for key, value in kwargs.items():
                if key == 'error_message':
                    update_fields.append(f"{key} = %s")
                    params.append(value)
            
            params.append(restore_id)
            
            query = f"""
                UPDATE restore_operations 
                SET {', '.join(update_fields)}
                WHERE restore_id = %s
            """
            
            cursor.execute(query, params)
            conn.commit()
            
            self.logger.info(f"Status do restore {restore_id} atualizado para {status}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao atualizar status do restore: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def _cleanup_temp_files(self):
        """Limpa arquivos temporários"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.logger.debug(f"Arquivos temporários removidos: {self.temp_dir}")
        except Exception as e:
            self.logger.error(f"Erro na limpeza de arquivos temporários: {e}")
    
    def list_restore_operations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Lista operações de restore"""
        try:
            conn = self.metadata_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM restore_operations 
                ORDER BY start_ts DESC LIMIT %s
            """, (limit,))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Erro ao listar operações de restore: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def get_restore_status(self, restore_id: str) -> Optional[Dict[str, Any]]:
        """Obtém status de uma operação de restore"""
        try:
            conn = self.metadata_manager._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM restore_operations WHERE restore_id = %s
            """, (restore_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao obter status do restore {restore_id}: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def cleanup(self):
        """Limpa recursos"""
        try:
            self._cleanup_temp_files()
            self.metadata_manager.close()
        except Exception as e:
            self.logger.error(f"Erro no cleanup: {e}")