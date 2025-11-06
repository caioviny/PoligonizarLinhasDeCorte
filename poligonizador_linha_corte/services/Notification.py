"""
Sistema de Notificações Modernas para QGIS
Módulo independente e reutilizável
Resolve problema de travamento ao usar notificações rapidamente

Uso em qualquer projeto:
    from services.notification import show_notification
    
    show_notification("Título", "Mensagem", "success", 3000)
"""

from qgis.PyQt.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal, QObject
from qgis.PyQt.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget
from qgis.utils import iface as global_iface
from collections import deque
import time


class ModernNotification(QFrame):
    """Widget de notificação moderna com animação"""
    
    closed = pyqtSignal()
    
    def __init__(self, titulo, mensagem, tipo="success", duracao=3000, parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_DeleteOnClose)
        
        self.duracao = duracao
        self.tipo = tipo
        
        # Layout principal
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Container interno com estilo
        self.container = QFrame()
        self.container.setFixedSize(350, 80)
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(15, 10, 15, 10)
        
        # Ícone
        icon_label = QLabel()
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignCenter)
        
        # Definir ícone e cor baseado no tipo
        icones = {
            "success": ("✓", "#10b981", "#d1fae5"),
            "error": ("✕", "#ef4444", "#fee2e2"),
            "warning": ("⚠", "#f59e0b", "#fef3c7"),
            "info": ("ℹ", "#3b82f6", "#dbeafe")
        }
        
        icone, cor_principal, cor_fundo = icones.get(tipo, icones["info"])
        
        icon_label.setText(icone)
        icon_label.setStyleSheet(f"""
            QLabel {{
                background-color: {cor_principal};
                color: white;
                border-radius: 20px;
                font-size: 24px;
                font-weight: bold;
            }}
        """)
        
        # Área de texto
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(10, 5, 10, 5)
        text_layout.setSpacing(2)
        
        # Título
        titulo_label = QLabel(titulo)
        titulo_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: #1f2937;
        """)
        
        # Mensagem
        msg_label = QLabel(mensagem)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("""
            font-size: 12px;
            color: #6b7280;
        """)
        
        text_layout.addWidget(titulo_label)
        text_layout.addWidget(msg_label)
        text_layout.addStretch()
        
        # Botão fechar
        btn_fechar = QPushButton("×")
        btn_fechar.setFixedSize(25, 25)
        btn_fechar.clicked.connect(self.fechar_animado)
        btn_fechar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9ca3af;
                border: none;
                border-radius: 12px;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
                color: #4b5563;
            }
        """)
        
        # Adicionar ao container
        container_layout.addWidget(icon_label)
        container_layout.addWidget(text_container, 1)
        container_layout.addWidget(btn_fechar, 0, Qt.AlignTop)
        
        # Estilo do container
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {cor_fundo};
                border-radius: 10px;
            }}
        """)
        
        # Sombra simulada
        shadow_frame = QFrame(self)
        shadow_frame.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.1);
            border-radius: 10px;
        """)
        shadow_frame.setGeometry(3, 3, 350, 80)
        shadow_frame.lower()
        
        layout.addWidget(self.container)
        
        # Barra de progresso (tempo restante)
        self.progress_bar = QFrame(self.container)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet(f"""
            background-color: {cor_principal};
            border-radius: 1px;
        """)
        self.progress_bar.setGeometry(0, 77, 350, 3)
        
        # Animação da barra de progresso
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"geometry")
        self.progress_animation.setDuration(duracao)
        self.progress_animation.setStartValue(self.progress_bar.geometry())
        end_rect = self.progress_bar.geometry()
        end_rect.setWidth(0)
        self.progress_animation.setEndValue(end_rect)
        self.progress_animation.setEasingCurve(QEasingCurve.Linear)
        
        # Timer para fechar automaticamente
        self.close_timer = QTimer()
        self.close_timer.setSingleShot(True)
        self.close_timer.timeout.connect(self.fechar_animado)
        
        # Ajustar tamanho do widget
        self.setFixedSize(356, 86)
    
    def mostrar(self, posicao):
        """Mostra a notificação com animação"""
        self.move(posicao.x(), posicao.y() - 100)
        self.show()
        self.raise_()
        
        # Animação de entrada (desliza de cima)
        self.entrada_anim = QPropertyAnimation(self, b"pos")
        self.entrada_anim.setDuration(400)
        self.entrada_anim.setStartValue(self.pos())
        self.entrada_anim.setEndValue(posicao)
        self.entrada_anim.setEasingCurve(QEasingCurve.OutBack)
        self.entrada_anim.start()
        
        # Iniciar barra de progresso e timer
        self.progress_animation.start()
        self.close_timer.start(self.duracao)
    
    def fechar_animado(self):
        """Fecha a notificação com animação"""
        # Parar timers
        self.close_timer.stop()
        self.progress_animation.stop()
        
        # Animação de saída (desliza para direita)
        self.saida_anim = QPropertyAnimation(self, b"pos")
        self.saida_anim.setDuration(300)
        self.saida_anim.setStartValue(self.pos())
        end_pos = QPoint(self.pos().x() + 400, self.pos().y())
        self.saida_anim.setEndValue(end_pos)
        self.saida_anim.setEasingCurve(QEasingCurve.InBack)
        self.saida_anim.finished.connect(self.close)
        self.saida_anim.finished.connect(self.closed.emit)
        self.saida_anim.start()


