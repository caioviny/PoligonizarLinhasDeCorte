from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QComboBox, QPushButton, QFrame, QGraphicsDropShadowEffect,
                             QSizePolicy, QStyledItemDelegate, QListView, QApplication,QScrollArea,QTextEdit,QWidget)
from PyQt5.QtCore import Qt, QSize,QTimer,QPropertyAnimation,QEasingCurve
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPixmap, QPen, QBrush, QLinearGradient, QPalette,QIcon
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

class ReportDialog(QDialog):
    """Diálogo moderno para exibição de relatórios"""
    
    def __init__(self, titulo, mensagem, tipo="info", detalhes=None, parent=None):
        """
        Args:
            titulo (str): Título do relatório
            mensagem (str): Mensagem principal
            tipo (str): Tipo do relatório ('success', 'warning', 'error', 'info', 'partial')
            detalhes (dict): Dicionário com detalhes estruturados (opcional)
            parent: Widget pai
        """
        super().__init__(parent)
        self.tipo = tipo
        self.detalhes = detalhes
        
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMaximumWidth(800)
        
        self._setup_ui(titulo, mensagem)
        self._aplicar_estilo()
        self._animar_entrada()
    
    def _setup_ui(self, titulo, mensagem):
        """Configura a interface do diálogo"""
        layout_principal = QVBoxLayout()
        layout_principal.setSpacing(0)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        
        # ==================== HEADER ====================
        header = self._criar_header(titulo)
        layout_principal.addWidget(header)
        
        # ==================== CONTEÚDO ====================
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        conteudo_widget = QWidget()
        conteudo_layout = QVBoxLayout(conteudo_widget)
        conteudo_layout.setContentsMargins(30, 20, 30, 20)
        conteudo_layout.setSpacing(20)
        
        # Mensagem principal
        msg_label = QLabel(mensagem)
        msg_label.setWordWrap(True)
        msg_label.setObjectName("mensagemPrincipal")
        conteudo_layout.addWidget(msg_label)
        
        # Detalhes estruturados
        if self.detalhes:
            detalhes_widget = self._criar_detalhes_widget()
            conteudo_layout.addWidget(detalhes_widget)
        
        conteudo_layout.addStretch()
        scroll.setWidget(conteudo_widget)
        layout_principal.addWidget(scroll, 1)
        
        # ==================== FOOTER (BOTÕES) ====================
        footer = self._criar_footer()
        layout_principal.addWidget(footer)
        
        self.setLayout(layout_principal)
    
    def _criar_header(self, titulo):
        """Cria o header colorido do diálogo"""
        header_widget = QFrame()
        header_widget.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(30, 25, 30, 25)
        header_layout.setSpacing(15)
        
        # Ícone
        icone_label = QLabel()
        icone_label.setFixedSize(48, 48)
        icone_label.setScaledContents(True)
        icone_label.setPixmap(self._get_icone_pixmap())
        header_layout.addWidget(icone_label)
        
        # Título
        titulo_label = QLabel(titulo)
        titulo_label.setObjectName("tituloLabel")
        titulo_label.setWordWrap(True)
        header_layout.addWidget(titulo_label, 1)
        
        return header_widget
    
    def _criar_detalhes_widget(self):
        """Cria widget com detalhes estruturados"""
        container = QFrame()
        container.setObjectName("detalhesContainer")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Processadas
        if self.detalhes.get('processadas'):
            processadas_frame = self._criar_secao_processadas()
            layout.addWidget(processadas_frame)
        
        # Ignoradas
        if self.detalhes.get('ignoradas'):
            ignoradas_frame = self._criar_secao_ignoradas()
            layout.addWidget(ignoradas_frame)
        
        # Resumo
        resumo_frame = self._criar_secao_resumo()
        layout.addWidget(resumo_frame)
        
        return container
    
    def _criar_secao_processadas(self):
        """Cria seção de quadras/lotes processados"""
        frame = QFrame()
        frame.setObjectName("secaoProcessadas")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Título da seção
        titulo = QLabel(f"✅ {len(self.detalhes['processadas'])} Quadra(s) Processada(s)")
        titulo.setObjectName("tituloSecao")
        layout.addWidget(titulo)
        
        # Lista de itens
        for item in self.detalhes['processadas']:
            item_widget = self._criar_item_processado(item)
            layout.addWidget(item_widget)
        
        return frame
    
    def _criar_secao_ignoradas(self):
        """Cria seção de quadras/lotes ignorados"""
        frame = QFrame()
        frame.setObjectName("secaoIgnoradas")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        # Título da seção
        titulo = QLabel(f"❌ {len(self.detalhes['ignoradas'])} Quadra(s) Ignorada(s)")
        titulo.setObjectName("tituloSecao")
        layout.addWidget(titulo)
        
        # Lista de itens
        for item in self.detalhes['ignoradas']:
            item_widget = self._criar_item_ignorado(item)
            layout.addWidget(item_widget)
        
        return frame
    
    def _criar_secao_resumo(self):
        """Cria seção de resumo com estatísticas"""
        frame = QFrame()
        frame.setObjectName("secaoResumo")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)
        
        titulo = QLabel("📊 Resumo")
        titulo.setObjectName("tituloSecao")
        layout.addWidget(titulo)
        
        # Estatísticas
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # Total de quadras
        total_quadras = len(self.detalhes.get('processadas', [])) + len(self.detalhes.get('ignoradas', []))
        stats_layout.addWidget(self._criar_stat_card("Total de Quadras", str(total_quadras), "#5f6368"))
        
        # Total de lotes (se aplicável)
        if 'total_lotes' in self.detalhes:
            stats_layout.addWidget(self._criar_stat_card("Lotes Gerados", str(self.detalhes['total_lotes']), "#1a73e8"))
        
        # Total removidos (se aplicável)
        if 'total_removidos' in self.detalhes:
            stats_layout.addWidget(self._criar_stat_card("Lotes Removidos", str(self.detalhes['total_removidos']), "#ea4335"))
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        return frame
    
    def _criar_item_processado(self, item):
        """Cria widget para item processado"""
        widget = QFrame()
        widget.setObjectName("itemProcessado")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(10)
        
        # Inscrição
        inscricao_label = QLabel(f"<b>Insc:</b> {item['inscricao']}")
        inscricao_label.setObjectName("itemLabel")
        layout.addWidget(inscricao_label)
        
        layout.addStretch()
        
        # Resultado
        if 'lotes' in item:
            resultado_label = QLabel(f"<b>{item['lotes']}</b> lote(s)")
        elif 'lotes_removidos' in item:
            resultado_label = QLabel(f"<b>{item['lotes_removidos']}</b> removido(s)")
        else:
            resultado_label = QLabel("Processado")
        
        resultado_label.setObjectName("resultadoLabel")
        layout.addWidget(resultado_label)
        
        return widget
    
    def _criar_item_ignorado(self, item):
        """Cria widget para item ignorado"""
        widget = QFrame()
        widget.setObjectName("itemIgnorado")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        # Inscrição
        inscricao_label = QLabel(f"<b>Insc:</b> {item['inscricao']}")
        inscricao_label.setObjectName("itemLabel")
        layout.addWidget(inscricao_label)
        
        # Motivo
        motivo_label = QLabel(f"<i>Motivo:</i> {item['motivo']}")
        motivo_label.setObjectName("motivoLabel")
        motivo_label.setWordWrap(True)
        layout.addWidget(motivo_label)
        
        return widget
    
    def _criar_stat_card(self, titulo, valor, cor):
        """Cria card de estatística"""
        card = QFrame()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)
        
        valor_label = QLabel(valor)
        valor_label.setObjectName("statValor")
        valor_label.setStyleSheet(f"color: {cor}; font-size: 24px; font-weight: 700;")
        layout.addWidget(valor_label)
        
        titulo_label = QLabel(titulo)
        titulo_label.setObjectName("statTitulo")
        titulo_label.setStyleSheet("color: #5f6368; font-size: 12px;")
        layout.addWidget(titulo_label)
        
        return card
    
    def _criar_footer(self):
        """Cria footer com botões"""
        footer_widget = QFrame()
        footer_widget.setObjectName("footerFrame")
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(30, 20, 30, 20)
        footer_layout.setSpacing(10)
        
        footer_layout.addStretch()
        
        # Botão OK
        btn_ok = QPushButton("OK")
        btn_ok.setObjectName("btnOk")
        btn_ok.setMinimumWidth(120)
        btn_ok.setMinimumHeight(40)
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self.accept)
        footer_layout.addWidget(btn_ok)
        
        return footer_widget
    
    def _get_icone_pixmap(self):
        """Retorna ícone baseado no tipo"""
        size = 48
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Cores por tipo
        cores = {
            'success': QColor('#34a853'),
            'warning': QColor('#fbbc04'),
            'error': QColor('#ea4335'),
            'info': QColor('#1a73e8'),
            'partial': QColor('#ff6d00')
        }
        
        cor = cores.get(self.tipo, QColor('#1a73e8'))
        
        # Desenha círculo
        painter.setBrush(cor)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(4, 4, size-8, size-8)
        
        # Desenha ícone
        painter.setPen(QColor('#ffffff'))
        font = QFont('Arial', 20, QFont.Bold)
        painter.setFont(font)
        
        icones = {
            'success': '✓',
            'warning': '!',
            'error': '✕',
            'info': 'i',
            'partial': '≈'
        }
        
        icone = icones.get(self.tipo, 'i')
        painter.drawText(pixmap.rect(), Qt.AlignCenter, icone)
        
        painter.end()
        return pixmap
    
    def _aplicar_estilo(self):
        """Aplica stylesheet ao diálogo"""
        cores_header = {
            'success': '#e6f4ea',
            'warning': '#fef7e0',
            'error': '#fce8e6',
            'info': '#e8f0fe',
            'partial': '#fff3e0'
        }
        
        cores_border = {
            'success': '#34a853',
            'warning': '#fbbc04',
            'error': '#ea4335',
            'info': '#1a73e8',
            'partial': '#ff6d00'
        }
        
        header_bg = cores_header.get(self.tipo, '#e8f0fe')
        border_color = cores_border.get(self.tipo, '#1a73e8')
        
        stylesheet = f"""
            QDialog {{
                background-color: #ffffff;
            }}
            
            #headerFrame {{
                background-color: {header_bg};
                border-bottom: 3px solid {border_color};
            }}
            
            #tituloLabel {{
                font-size: 20px;
                font-weight: 700;
                color: #202124;
            }}
            
            #mensagemPrincipal {{
                font-size: 14px;
                color: #3c4043;
                line-height: 1.6;
            }}
            
            #detalhesContainer {{
                background-color: transparent;
            }}
            
            #secaoProcessadas, #secaoIgnoradas, #secaoResumo {{
                background-color: #f8f9fa;
                border: 1px solid #e1e4e8;
                border-radius: 8px;
            }}
            
            #tituloSecao {{
                font-size: 15px;
                font-weight: 600;
                color: #202124;
            }}
            
            #itemProcessado {{
                background-color: #ffffff;
                border: 1px solid #d1f4dd;
                border-left: 4px solid #34a853;
                border-radius: 6px;
            }}
            
            #itemIgnorado {{
                background-color: #ffffff;
                border: 1px solid #f9d6d2;
                border-left: 4px solid #ea4335;
                border-radius: 6px;
            }}
            
            #itemLabel {{
                font-size: 13px;
                color: #202124;
            }}
            
            #resultadoLabel {{
                font-size: 13px;
                color: #34a853;
                font-weight: 600;
            }}
            
            #motivoLabel {{
                font-size: 12px;
                color: #5f6368;
            }}
            
            #statCard {{
                background-color: #ffffff;
                border: 1px solid #e1e4e8;
                border-radius: 8px;
                min-width: 120px;
            }}
            
            #footerFrame {{
                background-color: #f8f9fa;
                border-top: 1px solid #e1e4e8;
            }}
            
            #btnOk {{
                background-color: {border_color};
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                padding: 10px 30px;
            }}
            
            #btnOk:hover {{
                background-color: {self._escurecer_cor(border_color)};
            }}
            
            #btnOk:pressed {{
                background-color: {self._escurecer_cor(border_color, 0.3)};
            }}
            
            QScrollBar:vertical {{
                background-color: #f1f3f4;
                width: 10px;
                border-radius: 5px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: #c5c9cd;
                border-radius: 5px;
                min-height: 30px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: #9aa0a6;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """
        
        self.setStyleSheet(stylesheet)
    
    def _escurecer_cor(self, cor_hex, fator=0.15):
        """Escurece uma cor hexadecimal"""
        cor = QColor(cor_hex)
        h, s, v, a = cor.getHsv()
        v = max(0, int(v * (1 - fator)))
        cor.setHsv(h, s, v, a)
        return cor.name()
    
    def _animar_entrada(self):
        """Anima a entrada do diálogo"""
        self.setWindowOpacity(0.0)
        
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(250)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.OutCubic)
        animation.start()
        
        # Guarda referência para não ser destruída
        self._animation = animation



