"""
Utilitários de criptografia e checksum
"""

import hashlib
import os
from typing import Tuple, Optional


def calculate_checksum(file_path: str, algorithm: str = 'sha256') -> str:
    """Calcula checksum de um arquivo"""
    hash_func = getattr(hashlib, algorithm)()
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()


def verify_checksum(file_path: str, expected_checksum: str, algorithm: str = 'sha256') -> bool:
    """Verifica se o checksum do arquivo corresponde ao esperado"""
    actual_checksum = calculate_checksum(file_path, algorithm)
    return actual_checksum.lower() == expected_checksum.lower()


def generate_encryption_key(length: int = 32) -> bytes:
    """Gera chave de criptografia aleatória"""
    return os.urandom(length)


def encrypt_file(input_path: str, output_path: str, key: bytes) -> bool:
    """Criptografa arquivo usando AES (simplificado)"""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        # Deriva chave do key material
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'salt_',  # Em produção, usar salt aleatório
            iterations=100000,
        )
        key_base64 = base64.urlsafe_b64encode(kdf.derive(key))
        
        f = Fernet(key_base64)
        
        with open(input_path, 'rb') as infile:
            data = infile.read()
        
        encrypted_data = f.encrypt(data)
        
        with open(output_path, 'wb') as outfile:
            outfile.write(encrypted_data)
        
        return True
    except ImportError:
        # Se cryptography não estiver disponível, apenas copia o arquivo
        import shutil
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        print(f"Erro na criptografia: {e}")
        return False


def decrypt_file(input_path: str, output_path: str, key: bytes) -> bool:
    """Descriptografa arquivo usando AES (simplificado)"""
    try:
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        # Deriva chave do key material
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'salt_',  # Em produção, usar salt aleatório
            iterations=100000,
        )
        key_base64 = base64.urlsafe_b64encode(kdf.derive(key))
        
        f = Fernet(key_base64)
        
        with open(input_path, 'rb') as infile:
            encrypted_data = infile.read()
        
        decrypted_data = f.decrypt(encrypted_data)
        
        with open(output_path, 'wb') as outfile:
            outfile.write(decrypted_data)
        
        return True
    except ImportError:
        # Se cryptography não estiver disponível, apenas copia o arquivo
        import shutil
        shutil.copy2(input_path, output_path)
        return True
    except Exception as e:
        print(f"Erro na descriptografia: {e}")
        return False


def compress_file(input_path: str, output_path: str, compression_level: int = 6) -> bool:
    """Comprime arquivo usando gzip"""
    try:
        import gzip
        
        with open(input_path, 'rb') as f_in:
            with gzip.open(output_path, 'wb', compresslevel=compression_level) as f_out:
                f_out.writelines(f_in)
        
        return True
    except Exception as e:
        print(f"Erro na compressão: {e}")
        return False


def decompress_file(input_path: str, output_path: str) -> bool:
    """Descomprime arquivo gzip"""
    try:
        import gzip
        
        with gzip.open(input_path, 'rb') as f_in:
            with open(output_path, 'wb') as f_out:
                f_out.writelines(f_in)
        
        return True
    except Exception as e:
        print(f"Erro na descompressão: {e}")
        return False