class NotificationManager(QObject):
    """
    Gerenciador de notificações com controle de taxa
    ✅ RESOLVE TRAVAMENTO: Controla velocidade de exibição
    """
    
    def __init__(self, parent_window=None, intervalo_minimo_ms=300, max_fila=30):
        super().__init__()
        
        self.parent = parent_window
        self.notifications = []
        self.spacing = 10
        
        # ✅ Controle de taxa para evitar travamento
        self.intervalo_minimo = intervalo_minimo_ms
        self.max_fila = max_fila
        self.fila = deque(maxlen=max_fila)
        self.ultima_notificacao_tempo = 0
        
        # Timer para processar fila
        self.timer_processamento = QTimer()
        self.timer_processamento.setSingleShot(False)
        self.timer_processamento.timeout.connect(self._processar_fila)
        
        # Debounce para notificações similares
        self.debounce_timers = {}
    
    def show_notification(self, titulo, mensagem, tipo="success", duracao=3000, debounce=0):
        """
        Mostra notificação com controle inteligente
        
        Args:
            titulo: Título da notificação
            mensagem: Mensagem detalhada
            tipo: "success", "error", "warning", "info"
            duracao: Duração em ms
            debounce: Delay antes de mostrar (agrupa notificações rápidas)
        """
        # Se tem debounce, agrupa notificações similares
        if debounce > 0:
            chave = f"{titulo}_{tipo}"
            
            # Cancela timer anterior se existir
            if chave in self.debounce_timers:
                self.debounce_timers[chave].stop()
            
            # Cria novo timer
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(
                lambda: self._adicionar_na_fila(titulo, mensagem, tipo, duracao)
            )
            timer.start(debounce)
            self.debounce_timers[chave] = timer
            return
        
        # Adiciona direto na fila
        self._adicionar_na_fila(titulo, mensagem, tipo, duracao)
    
    def _adicionar_na_fila(self, titulo, mensagem, tipo, duracao):
        """Adiciona notificação na fila de processamento"""
        # Previne overflow da fila
        if len(self.fila) >= self.max_fila:
            # Mostra aviso de overflow
            self._mostrar_overflow_warning()
            self.fila.clear()
        
        # Adiciona na fila
        self.fila.append({
            'titulo': titulo,
            'mensagem': mensagem,
            'tipo': tipo,
            'duracao': duracao,
            'timestamp': time.time()
        })
        
        # Inicia processamento se não estiver ativo
        if not self.timer_processamento.isActive():
            self.timer_processamento.start(self.intervalo_minimo)
    
    def _processar_fila(self):
        """Processa fila de notificações respeitando taxa máxima"""
        if not self.fila:
            self.timer_processamento.stop()
            return
        
        # Verifica se já pode mostrar próxima notificação
        tempo_atual = time.time() * 1000
        tempo_decorrido = tempo_atual - self.ultima_notificacao_tempo
        
        if tempo_decorrido < self.intervalo_minimo:
            return
        
        # Remove da fila e mostra
        notif = self.fila.popleft()
        self._mostrar_notificacao_real(
            notif['titulo'],
            notif['mensagem'],
            notif['tipo'],
            notif['duracao']
        )
        
        self.ultima_notificacao_tempo = tempo_atual
    
    def _mostrar_notificacao_real(self, titulo, mensagem, tipo, duracao):
        """Mostra notificação na tela (função interna)"""
        try:
            # Obter geometria da tela
            if global_iface and global_iface.mainWindow():
                screen_geometry = global_iface.mainWindow().screen().geometry()
            else:
                from PyQt5.QtWidgets import QDesktopWidget
                screen_geometry = QDesktopWidget().screenGeometry()
        except:
            from PyQt5.QtWidgets import QDesktopWidget
            screen_geometry = QDesktopWidget().screenGeometry()
        
        # Calcular posição
        x = screen_geometry.width() - 370
        y = 20 + len(self.notifications) * (80 + self.spacing)
        
        # Criar notificação
        notification = ModernNotification(titulo, mensagem, tipo, duracao, self.parent)
        notification.closed.connect(lambda: self.remove_notification(notification))
        
        # Adicionar à lista
        self.notifications.append(notification)
        
        # Mostrar
        notification.mostrar(QPoint(x, y))
        
        # Reposicionar outras
        self.reposition_notifications()
    
    def _mostrar_overflow_warning(self):
        """Mostra aviso quando fila está cheia"""
        self._mostrar_notificacao_real(
            "⚠️ Muitas Notificações",
            f"Fila cheia ({self.max_fila}+). Algumas descartadas.",
            "warning",
            3000
        )
    
    def remove_notification(self, notification):
        """Remove notificação da lista"""
        if notification in self.notifications:
            self.notifications.remove(notification)
            self.reposition_notifications()
    
    def reposition_notifications(self):
        """Reposiciona todas as notificações"""
        try:
            if global_iface and global_iface.mainWindow():
                screen_geometry = global_iface.mainWindow().screen().geometry()
            else:
                from PyQt5.QtWidgets import QDesktopWidget
                screen_geometry = QDesktopWidget().screenGeometry()
        except:
            from PyQt5.QtWidgets import QDesktopWidget
            screen_geometry = QDesktopWidget().screenGeometry()
        
        x = screen_geometry.width() - 370
        
        for i, notif in enumerate(self.notifications):
            new_y = 20 + i * (80 + self.spacing)
            
            # Animar reposicionamento
            anim = QPropertyAnimation(notif, b"pos")
            anim.setDuration(300)
            anim.setStartValue(notif.pos())
            anim.setEndValue(QPoint(x, new_y))
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.start()
            
            # Manter referência
            notif.reposition_anim = anim
    
    def clear(self):
        """Limpa todas as notificações e fila"""
        self.fila.clear()
        self.timer_processamento.stop()
        for timer in self.debounce_timers.values():
            timer.stop()
        self.debounce_timers.clear()
    
    def cancel(self):
        """Alias para clear()"""
        self.clear()


