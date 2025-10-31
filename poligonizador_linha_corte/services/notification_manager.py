# -*- coding: utf-8 -*-
"""
Gerenciador centralizado de notificações para evitar sobreposições
"""
from qgis.PyQt.QtCore import QTimer, QObject
from .Notification import show_notification


class NotificationManager(QObject):
    """Gerencia notificações para evitar bugs de sobreposição"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self.notification_queue = []
        self.current_notification = None
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._process_next_notification)
        self.delay_timer = QTimer()
        self.delay_timer.setSingleShot(True)
        self.delay_timer.timeout.connect(self._show_current_notification)
    
    def notify(self, titulo, mensagem, tipo="info", duracao=2000, delay=0, priority=1):
        """
        Adiciona notificação à fila
        
        Args:
            titulo: Título da notificação
            mensagem: Mensagem da notificação
            tipo: Tipo (info, success, warning, error)
            duracao: Duração em ms
            delay: Atraso antes de mostrar (ms)
            priority: Prioridade (0=alta, 1=normal, 2=baixa)
        """
        notification = {
            'titulo': titulo,
            'mensagem': mensagem,
            'tipo': tipo,
            'duracao': duracao,
            'delay': delay,
            'priority': priority
        }
        
        # Se já existe notificação pendente com mesmo título, substitui
        self.notification_queue = [n for n in self.notification_queue 
                                   if n['titulo'] != titulo]
        
        # Adiciona à fila ordenada por prioridade
        self.notification_queue.append(notification)
        self.notification_queue.sort(key=lambda x: x['priority'])
        
        # Se não há notificação sendo exibida, processa imediatamente
        if not self.current_notification and not self.timer.isActive():
            self._process_next_notification()
    
    def notify_immediate(self, titulo, mensagem, tipo="info", duracao=2000):
        """Mostra notificação imediata, cancelando a atual se necessário"""
        self.cancel_all()
        self.current_notification = {
            'titulo': titulo,
            'mensagem': mensagem,
            'tipo': tipo,
            'duracao': duracao,
            'delay': 0,
            'priority': 0
        }
        self._show_current_notification()
    
    def _process_next_notification(self):
        """Processa próxima notificação da fila"""
        if not self.notification_queue:
            self.current_notification = None
            return
        
        self.current_notification = self.notification_queue.pop(0)
        
        if self.current_notification['delay'] > 0:
            self.delay_timer.start(self.current_notification['delay'])
        else:
            self._show_current_notification()
    
    def _show_current_notification(self):
        """Exibe a notificação atual"""
        if not self.current_notification:
            return
        
        try:
            show_notification(
                self.current_notification['titulo'],
                self.current_notification['mensagem'],
                self.current_notification['tipo'],
                self.current_notification['duracao']
            )
        except Exception as e:
            print(f"Erro ao mostrar notificação: {e}")
        
        # Agenda próxima notificação
        self.timer.start(self.current_notification['duracao'] + 200)
    
    def cancel_all(self):
        """Cancela todas as notificações pendentes"""
        self.notification_queue.clear()
        self.timer.stop()
        self.delay_timer.stop()
        self.current_notification = None
    
    def cancel_by_title(self, titulo):
        """Cancela notificações específicas pelo título"""
        self.notification_queue = [n for n in self.notification_queue 
                                   if n['titulo'] != titulo]
        
        if self.current_notification and self.current_notification['titulo'] == titulo:
            self.timer.stop()
            self.delay_timer.stop()
            self._process_next_notification()
    
    def clear_queue(self):
        """Limpa fila mas mantém notificação atual"""
        self.notification_queue.clear()


# Singleton global
notification_manager = NotificationManager()