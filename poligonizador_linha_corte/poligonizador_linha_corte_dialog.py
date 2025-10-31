from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QSizePolicy, QStyledItemDelegate, QListView, QApplication)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap, QPen, QBrush, QLinearGradient, QPalette
import os
import sys

class ModernComboBox(QComboBox):
    """ComboBox customizado com estilo moderno"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(35)  # Reduzido de 40 para 35
        self.setMaxVisibleItems(6)
        self.setFont(QFont("Segoe UI", 8))  # Reduzido de 9 para 8
        view = QListView(self)
        view.setFont(QFont("Segoe UI", 8))
        self.setView(view)
        self.setStyleSheet("""
            QComboBox {
                background-color: #f8f9fa;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 6px 10px;
                padding-right: 28px;
                color: #000000;
                font-size: 8pt;
                font-family: "Segoe UI";
            }
            QComboBox:hover { background-color: #ffffff; border: 2px solid #2196f3; }
            QComboBox:focus { border: 2px solid #2196f3; }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox::down-arrow {
                image: none; width: 0; height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #78909c;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 4px;
                color: #000000;
                font-size: 8pt;
                outline: none;
            }
            QComboBox QAbstractItemView::item { min-height: 26px; padding-left: 8px; }
            QComboBox QAbstractItemView::item:hover { background-color: #e3f2fd; color: #1976d2; }
            QComboBox QAbstractItemView::item:selected { background-color: #2196f3; color: white; }
        """)

    def showPopup(self):
        super().showPopup()
        popup = self.view()
        if popup:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(15)
            shadow.setXOffset(0)
            shadow.setYOffset(0)
            shadow.setColor(QColor(0, 0, 0, 100))
            popup.setGraphicsEffect(shadow)

class ModernButton(QPushButton):
    """Botão customizado com efeitos"""

    def __init__(self, text, primary=False, custom_color=None, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.custom_color = custom_color  # Nova propriedade para cor customizada
        self.setMouseTracking(True)
        self._hover = False
        self.setFont(QFont("Segoe UI", 8, QFont.DemiBold))

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
        path.addRoundedRect(rect.x(), rect.y(), rect.width(), rect.height(), 8, 8)
        
        # Se tiver cor customizada, usa ela
        if self.custom_color:
            base_color = QColor(self.custom_color)
            if self.isDown():
                # Escurece mais quando pressionado
                painter.fillPath(path, base_color.darker(130))
            elif self._hover:
                # Escurece um pouco no hover
                painter.fillPath(path, base_color.darker(110))
            else:
                painter.fillPath(path, base_color)
            # Texto preto para cores customizadas
            painter.setPen(QColor(0, 0, 0))
        elif self.primary:
            if self.isDown():
                painter.fillPath(path, QColor("#0056b3"))
            elif self._hover:
                painter.fillPath(path, QColor("#0066cc"))
            else:
                painter.fillPath(path, QColor("#0073e6"))
            painter.setPen(QColor(255, 255, 255))
        else:
            if self.isDown():
                painter.fillPath(path, QColor(222, 226, 230))
            elif self._hover:
                painter.fillPath(path, QColor(233, 236, 239))
            else:
                painter.fillPath(path, QColor(200, 200, 200))
            painter.setPen(QColor(73, 80, 87))
        
        font = QFont("Segoe UI", 8, QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())

class PoligonizadorDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Poligonizador de Linha de Corte")
        self.setFixedSize(360, 420)  # Reduzido de 400x480 para 360x420
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_ui()
        self.load_embasa_logo()

    def setup_ui(self):
        main_container = QFrame(self)
        main_container.setObjectName("mainContainer")
        main_container.setGeometry(10, 10, 340, 400)  # Reduzido de 380x460 para 340x400

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 40))
        main_container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(main_container)
        layout.setSpacing(6)  # Reduzido de 10 para 6
        layout.setContentsMargins(16, 16, 16, 16)  # Reduzido de 20 para 16

        # Logo
        self.logo_label = QLabel(main_container)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setMaximumHeight(24)  # Reduzido de 30 para 24
        self.logo_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.logo_label)
        
        # Header
        header_layout = QHBoxLayout()
        title_container = QVBoxLayout()
        title_container.setSpacing(1)  # Reduzido de 2 para 1

        title = QLabel("Poligonizador")
        title.setObjectName("title")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))  # Reduzido de 14 para 12

        subtitle = QLabel("Configure a conexão e selecione a área")
        subtitle.setObjectName("subtitle")
        subtitle.setFont(QFont("Segoe UI", 7))  # Reduzido de 8 para 7

        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        header_layout.addLayout(title_container)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Separador
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)

        # Label conexão
        conn_label = QLabel("Conexão PostgreSQL")
        conn_label.setFont(QFont("Segoe UI", 8, QFont.DemiBold))  # Reduzido de 9 para 8
        conn_label.setStyleSheet("color: #37474f; margin-top: 2px;")
        layout.addWidget(conn_label)

        # ComboBox
        self.combo_conexao = ModernComboBox()
        self.combo_conexao.setObjectName("comboBox_conexao")
        items = [
            "Conexão Principal - localhost:5432",
            "Servidor Produção - 192.168.1.100",
            "Servidor Desenvolvimento - dev.example.com",
        ]
        for item in items:
            self.combo_conexao.addItem(item)
        if self.combo_conexao.count() > 0:
            self.combo_conexao.setCurrentIndex(0)
        layout.addWidget(self.combo_conexao)

        layout.addSpacing(4)  # Reduzido de 6 para 4

        # Label quadra
        info_label = QLabel("Quadra Selecionada")
        info_label.setFont(QFont("Segoe UI", 8, QFont.DemiBold))  # Reduzido de 9 para 8
        info_label.setStyleSheet("color: #37474f; margin-top: 2px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # Info quadra
        self.lblQuadraSelecionada = QLabel("Nenhuma quadra selecionada")
        self.lblQuadraSelecionada.setObjectName("lblQuadra")
        self.lblQuadraSelecionada.setFont(QFont("Segoe UI", 7))  # Reduzido de 8 para 7
        self.lblQuadraSelecionada.setStyleSheet("""
            background-color: #f0f7ff;
            border: 1px solid #bbdefb;
            border-radius: 6px;
            padding: 6px 8px;
            color: #1976d2;
        """)
        self.lblQuadraSelecionada.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lblQuadraSelecionada)

        layout.addSpacing(4)  # Reduzido de 6 para 4

        # Botão selecionar
        self.btn_selecionar = ModernButton("Selecionar Quadra", primary=True)
        self.btn_selecionar.setObjectName("btnSelecionar")
        self.btn_selecionar.setCursor(Qt.PointingHandCursor)
        self.btn_selecionar.setFixedHeight(30)  # Reduzido de 35 para 30
        layout.addWidget(self.btn_selecionar)

       

        # Botões ação (Cancelar e Poligonizar)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(2)  # Reduzido de 8 para 6

        self.btn_cancelar = ModernButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.setFixedHeight(28)  # Reduzido de 30 para 28
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_ok = ModernButton("Poligonizar", primary=True)
        self.btn_ok.setObjectName("btnOk")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setFixedHeight(28)  # Reduzido de 30 para 28

        buttons_layout.addWidget(self.btn_cancelar)
        buttons_layout.addWidget(self.btn_ok)
        layout.addLayout(buttons_layout)

        layout.addSpacing(5)  # Reduzido de 8 para 5

        # Botão deletar lotes (abaixo dos outros botões)
        self.btn_remover_lotes = ModernButton("Deletar Lotes", primary=False, custom_color="#ffc107")
        self.btn_remover_lotes.setObjectName("btn_remover_lotes")
        self.btn_remover_lotes.setCursor(Qt.PointingHandCursor)
        self.btn_remover_lotes.setFixedHeight(28)
        layout.addWidget(self.btn_remover_lotes)
       

        layout.addSpacing(3)  # Reduzido de 4 para 3

        # Label de autores
        authors_label = QLabel("Desenvolvido por Lucas, Tavares e Caio")
        authors_label.setAlignment(Qt.AlignCenter)
        authors_label.setFont(QFont("Segoe UI", 6))  # Reduzido de 7 para 6
        authors_label.setStyleSheet("color: #000000; margin-top: 2px;")
        layout.addWidget(authors_label)

        self.apply_styles()

    def apply_styles(self):
        self.setStyleSheet("""
            QFrame#mainContainer {
                background-color: white;
                border-radius: 12px;
            }
            QLabel#title { color: #1414b8; }
            QLabel#subtitle { color: #5f5f5f; }
            QFrame#separator {
                max-height: 1px; min-height: 1px; border: none;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(20,20,184,0),
                    stop:0.15 rgba(20,20,184,1),
                    stop:0.85 rgba(20,20,184,1),
                    stop:1 rgba(20,20,184,0)
                );
            }
                           
        """)

    def load_embasa_logo(self):
        """Carrega logo"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            image_path = os.path.join(current_dir, "geotecnologia_azul.png")
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(60, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)  # Reduzido
                self.logo_label.setPixmap(scaled_pixmap)
        except Exception as e:
            print(f"Erro ao carregar logo: {e}")

    def mousePressEvent(self, event):
        
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()