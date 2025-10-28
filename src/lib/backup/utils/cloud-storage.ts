/* eslint-disable @typescript-eslint/no-require-imports */
import { db } from '@/lib/db';
import { CloudType } from '@prisma/client';

export interface CloudUploadOptions {
  backupId: string;
  databaseId: string;
  type: string;
  metadata?: Record<string, any>;
}

export interface CloudStorageConfig {
  type: CloudType;
  config: Record<string, any>;
}

/**
 * Upload de arquivo para armazenamento em nuvem
 */
export async function uploadToCloud(
  filePath: string,
  options: CloudUploadOptions
): Promise<string> {
  // Busca configuração de armazenamento padrão ou específica
  const cloudStorage = await getDefaultCloudStorage();
  
  if (!cloudStorage) {
    throw new Error('No cloud storage configured');
  }

  const config = JSON.parse(cloudStorage.config) as CloudStorageConfig;
  
  switch (cloudStorage.type) {
    case 'AWS_S3':
      return await uploadToS3(filePath, options, config);
      
    case 'AZURE_BLOB':
      return await uploadToAzureBlob(filePath, options, config);
      
    case 'GCP_STORAGE':
      return await uploadToGCPStorage(filePath, options, config);
      
    case 'FTP':
      return await uploadToFTP(filePath, options, config);
      
    case 'SFTP':
      return await uploadToSFTP(filePath, options, config);
      
    case 'LOCAL':
      return await uploadToLocal(filePath, options, config);
      
    default:
      throw new Error(`Unsupported cloud storage type: ${cloudStorage.type}`);
  }
}

/**
 * Download de arquivo da nuvem
 */
export async function downloadFromCloud(
  s3Key: string,
  localPath: string,
  cloudStorageId?: string
): Promise<void> {
  const cloudStorage = cloudStorageId 
    ? await db.cloudStorage.findUnique({ where: { id: cloudStorageId } })
    : await getDefaultCloudStorage();
    
  if (!cloudStorage) {
    throw new Error('Cloud storage not found');
  }

  const config = JSON.parse(cloudStorage.config) as CloudStorageConfig;
  
  switch (cloudStorage.type) {
    case 'AWS_S3':
      await downloadFromS3(s3Key, localPath, config);
      break;
      
    case 'AZURE_BLOB':
      await downloadFromAzureBlob(s3Key, localPath, config);
      break;
      
    case 'GCP_STORAGE':
      await downloadFromGCPStorage(s3Key, localPath, config);
      break;
      
    case 'FTP':
      await downloadFromFTP(s3Key, localPath, config);
      break;
      
    case 'SFTP':
      await downloadFromSFTP(s3Key, localPath, config);
      break;
      
    case 'LOCAL':
      await downloadFromLocal(s3Key, localPath, config);
      break;
      
    default:
      throw new Error(`Unsupported cloud storage type: ${cloudStorage.type}`);
  }
}

/**
 * Upload para AWS S3
 */
async function uploadToS3(
  filePath: string,
  options: CloudUploadOptions,
  config: any
): Promise<string> {
  const AWS = require('aws-sdk');
  
  const s3 = new AWS.S3({
    accessKeyId: config.accessKeyId,
    secretAccessKey: config.secretAccessKey,
    region: config.region || 'us-east-1'
  });

  const s3Key = generateS3Key(options);
  
  const params = {
    Bucket: config.bucket,
    Key: s3Key,
    Body: require('fs').createReadStream(filePath),
    ServerSideEncryption: config.encryption || 'AES256',
    Metadata: {
      backupId: options.backupId,
      databaseId: options.databaseId,
      type: options.type,
      ...options.metadata
    }
  };

  await s3.upload(params).promise();
  
  return s3Key;
}

/**
 * Download do AWS S3
 */
async function downloadFromS3(
  s3Key: string,
  localPath: string,
  config: any
): Promise<void> {
  const AWS = require('aws-sdk');
  
  const s3 = new AWS.S3({
    accessKeyId: config.accessKeyId,
    secretAccessKey: config.secretAccessKey,
    region: config.region || 'us-east-1'
  });

  const params = {
    Bucket: config.bucket,
    Key: s3Key
  };

  const file = require('fs').createWriteStream(localPath);
  await s3.getObject(params).createReadStream().pipe(file);
}

/**
 * Upload para Azure Blob Storage
 */
