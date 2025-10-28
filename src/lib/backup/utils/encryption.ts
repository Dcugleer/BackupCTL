import { createCipheriv, createDecipheriv, randomBytes, scrypt } from 'crypto';
import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import * as fs from 'fs/promises';

export interface EncryptionResult {
  filePath: string;
  key: string;
  iv: string;
  algorithm: string;
}

export interface DecryptionResult {
  filePath: string;
  originalSize: number;
}

const ALGORITHM = 'aes-256-gcm';
const KEY_LENGTH = 32;
const IV_LENGTH = 16;
const SALT_LENGTH = 32;
const TAG_LENGTH = 16;

/**
 * Criptografa um arquivo usando AES-256-GCM
 */
export async function encrypt(
  inputPath: string,
  password?: string
): Promise<EncryptionResult> {
  // Gera senha aleatória se não fornecida
  const encryptionPassword = password || randomBytes(32).toString('hex');
  
  // Gera salt para derivar chave
  const salt = randomBytes(SALT_LENGTH);
  
  // Deriva chave usando scrypt
  const key = await deriveKey(encryptionPassword, salt);
  
  // Gera IV (Initialization Vector)
  const iv = randomBytes(IV_LENGTH);
  
  // Cria cipher
  const cipher = createCipheriv(ALGORITHM, key, iv);
  
  const outputPath = `${inputPath}.enc`;
  const source = createReadStream(inputPath);
  const destination = createWriteStream(outputPath);
  
  try {
    // Escreve header no arquivo: salt + iv
    await fs.writeFile(outputPath, Buffer.concat([salt, iv]));
    
    // Criptografa o conteúdo
    await pipeline(source, cipher, destination);
    
    // Obtém authentication tag
    const tag = cipher.getAuthTag();
    
    // Adiciona tag ao final do arquivo
    await fs.appendFile(outputPath, tag);
    
    return {
      filePath: outputPath,
      key: encryptionPassword,
      iv: iv.toString('hex'),
      algorithm: ALGORITHM
    };
    
  } catch (error) {
    // Limpa arquivo parcial em caso de erro
    try {
      await fs.unlink(outputPath);
    } catch {}
    throw error;
  }
}

/**
 * Descriptografa um arquivo
 */
export async function decrypt(
  inputPath: string,
  password: string,
  outputPath?: string
): Promise<DecryptionResult> {
  const fileBuffer = await fs.readFile(inputPath);
  
  // Extrai salt e iv do header
  const salt = fileBuffer.slice(0, SALT_LENGTH);
  const iv = fileBuffer.slice(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
  
  // Extrai tag do final do arquivo
  const tag = fileBuffer.slice(-TAG_LENGTH);
  
  // Conteúdo criptografado (sem header e tag)
  const encryptedContent = fileBuffer.slice(
    SALT_LENGTH + IV_LENGTH,
    -TAG_LENGTH
  );
  
  // Deriva chave
  const key = await deriveKey(password, salt);
  
  // Cria decipher
  const decipher = createDecipheriv(ALGORITHM, key, iv);
  decipher.setAuthTag(tag);
  
  const finalOutputPath = outputPath || `${inputPath}.dec`;
  
  try {
    // Escreve conteúdo descriptografado
    await fs.writeFile(finalOutputPath, decipher.update(encryptedContent));
    await fs.appendFile(finalOutputPath, decipher.final());
    
    const stats = await fs.stat(finalOutputPath);
    
    return {
      filePath: finalOutputPath,
      originalSize: stats.size
    };
    
  } catch (error) {
    // Limpa arquivo parcial em caso de erro
    try {
      await fs.unlink(finalOutputPath);
    } catch {}
    throw new Error('Decryption failed: Invalid password or corrupted file');
  }
}

/**
 * Deriva chave a partir de senha usando scrypt
 */
async function deriveKey(password: string, salt: Buffer): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    scrypt(password, salt, KEY_LENGTH, (err, derivedKey) => {
      if (err) reject(err);
      else resolve(derivedKey);
    });
  });
}

/**
 * Gera uma chave de criptografia aleatória
 */
export function generateEncryptionKey(): string {
  return randomBytes(32).toString('hex');
}

/**
 * Verifica integridade de arquivo criptografado
 */
