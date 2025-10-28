"""
Gerenciamento de configuração
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    """Gerenciador de configuração do backupctl"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config = {}
        self.load()
    
    def _find_config_file(self) -> str:
        """Encontra o arquivo de configuração"""
        possible_paths = [
            os.environ.get('BACKUPCTL_CONFIG'),
            './config/config.yaml',
            '/etc/backupctl/config.yaml',
            os.path.expanduser('~/.backupctl/config.yaml'),
            './config.yaml',
        ]
        
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
        
        raise FileNotFoundError("Arquivo de configuração não encontrado")
    
    def load(self) -> None:
        """Carrega configuração do arquivo"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Erro ao carregar configuração: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Obtém valor da configuração usando notação de ponto"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        # Substitui variáveis de ambiente
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            if ':' in env_var:
                var_name, default_value = env_var.split(':', 1)
                return os.environ.get(var_name, default_value)
            return os.environ.get(env_var)
        
        return value
    
    def get_postgresql_config(self) -> Dict[str, Any]:
        """Obtém configuração do PostgreSQL"""
        return self.get('postgresql', {})
    
    def get_aws_config(self) -> Dict[str, Any]:
        """Obtém configuração AWS"""
        return self.get('aws', {})
    
    def get_backup_config(self) -> Dict[str, Any]:
        """Obtém configuração de backup"""
        return self.get('backup', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Obtém configuração de logging"""
        return self.get('logging', {})
    
    def get_alerts_config(self) -> Dict[str, Any]:
        """Obtém configuração de alertas"""
        return self.get('alerts', {})
    
    def validate(self) -> bool:
        """Valida configuração essencial"""
        required_keys = [
            'postgresql.host',
            'postgresql.user',
            'postgresql.database',
            'aws.bucket',
        ]
        
        for key in required_keys:
            if not self.get(key):
                raise ValueError(f"Configuração obrigatória ausente: {key}")
        
        return True