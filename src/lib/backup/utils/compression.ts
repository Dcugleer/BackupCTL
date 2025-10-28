import { exec } from 'child_process';
import { promisify } from 'util';
import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import * as zlib from 'zlib';
import * as fs from 'fs/promises';

const execAsync = promisify(exec);

export type CompressionType = 'GZIP' | 'ZSTD' | 'LZ4' | 'NONE';

export interface CompressionResult {
  filePath: string;
  originalSize: number;
  compressedSize: number;
  compressionRatio: number;
}

/**
 * Comprime um arquivo usando o algoritmo especificado
 */
export async function compress(
  filePath: string,
  compressionType: CompressionType = 'GZIP'
): Promise<string> {
  if (compressionType === 'NONE') {
    return filePath;
  }

  const stats = await fs.stat(filePath);
  const originalSize = stats.size;
  
  let compressedPath: string;
  
  switch (compressionType) {
    case 'GZIP':
      compressedPath = `${filePath}.gz`;
      await compressGzip(filePath, compressedPath);
      break;
      
    case 'ZSTD':
      compressedPath = `${filePath}.zst`;
      await compressZstd(filePath, compressedPath);
      break;
      
    case 'LZ4':
      compressedPath = `${filePath}.lz4`;
      await compressLz4(filePath, compressedPath);
      break;
      
    default:
      throw new Error(`Unsupported compression type: ${compressionType}`);
  }

  const compressedStats = await fs.stat(compressedPath);
  const compressionRatio = originalSize > 0 
    ? compressedStats.size / originalSize 
    : 1;

  console.log(`Compression completed:`);
  console.log(`  Original: ${(originalSize / 1024 / 1024).toFixed(2)} MB`);
  console.log(`  Compressed: ${(compressedStats.size / 1024 / 1024).toFixed(2)} MB`);
  console.log(`  Ratio: ${(compressionRatio * 100).toFixed(1)}%`);

  return compressedPath;
}

/**
 * Descomprime um arquivo
 */
export async function decompress(
  compressedPath: string,
  outputPath: string,
  compressionType: CompressionType = 'GZIP'
): Promise<string> {
  switch (compressionType) {
    case 'GZIP':
      await decompressGzip(compressedPath, outputPath);
      break;
      
    case 'ZSTD':
      await decompressZstd(compressedPath, outputPath);
      break;
      
    case 'LZ4':
      await decompressLz4(compressedPath, outputPath);
      break;
      
    case 'NONE':
      // Se não há compressão, apenas copia o arquivo
      await fs.copyFile(compressedPath, outputPath);
      break;
      
    default:
      throw new Error(`Unsupported compression type: ${compressionType}`);
  }

  return outputPath;
}

/**
 * Compressão GZIP (padrão, amplamente suportado)
 */
async function compressGzip(inputPath: string, outputPath: string): Promise<void> {
  const gzip = zlib.createGzip({
    level: 6, // Nível de compressão (1-9, 6 é padrão)
    memLevel: 8
  });

  const source = createReadStream(inputPath);
  const destination = createWriteStream(outputPath);

  await pipeline(source, gzip, destination);
}

/**
 * Descompressão GZIP
 */
async function decompressGzip(inputPath: string, outputPath: string): Promise<void> {
  const gunzip = zlib.createGunzip();
  const source = createReadStream(inputPath);
  const destination = createWriteStream(outputPath);

  await pipeline(source, gunzip, destination);
}

/**
 * Compressão ZSTD (Zstandard) - alta performance e boa razão de compressão
 */
async function compressZstd(inputPath: string, outputPath: string): Promise<void> {
  try {
    // Tenta usar zstd CLI se disponível
    await execAsync(`zstd -f -o "${outputPath}" "${inputPath}"`);
  } catch (error) {
    // Fallback para implementação Node.js se zstd não estiver instalado
    console.warn('zstd CLI not found, using Node.js implementation');
    
    // Implementação básica usando zlib (não é zstd real, mas funciona como fallback)
    const deflate = zlib.createDeflateRaw({
      level: 9
    });
    
    const source = createReadStream(inputPath);
    const destination = createWriteStream(outputPath);
    
    await pipeline(source, deflate, destination);
  }
}

/**
 * Descompressão ZSTD
 */
