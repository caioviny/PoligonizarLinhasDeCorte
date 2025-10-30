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
        self.setMinimumHeight(40)
        self.setMaxVisibleItems(6)
        self.setFont(QFont("Segoe UI", 9))
        view = QListView(self)
        view.setFont(QFont("Segoe UI", 9))
        self.setView(view)
        self.setStyleSheet("""
            QComboBox {
                background-color: #f8f9fa;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                padding: 8px 12px;
                padding-right: 30px;
                color: #000000;
                font-size: 9pt;
                font-family: "Segoe UI";
            }
            QComboBox:hover { background-color: #ffffff; border: 2px solid #2196f3; }
            QComboBox:focus { border: 2px solid #2196f3; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow {
                image: none; width: 0; height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #78909c;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                padding: 6px;
                color: #000000;
                font-size: 9pt;
                outline: none;
            }
            QComboBox QAbstractItemView::item { min-height: 30px; padding-left: 10px; }
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

    def __init__(self, text, primary=False, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self.setMouseTracking(True)
        self._hover = False
        self.setFont(QFont("Segoe UI", 9, QFont.DemiBold))

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
        if self.primary:
            if self.isDown():
                painter.fillPath(path, QColor("#0056b3"))
            elif self._hover:
                painter.fillPath(path, QColor("#0066cc"))
            else:
                painter.fillPath(path, QColor("#0073e6"))
        else:
            if self.isDown():
                painter.fillPath(path, QColor(222, 226, 230))
            elif self._hover:
                painter.fillPath(path, QColor(233, 236, 239))
            else:
                painter.fillPath(path, QColor(200, 200, 200))
        painter.setPen(QColor(255, 255, 255) if self.primary else QColor(73, 80, 87))
        font = QFont("Segoe UI", 9, QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, self.text())

class PoligonizadorDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Poligonizador de Linha de Corte")
        self.setFixedSize(400, 400)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setup_ui()
        self.load_embasa_logo()

    def setup_ui(self):
        main_container = QFrame(self)
        main_container.setObjectName("mainContainer")
        main_container.setGeometry(10, 10, 380, 380)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(3)
        shadow.setColor(QColor(0, 0, 0, 40))
        main_container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(main_container)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.logo_label = QLabel(main_container)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setMaximumHeight(30)
        self.logo_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.logo_label)
        # Header
        header_layout = QHBoxLayout()
        title_container = QVBoxLayout()
        title_container.setSpacing(2)

        title = QLabel("Poligonizador")
        title.setObjectName("title")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))

        subtitle = QLabel("Configure a conexão e selecione a área")
        subtitle.setObjectName("subtitle")
        subtitle.setFont(QFont("Segoe UI", 8))

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
        conn_label.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        conn_label.setStyleSheet("color: #37474f; margin-top: 3px;")
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

        layout.addSpacing(6)

        # Label quadra
        info_label = QLabel("Quadra Selecionada")
        info_label.setFont(QFont("Segoe UI", 9, QFont.DemiBold))
        info_label.setStyleSheet("color: #37474f; margin-top: 3px;")
        layout.addWidget(info_label)

        # Info quadra
        self.lblQuadraSelecionada = QLabel("Nenhuma quadra selecionada")
        self.lblQuadraSelecionada.setObjectName("lblQuadra")
        self.lblQuadraSelecionada.setFont(QFont("Segoe UI", 8))
        self.lblQuadraSelecionada.setStyleSheet("""
            background-color: #f0f7ff;
            border: 1px solid #bbdefb;
            border-radius: 8px;
            padding: 8px 10px;
            color: #1976d2;
        """)
        self.lblQuadraSelecionada.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lblQuadraSelecionada)

        layout.addSpacing(6)

        # Botão selecionar
        self.btn_selecionar = ModernButton("Selecionar Quadra", primary=True)
        self.btn_selecionar.setObjectName("btnSelecionar")
        self.btn_selecionar.setCursor(Qt.PointingHandCursor)
        self.btn_selecionar.setFixedHeight(35)
        layout.addWidget(self.btn_selecionar)

        layout.addStretch()

        # Logo
     

        # Botões ação
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        self.btn_cancelar = ModernButton("Cancelar")
        self.btn_cancelar.setObjectName("btnCancelar")
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.setFixedHeight(30)
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_ok = ModernButton("Poligonizar", primary=True)
        self.btn_ok.setObjectName("btnOk")
        self.btn_ok.setCursor(Qt.PointingHandCursor)
        self.btn_ok.setFixedHeight(30)
        

        buttons_layout.addWidget(self.btn_cancelar)
        buttons_layout.addWidget(self.btn_ok)
        layout.addLayout(buttons_layout)

        authors_label = QLabel("Desenvolvido por Lucas, Tavares e Caio")
        authors_label.setAlignment(Qt.AlignCenter)
        authors_label.setFont(QFont("Segoe UI", 7))
        authors_label.setStyleSheet("color: #000000; margin-top: 4px;")
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
                scaled_pixmap = pixmap.scaled(70, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
