/* eslint-disable @typescript-eslint/no-require-imports */
import { db } from '@/lib/db';
import { deleteFromCloud } from '../utils/cloud-storage';

export interface VersioningOptions {
  databaseId: string;
  maxVersions?: number;
  retentionDays?: number;
  maxSizeGB?: number;
  keepDaily?: number;
  keepWeekly?: number;
  keepMonthly?: number;
  keepYearly?: number;
}

export interface RotationResult {
  deletedBackups: string[];
  freedSpace: number;
  totalBackupsBefore: number;
  totalBackupsAfter: number;
}

export class VersioningService {
  /**
   * Cria uma nova versão de backup
   */
  static async createVersion(
    backupId: string,
    options: Partial<VersioningOptions> = {}
  ) {
    const backup = await db.backupOperation.findUnique({
      where: { id: backupId },
      include: { database: true }
    });

    if (!backup) {
      throw new Error('Backup not found');
    }

    // Determina versão baseada em backups anteriores do mesmo tipo
    const lastVersion = await db.backupOperation.findFirst({
      where: {
        databaseId: backup.databaseId,
        type: backup.type,
        isDeleted: false
      },
      orderBy: { version: 'desc' }
    });

    const newVersion = (lastVersion?.version || 0) + 1;

    // Atualiza backup com nova versão
    const updatedBackup = await db.backupOperation.update({
      where: { id: backupId },
      data: {
        version: newVersion,
        metadata: JSON.stringify({
          ...JSON.parse(backup.metadata || '{}'),
          versionedAt: new Date().toISOString(),
          previousVersion: lastVersion?.version
        })
      }
    });

    // Aplica rotação automática se configurado
    await this.applyRotation(backup.databaseId, options);

    return updatedBackup;
  }

  /**
   * Aplica política de rotação automática
   */
  static async applyRotation(
    databaseId: string,
    options: Partial<VersioningOptions> = {}
  ): Promise<RotationResult> {
    const {
      maxVersions = 10,
      retentionDays = 30,
      maxSizeGB = 100,
      keepDaily = 7,
      keepWeekly = 4,
      keepMonthly = 12,
      keepYearly = 3
    } = options;

    // Busca política de retenção configurada ou usa padrão
    const retentionPolicy = await this.getRetentionPolicy(databaseId);
    
    const finalOptions = retentionPolicy ? {
      keepDaily: retentionPolicy.keepDaily,
      keepWeekly: retentionPolicy.keepWeekly,
      keepMonthly: retentionPolicy.keepMonthly,
      keepYearly: retentionPolicy.keepYearly,
      maxSizeGB: retentionPolicy.maxSizeGB || undefined,
      retentionDays: undefined // Usar política baseada em tempo vs contagem
    } : options;

    // Busca todos os backups não deletados
    const allBackups = await db.backupOperation.findMany({
      where: {
        databaseId,
        isDeleted: false
      },
      orderBy: { startTime: 'desc' }
    });

    const result: RotationResult = {
      deletedBackups: [],
      freedSpace: 0,
      totalBackupsBefore: allBackups.length,
      totalBackupsAfter: 0
    };

    // Aplica diferentes estratégias de rotação
    await this.rotateByTime(allBackups, finalOptions, result);
    await this.rotateBySize(allBackups, finalOptions, result);
    await this.rotateByVersion(allBackups, finalOptions, result);

    result.totalBackupsAfter = allBackups.length - result.deletedBackups.length;

    return result;
  }

