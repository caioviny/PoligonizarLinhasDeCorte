"""
Sistema de Notificações Modernas para QGIS
Arquivo: notification_system.py
"""

from qgis.PyQt.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from qgis.PyQt.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QWidget
from qgis.utils import iface as global_iface


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


class NotificationManager:
    """Gerenciador de notificações"""
    
    def __init__(self, parent_window=None):
        self.parent = parent_window
        self.notifications = []
        self.spacing = 10
    
    def show_notification(self, titulo, mensagem, tipo="success", duracao=3000):
        """Mostra uma nova notificação"""
        # Obter geometria da tela
        try:
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
        
        # Reposicionar outras notificações
        self.reposition_notifications()
    
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


# Gerenciador global
_notification_manager = None


def show_notification(titulo, mensagem, tipo="success", duracao=5000):
    """
    Função global para mostrar notificações modernas no QGIS
    
    Args:
        titulo: Título da notificação
        mensagem: Mensagem detalhada
        tipo: Tipo da notificação ("success", "error", "warning", "info")
        duracao: Duração em milissegundos (padrão 5000ms = 5s)
    
    Exemplos de uso:
        show_notification("Sucesso!", "Operação realizada com sucesso!", "success")
        show_notification("Atenção", "Selecione uma quadra válida!", "warning")
        show_notification("Erro", "Não foi possível processar!", "error")
        show_notification("Info", "Processamento iniciado...", "info")
    """
    global _notification_manager
    
    # Criar gerenciador se não existir
    if _notification_manager is None:
        parent = global_iface.mainWindow() if global_iface else None
        _notification_manager = NotificationManager(parent)
    
    # Mostrar notificação
    _notification_manager.show_notification(titulo, mensagem, tipo, duracao)