def exibir_relatorio_processamento(relatorio, parent=None):
    """
    Exibe relatório de processamento de poligonização
    
    Args:
        relatorio (dict): Dicionário com estrutura:
            {
                'processadas': [{'inscricao': '...', 'id': ..., 'lotes': ...}, ...],
                'ignoradas': [{'inscricao': '...', 'id': ..., 'motivo': '...'}, ...],
                'total_lotes': int
            }
        parent: Widget pai
    
    Returns:
        int: Resultado do diálogo (QDialog.Accepted ou QDialog.Rejected)
    """
    # Determina tipo baseado no resultado
    if not relatorio['processadas']:
        tipo = 'warning'
        titulo = ' Nenhuma Quadra Processada'
        mensagem = 'Não foi possível processar nenhuma quadra. Verifique os detalhes abaixo.'
    elif relatorio['ignoradas']:
        tipo = 'partial'
        titulo = 'Processamento Parcial'
        mensagem = f"{len(relatorio['processadas'])} quadra(s) processada(s) com sucesso, mas {len(relatorio['ignoradas'])} foram ignoradas."
    else:
        tipo = 'success'
        titulo = ' Processamento Concluído'
        mensagem = f"Todas as {len(relatorio['processadas'])} quadra(s) foram processadas com sucesso!"
    
    dialog = ReportDialog(titulo, mensagem, tipo, relatorio, parent)
    return dialog.exec_()


