"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, Clock, Database, Cloud, AlertCircle, Play, Settings, Activity, Upload, Image as ImageIcon, Trash2, Download, Shield, BarChart3, Calendar, Lock, RefreshCw, HardDrive, Users, Bell, Zap, History, Filter, Search, MoreVertical } from "lucide-react";

interface BackupStatus {
  id: string;
  type: "full" | "incremental" | "differential" | "wal";
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  startTime: string;
  endTime?: string;
  size?: number;
  compressedSize?: number;
  label?: string;
  version?: number;
  compressionType?: "NONE" | "GZIP" | "ZSTD" | "LZ4";
  isEncrypted?: boolean;
  isDeleted?: boolean;
  deletedAt?: string;
  errorMessage?: string;
  databaseName?: string;
}

interface SystemStats {
  totalBackups: number;
  lastBackup: string;
  storageUsed: string;
  successRate: number;
}

export default function Home() {
  const [backups, setBackups] = useState<BackupStatus[]>([]);
  const [stats, setStats] = useState<SystemStats>({
    totalBackups: 0,
    lastBackup: "N/A",
    storageUsed: "0 MB",
    successRate: 0
  });
  const [isRunning, setIsRunning] = useState(false);
  const [currentOperation, setCurrentOperation] = useState<string>("");
  const [customLogo, setCustomLogo] = useState<string | null>(null);
  const [selectedBackupType, setSelectedBackupType] = useState<string>("full");
  const [selectedCompression, setSelectedCompression] = useState<string>("GZIP");
  const [encryptionEnabled, setEncryptionEnabled] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");
  const [showDeleted, setShowDeleted] = useState<boolean>(false);

  // Simulação de dados - em produção, viria da API
  useEffect(() => {
    const mockBackups: BackupStatus[] = [
      {
        id: "backup-001",
        type: "full",
        status: "completed",
        startTime: "2024-01-15T02:00:00Z",
        endTime: "2024-01-15T02:15:00Z",
        size: 1073741824,
        compressedSize: 536870912,
        label: "weekly-full",
        version: 1,
        compressionType: "GZIP",
        isEncrypted: true,
        databaseName: "production"
      },
      {
        id: "backup-002",
        type: "differential",
        status: "completed",
        startTime: "2024-01-15T08:00:00Z",
        endTime: "2024-01-15T08:05:00Z",
        size: 268435456,
        compressedSize: 134217728,
        label: "daily-differential",
        version: 1,
        compressionType: "ZSTD",
        isEncrypted: true,
        databaseName: "production"
      },
      {
        id: "backup-003",
        type: "incremental",
        status: "running",
        startTime: "2024-01-15T14:00:00Z",
        label: "wal-archive",
        version: 1,
        compressionType: "LZ4",
        isEncrypted: false,
        databaseName: "production"
      },
      {
        id: "backup-004",
        type: "full",
        status: "completed",
        startTime: "2024-01-14T02:00:00Z",
        endTime: "2024-01-14T02:18:00Z",
        size: 1073741824,
        compressedSize: 536870912,
        label: "weekly-full",
        version: 2,
        compressionType: "GZIP",
        isEncrypted: true,
        isDeleted: true,
        deletedAt: "2024-01-15T01:00:00Z",
        databaseName: "production"
      }
    ];

    const mockStats: SystemStats = {
      totalBackups: 156,
      lastBackup: "2024-01-15T14:00:00Z",
      storageUsed: "15.2 GB",
      successRate: 98.7
    };

    setBackups(mockBackups);
    setStats(mockStats);
  }, []);

  const handleBackup = async (type: "full" | "incremental" | "differential" | "wal") => {
    setIsRunning(true);
    const compressionText = selectedCompression === "NONE" ? "sem compressão" : 
                           selectedCompression === "GZIP" ? "compressão GZIP" :
                           selectedCompression === "ZSTD" ? "compressão ZSTD" : "compressão LZ4";
    setCurrentOperation(`Criando backup ${type} com ${compressionText}${encryptionEnabled ? ' e criptografia' : ''}...`);
    
    // Simulação de backup
    setTimeout(() => {
      const baseSize = type === "full" ? 1073741824 : type === "differential" ? 268435456 : 1048576;
      const compressionRatio = selectedCompression === "NONE" ? 1 : selectedCompression === "GZIP" ? 0.5 : selectedCompression === "ZSTD" ? 0.4 : 0.6;
      
      const newBackup: BackupStatus = {
        id: `backup-${Date.now()}`,
        type,
        status: "completed",
        startTime: new Date().toISOString(),
        endTime: new Date().toISOString(),
        size: baseSize,
        compressedSize: Math.floor(baseSize * compressionRatio),
        label: `${type}-backup-${Date.now()}`,
        version: 1,
        compressionType: selectedCompression as any,
        isEncrypted: encryptionEnabled,
        databaseName: "production"
      };
      
      setBackups(prev => [newBackup, ...prev]);
      setIsRunning(false);
      setCurrentOperation("");
    }, 3000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "running":
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case "failed":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case "cancelled":
        return <AlertCircle className="h-4 w-4 text-orange-500" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants = {
      completed: "default",
      running: "secondary",
      failed: "destructive",
      cancelled: "outline",
      pending: "secondary"
    } as const;

    const statusText = {
      completed: "Concluído",
      running: "Executando",
      failed: "Falhou",
      cancelled: "Cancelado",
      pending: "Pendente"
    };

    return (
      <Badge variant={variants[status as keyof typeof variants] || "default"}>
        {statusText[status as keyof typeof statusText] || status}
      </Badge>
    );
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const handleLogoUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setCustomLogo(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleRemoveLogo = () => {
    setCustomLogo(null);
  };

  const handleDeleteBackup = async (backupId: string) => {
    if (confirm('Tem certeza que deseja excluir este backup? Esta ação pode ser desfeita.')) {
      setBackups(prev => prev.map(backup => 
        backup.id === backupId 
          ? { ...backup, isDeleted: true, deletedAt: new Date().toISOString() }
          : backup
      ));
    }
  };

  const handleRestoreBackup = async (backupId: string) => {
    setBackups(prev => prev.map(backup => 
      backup.id === backupId 
        ? { ...backup, isDeleted: false, deletedAt: undefined }
        : backup
    ));
  };

  const filteredBackups = backups.filter(backup => {
    const matchesSearch = backup.label?.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          backup.databaseName?.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === "all" || backup.status === filterStatus;
    const matchesType = filterType === "all" || backup.type === filterType;
    const matchesDeleted = showDeleted || !backup.isDeleted;
    
    return matchesSearch && matchesStatus && matchesType && matchesDeleted;
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-4 py-8">
          <div className="flex justify-center">
            {customLogo ? (
              <div className="relative w-16 h-16 md:w-20 md:h-20">
                <img
                  src={customLogo}
                  alt="Custom Logo"
                  className="w-full h-full object-contain rounded-2xl shadow-lg"
                />
              </div>
            ) : (
              <div className="w-16 h-16 md:w-20 md:h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                <Database className="w-8 h-8 md:w-10 md:h-10 text-white" />
              </div>
            )}
          </div>
          <div>
            <h1 className="text-4xl font-bold text-slate-900">BackupCTL</h1>
            <p className="text-lg text-slate-600 mt-2">
              Sistema de Backup Automatizado PostgreSQL
            </p>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total de Backups</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.totalBackups}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Último Backup</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-sm font-medium">{formatDate(stats.lastBackup)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Armazenamento Usado</CardTitle>
              <Cloud className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.storageUsed}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Taxa de Sucesso</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.successRate}%</div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <Tabs defaultValue="backups" className="space-y-4">
          <TabsList className="grid w-full grid-cols-7">
            <TabsTrigger value="backups">Backups</TabsTrigger>
            <TabsTrigger value="operations">Operações</TabsTrigger>
            <TabsTrigger value="restore">Restauração</TabsTrigger>
            <TabsTrigger value="schedule">Agendamento</TabsTrigger>
            <TabsTrigger value="analytics">Análises</TabsTrigger>
            <TabsTrigger value="branding">Marca</TabsTrigger>
            <TabsTrigger value="settings">Configurações</TabsTrigger>
          </TabsList>

          <TabsContent value="backups" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Gerenciamento de Backups</CardTitle>
                    <CardDescription>
                      Histórico completo de backups com filtragem avançada e gerenciamento
                    </CardDescription>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant={showDeleted ? "default" : "outline"}
                      size="sm"
                      onClick={() => setShowDeleted(!showDeleted)}
                    >
                      <Trash2 className="h-4 w-4 mr-2" />
                      {showDeleted ? "Ocultar Excluídos" : "Mostrar Excluídos"}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {/* Filters */}
                <div className="flex flex-col md:flex-row gap-4 mb-6">
                  <div className="flex-1">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <input
                        type="text"
                        placeholder="Pesquisar backups..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                      />
                    </div>
                  </div>
                  <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">Todos os Status</option>
                    <option value="completed">Concluídos</option>
                    <option value="running">Executando</option>
                    <option value="failed">Falharam</option>
                    <option value="pending">Pendentes</option>
                    <option value="cancelled">Cancelados</option>
                  </select>
                  <select
                    value={filterType}
                    onChange={(e) => setFilterType(e.target.value)}
                    className="px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="all">Todos os Tipos</option>
                    <option value="full">Completo</option>
                    <option value="differential">Diferencial</option>
                    <option value="incremental">Incremental</option>
                    <option value="wal">WAL</option>
                  </select>
                </div>

                {/* Backups List */}
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {filteredBackups.map((backup) => (
                    <div
                      key={backup.id}
                      className={`flex items-center justify-between p-4 border rounded-lg ${
                        backup.isDeleted ? 'bg-red-50 border-red-200' : 'bg-white'
                      }`}
                    >
                      <div className="flex items-center space-x-4">
                        {getStatusIcon(backup.status)}
                        <div>
                          <div className="font-medium flex items-center space-x-2">
                            <span>{backup.label}</span>
                            {backup.isDeleted && (
                              <Badge variant="destructive" className="text-xs">
                                Excluído
                              </Badge>
                            )}
                            {backup.version && backup.version > 1 && (
                              <Badge variant="secondary" className="text-xs">
                                v{backup.version}
                              </Badge>
                            )}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {backup.databaseName} • {formatDate(backup.startTime)}
                          </div>
                          <div className="flex items-center space-x-4 mt-1">
                            <Badge variant="outline">{backup.type}</Badge>
                            {backup.compressionType && (
                              <Badge variant="secondary" className="text-xs">
                                {backup.compressionType}
                              </Badge>
                            )}
                            {backup.isEncrypted && (
                              <Lock className="h-3 w-3 text-green-500" />
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-4">
                        <div className="text-right">
                          {getStatusBadge(backup.status)}
                          {backup.size && (
                            <div className="text-sm text-muted-foreground mt-1">
                              {formatSize(backup.size)}
                              {backup.compressedSize && (
                                <span className="text-green-600 ml-1">
                                  → {formatSize(backup.compressedSize)}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                        <div className="flex items-center space-x-2">
                          {backup.isDeleted ? (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRestoreBackup(backup.id)}
                            >
                              <RefreshCw className="h-4 w-4" />
                            </Button>
                          ) : (
                            <>
                              <Button size="sm" variant="outline">
                                <Download className="h-4 w-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleDeleteBackup(backup.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="operations" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Operações Avançadas de Backup</CardTitle>
                <CardDescription>
                  Execute operações de backup com opções avançadas de configuração
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {isRunning && (
                  <Alert>
                    <Clock className="h-4 w-4" />
                    <AlertDescription>
                      {currentOperation}
                      <Progress value={66} className="mt-2" />
                    </AlertDescription>
                  </Alert>
                )}
                
                {/* Backup Configuration */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 border rounded-lg bg-muted/50">
                  <div>
                    <label className="text-sm font-medium">Tipo de Backup</label>
                    <select
                      value={selectedBackupType}
                      onChange={(e) => setSelectedBackupType(e.target.value)}
                      className="w-full mt-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="full">Backup Completo</option>
                      <option value="differential">Backup Diferencial</option>
                      <option value="incremental">Backup Incremental</option>
                      <option value="wal">Arquivo WAL</option>
                    </select>
                  </div>
                  
                  <div>
                    <label className="text-sm font-medium">Compressão</label>
                    <select
                      value={selectedCompression}
                      onChange={(e) => setSelectedCompression(e.target.value)}
                      className="w-full mt-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="NONE">Sem Compressão</option>
                      <option value="GZIP">GZIP (Padrão)</option>
                      <option value="ZSTD">ZSTD (Alta Razão)</option>
                      <option value="LZ4">LZ4 (Rápido)</option>
                    </select>
                  </div>
                  
                  <div className="flex items-center space-x-2 pt-6">
                    <input
                      type="checkbox"
                      id="encryption"
                      checked={encryptionEnabled}
                      onChange={(e) => setEncryptionEnabled(e.target.checked)}
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="encryption" className="text-sm font-medium flex items-center">
                      <Lock className="h-4 w-4 mr-1" />
                      Criptografia Ponta-a-Ponta
                    </label>
                  </div>
                </div>

                {/* Backup Buttons */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Button
                    onClick={() => handleBackup("full")}
                    disabled={isRunning}
                    className="w-full"
                    size="lg"
                  >
                    <Database className="mr-2 h-4 w-4" />
                    Backup Completo
                  </Button>
                  <Button
                    onClick={() => handleBackup("differential")}
                    disabled={isRunning}
                    variant="outline"
                    className="w-full"
                    size="lg"
                  >
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Diferencial
                  </Button>
                  <Button
                    onClick={() => handleBackup("incremental")}
                    disabled={isRunning}
                    variant="outline"
                    className="w-full"
                    size="lg"
                  >
                    <Zap className="mr-2 h-4 w-4" />
                    Incremental
                  </Button>
                  <Button
                    onClick={() => handleBackup("wal")}
                    disabled={isRunning}
                    variant="outline"
                    className="w-full"
                    size="lg"
                  >
                    <History className="mr-2 h-4 w-4" />
                    Arquivo WAL
                  </Button>
                </div>

                {/* Operation Info */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2 flex items-center">
                      <Shield className="h-4 w-4 mr-2 text-green-500" />
                      Tipos de Backup
                    </h4>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      <div><strong>Completo:</strong> Backup completo do banco de dados</div>
                      <div><strong>Diferencial:</strong> Mudanças desde o último backup completo</div>
                      <div><strong>Incremental:</strong> Mudanças desde o último backup</div>
                      <div><strong>WAL:</strong> Arquivo de log de transações</div>
                    </div>
                  </div>
                  
                  <div className="p-4 border rounded-lg">
                    <h4 className="font-medium mb-2 flex items-center">
                      <BarChart3 className="h-4 w-4 mr-2 text-blue-500" />
                      Opções de Compressão
                    </h4>
                    <div className="space-y-2 text-sm text-muted-foreground">
                      <div><strong>GZIP:</strong> Compressão padrão (50% de razão)</div>
                      <div><strong>ZSTD:</strong> Alta compressão (40% de razão)</div>
                      <div><strong>LZ4:</strong> Compressão rápida (60% de razão)</div>
                      <div><strong>Nenhuma:</strong> Sem compressão (100% do tamanho)</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="restore" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Operações de Restauração</CardTitle>
                <CardDescription>
                  Restaure bancos de dados com opções seletivas e recuperação pontual
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Restore Type Selection */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <Card className="cursor-pointer hover:shadow-md transition-shadow">
                    <CardContent className="p-4 text-center">
                      <Database className="h-8 w-8 mx-auto mb-2 text-blue-500" />
                      <h4 className="font-medium">Restauração Completa</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        Restauração completa do banco de dados
                      </p>
                    </CardContent>
                  </Card>
                  
                  <Card className="cursor-pointer hover:shadow-md transition-shadow">
                    <CardContent className="p-4 text-center">
                      <Filter className="h-8 w-8 mx-auto mb-2 text-green-500" />
                      <h4 className="font-medium">Seletivo</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        Restaurar tabelas/schemas
                      </p>
                    </CardContent>
                  </Card>
                  
                  <Card className="cursor-pointer hover:shadow-md transition-shadow">
                    <CardContent className="p-4 text-center">
                      <Calendar className="h-8 w-8 mx-auto mb-2 text-orange-500" />
                      <h4 className="font-medium">Pontual</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        Restaurar para momento específico
                      </p>
                    </CardContent>
                  </Card>
                  
                  <Card className="cursor-pointer hover:shadow-md transition-shadow">
                    <CardContent className="p-4 text-center">
                      <RefreshCw className="h-8 w-8 mx-auto mb-2 text-purple-500" />
                      <h4 className="font-medium">Teste de Restauração</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        Verificar integridade do backup
                      </p>
                    </CardContent>
                  </Card>
                </div>

                {/* Restore Configuration */}
                <div className="p-4 border rounded-lg bg-muted/50">
                  <h4 className="font-medium mb-4">Configuração de Restauração</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm font-medium">Selecionar Backup</label>
                      <select className="w-full mt-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option>Escolha um backup para restaurar...</option>
                        {filteredBackups.filter(b => b.status === 'completed' && !b.isDeleted).map(backup => (
                          <option key={backup.id} value={backup.id}>
                            {backup.label} - {formatDate(backup.startTime)}
                          </option>
                        ))}
                      </select>
                    </div>
                    
                    <div>
                      <label className="text-sm font-medium">Banco de Dados de Destino</label>
                      <select className="w-full mt-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <option>production</option>
                        <option>staging</option>
                        <option>test</option>
                        <option>development</option>
                      </select>
                    </div>
                  </div>
                  
                  <div className="mt-4">
                    <label className="text-sm font-medium">Tabelas/Schemas de Destino (Opcional)</label>
                    <input
                      type="text"
                      placeholder="ex: usuarios, pedidos, schema publico"
                      className="w-full mt-1 px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  
                  <div className="mt-4 flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="dryRun"
                      className="rounded border-gray-300"
                    />
                    <label htmlFor="dryRun" className="text-sm font-medium">
                      Simulação (Visualizar alterações apenas)
                    </label>
                  </div>
                </div>

                {/* Restore Actions */}
                <div className="flex items-center justify-between">
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Operações de restauração sobrescreverão dados existentes. Certifique-se de ter um backup atual antes de prosseguir.
                    </AlertDescription>
                  </Alert>
                  
                  <div className="flex space-x-2">
                    <Button variant="outline">
                      Visualizar Restauração
                    </Button>
                    <Button>
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Iniciar Restauração
                    </Button>
                  </div>
                </div>

                {/* Recent Restores */}
                <div>
                  <h4 className="font-medium mb-4">Operações de Restauração Recentes</h4>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center space-x-3">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <div>
                          <div className="font-medium">Teste de Restauração - backup-001</div>
                          <div className="text-sm text-muted-foreground">
                            production → test • 2 horas atrás
                          </div>
                        </div>
                      </div>
                      <Badge variant="default">Concluído</Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="analytics" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Análises e Monitoramento de Backup</CardTitle>
                <CardDescription>
                  Métricas em tempo real, tendências e insights de performance do sistema
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Key Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Taxa de Sucesso</p>
                          <p className="text-2xl font-bold text-green-600">98,7%</p>
                        </div>
                        <CheckCircle className="h-8 w-8 text-green-500" />
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Duração Média</p>
                          <p className="text-2xl font-bold">12m</p>
                        </div>
                        <Clock className="h-8 w-8 text-blue-500" />
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Economia de Storage</p>
                          <p className="text-2xl font-bold text-orange-600">45%</p>
                        </div>
                        <HardDrive className="h-8 w-8 text-orange-500" />
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Alertas Ativos</p>
                          <p className="text-2xl font-bold text-red-600">2</p>
                        </div>
                        <Bell className="h-8 w-8 text-red-500" />
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Charts Section */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Tendências de Backup (7 dias)</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64 flex items-center justify-center bg-muted/20 rounded-lg">
                        <div className="text-center">
                          <BarChart3 className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                          <p className="text-muted-foreground">Visualização de gráfico aqui</p>
                          <p className="text-sm text-muted-foreground">Volumes diários de backup e taxas de sucesso</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                  
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Uso de Armazenamento</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="h-64 flex items-center justify-center bg-muted/20 rounded-lg">
                        <div className="text-center">
                          <HardDrive className="h-12 w-12 mx-auto mb-2 text-muted-foreground" />
                          <p className="text-muted-foreground">Gráfico de breakdown de storage</p>
                          <p className="text-sm text-muted-foreground">Razões de compressão por tipo de backup</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Performance Metrics */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Métricas de Performance</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                          <span className="font-medium">Performance de Backup Completo</span>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">15,2 GB/min</div>
                          <div className="text-sm text-muted-foreground">↑ 12% na última semana</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
                          <span className="font-medium">Eficiência de Compressão</span>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">55% média</div>
                          <div className="text-sm text-muted-foreground">ZSTD com melhor desempenho</div>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center space-x-3">
                          <div className="w-3 h-3 bg-orange-500 rounded-full"></div>
                          <span className="font-medium">Velocidade de Restauração</span>
                        </div>
                        <div className="text-right">
                          <div className="font-medium">8,5 GB/min</div>
                          <div className="text-sm text-muted-foreground">↑ 5% na última semana</div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Recent Alerts */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Alertas Recentes</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between p-3 border-l-4 border-red-500 bg-red-50 rounded">
                        <div>
                          <div className="font-medium text-red-800">Falha no Backup</div>
                          <div className="text-sm text-red-600">Backup diferencial backup-003 falhou ao completar</div>
                          <div className="text-xs text-red-500">2 horas atrás</div>
                        </div>
                        <Button size="sm" variant="outline">Ver Detalhes</Button>
                      </div>
                      
                      <div className="flex items-center justify-between p-3 border-l-4 border-yellow-500 bg-yellow-50 rounded">
                        <div>
                          <div className="font-medium text-yellow-800">Alerta de Storage</div>
                          <div className="text-sm text-yellow-600">Uso de armazenamento em 85% da capacidade</div>
                          <div className="text-xs text-yellow-500">5 horas atrás</div>
                        </div>
                        <Button size="sm" variant="outline">Gerenciar</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="schedule" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Tarefas Agendadas</CardTitle>
                <CardDescription>
                  Configurações de agendamento automático
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="p-4 border rounded-lg">
                      <div className="font-medium">Backup Completo</div>
                      <div className="text-sm text-muted-foreground">Domingo 02:00</div>
                      <Badge variant="secondary" className="mt-2">Ativo</Badge>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <div className="font-medium">Backup Incremental</div>
                      <div className="text-sm text-muted-foreground">A cada 6 horas</div>
                      <Badge variant="secondary" className="mt-2">Ativo</Badge>
                    </div>
                    <div className="p-4 border rounded-lg">
                      <div className="font-medium">Limpar Backups Antigos</div>
                      <div className="text-sm text-muted-foreground">Domingo 03:00</div>
                      <Badge variant="secondary" className="mt-2">Ativo</Badge>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="branding" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Logo Personalizada</CardTitle>
                <CardDescription>
                  Personalize a aparência do sistema com sua própria logo
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Upload Section */}
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Upload da Logo</label>
                      <p className="text-xs text-muted-foreground mt-1">
                        Formatos: PNG, JPG, SVG. Tamanho recomendado: 200x200px
                      </p>
                    </div>
                    
                    <div className="border-2 border-dashed border-muted-foreground/25 rounded-lg p-6 text-center">
                      <input
                        type="file"
                        id="logo-upload"
                        accept="image/*"
                        onChange={handleLogoUpload}
                        className="hidden"
                      />
                      <label
                        htmlFor="logo-upload"
                        className="cursor-pointer flex flex-col items-center space-y-2"
                      >
                        <Upload className="h-8 w-8 text-muted-foreground" />
                        <span className="text-sm text-muted-foreground">
                          Clique para fazer upload ou arraste a imagem
                        </span>
                        <span className="text-xs text-muted-foreground">
                          PNG, JPG, SVG até 5MB
                        </span>
                      </label>
                    </div>
                  </div>

                  {/* Preview Section */}
                  <div className="space-y-4">
                    <div>
                      <label className="text-sm font-medium">Visualização</label>
                      <p className="text-xs text-muted-foreground mt-1">
                        Como sua logo aparecerá no sistema
                      </p>
                    </div>
                    
                    <div className="border rounded-lg p-6 bg-muted/50">
                      <div className="flex justify-center mb-4">
                        {customLogo ? (
                          <div className="relative w-20 h-20">
                            <img
                              src={customLogo}
                              alt="Logo Preview"
                              className="w-full h-full object-contain rounded-lg shadow-md"
                            />
                          </div>
                        ) : (
                          <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shadow-md">
                            <Database className="w-10 h-10 text-white" />
                          </div>
                        )}
                      </div>
                      
                      <div className="text-center">
                        <h3 className="font-semibold text-lg">BackupCTL</h3>
                        <p className="text-sm text-muted-foreground">
                          Sistema de Backup Automatizado PostgreSQL
                        </p>
                      </div>
                    </div>

                    {customLogo && (
                      <Button
                        onClick={handleRemoveLogo}
                        variant="outline"
                        className="w-full"
                      >
                        <ImageIcon className="mr-2 h-4 w-4" />
                        Remover Logo
                      </Button>
                    )}
                  </div>
                </div>

                {/* Brand Guidelines */}
                <div className="border rounded-lg p-4 bg-muted/30">
                  <h4 className="font-medium mb-2">Diretrizes de Marca</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• Use imagens de alta qualidade para melhor visualização</li>
                    <li>• Logos quadradas funcionam melhor no layout atual</li>
                    <li>• Fundo transparente recomendado para melhor integração</li>
                    <li>• A logo será redimensionada automaticamente para se adequar ao layout</li>
                    <li>• A logo customizada substitui o ícone padrão do sistema</li>
                  </ul>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Configuração do Sistema</CardTitle>
                <CardDescription>
                  Configurações do sistema de backup
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Host PostgreSQL</label>
                      <div className="p-2 border rounded bg-muted">localhost</div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Bucket AWS S3</label>
                      <div className="p-2 border rounded bg-muted">backupctl-bucket</div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Retenção (Completo)</label>
                      <div className="p-2 border rounded bg-muted">30 days</div>
                    </div>
                    <div className="space-y-2">
                      <label className="text-sm font-medium">Criptografia</label>
                      <div className="p-2 border rounded bg-muted">SSE-KMS</div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}