# ==================== INTERFACE PÚBLICA ====================

# Singleton global
_notification_manager = None


def get_notification_manager():
    """
    Retorna instância singleton do gerenciador
    Útil quando você precisa de controle avançado (clear, cancel, etc)
    
    Exemplo:
        manager = get_notification_manager()
        manager.clear()  # Limpa todas notificações
    """
    global _notification_manager
    
    if _notification_manager is None:
        parent = global_iface.mainWindow() if global_iface else None
        _notification_manager = NotificationManager(
            parent_window=parent,
            intervalo_minimo_ms=300,  # 300ms entre notificações
            max_fila=3  # Máximo 30 notificações na fila
        )
    
    return _notification_manager


def show_notification(titulo, mensagem, tipo="success", duracao=3000, debounce=0):
    """
    Função principal para mostrar notificações
    ✅ USO RECOMENDADO - Simples e direto
    
    Args:
        titulo: Título da notificação
        mensagem: Mensagem detalhada
        tipo: "success", "error", "warning", "info"
        duracao: Duração em milissegundos (padrão 3000ms = 3s)
        debounce: Delay para agrupar notificações similares (0 = desabilitado)
    
    Exemplos:
        # Básico
        show_notification("Sucesso!", "Operação concluída", "success")
        
        # Com duração customizada
        show_notification("Processando", "Aguarde...", "info", 5000)
        
        # Com debounce (agrupa cliques rápidos)
        show_notification("Selecionado", "Item X", "info", 1500, debounce=500)
        
        # Diferentes tipos
        show_notification("Atenção", "Verifique os dados", "warning")
        show_notification("Erro", "Falha na operação", "error")
    """
    manager = get_notification_manager()
    manager.show_notification(titulo, mensagem, tipo, duracao, debounce)


# ==================== UTILITÁRIOS EXTRAS ====================

def clear_all_notifications():
    """
    Limpa todas as notificações da tela e fila
    Útil ao fechar aplicação ou resetar estado
    """
    manager = get_notification_manager()
    manager.clear()


def cancel_pending_notifications():
    """
    Cancela notificações pendentes (alias para clear_all_notifications)
    """
    clear_all_notifications()