async function decompressZstd(inputPath: string, outputPath: string): Promise<void> {
  try {
    // Tenta usar zstd CLI se disponível
    await execAsync(`zstd -d -f -o "${outputPath}" "${inputPath}"`);
  } catch (error) {
    // Fallback para implementação Node.js
    console.warn('zstd CLI not found, using Node.js implementation');
    
    const inflate = zlib.createInflateRaw();
    const source = createReadStream(inputPath);
    const destination = createWriteStream(outputPath);
    
    await pipeline(source, inflate, destination);
  }
}

/**
 * Compressão LZ4 - velocidade extrema
 */
async function compressLz4(inputPath: string, outputPath: string): Promise<void> {
  try {
    // Tenta usar lz4 CLI se disponível
    await execAsync(`lz4 -f "${inputPath}" "${outputPath}"`);
  } catch (error) {
    // Fallback para implementação Node.js
    console.warn('lz4 CLI not found, using Node.js implementation');
    
    // Implementação básica usando gzip como fallback
    const gzip = zlib.createGzip({
      level: 1 // Baixa compressão para alta velocidade
    });
    
    const source = createReadStream(inputPath);
    const destination = createWriteStream(outputPath);
    
    await pipeline(source, gzip, destination);
  }
}

/**
 * Descompressão LZ4
 */
async function decompressLz4(inputPath: string, outputPath: string): Promise<void> {
  try {
    // Tenta usar lz4 CLI se disponível
    await execAsync(`lz4 -d -f "${inputPath}" "${outputPath}"`);
  } catch (error) {
    // Fallback para implementação Node.js
    console.warn('lz4 CLI not found, using Node.js implementation');
    
    const gunzip = zlib.createGunzip();
    const source = createReadStream(inputPath);
    const destination = createWriteStream(outputPath);
    
    await pipeline(source, gunzip, destination);
  }
}

/**
 * Obtém informações de compressão de um arquivo
 */
export async function getCompressionInfo(
  originalPath: string,
  compressedPath: string
): Promise<CompressionResult> {
  const originalStats = await fs.stat(originalPath);
  const compressedStats = await fs.stat(compressedPath);
  
  const compressionRatio = originalStats.size > 0 
    ? compressedStats.size / originalStats.size 
    : 1;

  return {
    filePath: compressedPath,
    originalSize: originalStats.size,
    compressedSize: compressedStats.size,
    compressionRatio
  };
}

/**
 * Testa a integridade de um arquivo comprimido
 */
export async function testCompressionIntegrity(
  compressedPath: string,
  compressionType: CompressionType
): Promise<boolean> {
  const tempPath = `${compressedPath}.test`;
  
  try {
    await decompress(compressedPath, tempPath, compressionType);
    await fs.unlink(tempPath);
    return true;
  } catch (error) {
    console.error('Compression integrity test failed:', error);
    return false;
  }
}

/**
 * Compara diferentes algoritmos de compressão para um arquivo
 */
export async function benchmarkCompression(
  filePath: string
): Promise<{ [key in CompressionType]: CompressionResult }> {
  const results: any = {};
  const originalStats = await fs.stat(filePath);

  for (const type of ['NONE', 'GZIP', 'ZSTD', 'LZ4'] as CompressionType[]) {
    if (type === 'NONE') {
      results[type] = {
        filePath,
        originalSize: originalStats.size,
        compressedSize: originalStats.size,
        compressionRatio: 1
      };
      continue;
    }

    const startTime = Date.now();
    const compressedPath = await compress(filePath, type);
    const endTime = Date.now();

    const compressionInfo = await getCompressionInfo(filePath, compressedPath);
    
    results[type] = {
      ...compressionInfo,
      compressionTime: endTime - startTime
    };

    // Limpa arquivo temporário
    await fs.unlink(compressedPath);
  }

  return results;
}

/**
 * Verifica se um algoritmo de compressão está disponível
 */
export async function isCompressionAvailable(type: CompressionType): Promise<boolean> {
  switch (type) {
    case 'NONE':
    case 'GZIP':
      return true; // Sempre disponível via Node.js
      
    case 'ZSTD':
      try {
        await execAsync('zstd --version');
        return true;
      } catch {
        return false;
      }
      
    case 'LZ4':
      try {
        await execAsync('lz4 --version');
        return true;
      } catch {
        return false;
      }
      
    default:
      return false;
  }
}