# -*- coding: utf-8 -*-
"""
Interface Premium para o plugin Poligonizador de Linha de Corte
Design Embasa - Compatível com PyQt5
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
    QPushButton, QFrame, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QLinearGradient, QPixmap, QImage
import os


class ModernComboBox(QComboBox):
    """ComboBox customizado com animação"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._border_color = QColor("#dee2e6")
        
    def get_border_color(self):
        return self._border_color
    
    def set_border_color(self, color):
        self._border_color = color
        self.update()
    
    border_color = pyqtProperty(QColor, get_border_color, set_border_color)
    
    def enterEvent(self, event):
        self.animate_border(QColor("#4fa3d1"))
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if not self.hasFocus():
            self.animate_border(QColor("#dee2e6"))
        super().leaveEvent(event)
    
    def animate_border(self, color):
        anim = QPropertyAnimation(self, b"border_color")
        anim.setDuration(200)
        anim.setStartValue(self._border_color)
        anim.setEndValue(color)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.start()


class CloseButton(QPushButton):
    """Botão de fechar customizado"""
    def __init__(self, parent=None):
        super().__init__("×", parent)
        self.setFixedSize(30, 30)
        self.setCursor(Qt.PointingHandCursor)
        self._hover = False
        
    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # Fundo circular
        if self.isDown():
            painter.setBrush(QColor(220, 53, 69, 200))
        elif self._hover:
            painter.setBrush(QColor(220, 53, 69, 180))
        else:
            painter.setBrush(QColor(255, 255, 255, 50))
        
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect.center(), 13, 13)
        
        # Símbolo X (ajustado para cima)
        painter.setPen(QColor("white"))
        font = QFont("Segoe UI", 18, QFont.Bold)
        painter.setFont(font)
        text_rect = rect.adjusted(0, -3, 0, -3)  # Move 3 pixels para cima
        painter.drawText(text_rect, Qt.AlignCenter, "×")


class ModernButton(QPushButton):
    """Botão customizado com efeitos"""
    def __init__(self, text, button_style="primary", parent=None):
        super().__init__(text, parent)
        self.button_style = button_style
        self.setMouseTracking(True)
        self._hover = False
        
    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        path = QPainterPath()
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 12, 12)
        
        if self.button_style == "primary":
            # Gradiente Embasa - Azul
            gradient = QLinearGradient(0, 0, 0, rect.height())
            if self.isDown():
                gradient.setColorAt(0, QColor("#002d5c"))
                gradient.setColorAt(1, QColor("#003d7a"))
            elif self._hover:
                gradient.setColorAt(0, QColor("#0056a8"))
                gradient.setColorAt(1, QColor("#4fa3d1"))
            else:
                gradient.setColorAt(0, QColor("#003d7a"))
                gradient.setColorAt(1, QColor("#4fa3d1"))
            painter.fillPath(path, gradient)
            
        elif self.button_style == "danger":
            # Gradiente Embasa - Azul escuro
            gradient = QLinearGradient(0, 0, 0, rect.height())
            if self.isDown():
                gradient.setColorAt(0, QColor("#001f3f"))
                gradient.setColorAt(1, QColor("#002d5c"))
            elif self._hover:
                gradient.setColorAt(0, QColor("#003d7a"))
                gradient.setColorAt(1, QColor("#0056a8"))
            else:
                gradient.setColorAt(0, QColor("#002d5c"))
                gradient.setColorAt(1, QColor("#003d7a"))
            painter.fillPath(path, gradient)
            
        else:  # secondary
            gradient = QLinearGradient(0, 0, 0, rect.height())
            if self.isDown():
                gradient.setColorAt(0, QColor("#4fa3d1"))
                gradient.setColorAt(1, QColor("#7dc8e8"))
            elif self._hover:
                gradient.setColorAt(0, QColor("#7dc8e8"))
                gradient.setColorAt(1, QColor("#a8d8f0"))
            else:
                gradient.setColorAt(0, QColor("#7dc8e8"))
                gradient.setColorAt(1, QColor("#b8e3f5"))
            painter.fillPath(path, gradient)
        
        # Texto
        if self.button_style in ["primary", "danger"]:
            painter.setPen(QColor("white"))
        elif self.button_style == "secondary":
            painter.setPen(QColor("#003d7a"))
        else:
            painter.setPen(QColor("#495057"))
        font = QFont("Segoe UI", 10, QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())


