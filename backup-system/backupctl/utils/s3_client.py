"""
Cliente AWS S3 para upload/download de backups
"""

import os
import boto3
import botocore
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from .crypto import calculate_checksum, verify_checksum


class S3Client:
    """Cliente S3 com retry e verificação de integridade"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.client = self._create_client()
        self.bucket = config.get('bucket')
        self.prefix = config.get('prefix', 'backups')
    
    def _create_client(self) -> boto3.client:
        """Cria cliente S3 com configurações"""
        try:
            session = boto3.Session(
                aws_access_key_id=self.config.get('access_key_id'),
                aws_secret_access_key=self.config.get('secret_access_key'),
                region_name=self.config.get('region', 'us-east-1')
            )
            
            client = session.client('s3')
            
            # Configura retry
            config = botocore.config.Config(
                retries={'max_attempts': 3, 'mode': 'adaptive'},
                max_pool_connections=50
            )
            
            return session.client('s3', config=config)
            
        except Exception as e:
            self.logger.error(f"Erro ao criar cliente S3: {e}")
            raise
    
    def _get_s3_key(self, backup_type: str, filename: str) -> str:
        """Gera chave S3 para o arquivo"""
        timestamp = datetime.utcnow().strftime('%Y/%m/%d')
        return f"{self.prefix}/{backup_type}/{timestamp}/{filename}"
    
    def upload_file(self, local_path: str, backup_type: str, 
                   filename: Optional[str] = None) -> Tuple[bool, str]:
        """
        Faz upload de arquivo para S3 com verificação de integridade
        
        Returns:
            Tuple[bool, str]: (sucesso, s3_key ou mensagem de erro)
        """
        try:
            if not filename:
                filename = os.path.basename(local_path)
            
            s3_key = self._get_s3_key(backup_type, filename)
            
            # Calcula checksum antes do upload
            local_checksum = calculate_checksum(local_path)
            
            # Configurações de upload
            extra_args = {
                'Metadata': {
                    'original-filename': filename,
                    'checksum': local_checksum,
                    'upload-timestamp': datetime.utcnow().isoformat(),
                    'backup-type': backup_type
                }
            }
            
            # Configura criptografia
            encryption = self.config.get('encryption', 'SSE-S3')
            if encryption == 'SSE-KMS':
                kms_key_id = self.config.get('kms_key_id')
                if kms_key_id:
                    extra_args['ServerSideEncryption'] = 'aws:kms'
                    extra_args['SSEKMSKeyId'] = kms_key_id
            elif encryption == 'SSE-S3':
                extra_args['ServerSideEncryption'] = 'AES256'
            
            # Upload com progress
            self.logger.info(f"Fazendo upload de {local_path} para s3://{self.bucket}/{s3_key}")
            
            self.client.upload_file(
                local_path,
                self.bucket,
                s3_key,
                ExtraArgs=extra_args
            )
            
            # Verifica se o arquivo foi enviado corretamente
            if self._verify_upload(local_path, s3_key, local_checksum):
                self.logger.info(f"Upload concluído com sucesso: {s3_key}")
                return True, s3_key
            else:
                self.logger.error(f"Verificação de integridade falhou para {s3_key}")
                return False, "Falha na verificação de integridade"
                
        except Exception as e:
            self.logger.error(f"Erro no upload para S3: {e}")
            return False, str(e)
    
    def _verify_upload(self, local_path: str, s3_key: str, expected_checksum: str) -> bool:
        """Verifica integridade do arquivo no S3"""
        try:
            # Download temporário para verificação
            temp_path = f"{local_path}.verify"
            
            self.client.download_file(self.bucket, s3_key, temp_path)
            
            # Verifica checksum
            is_valid = verify_checksum(temp_path, expected_checksum)
            
            # Remove arquivo temporário
            os.remove(temp_path)
            
            return is_valid
            
        except Exception as e:
            self.logger.error(f"Erro na verificação de upload: {e}")
            return False
    
    def download_file(self, s3_key: str, local_path: str) -> Tuple[bool, str]:
        """
        Baixa arquivo do S3 com verificação de integridade
        
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        try:
            self.logger.info(f"Baixando s3://{self.bucket}/{s3_key} para {local_path}")
            
            # Obtém metadados
            response = self.client.head_object(Bucket=self.bucket, Key=s3_key)
            metadata = response.get('Metadata', {})
            expected_checksum = metadata.get('checksum')
            
            # Download
            self.client.download_file(self.bucket, s3_key, local_path)
            
            # Verifica integridade se tiver checksum
            if expected_checksum:
                if verify_checksum(local_path, expected_checksum):
                    self.logger.info(f"Download verificado com sucesso: {local_path}")
                    return True, "Download concluído com sucesso"
                else:
                    self.logger.error(f"Checksum inválido para {local_path}")
                    os.remove(local_path)
                    return False, "Checksum inválido"
            else:
                self.logger.warning(f"Sem checksum para verificação: {s3_key}")
                return True, "Download concluído (sem verificação)"
                
        except Exception as e:
            self.logger.error(f"Erro no download do S3: {e}")
            return False, str(e)
    
    def list_backups(self, backup_type: Optional[str] = None, 
                    limit: int = 100) -> List[Dict[str, Any]]:
        """Lista backups no S3"""
        try:
            prefix = self.prefix
            if backup_type:
                prefix += f"/{backup_type}"
            
            paginator = self.client.get_paginator('list_objects_v2')
            pages = paginator.paginate(
                Bucket=self.bucket,
                Prefix=prefix,
                PaginationConfig={'MaxItems': limit}
            )
            
            backups = []
            for page in pages:
                for obj in page.get('Contents', []):
                    # Obtém metadados
                    try:
                        metadata_response = self.client.head_object(
                            Bucket=self.bucket,
                            Key=obj['Key']
                        )
                        metadata = metadata_response.get('Metadata', {})
                    except:
                        metadata = {}
                    
                    backups.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'],
                        'etag': obj['ETag'].strip('"'),
                        'backup_type': metadata.get('backup-type'),
                        'checksum': metadata.get('checksum'),
                        'upload_timestamp': metadata.get('upload-timestamp')
                    })
            
            # Ordena por data de modificação (mais recente primeiro)
            backups.sort(key=lambda x: x['last_modified'], reverse=True)
            
            return backups
            
        except Exception as e:
            self.logger.error(f"Erro ao listar backups: {e}")
            return []
    
    def delete_file(self, s3_key: str) -> bool:
        """Remove arquivo do S3"""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=s3_key)
            self.logger.info(f"Arquivo removido: {s3_key}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao remover arquivo {s3_key}: {e}")
            return False
    
    def get_bucket_info(self) -> Dict[str, Any]:
        """Obtém informações do bucket"""
        try:
            # Informações do bucket
            response = self.client.head_bucket(Bucket=self.bucket)
            
            # Estatísticas de uso
            objects = self.client.list_objects_v2(Bucket=self.bucket)
            total_size = sum(obj['Size'] for obj in objects.get('Contents', []))
            total_files = len(objects.get('Contents', []))
            
            return {
                'bucket': self.bucket,
                'region': self.config.get('region'),
                'total_files': total_files,
                'total_size_bytes': total_size,
                'total_size_human': self._format_bytes(total_size)
            }
            
        except Exception as e:
            self.logger.error(f"Erro ao obter informações do bucket: {e}")
            return {}
    
    def _format_bytes(self, bytes_value: int) -> str:
        """Formata bytes para representação humana"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"