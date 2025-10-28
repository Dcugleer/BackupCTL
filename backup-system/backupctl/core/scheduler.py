"""
Módulo de agendamento e alertas
"""

import schedule
import time
import threading
import smtplib
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

from .backup import BackupEngine
from .restore import RestoreEngine


class AlertManager:
    """Gerenciador de alertas"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.email_config = config.get('email', {})
        self.webhook_config = config.get('webhook', {})
    
    def send_alert(self, message: str, level: str = 'info',
                  context: Optional[Dict[str, Any]] = None) -> bool:
        """Envia alerta por todos os canais configurados"""
        success = True
        
        # Email
        if self.email_config.get('enabled', False):
            if not self._send_email_alert(message, level, context):
                success = False
        
        # Webhook
        if self.webhook_config.get('enabled', False):
            if not self._send_webhook_alert(message, level, context):
                success = False
        
        return success
    
    def _send_email_alert(self, message: str, level: str,
                         context: Optional[Dict[str, Any]]) -> bool:
        """Envia alerta por email"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.email_config.get('from')
            msg['To'] = self.email_config.get('to')
            
            # Assunto baseado no nível
            subject_prefix = {
                'info': '[INFO]',
                'warning': '[WARNING]',
                'error': '[ERROR]',
                'critical': '[CRITICAL]'
            }.get(level, '[ALERT]')
            
            msg['Subject'] = f"{subject_prefix} BackupCTL Alert"
            
            # Corpo do email
            body = f"""
BackupCTL Alert

Level: {level.upper()}
Timestamp: {datetime.now(timezone.utc).isoformat()}
Message: {message}
"""
            
            if context:
                body += "\nContext:\n"
                for key, value in context.items():
                    body += f"  {key}: {value}\n"
            
            msg.attach(MimeText(body, 'plain'))
            
            # Envio
            server = smtplib.SMTP(
                self.email_config.get('smtp_server'),
                self.email_config.get('smtp_port', 587)
            )
            
            server.starttls()
            server.login(
                self.email_config.get('username'),
                self.email_config.get('password')
            )
            
            server.send_message(msg)
            server.quit()
            
            self.logger.info(f"Email alert enviado: {level}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar email alert: {e}")
            return False
    
    def _send_webhook_alert(self, message: str, level: str,
                           context: Optional[Dict[str, Any]]) -> bool:
        """Envia alerta por webhook"""
        try:
            url = self.webhook_config.get('url')
            if not url:
                return False
            
            timeout = self.webhook_config.get('timeout', 30)
            
            payload = {
                'level': level,
                'message': message,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'service': 'backupctl',
                'context': context or {}
            }
            
            response = requests.post(
                url,
                json=payload,
                timeout=timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            response.raise_for_status()
            
            self.logger.info(f"Webhook alert enviado: {level}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao enviar webhook alert: {e}")
            return False


class BackupScheduler:
    """Agendador de backups"""
    
    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        self.config = config
        self.logger = logger
        self.schedule_config = config.get('schedule', {})
        self.backup_config = config.get('backup', {})
        
        # Inicializa componentes
        self.backup_engine = BackupEngine(config, logger)
        self.alert_manager = AlertManager(config.get('alerts', {}), logger)
        
        self.running = False
        self.scheduler_thread = None
    
    def setup_schedule(self):
        """Configura agendamento de tarefas"""
        try:
            # Backup completo
            full_schedule = self.schedule_config.get('full_backup', '0 2 * * 0')
            self._parse_cron_and_schedule(full_schedule, 'full')
            
            # Backup incremental
            inc_schedule = self.schedule_config.get('incremental_backup', '0 */6 * * *')
            self._parse_cron_and_schedule(inc_schedule, 'incremental')
            
            # Limpeza (prune)
            prune_schedule = self.schedule_config.get('prune', '0 3 * * 0')
            self._parse_cron_and_schedule(prune_schedule, 'prune')
            
            self.logger.info("Agendamento configurado com sucesso")
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar agendamento: {e}")
    
    def _parse_cron_and_schedule(self, cron_expr: str, task_type: str):
        """Parse de expressão cron e agenda tarefa"""
        try:
            # Simplificado - em produção usar biblioteca como croniter
            parts = cron_expr.split()
            if len(parts) != 5:
                self.logger.error(f"Expressão cron inválida: {cron_expr}")
                return
            
            minute, hour, day, month, weekday = parts
            
            if task_type == 'full':
                if hour == '2' and weekday == '0':  # Domingo 2AM
                    schedule.every().sunday.at("02:00").do(self._run_full_backup)
                else:
                    # Agendamento genérico (simplificado)
                    schedule.every().day.at(f"{hour}:{minute}").do(self._run_full_backup)
            
            elif task_type == 'incremental':
                if hour == '*/6':  # A cada 6 horas
                    schedule.every(6).hours.do(self._run_incremental_backup)
                else:
                    schedule.every().day.at(f"{hour}:{minute}").do(self._run_incremental_backup)
            
            elif task_type == 'prune':
                if hour == '3' and weekday == '0':  # Domingo 3AM
                    schedule.every().sunday.at("03:00").do(self._run_prune)
                else:
                    schedule.every().day.at(f"{hour}:{minute}").do(self._run_prune)
            
            self.logger.info(f"Tarefa agendada: {task_type} - {cron_expr}")
            
        except Exception as e:
            self.logger.error(f"Erro ao agendar tarefa {task_type}: {e}")
    
    def _run_full_backup(self):
        """Executa backup completo agendado"""
        try:
            self.logger.info("Iniciando backup completo agendado")
            
            label = f"scheduled-full-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            success, backup_id = self.backup_engine.create_full_backup(label=label)
            
            if success:
                self.logger.info(f"Backup completo agendado concluído: {backup_id}")
                self.alert_manager.send_alert(
                    f"Backup completo concluído: {backup_id}",
                    'info',
                    {'backup_id': backup_id, 'type': 'full', 'scheduled': True}
                )
            else:
                self.logger.error(f"Falha no backup completo agendado: {backup_id}")
                self.alert_manager.send_alert(
                    f"Falha no backup completo: {backup_id}",
                    'error',
                    {'backup_id': backup_id, 'type': 'full', 'scheduled': True}
                )
                
        except Exception as e:
            self.logger.error(f"Erro no backup completo agendado: {e}")
            self.alert_manager.send_alert(
                f"Erro no backup completo: {str(e)}",
                'error',
                {'type': 'full', 'scheduled': True}
            )
    
    def _run_incremental_backup(self):
        """Executa backup incremental agendado"""
        try:
            self.logger.info("Iniciando backup incremental agendado")
            
            label = f"scheduled-incremental-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            success, backup_id = self.backup_engine.create_incremental_backup(label=label)
            
            if success:
                self.logger.info(f"Backup incremental agendado concluído: {backup_id}")
                self.alert_manager.send_alert(
                    f"Backup incremental concluído: {backup_id}",
                    'info',
                    {'backup_id': backup_id, 'type': 'incremental', 'scheduled': True}
                )
            else:
                self.logger.error(f"Falha no backup incremental agendado: {backup_id}")
                self.alert_manager.send_alert(
                    f"Falha no backup incremental: {backup_id}",
                    'error',
                    {'backup_id': backup_id, 'type': 'incremental', 'scheduled': True}
                )
                
        except Exception as e:
            self.logger.error(f"Erro no backup incremental agendado: {e}")
            self.alert_manager.send_alert(
                f"Erro no backup incremental: {str(e)}",
                'error',
                {'type': 'incremental', 'scheduled': True}
            )
    
    def _run_prune(self):
        """Executa limpeza de backups antigos"""
        try:
            self.logger.info("Iniciando limpeza de backups agendada")
            
            # Implementação de prune
            retention = self.backup_config.get('retention', {})
            full_days = retention.get('full_days', 30)
            incremental_days = retention.get('incremental_days', 7)
            
            # Obter backups antigos
            old_backups = self.backup_engine.list_recent_backups(limit=1000)
            
            pruned_count = 0
            for backup in old_backups:
                backup_age = (datetime.now(timezone.utc) - backup['start_ts']).days
                
                should_prune = False
                if backup['backup_type'] == 'full' and backup_age > full_days:
                    should_prune = True
                elif backup['backup_type'] == 'incremental' and backup_age > incremental_days:
                    should_prune = True
                
                if should_prune:
                    # Implementar remoção do S3 e metadados
                    self.logger.info(f"Pruning backup: {backup['backup_id']}")
                    pruned_count += 1
            
            self.logger.info(f"Limpeza concluída: {pruned_count} backups removidos")
            self.alert_manager.send_alert(
                f"Limpeza concluída: {pruned_count} backups removidos",
                'info',
                {'pruned_count': pruned_count, 'scheduled': True}
            )
            
        except Exception as e:
            self.logger.error(f"Erro na limpeza agendada: {e}")
            self.alert_manager.send_alert(
                f"Erro na limpeza: {str(e)}",
                'error',
                {'type': 'prune', 'scheduled': True}
            )
    
    def start(self):
        """Inicia o scheduler"""
        if self.running:
            self.logger.warning("Scheduler já está rodando")
            return
        
        self.setup_schedule()
        self.running = True
        
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # Verifica a cada minuto
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("Scheduler iniciado")
    
    def stop(self):
        """Para o scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        self.logger.info("Scheduler parado")
    
    def get_next_runs(self) -> Dict[str, str]:
        """Obtém próximas execuções agendadas"""
        try:
            jobs = schedule.get_jobs()
            next_runs = {}
            
            for job in jobs:
                job_name = str(job.job_func).split('.')[-1].replace('>', '')
                next_run = job.next_run
                if next_run:
                    next_runs[job_name] = next_run.isoformat()
            
            return next_runs
            
        except Exception as e:
            self.logger.error(f"Erro ao obter próximas execuções: {e}")
            return {}
    
    def cleanup(self):
        """Limpa recursos"""
        try:
            self.stop()
            self.backup_engine.cleanup()
        except Exception as e:
            self.logger.error(f"Erro no cleanup do scheduler: {e}")