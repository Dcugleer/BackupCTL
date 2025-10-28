"""
Gerenciamento de metadados de backups
"""

import psycopg2
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import logging


class MetadataManager:
    """Gerenciador de metadados de backups no PostgreSQL"""
    
    def __init__(self, pg_config: Dict[str, Any], logger: logging.Logger):
        self.pg_config = pg_config
        self.logger = logger
        self.connection = None
        self._initialize_schema()
    
    def _get_connection(self):
        """Obtém conexão com PostgreSQL"""
        if not self.connection or self.connection.closed:
            try:
                self.connection = psycopg2.connect(
                    host=self.pg_config.get('host'),
                    port=self.pg_config.get('port', 5432),
                    user=self.pg_config.get('user'),
                    password=self.pg_config.get('password'),
                    database=self.pg_config.get('database'),
                    connect_timeout=self.pg_config.get('connection_timeout', 30)
                )
                self.connection.autocommit = False
            except Exception as e:
                self.logger.error(f"Erro ao conectar ao PostgreSQL: {e}")
                raise
        
        return self.connection
    
    def _initialize_schema(self):
        """Inicializa schema de metadados"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Tabela de backups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS backup_metadata (
                    id SERIAL PRIMARY KEY,
                    backup_id VARCHAR(255) UNIQUE NOT NULL,
                    backup_type VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    start_ts TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_ts TIMESTAMP WITH TIME ZONE,
                    size_bytes BIGINT,
                    s3_key VARCHAR(1000),
                    s3_bucket VARCHAR(255),
                    checksum VARCHAR(256),
                    compression VARCHAR(50),
                    encryption VARCHAR(50),
                    label VARCHAR(255),
                    description TEXT,
                    metadata_json JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Tabela de WAL files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wal_metadata (
                    id SERIAL PRIMARY KEY,
                    wal_name VARCHAR(255) NOT NULL,
                    backup_id VARCHAR(255) REFERENCES backup_metadata(backup_id),
                    start_ts TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_ts TIMESTAMP WITH TIME ZONE NOT NULL,
                    size_bytes BIGINT,
                    s3_key VARCHAR(1000),
                    checksum VARCHAR(256),
                    sequence_number BIGINT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Tabela de restore operations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS restore_operations (
                    id SERIAL PRIMARY KEY,
                    restore_id VARCHAR(255) UNIQUE NOT NULL,
                    backup_id VARCHAR(255) REFERENCES backup_metadata(backup_id),
                    target_time TIMESTAMP WITH TIME ZONE,
                    target_xid VARCHAR(255),
                    target_lsn VARCHAR(255),
                    status VARCHAR(50) NOT NULL,
                    start_ts TIMESTAMP WITH TIME ZONE NOT NULL,
                    end_ts TIMESTAMP WITH TIME ZONE,
                    destination_path VARCHAR(1000),
                    error_message TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            
            # Índices
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_backup_metadata_type_status 
                ON backup_metadata(backup_type, status);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_backup_metadata_start_ts 
                ON backup_metadata(start_ts DESC);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wal_metadata_sequence 
                ON wal_metadata(sequence_number);
            """)
            
            conn.commit()
            self.logger.info("Schema de metadados inicializado com sucesso")
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Erro ao inicializar schema: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def create_backup_record(self, backup_data: Dict[str, Any]) -> str:
        """Cria registro de backup"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO backup_metadata (
                    backup_id, backup_type, status, start_ts, end_ts,
                    size_bytes, s3_key, s3_bucket, checksum, compression,
                    encryption, label, description, metadata_json
                ) VALUES (
                    %(backup_id)s, %(backup_type)s, %(status)s, 
                    %(start_ts)s, %(end_ts)s, %(size_bytes)s, %(s3_key)s,
                    %(s3_bucket)s, %(checksum)s, %(compression)s, %(encryption)s,
                    %(label)s, %(description)s, %(metadata_json)s
                ) RETURNING backup_id;
            """, backup_data)
            
            backup_id = cursor.fetchone()[0]
            conn.commit()
            
            self.logger.info(f"Registro de backup criado: {backup_id}")
            return backup_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Erro ao criar registro de backup: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def update_backup_status(self, backup_id: str, status: str, 
                           end_ts: Optional[datetime] = None,
                           **kwargs) -> bool:
        """Atualiza status do backup"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            update_fields = ["status = %s"]
            params = [status]
            
            if end_ts:
                update_fields.append("end_ts = %s")
                params.append(end_ts)
            
            for key, value in kwargs.items():
                if key in ['size_bytes', 's3_key', 'checksum']:
                    update_fields.append(f"{key} = %s")
                    params.append(value)
            
            params.append(backup_id)
            
            query = f"""
                UPDATE backup_metadata 
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE backup_id = %s
            """
            
            cursor.execute(query, params)
            conn.commit()
            
            self.logger.info(f"Status do backup {backup_id} atualizado para {status}")
            return True
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Erro ao atualizar status do backup: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
    
    def get_backup_by_id(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Obtém backup por ID"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM backup_metadata WHERE backup_id = %s
            """, (backup_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao buscar backup {backup_id}: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def list_backups(self, backup_type: Optional[str] = None,
                    status: Optional[str] = None,
                    limit: int = 50) -> List[Dict[str, Any]]:
        """Lista backups com filtros"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = "SELECT * FROM backup_metadata WHERE 1=1"
            params = []
            
            if backup_type:
                query += " AND backup_type = %s"
                params.append(backup_type)
            
            if status:
                query += " AND status = %s"
                params.append(status)
            
            query += " ORDER BY start_ts DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Erro ao listar backups: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def get_latest_backup(self, backup_type: str = 'full') -> Optional[Dict[str, Any]]:
        """Obtém backup mais recente"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM backup_metadata 
                WHERE backup_type = %s AND status = 'completed'
                ORDER BY start_ts DESC LIMIT 1
            """, (backup_type,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            
            return None
            
        except Exception as e:
            self.logger.error(f"Erro ao obter backup mais recente: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def create_wal_record(self, wal_data: Dict[str, Any]) -> str:
        """Cria registro de WAL"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO wal_metadata (
                    wal_name, backup_id, start_ts, end_ts, size_bytes,
                    s3_key, checksum, sequence_number
                ) VALUES (
                    %(wal_name)s, %(backup_id)s, %(start_ts)s, %(end_ts)s,
                    %(size_bytes)s, %(s3_key)s, %(checksum)s, %(sequence_number)s
                ) RETURNING id;
            """, wal_data)
            
            wal_id = cursor.fetchone()[0]
            conn.commit()
            
            self.logger.info(f"Registro de WAL criado: {wal_id}")
            return str(wal_id)
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Erro ao criar registro de WAL: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def get_wals_for_backup(self, backup_id: str) -> List[Dict[str, Any]]:
        """Obtém WALs associados a um backup"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM wal_metadata 
                WHERE backup_id = %s 
                ORDER BY sequence_number
            """, (backup_id,))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            self.logger.error(f"Erro ao obter WALs do backup {backup_id}: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
    
    def create_restore_record(self, restore_data: Dict[str, Any]) -> str:
        """Cria registro de restore"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO restore_operations (
                    restore_id, backup_id, target_time, target_xid,
                    target_lsn, status, start_ts, destination_path
                ) VALUES (
                    %(restore_id)s, %(backup_id)s, %(target_time)s,
                    %(target_xid)s, %(target_lsn)s, %(status)s,
                    %(start_ts)s, %(destination_path)s
                ) RETURNING restore_id;
            """, restore_data)
            
            restore_id = cursor.fetchone()[0]
            conn.commit()
            
            self.logger.info(f"Registro de restore criado: {restore_id}")
            return restore_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Erro ao criar registro de restore: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
    
    def get_backup_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas dos backups"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Estatísticas gerais
            cursor.execute("""
                SELECT 
                    backup_type,
                    status,
                    COUNT(*) as count,
                    AVG(size_bytes) as avg_size,
                    SUM(size_bytes) as total_size
                FROM backup_metadata 
                GROUP BY backup_type, status
            """)
            
            stats = {}
            for row in cursor.fetchall():
                backup_type, status, count, avg_size, total_size = row
                if backup_type not in stats:
                    stats[backup_type] = {}
                stats[backup_type][status] = {
                    'count': count,
                    'avg_size': avg_size,
                    'total_size': total_size
                }
            
            # Últimos backups
            cursor.execute("""
                SELECT backup_type, MAX(start_ts) as last_backup
                FROM backup_metadata 
                WHERE status = 'completed'
                GROUP BY backup_type
            """)
            
            last_backups = {}
            for row in cursor.fetchall():
                backup_type, last_backup = row
                last_backups[backup_type] = last_backup
            
            return {
                'statistics': stats,
                'last_backups': last_backups
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter estatísticas: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()
    
    def close(self):
        """Fecha conexão com PostgreSQL"""
        if self.connection and not self.connection.closed:
            self.connection.close()
            self.logger.info("Conexão com PostgreSQL fechada")