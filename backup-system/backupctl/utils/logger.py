"""
Configuração de logging
"""

import logging
import logging.handlers
import json
import sys
from typing import Dict, Any
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Formatter para logs em formato JSON"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Adiciona campos extras
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'lineno', 
                          'funcName', 'created', 'msecs', 'relativeCreated', 
                          'thread', 'threadName', 'processName', 'process',
                          'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        return json.dumps(log_entry)


class Logger:
    """Gerenciador de logs do backupctl"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Configura o logger"""
        logger = logging.getLogger('backupctl')
        logger.setLevel(getattr(logging, self.config.get('level', 'INFO')))
        
        # Remove handlers existentes
        logger.handlers.clear()
        
        # Formato
        log_format = self.config.get('format', 'text')
        if log_format == 'json':
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = self.config.get('file')
        if log_file:
            try:
                max_size = self._parse_size(self.config.get('max_size', '100MB'))
                backup_count = self.config.get('backup_count', 5)
                
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=max_size,
                    backupCount=backup_count
                )
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"Não foi possível configurar log de arquivo: {e}")
        
        return logger
    
    def _parse_size(self, size_str: str) -> int:
        """Converte string de tamanho para bytes"""
        size_str = size_str.upper()
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self) -> logging.Logger:
        """Retorna o logger configurado"""
        return self.logger


def get_logger(config: Dict[str, Any]) -> logging.Logger:
    """Função helper para obter logger"""
    logger_manager = Logger(config)
    return logger_manager.get_logger()