class PoligonizadorDialog_2(QDialog):
    """Interface Premium do Poligonizador de Linha de Corte"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Poligonizador de Linha de Corte")
        self.setFixedSize(360, 360)
        
        # Remove borda do Qt e deixa fundo transparente
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.setup_ui()
        self.apply_styles()
        self.load_logo()
        
    def setup_ui(self):
        """Configura a interface do usuário"""
        # Container principal com sombra (margem para a sombra)
        main_container = QFrame(self)
        main_container.setObjectName("mainContainer")
        main_container.setGeometry(10, 10, 340, 340)
        
        # Efeito de sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 40))
        main_container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(main_container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # ===== HEADER COM GRADIENTE =====
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setFixedHeight(65)
        
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 12, 15, 12)
        header_layout.setSpacing(5)
        
        # Logo em marca d'água no header
        self.logo_background = QLabel(header_frame)
        self.logo_background.setStyleSheet("background: transparent;")
        self.logo_background.setAlignment(Qt.AlignCenter)
        self.logo_background.setGeometry(0, 0, 340, 65)
        self.logo_background.lower()
        self.logo_background.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Botão fechar no canto superior direito
        self.btn_close = CloseButton(header_frame)
        self.btn_close.setGeometry(300, 8, 30, 30)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.clicked.connect(self.reject)
        
        # Título com ícone
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        
        icon_label = QLabel("🗺️")
        icon_label.setStyleSheet("font-size: 28px; background: transparent;")
        
        title_text_layout = QVBoxLayout()
        title_text_layout.setSpacing(2)
        
        title = QLabel("Poligonizador")
        title.setObjectName("headerTitle")
        title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        
        subtitle = QLabel("Configure e selecione a área")
        subtitle.setObjectName("headerSubtitle")
        subtitle.setFont(QFont("Segoe UI", 8))
        
        title_text_layout.addWidget(title)
        title_text_layout.addWidget(subtitle)
        
        title_layout.addWidget(icon_label)
        title_layout.addLayout(title_text_layout)
        title_layout.addStretch()
        
        header_layout.addLayout(title_layout)
        
        container_layout.addWidget(header_frame)
        
        # ===== CONTEÚDO PRINCIPAL =====
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        
        content_layout = QVBoxLayout(content_frame)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(15, 15, 15, 15)
        
        # ===== CARD: CONEXÃO =====
        conexao_card = self.create_input_card(
            "🔌",
            "Conexão PostgreSQL",
            "Selecione a conexão"
        )
        
        self.combo_conexao = ModernComboBox()
        self.combo_conexao.setObjectName("comboConexao")
        self.combo_conexao.setFont(QFont("Segoe UI", 9))
        self.combo_conexao.setMinimumHeight(35)
        self.combo_conexao.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        conexao_card.layout().addWidget(self.combo_conexao)
        
        content_layout.addWidget(conexao_card)
        
        # ===== CARD: QUADRA =====
        quadra_card = self.create_input_card(
            "📍",
            "Seleção de Área",
            "Selecione no mapa"
        )
        
        # Botão selecionar dentro do card
        self.btn_selecionar = ModernButton("🗺️  Selecionar Quadra", "secondary")
        self.btn_selecionar.setObjectName("btnSelecionarQuadra")
        self.btn_selecionar.setCursor(Qt.PointingHandCursor)
        self.btn_selecionar.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        self.btn_selecionar.setMinimumHeight(30)
        self.btn_selecionar.setMaximumHeight(30)
        quadra_card.layout().addWidget(self.btn_selecionar)
        
        content_layout.addWidget(quadra_card)
        
        content_layout.addSpacing(5)
        
        # ===== BOTÃO CONFIRMAR (ÚNICO) =====
        self.btn_ok = ModernButton("✅  Confirmar", "primary")
        self.btn_ok.setObjectName("btnOk")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.btn_ok.setMinimumHeight(40)
        self.btn_ok.clicked.connect(self.accept)
        
        content_layout.addWidget(self.btn_ok)
        
        content_layout.addStretch()
        
        container_layout.addWidget(content_frame)
    
    def create_input_card(self, icon, title, description):
        """Cria card de input estilizado"""
        card = QFrame()
        card.setObjectName("inputCard")
        
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(12, 10, 12, 10)
        
        # Header
        header = QHBoxLayout()
        header.setSpacing(8)
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 18px;")
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        
        desc_label = QLabel(description)
        desc_label.setObjectName("cardDesc")
        desc_label.setFont(QFont("Segoe UI", 8))
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        
        header.addWidget(icon_label)
        header.addLayout(text_layout)
        header.addStretch()
        
        card_layout.addLayout(header)
        
        return card
    
    def apply_styles(self):
        """Aplica estilos CSS"""
        self.setStyleSheet("""
            QDialog {
                background-color: transparent;
            }
            
            QFrame#mainContainer {
                background-color: white;
                border-radius: 16px;
            }
            
            /* Header com gradiente Embasa */
            QFrame#headerFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #003d7a, stop:0.4 #0056a8, stop:0.7 #4fa3d1, stop:1 #7dc8e8);
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
            
            QLabel#headerTitle {
                color: white;
                background: transparent;
            }
            
            QLabel#headerSubtitle {
                color: rgba(255, 255, 255, 0.95);
                background: transparent;
            }
            
            QFrame#contentFrame {
                background-color: white;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }
            
            /* Cards de Input */
            QFrame#inputCard {
                background-color: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 12px;
            }
            
            QFrame#inputCard:hover {
                background-color: white;
                border: 2px solid #dee2e6;
            }
            
            QLabel#cardTitle {
                color: #212529;
            }
            
            QLabel#cardDesc {
                color: #6c757d;
            }
            
            /* ComboBox */
            QComboBox#comboConexao {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                padding: 10px 15px;
                color: #495057;
            }
            
            QComboBox#comboConexao:hover {
                border: 2px solid #4fa3d1;
            }
            
            QComboBox#comboConexao:focus {
                border: 2px solid #003d7a;
                background-color: #f0f8ff;
            }
            
            QComboBox#comboConexao::drop-down {
                border: none;
                width: 30px;
            }
            
            QComboBox#comboConexao::down-arrow {
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #6c757d;
                margin-right: 10px;
            }
            
            QComboBox#comboConexao QAbstractItemView {
                background-color: white;
                border: 2px solid #dee2e6;
                border-radius: 10px;
                selection-background-color: #e3f2fd;
                selection-color: #003d7a;
                padding: 6px;
                outline: none;
            }
            
            QComboBox#comboConexao QAbstractItemView::item {
                padding: 10px 15px;
                border-radius: 6px;
            }
            
            QComboBox#comboConexao QAbstractItemView::item:hover {
                background-color: #e3f2fd;
            }
        """)
    
    def load_logo(self):
        """Carrega logo no header com transparência"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(current_dir, "logo.png")

            if os.path.exists(image_path):
                # Carrega imagem com suporte a canal alfa
                image = QImage(image_path).convertToFormat(QImage.Format_ARGB32)
                if not image.isNull():
                    # Redimensiona mantendo transparência
                    scaled_image = image.scaled(
                        120, 50,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )

                    # Converte para pixmap preservando alfa
                    transparent_pixmap = QPixmap.fromImage(scaled_image)

                    # Aplica opacidade sobre um fundo transparente
                    final_pixmap = QPixmap(transparent_pixmap.size())
                    final_pixmap.fill(Qt.transparent)

                    painter = QPainter(final_pixmap)
                    painter.setOpacity(0.15)  # 15% de opacidade
                    painter.drawPixmap(0, 0, transparent_pixmap)
                    painter.end()

                    # Define o label com fundo transparente
                    self.logo_background.setPixmap(final_pixmap)
                    self.logo_background.setStyleSheet("background: transparent; border: none;")
                
        except Exception as e:
            print(f"Erro ao carregar logo: {e}")
    
    def mousePressEvent(self, event):
        """Permite arrastar a janela"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Move a janela ao arrastar"""
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()