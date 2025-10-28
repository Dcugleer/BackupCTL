"""
Testes automatizados para backupctl
"""

import unittest
import tempfile
import os
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backupctl.utils.config import Config
from backupctl.utils.logger import get_logger
from backupctl.core.backup import BackupEngine
from backupctl.core.restore import RestoreEngine


class TestBackupRestore(unittest.TestCase):
    """Testes para backup e restore"""
    
    def setUp(self):
        """Configuração dos testes"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'user': 'test_user',
                'password': 'test_pass',
                'database': 'test_db',
                'backup_dir': self.temp_dir
            },
            'aws': {
                'region': 'us-east-1',
                'bucket': 'test-bucket',
                'prefix': 'test-backups',
                'encryption': 'SSE-S3'
            },
            'backup': {
                'retention': {
                    'full_days': 7,
                    'incremental_days': 2
                },
                'compression': {
                    'enabled': True,
                    'level': 6
                }
            },
            'restore': {
                'temp_dir': self.temp_dir
            },
            'logging': {
                'level': 'DEBUG',
                'format': 'text'
            }
        }
        
        self.logger = get_logger(self.test_config['logging'])
    
    def tearDown(self):
        """Limpeza dos testes"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_config_validation(self):
        """Testa validação de configuração"""
        config = Config()
        
        # Config válida
        with patch.object(config, '_config', self.test_config):
            self.assertTrue(config.validate())
        
        # Config inválida (sem bucket)
        invalid_config = self.test_config.copy()
        del invalid_config['aws']['bucket']
        
        with patch.object(config, '_config', invalid_config):
            with self.assertRaises(ValueError):
                config.validate()
    
    def test_checksum_calculation(self):
        """Testa cálculo de checksum"""
        from backupctl.utils.crypto import calculate_checksum, verify_checksum
        
        # Cria arquivo de teste
        test_file = os.path.join(self.temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('test content')
        
        # Calcula checksum
        checksum = calculate_checksum(test_file)
        self.assertIsNotNone(checksum)
        self.assertEqual(len(checksum), 64)  # SHA256
        
        # Verifica checksum
        self.assertTrue(verify_checksum(test_file, checksum))
        self.assertFalse(verify_checksum(test_file, 'invalid_checksum'))
    
    def test_compression_decompression(self):
        """Testa compressão e descompressão"""
        from backupctl.utils.crypto import compress_file, decompress_file
        
        # Cria arquivo de teste
        test_file = os.path.join(self.temp_dir, 'test.txt')
        compressed_file = test_file + '.gz'
        decompressed_file = test_file + '.decompressed'
        
        with open(test_file, 'w') as f:
            f.write('test content for compression')
        
        # Comprime
        self.assertTrue(compress_file(test_file, compressed_file))
        self.assertTrue(os.path.exists(compressed_file))
        
        # Verifica que arquivo comprimido é menor
        self.assertLess(os.path.getsize(compressed_file), os.path.getsize(test_file))
        
        # Descomprime
        self.assertTrue(decompress_file(compressed_file, decompressed_file))
        self.assertTrue(os.path.exists(decompressed_file))
        
        # Verifica conteúdo
        with open(test_file, 'r') as f1, open(decompressed_file, 'r') as f2:
            self.assertEqual(f1.read(), f2.read())
    
    @patch('backupctl.core.backup.subprocess.run')
    @patch('backupctl.core.backup.S3Client')
    @patch('backupctl.core.backup.MetadataManager')
    def test_full_backup_success(self, mock_metadata, mock_s3, mock_subprocess):
        """Testa backup completo bem-sucedido"""
        # Mock subprocess
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Mock S3
        mock_s3_instance = Mock()
        mock_s3_instance.upload_file.return_value = (True, 'test-key')
        mock_s3.return_value = mock_s3_instance
        
        # Mock metadata
        mock_metadata_instance = Mock()
        mock_metadata_instance.create_backup_record.return_value = 'test-backup-id'
        mock_metadata_instance.update_backup_status.return_value = True
        mock_metadata.return_value = mock_metadata_instance
        
        # Cria arquivo de backup fake
        backup_file = os.path.join(self.temp_dir, 'test-backup.sql')
        with open(backup_file, 'w') as f:
            f.write('-- SQL backup content')
        
        # Mock pg_dump para criar arquivo
        def mock_subprocess_side_effect(cmd, **kwargs):
            if 'pg_dump' in cmd:
                with open(backup_file, 'w') as f:
                    f.write('-- SQL backup content')
            return Mock(returncode=0)
        
        mock_subprocess.side_effect = mock_subprocess_side_effect
        
        # Executa backup
        backup_engine = BackupEngine(self.test_config, self.logger)
        success, backup_id = backup_engine.create_full_backup('test-label')
        
        # Verificações
        self.assertTrue(success)
        self.assertIsNotNone(backup_id)
        mock_metadata_instance.create_backup_record.assert_called_once()
        mock_s3_instance.upload_file.assert_called_once()
        mock_metadata_instance.update_backup_status.assert_called_once()
    
    @patch('backupctl.core.restore.subprocess.run')
    @patch('backupctl.core.restore.S3Client')
    @patch('backupctl.core.restore.MetadataManager')
    def test_restore_success(self, mock_metadata, mock_s3, mock_subprocess):
        """Testa restore bem-sucedido"""
        # Mock metadata
        mock_metadata_instance = Mock()
        mock_metadata_instance.get_backup_by_id.return_value = {
            'backup_id': 'test-backup-id',
            'status': 'completed',
            's3_key': 'test-key',
            'checksum': 'test-checksum'
        }
        mock_metadata_instance.create_restore_record.return_value = 'test-restore-id'
        mock_metadata_instance._get_connection.return_value = Mock()
        mock_metadata.return_value = mock_metadata_instance
        
        # Mock S3
        mock_s3_instance = Mock()
        mock_s3_instance.download_file.return_value = (True, 'downloaded-file')
        mock_s3.return_value = mock_s3_instance
        
        # Mock subprocess
        mock_subprocess.return_value = Mock(returncode=0)
        
        # Executa restore
        restore_engine = RestoreEngine(self.test_config, self.logger)
        success, restore_id = restore_engine.restore_backup(
            backup_id='test-backup-id',
            destination=self.temp_dir
        )
        
        # Verificações
        self.assertTrue(success)
        self.assertIsNotNone(restore_id)
        mock_metadata_instance.get_backup_by_id.assert_called_once()
        mock_s3_instance.download_file.assert_called_once()
        mock_metadata_instance.create_restore_record.assert_called_once()
    
    def test_backup_engine_initialization(self):
        """Testa inicialização do BackupEngine"""
        with patch('backupctl.core.backup.S3Client'), \
             patch('backupctl.core.backup.MetadataManager'):
            
            backup_engine = BackupEngine(self.test_config, self.logger)
            
            self.assertIsNotNone(backup_engine.s3_client)
            self.assertIsNotNone(backup_engine.metadata_manager)
            self.assertIsNotNone(backup_engine.temp_dir)
            self.assertTrue(os.path.exists(backup_engine.temp_dir))
    
    def test_restore_engine_initialization(self):
        """Testa inicialização do RestoreEngine"""
        with patch('backupctl.core.restore.S3Client'), \
             patch('backupctl.core.restore.MetadataManager'):
            
            restore_engine = RestoreEngine(self.test_config, self.logger)
            
            self.assertIsNotNone(restore_engine.s3_client)
            self.assertIsNotNone(restore_engine.metadata_manager)
            self.assertIsNotNone(restore_engine.temp_dir)
            self.assertTrue(os.path.exists(restore_engine.temp_dir))
    
    def test_wal_sequence_extraction(self):
        """Testa extração de número de sequência WAL"""
        backup_engine = BackupEngine(self.test_config, self.logger)
        
        # Testa extração de sequência
        sequence = backup_engine._extract_wal_sequence('000000010000000000000001')
        self.assertEqual(sequence, 1)
        
        sequence = backup_engine._extract_wal_sequence('0000000A0000000B0000000C')
        self.assertEqual(sequence, int('0000000A0000000B0000000C', 16))
    
    def test_postgres_version_detection(self):
        """Testa detecção de versão PostgreSQL"""
        with patch('backupctl.core.backup.subprocess.run') as mock_subprocess:
            mock_subprocess.return_value = Mock(
                returncode=0,
                stdout='PostgreSQL 13.7 on x86_64-pc-linux-gnu'
            )
            
            backup_engine = BackupEngine(self.test_config, self.logger)
            version = backup_engine._get_postgres_version()
            
            self.assertIn('PostgreSQL', version)
            mock_subprocess.assert_called_once()
    
    def test_cleanup_temp_files(self):
        """Testa limpeza de arquivos temporários"""
        backup_engine = BackupEngine(self.test_config, self.logger)
        
        # Cria arquivo temporário
        temp_file = os.path.join(backup_engine.temp_dir, 'test.txt')
        with open(temp_file, 'w') as f:
            f.write('test')
        
        self.assertTrue(os.path.exists(temp_file))
        
        # Limpa
        backup_engine._cleanup_temp_files()
        
        # Verifica que diretório foi removido
        self.assertFalse(os.path.exists(backup_engine.temp_dir))


class TestS3Client(unittest.TestCase):
    """Testes para S3Client"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            'region': 'us-east-1',
            'bucket': 'test-bucket',
            'prefix': 'test-backups',
            'encryption': 'SSE-S3'
        }
        self.logger = get_logger({'level': 'DEBUG', 'format': 'text'})
    
    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_s3_key_generation(self):
        """Testa geração de chaves S3"""
        from backupctl.utils.s3_client import S3Client
        
        with patch('boto3.Session'):
            s3_client = S3Client(self.test_config, self.logger)
            
            key = s3_client._get_s3_key('full', 'test-backup.sql')
            expected_prefix = f"test-backups/full/{datetime.now().strftime('%Y/%m/%d')}/test-backup.sql"
            self.assertEqual(key, expected_prefix)
    
    def test_bytes_formatting(self):
        """Testa formatação de bytes"""
        from backupctl.utils.s3_client import S3Client
        
        with patch('boto3.Session'):
            s3_client = S3Client(self.test_config, self.logger)
            
            self.assertEqual(s3_client._format_bytes(1024), "1.00 KB")
            self.assertEqual(s3_client._format_bytes(1024*1024), "1.00 MB")
            self.assertEqual(s3_client._format_bytes(1024*1024*1024), "1.00 GB")


if __name__ == '__main__':
    unittest.main()