def exibir_relatorio_remocao(relatorio, parent=None):
    """
    Exibe relatório de remoção de lotes
    
    Args:
        relatorio (dict): Dicionário com estrutura:
            {
                'processadas': [{'inscricao': '...', 'id': ..., 'lotes_removidos': ...}, ...],
                'ignoradas': [{'inscricao': '...', 'id': ..., 'motivo': '...'}, ...],
                'total_removidos': int
            }
        parent: Widget pai
    
    Returns:
        int: Resultado do diálogo (QDialog.Accepted ou QDialog.Rejected)
    """
    # Determina tipo baseado no resultado
    if not relatorio['processadas']:
        tipo = 'warning'
        titulo = '⚠️  Nenhum Lote Removido'
        mensagem = 'Não foi possível remover lotes. Verifique os detalhes abaixo.'
    elif relatorio['ignoradas']:
        tipo = 'partial'
        titulo = ' Remoção Parcial'
        mensagem = f"{relatorio['total_removidos']} lote(s) removido(s) de {len(relatorio['processadas'])} quadra(s), mas {len(relatorio['ignoradas'])} apresentaram problemas."
    else:
        tipo = 'success'
        titulo = ' Remoção Concluída'
        mensagem = f"Todos os {relatorio['total_removidos']} lote(s) foram removidos com sucesso de {len(relatorio['processadas'])} quadra(s)!"
    
    dialog = ReportDialog(titulo, mensagem, tipo, relatorio, parent)
    return dialog.exec_()



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
        self.lblQuadraSelecionada.setFont(QFont("Segoe UI", 9))  # Reduzido de 8 para 7
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