async function uploadToAzureBlob(
  filePath: string,
  options: CloudUploadOptions,
  config: any
): Promise<string> {
  const { BlobServiceClient } = require('@azure/storage-blob');
  
  const blobServiceClient = BlobServiceClient.fromConnectionString(
    config.connectionString
  );
  
  const containerClient = blobServiceClient.getContainerClient(
    config.container || 'backups'
  );
  
  const blobKey = generateS3Key(options);
  const blockBlobClient = containerClient.getBlockBlobClient(blobKey);
  
  await blockBlobClient.uploadFile(filePath, {
    metadata: {
      backupId: options.backupId,
      databaseId: options.databaseId,
      type: options.type,
      ...options.metadata
    }
  });
  
  return blobKey;
}

/**
 * Download do Azure Blob Storage
 */
async function downloadFromAzureBlob(
  blobKey: string,
  localPath: string,
  config: any
): Promise<void> {
  const { BlobServiceClient } = require('@azure/storage-blob');
  
  const blobServiceClient = BlobServiceClient.fromConnectionString(
    config.connectionString
  );
  
  const containerClient = blobServiceClient.getContainerClient(
    config.container || 'backups'
  );
  
  const blockBlobClient = containerClient.getBlockBlobClient(blobKey);
  
  const file = require('fs').createWriteStream(localPath);
  await blockBlobClient.downloadToBuffer().then(buffer => {
    file.write(buffer);
    file.end();
  });
}

/**
 * Upload para Google Cloud Storage
 */
async function uploadToGCPStorage(
  filePath: string,
  options: CloudUploadOptions,
  config: any
): Promise<string> {
  const { Storage } = require('@google-cloud/storage');
  
  const storage = new Storage({
    projectId: config.projectId,
    keyFilename: config.keyFile
  });
  
  const bucket = storage.bucket(config.bucket);
  const gcsKey = generateS3Key(options);
  
  await bucket.upload(filePath, {
    destination: gcsKey,
    metadata: {
      metadata: {
        backupId: options.backupId,
        databaseId: options.databaseId,
        type: options.type,
        ...options.metadata
      }
    }
  });
  
  return gcsKey;
}

/**
 * Download do Google Cloud Storage
 */
async function downloadFromGCPStorage(
  gcsKey: string,
  localPath: string,
  config: any
): Promise<void> {
  const { Storage } = require('@google-cloud/storage');
  
  const storage = new Storage({
    projectId: config.projectId,
    keyFilename: config.keyFile
  });
  
  const bucket = storage.bucket(config.bucket);
  const file = bucket.file(gcsKey);
  
  await file.download({ destination: localPath });
}

/**
 * Upload para FTP
 */
async function uploadToFTP(
  filePath: string,
  options: CloudUploadOptions,
  config: any
): Promise<string> {
  const Client = require('ftp');
  
  return new Promise((resolve, reject) => {
    const client = new Client();
    const ftpKey = generateS3Key(options);
    
    client.on('ready', () => {
      client.put(filePath, ftpKey, (err: any) => {
        if (err) reject(err);
        else {
          client.end();
          resolve(ftpKey);
        }
      });
    });
    
    client.on('error', reject);
    
    client.connect({
      host: config.host,
      port: config.port || 21,
      user: config.username,
      password: config.password
    });
  });
}

/**
 * Download do FTP
 */
async function downloadFromFTP(
  ftpKey: string,
  localPath: string,
  config: any
): Promise<void> {
  const Client = require('ftp');
  
  return new Promise((resolve, reject) => {
    const client = new Client();
    
    client.on('ready', () => {
      client.get(ftpKey, (err: any, stream: any) => {
        if (err) reject(err);
        else {
          const file = require('fs').createWriteStream(localPath);
          stream.pipe(file);
          file.on('finish', () => {
            client.end();
            resolve();
          });
        }
      });
    });
    
    client.on('error', reject);
    
    client.connect({
      host: config.host,
      port: config.port || 21,
      user: config.username,
      password: config.password
    });
  });
}

/**
 * Upload para SFTP
 */