  /**
   * Rotação baseada em tempo (diário, semanal, mensal, anual)
   */
  private static async rotateByTime(
    backups: any[],
    options: Partial<VersioningOptions>,
    result: RotationResult
  ) {
    const { keepDaily = 7, keepWeekly = 4, keepMonthly = 12, keepYearly = 3 } = options;

    // Agrupa backups por tipo e período
    const groupedBackups = this.groupBackupsByPeriod(backups);

    // Processa cada grupo
    for (const [backupType, periodGroups] of Object.entries(groupedBackups)) {
      // Mantém backups diários
      const daily = periodGroups.daily || [];
      const toKeepDaily = daily.slice(0, keepDaily);
      const toDeleteDaily = daily.slice(keepDaily);

      // Mantém backups semanais
      const weekly = periodGroups.weekly || [];
      const toKeepWeekly = weekly.slice(0, keepWeekly);
      const toDeleteWeekly = weekly.slice(keepWeekly);

      // Mantém backups mensais
      const monthly = periodGroups.monthly || [];
      const toKeepMonthly = monthly.slice(0, keepMonthly);
      const toDeleteMonthly = monthly.slice(keepMonthly);

      // Mantém backups anuais
      const yearly = periodGroups.yearly || [];
      const toKeepYearly = yearly.slice(0, keepYearly);
      const toDeleteYearly = yearly.slice(keepYearly);

      // Deleta backups excedentes
      const toDelete = [
        ...toDeleteDaily,
        ...toDeleteWeekly,
        ...toDeleteMonthly,
        ...toDeleteYearly
      ];

      for (const backup of toDelete) {
        await this.deleteBackup(backup.id, result);
      }
    }
  }

  /**
   * Rotação baseada em tamanho total
   */
  private static async rotateBySize(
    backups: any[],
    options: Partial<VersioningOptions>,
    result: RotationResult
  ) {
    const maxSizeGB = options.maxSizeGB;
    if (!maxSizeGB) return;

    const maxSizeBytes = maxSizeGB * 1024 * 1024 * 1024;
    let totalSize = backups.reduce((sum, b) => sum + (b.sizeBytes || 0), 0);

    if (totalSize <= maxSizeBytes) return;

    // Ordena por data (mais antigos primeiro) e remove até atingir o limite
    const sortedBackups = [...backups].sort((a, b) => 
      new Date(a.startTime).getTime() - new Date(b.startTime).getTime()
    );

    for (const backup of sortedBackups) {
      if (totalSize <= maxSizeBytes) break;
      
      await this.deleteBackup(backup.id, result);
      totalSize -= (backup.sizeBytes || 0);
    }
  }

  /**
   * Rotação baseada em número máximo de versões
   */
  private static async rotateByVersion(
    backups: any[],
    options: Partial<VersioningOptions>,
    result: RotationResult
  ) {
    const maxVersions = options.maxVersions;
    if (!maxVersions) return;

    // Agrupa por tipo e mantém apenas as versões mais recentes
    const groupedByType = backups.reduce((groups, backup) => {
      if (!groups[backup.type]) {
        groups[backup.type] = [];
      }
      groups[backup.type].push(backup);
      return groups;
    }, {} as Record<string, any[]>);

    for (const [backupType, typeBackups] of Object.entries(groupedByType)) {
      if (typeBackups.length <= maxVersions) continue;

      // Ordena por versão (mais antigos primeiro)
      const sortedByVersion = typeBackups.sort((a, b) => a.version - b.version);
      const toDelete = sortedByVersion.slice(0, typeBackups.length - maxVersions);

      for (const backup of toDelete) {
        await this.deleteBackup(backup.id, result);
      }
    }
  }

  /**
   * Agrupa backups por período de tempo
   */
  private static groupBackupsByPeriod(backups: any[]) {
    const groups: Record<string, any> = {};

    for (const backup of backups) {
      const date = new Date(backup.startTime);
      const backupType = backup.type;

      if (!groups[backupType]) {
        groups[backupType] = {
          daily: [],
          weekly: [],
          monthly: [],
          yearly: []
        };
      }

      // Determina em qual período o backup se encaixa
      const now = new Date();
      const daysDiff = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
      
      if (daysDiff <= 7) {
        groups[backupType].daily.push(backup);
      } else if (daysDiff <= 30) {
        groups[backupType].weekly.push(backup);
      } else if (daysDiff <= 365) {
        groups[backupType].monthly.push(backup);
      } else {
        groups[backupType].yearly.push(backup);
      }
    }

    return groups;
  }