export async function verifyEncryptedFile(
  inputPath: string,
  password: string
): Promise<boolean> {
  try {
    const tempPath = `${inputPath}.verify`;
    await decrypt(inputPath, password, tempPath);
    await fs.unlink(tempPath);
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * Criptografa dados em memória
 */
export function encryptData(data: string, password: string): string {
  const salt = randomBytes(SALT_LENGTH);
  const iv = randomBytes(IV_LENGTH);
  const key = scryptSync(password, salt, KEY_LENGTH);
  
  const cipher = createCipheriv(ALGORITHM, key, iv);
  let encrypted = cipher.update(data, 'utf8', 'hex');
  encrypted += cipher.final('hex');
  
  const tag = cipher.getAuthTag();
  
  // Combina todos os componentes
  const combined = Buffer.concat([
    salt,
    iv,
    tag,
    Buffer.from(encrypted, 'hex')
  ]);
  
  return combined.toString('base64');
}

/**
 * Descriptografa dados em memória
 */
export function decryptData(encryptedData: string, password: string): string {
  const combined = Buffer.from(encryptedData, 'base64');
  
  const salt = combined.slice(0, SALT_LENGTH);
  const iv = combined.slice(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
  const tag = combined.slice(SALT_LENGTH + IV_LENGTH, SALT_LENGTH + IV_LENGTH + TAG_LENGTH);
  const encrypted = combined.slice(SALT_LENGTH + IV_LENGTH + TAG_LENGTH);
  
  const key = scryptSync(password, salt, KEY_LENGTH);
  
  const decipher = createDecipheriv(ALGORITHM, key, iv);
  decipher.setAuthTag(tag);
  
  let decrypted = decipher.update(encrypted, null, 'utf8');
  decrypted += decipher.final('utf8');
  
  return decrypted;
}

/**
 * Gera hash de senha para armazenamento seguro
 */
export function hashPassword(password: string): string {
  const salt = randomBytes(SALT_LENGTH);
  const key = scryptSync(password, salt, KEY_LENGTH);
  
  return Buffer.concat([salt, key]).toString('hex');
}

/**
 * Verifica hash de senha
 */
export function verifyPassword(password: string, hashedPassword: string): boolean {
  const combined = Buffer.from(hashedPassword, 'hex');
  const salt = combined.slice(0, SALT_LENGTH);
  const storedKey = combined.slice(SALT_LENGTH);
  
  const key = scryptSync(password, salt, KEY_LENGTH);
  
  return key.equals(storedKey);
}

/**
 * Criptografa stream de dados
 */
export async function encryptStream(
  inputStream: NodeJS.ReadableStream,
  outputStream: NodeJS.WritableStream,
  password: string
): Promise<{ key: string; iv: string }> {
  const encryptionPassword = password || generateEncryptionKey();
  const salt = randomBytes(SALT_LENGTH);
  const iv = randomBytes(IV_LENGTH);
  const key = await deriveKey(encryptionPassword, salt);
  
  // Escreve header
  outputStream.write(Buffer.concat([salt, iv]));
  
  // Cria cipher e pipeline
  const cipher = createCipheriv(ALGORITHM, key, iv);
  
  await pipeline(inputStream, cipher, outputStream);
  
  // Adiciona tag
  const tag = cipher.getAuthTag();
  outputStream.write(tag);
  
  return {
    key: encryptionPassword,
    iv: iv.toString('hex')
  };
}

/**
 * Descriptografa stream de dados
 */
export async function decryptStream(
  inputStream: NodeJS.ReadableStream,
  outputStream: NodeJS.WritableStream,
  password: string
): Promise<void> {
  // Lê header
  const header = await readBytes(inputStream, SALT_LENGTH + IV_LENGTH);
  const salt = header.slice(0, SALT_LENGTH);
  const iv = header.slice(SALT_LENGTH);
  
  // Deriva chave
  const key = await deriveKey(password, salt);
  
  // Cria decipher
  const decipher = createDecipheriv(ALGORITHM, key, iv);
  
  // Lê tudo menos a tag
  const chunks: Buffer[] = [];
  let tag: Buffer | null = null;
  
  inputStream.on('data', (chunk: Buffer) => {
    if (tag === null && chunks.length > 0) {
      // Último chunk contém a tag
      const tagStart = chunk.length - TAG_LENGTH;
      chunks.push(chunk.slice(0, tagStart));
      tag = chunk.slice(tagStart);
    } else {
      chunks.push(chunk);
    }
  });
  
  return new Promise((resolve, reject) => {
    inputStream.on('end', async () => {
      try {
        if (!tag) {
          throw new Error('Invalid encrypted file format');
        }
        
        decipher.setAuthTag(tag);
        
        // Processa chunks
        for (const chunk of chunks) {
          outputStream.write(decipher.update(chunk));
        }
        
        outputStream.write(decipher.final());
        outputStream.end();
        
        resolve();
      } catch (error) {
        reject(error);
      }
    });
    
    inputStream.on('error', reject);
  });
}

/**
 * Lê bytes específicos de um stream
 */
function readBytes(stream: NodeJS.ReadableStream, count: number): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let totalBytes = 0;
    
    const onData = (chunk: Buffer) => {
      chunks.push(chunk);
      totalBytes += chunk.length;
      
      if (totalBytes >= count) {
        stream.removeListener('data', onData);
        stream.removeListener('error', onError);
        
        const combined = Buffer.concat(chunks);
        resolve(combined.slice(0, count));
      }
    };
    
    const onError = (error: Error) => {
      stream.removeListener('data', onData);
      reject(error);
    };
    
    stream.on('data', onData);
    stream.on('error', onError);
  });
}