async function uploadToSFTP(
  filePath: string,
  options: CloudUploadOptions,
  config: any
): Promise<string> {
  const Client = require('ssh2-sftp-client');
  const sftp = new Client();
  
  const sftpKey = generateS3Key(options);
  
  try {
    await sftp.connect({
      host: config.host,
      port: config.port || 22,
      username: config.username,
      password: config.password,
      privateKey: config.privateKey
    });
    
    await sftp.put(filePath, sftpKey);
    await sftp.end();
    
    return sftpKey;
  } catch (error) {
    await sftp.end();
    throw error;
  }
}

/**
 * Download do SFTP
 */
async function downloadFromSFTP(
  sftpKey: string,
  localPath: string,
  config: any
): Promise<void> {
  const Client = require('ssh2-sftp-client');
  const sftp = new Client();
  
  try {
    await sftp.connect({
      host: config.host,
      port: config.port || 22,
      username: config.username,
      password: config.password,
      privateKey: config.privateKey
    });
    
    await sftp.get(sftpKey, localPath);
    await sftp.end();
  } catch (error) {
    await sftp.end();
    throw error;
  }
}

/**
 * Upload para armazenamento local
 */
async function uploadToLocal(
  filePath: string,
  options: CloudUploadOptions,
  config: any
): Promise<string> {
  const fs = require('fs').promises;
  const path = require('path');
  
  const localKey = generateS3Key(options);
  const destinationPath = path.join(config.path || '/var/backups', localKey);
  
  // Cria diretório se não existir
  await fs.mkdir(path.dirname(destinationPath), { recursive: true });
  
  // Copia arquivo
  await fs.copyFile(filePath, destinationPath);
  
  return localKey;
}

/**
 * Download do armazenamento local
 */
async function downloadFromLocal(
  localKey: string,
  localPath: string,
  config: any
): Promise<void> {
  const fs = require('fs').promises;
  const path = require('path');
  
  const sourcePath = path.join(config.path || '/var/backups', localKey);
  
  await fs.copyFile(sourcePath, localPath);
}

/**
 * Gera chave única para armazenamento
 */
function generateS3Key(options: CloudUploadOptions): string {
  const date = new Date().toISOString().split('T')[0]; // YYYY-MM-DD
  const timestamp = new Date().getTime();
  
  return `backups/${options.databaseId}/${date}/${options.type}/${options.backupId}-${timestamp}`;
}

/**
 * Busca armazenamento em nuvem padrão
 */
async function getDefaultCloudStorage() {
  return await db.cloudStorage.findFirst({
    where: {
      isActive: true,
      isDefault: true
    }
  });
}

/**
 * Lista arquivos em armazenamento em nuvem
 */
export async function listCloudFiles(
  cloudStorageId?: string,
  prefix?: string
): Promise<Array<{ key: string; size: number; lastModified: Date }>> {
  const cloudStorage = cloudStorageId 
    ? await db.cloudStorage.findUnique({ where: { id: cloudStorageId } })
    : await getDefaultCloudStorage();
    
  if (!cloudStorage) {
    throw new Error('Cloud storage not found');
  }

  const config = JSON.parse(cloudStorage.config) as CloudStorageConfig;
  
  switch (cloudStorage.type) {
    case 'AWS_S3':
      return await listS3Files(config, prefix);
      
    case 'AZURE_BLOB':
      return await listAzureBlobFiles(config, prefix);
      
    case 'GCP_STORAGE':
      return await listGCPStorageFiles(config, prefix);
      
    case 'LOCAL':
      return await listLocalFiles(config, prefix);
      
    default:
      throw new Error(`Listing not supported for: ${cloudStorage.type}`);
  }
}

/**
 * Lista arquivos no S3
 */
async function listS3Files(config: any, prefix?: string) {
  const AWS = require('aws-sdk');
  
  const s3 = new AWS.S3({
    accessKeyId: config.accessKeyId,
    secretAccessKey: config.secretAccessKey,
    region: config.region || 'us-east-1'
  });

  const params = {
    Bucket: config.bucket,
    Prefix: prefix
  };

  const result = await s3.listObjectsV2(params).promise();
  
  return (result.Contents || []).map(obj => ({
    key: obj.Key!,
    size: obj.Size!,
    lastModified: obj.LastModified!
  }));
}

/**
 * Lista arquivos no Azure Blob
 */