  /**
   * Deleta um backup (soft delete)
   */
  private static async deleteBackup(backupId: string, result: RotationResult) {
    const backup = await db.backupOperation.findUnique({
      where: { id: backupId }
    });

    if (!backup || backup.isDeleted) return;

    // Soft delete no banco
    await db.backupOperation.update({
      where: { id: backupId },
      data: {
        isDeleted: true,
        deletedAt: new Date()
      }
    });

    // Remove da nuvem se existir
    if (backup.s3Key) {
      try {
        await deleteFromCloud(backup.s3Key);
      } catch (error) {
        console.error(`Failed to delete from cloud: ${error}`);
      }
    }

    // Remove arquivo local se existir
    if (backup.filePath) {
      try {
        const fs = require('fs').promises;
        await fs.unlink(backup.filePath);
      } catch (error) {
        console.error(`Failed to delete local file: ${error}`);
      }
    }

    result.deletedBackups.push(backupId);
    result.freedSpace += backup.sizeBytes || 0;
  }

  /**
   * Busca política de retenção configurada
   */
  private static async getRetentionPolicy(databaseId: string) {
    // Busca política global ou específica do banco
    return await db.retentionPolicy.findFirst({
      where: { isActive: true },
      orderBy: { createdAt: 'desc' }
    });
  }

  /**
   * Lista versões de um backup
   */
  static async listVersions(databaseId: string, backupType?: string) {
    const where: any = {
      databaseId,
      isDeleted: false
    };

    if (backupType) {
      where.type = backupType;
    }

    return await db.backupOperation.findMany({
      where,
      include: {
        database: true,
        user: {
          select: { id: true, name: true, email: true }
        }
      },
      orderBy: [
        { type: 'asc' },
        { version: 'desc' }
      ]
    });
  }

  /**
   * Restaura uma versão específica
   */
  static async restoreVersion(backupId: string) {
    const backup = await db.backupOperation.findUnique({
      where: { id: backupId }
    });

    if (!backup) {
      throw new Error('Backup not found');
    }

    if (backup.isDeleted) {
      // Restaura backup deletado
      await db.backupOperation.update({
        where: { id: backupId },
        data: {
          isDeleted: false,
          deletedAt: null
        }
      });
    }

    return backup;
  }

  /**
   * Obtém estatísticas de versionamento
   */
  static async getVersioningStats(databaseId: string) {
    const backups = await db.backupOperation.findMany({
      where: { databaseId }
    });

    const total = backups.length;
    const active = backups.filter(b => !b.isDeleted).length;
    const deleted = backups.filter(b => b.isDeleted).length;
    
    // Agrupa por tipo
    const byType = backups.reduce((groups, backup) => {
      if (!groups[backup.type]) {
        groups[backup.type] = { total: 0, active: 0, deleted: 0 };
      }
      groups[backup.type].total++;
      if (backup.isDeleted) {
        groups[backup.type].deleted++;
      } else {
        groups[backup.type].active++;
      }
      return groups;
    }, {} as Record<string, any>);

    // Calcula espaço total
    const totalSpace = backups.reduce((sum, b) => sum + (b.sizeBytes || 0), 0);
    const activeSpace = backups
      .filter(b => !b.isDeleted)
      .reduce((sum, b) => sum + (b.sizeBytes || 0), 0);

    return {
      total,
      active,
      deleted,
      totalSpace,
      activeSpace,
      deletedSpace: totalSpace - activeSpace,
      byType
    };
  }

  /**
   * Configura política de retenção
   */
  static async configureRetentionPolicy(
    name: string,
    options: Omit<VersioningOptions, 'databaseId'>
  ) {
    return await db.retentionPolicy.create({
      data: {
        name,
        keepDaily: options.keepDaily || 7,
        keepWeekly: options.keepWeekly || 4,
        keepMonthly: options.keepMonthly || 12,
        keepYearly: options.keepYearly || 3,
        maxSizeGB: options.maxSizeGB,
        maxTotalSizeGB: options.maxSizeGB,
        isActive: true
      }
    });
  }

  /**
   * Limpeza programada de backups antigos
   */
  static async scheduledCleanup() {
    const databases = await db.database.findMany({
      where: { isActive: true }
    });

    const results = [];

    for (const database of databases) {
      try {
        const result = await this.applyRotation(database.id);
        results.push({
          databaseId: database.id,
          databaseName: database.name,
          ...result
        });
      } catch (error) {
        console.error(`Cleanup failed for database ${database.id}: ${error}`);
        results.push({
          databaseId: database.id,
          databaseName: database.name,
          error: error instanceof Error ? error.message : 'Unknown error'
        });
      }
    }

    return results;
  }
}