async function listAzureBlobFiles(config: any, prefix?: string) {
  const { BlobServiceClient } = require('@azure/storage-blob');
  
  const blobServiceClient = BlobServiceClient.fromConnectionString(
    config.connectionString
  );
  
  const containerClient = blobServiceClient.getContainerClient(
    config.container || 'backups'
  );
  
  const blobs = [];
  for await (const blob of containerClient.listBlobsFlat({ prefix })) {
    blobs.push({
      key: blob.name,
      size: blob.properties.contentLength || 0,
      lastModified: blob.properties.lastModified || new Date()
    });
  }
  
  return blobs;
}

/**
 * Lista arquivos no GCP Storage
 */
async function listGCPStorageFiles(config: any, prefix?: string) {
  const { Storage } = require('@google-cloud/storage');
  
  const storage = new Storage({
    projectId: config.projectId,
    keyFilename: config.keyFile
  });
  
  const bucket = storage.bucket(config.bucket);
  const [files] = await bucket.getFiles({ prefix });
  
  return files.map(file => ({
    key: file.name,
    size: parseInt(file.metadata.size || '0'),
    lastModified: new Date(file.metadata.updated)
  }));
}

/**
 * Lista arquivos locais
 */
async function listLocalFiles(config: any, prefix?: string) {
  const fs = require('fs').promises;
  const path = require('path');
  
  const basePath = config.path || '/var/backups';
  const searchPath = prefix ? path.join(basePath, prefix) : basePath;
  
  try {
    const files = await fs.readdir(searchPath, { withFileTypes: true });
    const result = [];
    
    for (const file of files) {
      if (file.isFile()) {
        const filePath = path.join(searchPath, file.name);
        const stats = await fs.stat(filePath);
        
        result.push({
          key: path.relative(basePath, filePath),
          size: stats.size,
          lastModified: stats.mtime
        });
      }
    }
    
    return result;
  } catch (error) {
    return [];
  }
}

/**
 * Remove arquivo da nuvem
 */
export async function deleteFromCloud(
  s3Key: string,
  cloudStorageId?: string
): Promise<void> {
  const cloudStorage = cloudStorageId 
    ? await db.cloudStorage.findUnique({ where: { id: cloudStorageId } })
    : await getDefaultCloudStorage();
    
  if (!cloudStorage) {
    throw new Error('Cloud storage not found');
  }

  const config = JSON.parse(cloudStorage.config) as CloudStorageConfig;
  
  switch (cloudStorage.type) {
    case 'AWS_S3':
      await deleteFromS3(s3Key, config);
      break;
      
    case 'AZURE_BLOB':
      await deleteFromAzureBlob(s3Key, config);
      break;
      
    case 'GCP_STORAGE':
      await deleteFromGCPStorage(s3Key, config);
      break;
      
    case 'LOCAL':
      await deleteFromLocal(s3Key, config);
      break;
      
    default:
      throw new Error(`Deletion not supported for: ${cloudStorage.type}`);
  }
}

/**
 * Remove arquivo do S3
 */
async function deleteFromS3(s3Key: string, config: any) {
  const AWS = require('aws-sdk');
  
  const s3 = new AWS.S3({
    accessKeyId: config.accessKeyId,
    secretAccessKey: config.secretAccessKey,
    region: config.region || 'us-east-1'
  });

  await s3.deleteObject({
    Bucket: config.bucket,
    Key: s3Key
  }).promise();
}

/**
 * Remove arquivo do Azure Blob
 */
async function deleteFromAzureBlob(blobKey: string, config: any) {
  const { BlobServiceClient } = require('@azure/storage-blob');
  
  const blobServiceClient = BlobServiceClient.fromConnectionString(
    config.connectionString
  );
  
  const containerClient = blobServiceClient.getContainerClient(
    config.container || 'backups'
  );
  
  const blockBlobClient = containerClient.getBlockBlobClient(blobKey);
  await blockBlobClient.delete();
}

/**
 * Remove arquivo do GCP Storage
 */
async function deleteFromGCPStorage(gcsKey: string, config: any) {
  const { Storage } = require('@google-cloud/storage');
  
  const storage = new Storage({
    projectId: config.projectId,
    keyFilename: config.keyFile
  });
  
  const bucket = storage.bucket(config.bucket);
  const file = bucket.file(gcsKey);
  await file.delete();
}

/**
 * Remove arquivo local
 */
async function deleteFromLocal(localKey: string, config: any) {
  const fs = require('fs').promises;
  const path = require('path');
  
  const filePath = path.join(config.path || '/var/backups', localKey);
  await fs.unlink(filePath);
}