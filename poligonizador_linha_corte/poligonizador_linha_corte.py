# -*- coding: utf-8 -*-
"""
PoligonizadorLinhaCorte - Plugin QGIS Refatorado
Estrutura modular com separação de responsabilidades
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QToolBar
from qgis.core import (QgsProcessing, QgsProcessingMultiStepFeedback,
                       QgsProviderRegistry, QgsCoordinateReferenceSystem,
                       QgsProject, QgsVectorLayer, QgsWkbTypes, QgsMessageLog, Qgis,
                       QgsFeatureRequest, QgsGeometry, QgsPointXY)
from qgis.gui import QgsMapToolIdentify, QgsMapTool, QgsRubberBand
import processing
from .resources import *
from .poligonizador_linha_corte_dialog import PoligonizadorDialog, exibir_relatorio_processamento,exibir_relatorio_remocao
from .services.Notification import show_notification, get_notification_manager, clear_all_notifications, cancel_pending_notifications
import os.path
import traceback


# ==================== CLASSES AUXILIARES ====================

class DatabaseManager:
    """Gerenciador centralizado de operações com banco de dados"""
    
    def __init__(self):
        self.metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
        self._cached_connections = {}
    
    def get_connection_names(self):
        """Retorna lista de nomes de conexões disponíveis"""
        if not self.metadata:
            return []
        return list(self.metadata.connections().keys())
    
    def get_connection(self, connection_name):
        """Obtém conexão do PostgreSQL (com cache)"""
        if connection_name in self._cached_connections:
            return self._cached_connections[connection_name]
        
        if not self.metadata:
            raise Exception("Metadata PostgreSQL não disponível")
        
        connections = self.metadata.connections()
        if connection_name not in connections:
            raise Exception(f"Conexão '{connection_name}' não encontrada")
        
        conn = connections[connection_name]
        self._cached_connections[connection_name] = conn
        return conn
    
    def get_connection_config(self, connection_name):
        """Obtém configuração de uma conexão"""
        conn = self.get_connection(connection_name)
        return conn.configuration()
    
    def execute_sql(self, connection_name, query):
        """Executa query SQL"""
        conn = self.get_connection(connection_name)
        return conn.executeSql(query)
    
    def build_postgres_uri(self, connection_name, table_schema, table_name, geometry_column='geom'):
        """Constrói URI para camada PostgreSQL"""
        config = self.get_connection_config(connection_name)
        password_part = f"password='{config['password']}' " if config.get('password') else ''
        
        return (
            f"dbname='{config['database']}' "
            f"host='{config['host']}' "
            f"port='{config['port']}' "
            f"user='{config['username']}' "
            f"{password_part}"
            f"sslmode=disable key='id' srid=31984 type=Polygon "
            f"checkPrimaryKeyUnicity='1' "
            f'table="{table_schema}"."{table_name}" ({geometry_column})'
        )


class LayerManager:
    """Gerenciador centralizado de camadas do QGIS"""
    
    @staticmethod
    def get_layer_by_name(layer_name):
        """Obtém camada pelo nome"""
        layers = QgsProject.instance().mapLayersByName(layer_name)
        return layers[0] if layers else None
    
    @staticmethod
    def remove_layer_by_name(layer_name):
        """Remove camada pelo nome"""
        layers = QgsProject.instance().mapLayersByName(layer_name)
        for layer in layers:
            QgsProject.instance().removeMapLayer(layer.id())
    
    @staticmethod
    def add_temporary_layer(output_path, layer_name, layername="output"):
        """Adiciona camada temporária ao projeto"""
        LayerManager.remove_layer_by_name(layer_name)
        temp_layer = QgsVectorLayer(f"{output_path}|layername={layername}", layer_name, "ogr")
        if temp_layer.isValid():
            QgsProject.instance().addMapLayer(temp_layer)
            return temp_layer
        return None
    
    @staticmethod
    def reload_layer(layer_name):
        """Recarrega camada existente"""
        layer = LayerManager.get_layer_by_name(layer_name)
        if layer:
            layer.reload()
            return True
        return False
    
    @staticmethod
    def create_postgres_layer(uri, layer_name):
        """Cria e adiciona camada PostgreSQL"""
        layer = QgsVectorLayer(uri, layer_name, "postgres")
        if layer.isValid():
            QgsProject.instance().addMapLayer(layer)
            return layer
        return None


class QuadraManager:
    """Gerenciador de operações com quadras"""
    
    def __init__(self, layer_manager):
        self.layer_manager = layer_manager
        self.quadra_layer = None
    
    def get_quadra_layer(self):
        """Obtém camada de quadras"""
        if not self.quadra_layer or not self.quadra_layer.isValid():
            self.quadra_layer = self.layer_manager.get_layer_by_name('Quadra')
        return self.quadra_layer
    
    def get_selected_count(self):
        """Retorna quantidade de quadras selecionadas"""
        layer = self.get_quadra_layer()
        return layer.selectedFeatureCount() if layer else 0
    
    def get_selected_features(self):
        """Retorna features selecionadas"""
        layer = self.get_quadra_layer()
        return layer.getSelectedFeatures() if layer else []
    
    def clear_selection(self):
        """Limpa seleção de quadras"""
        layer = self.get_quadra_layer()
        if layer:
            layer.removeSelection()
    
    def get_quadra_info(self, feature):
        """Extrai informações da quadra"""
        fields = feature.fields().names()
        return {
            'inscricao': feature['ins_quadra'] if 'ins_quadra' in fields else f"ID {feature.id()}",
            'id': feature['id'] if 'id' in fields else feature.id(),
            'geometry': feature.geometry()
        }


class ProcessingPipeline:
    """Pipeline de processamento de poligonização"""
    
    @staticmethod
    def build_field_mappings():
        """Constrói mapeamento de campos para refactorfields"""
        quadra_fields = [
            ('id_localidade', 'id_localidade'),
            ('id_setor', 'id_setor'),
            ('id_bairro', 'id_bairro'),
            ('id', 'id_quadra'),
            ('ins_quadra', 'ins_quadra')
        ]
        
        mappings = [
            {
                'expression': f'aggregate(layer:=\'Quadra\', aggregate:=\'max\', '
                             f'expression:="{field}", filter:=intersects($geometry, geometry(@parent)))',
                'length': -1,
                'name': name,
                'precision': 0,
                'type': 4
            }
            for field, name in quadra_fields
        ]
        
        mappings.extend([
            {'expression': '\'Habitado\'', 'length': -1, 'name': 'sit_imovel', 'precision': 0, 'type': 10},
            {'expression': '@user_account_name || \' - \' || @user_full_name', 'length': -1, 'name': 'usuario', 'precision': 0, 'type': 10},
            {'expression': 'to_date(now())', 'length': -1, 'name': 'data_atual', 'precision': 0, 'type': 14}
        ])
        
        return mappings
    
    @staticmethod
    def executar_pipeline_completo(quadra_layer, linhas_layer, conexao_nome, feedback):
        """Executa o pipeline completo de poligonização"""
        outputs = {}
        
        # Step 0: Extrair feições selecionadas da quadra
        feedback.setCurrentStep(0)
        outputs['ExtrairFeicoes'] = processing.run('native:saveselectedfeatures', {
            'INPUT': quadra_layer,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 1: Extrair linhas dentro da quadra
        feedback.setCurrentStep(1)
        outputs['LinhasDentroQuadra'] = processing.run('native:extractbylocation', {
            'INPUT': linhas_layer,
            'INTERSECT': outputs['ExtrairFeicoes']['OUTPUT'],
            'PREDICATE': [0],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 2: Estender linhas
        feedback.setCurrentStep(2)
        outputs['EstenderLinhas'] = processing.run('native:extendlines', {
            'INPUT': outputs['LinhasDentroQuadra']['OUTPUT'],
            'START_DISTANCE': 0.3,
            'END_DISTANCE': 0.3,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 3: Polígonos para linhas
        feedback.setCurrentStep(3)
        outputs['PoligonosParaLinhas'] = processing.run('native:polygonstolines', {
            'INPUT': outputs['ExtrairFeicoes']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 4: Mesclar camadas
        feedback.setCurrentStep(4)
        outputs['MesclarCamadas'] = processing.run('native:mergevectorlayers', {
            'LAYERS': [outputs['EstenderLinhas']['OUTPUT'], outputs['PoligonosParaLinhas']['OUTPUT']],
            'CRS': None,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 5: Simplificar geometrias
        feedback.setCurrentStep(5)
        outputs['Simplificar'] = processing.run('native:simplifygeometries', {
            'INPUT': outputs['MesclarCamadas']['OUTPUT'],
            'METHOD': 0,
            'TOLERANCE': 0.001,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 6: Poligonizar
        feedback.setCurrentStep(6)
        outputs['Poligonizar'] = processing.run('native:polygonize', {
            'INPUT': outputs['Simplificar']['OUTPUT'],
            'KEEP_FIELDS': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 7: Remover duplicados 1
        feedback.setCurrentStep(7)
        outputs['RemoverDuplicados1'] = processing.run('native:removeduplicatevertices', {
            'INPUT': outputs['Poligonizar']['OUTPUT'],
            'TOLERANCE': 1e-06,
            'USE_Z_VALUE': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 8: Remover duplicados 2
        feedback.setCurrentStep(8)
        outputs['RemoverDuplicados2'] = processing.run('native:removeduplicatevertices', {
            'INPUT': outputs['RemoverDuplicados1']['OUTPUT'],
            'TOLERANCE': 1e-06,
            'USE_Z_VALUE': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 9: Ajustar geometrias
        feedback.setCurrentStep(9)
        outputs['AjustarGeometrias'] = processing.run('native:snapgeometries', {
            'INPUT': outputs['RemoverDuplicados2']['OUTPUT'],
            'REFERENCE_LAYER': outputs['RemoverDuplicados2']['OUTPUT'],
            'TOLERANCE': 0.0001,
            'BEHAVIOR': 0,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 10: Calcular área do lote
        feedback.setCurrentStep(10)
        outputs['CalcularAreaLote'] = processing.run('qgis:fieldcalculator', {
            'INPUT': outputs['AjustarGeometrias']['OUTPUT'],
            'FIELD_NAME': 'area_lote',
            'FIELD_TYPE': 0,
            'FIELD_LENGTH': 20,
            'FIELD_PRECISION': 2,
            'FORMULA': '$area',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 11: Calcular área da quadra
        feedback.setCurrentStep(11)
        outputs['CalcularAreaQuadra'] = processing.run('qgis:fieldcalculator', {
            'INPUT': outputs['ExtrairFeicoes']['OUTPUT'],
            'FIELD_NAME': 'area_quadra',
            'FIELD_TYPE': 0,
            'FIELD_LENGTH': 20,
            'FIELD_PRECISION': 2,
            'FORMULA': '$area',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 12: Join de áreas
        feedback.setCurrentStep(12)
        outputs['JoinAreas'] = processing.run('native:joinattributesbylocation', {
            'INPUT': outputs['CalcularAreaLote']['OUTPUT'],
            'JOIN': outputs['CalcularAreaQuadra']['OUTPUT'],
            'PREDICATE': [0],
            'JOIN_FIELDS': ['area_quadra'],
            'METHOD': 0,
            'DISCARD_NONMATCHING': False,
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 13: Filtrar lotes válidos
        feedback.setCurrentStep(13)
        outputs['FiltrarLotesValidos'] = processing.run('native:extractbyexpression', {
            'INPUT': outputs['JoinAreas']['OUTPUT'],
            'EXPRESSION': '"area_lote" < ("area_quadra" * 0.95)',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 14: Remover campos auxiliares
        feedback.setCurrentStep(14)
        outputs['RemoverCamposAux'] = processing.run('qgis:deletecolumn', {
            'INPUT': outputs['FiltrarLotesValidos']['OUTPUT'],
            'COLUMN': ['area_lote', 'area_quadra'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        # Step 15: Adicionar campos personalizados
        feedback.setCurrentStep(15)
        outputs['EditarCampos'] = processing.run('native:refactorfields', {
            'FIELDS_MAPPING': ProcessingPipeline.build_field_mappings(),
            'INPUT': outputs['RemoverCamposAux']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }, feedback=feedback)
        
        return outputs
    
    @staticmethod
    def importar_para_banco(output_layer, conexao_nome, feedback):
        """Importa lotes gerados para o banco de dados"""
        processing.run('gdal:importvectorintopostgisdatabaseavailableconnections', {
            'ADDFIELDS': False,
            'APPEND': True,
            'A_SRS': QgsCoordinateReferenceSystem('EPSG:31984'),
            'DATABASE': conexao_nome,
            'GEOCOLUMN': 'geom',
            'INPUT': output_layer,
            'LAUNDER': False,
            'OVERWRITE': False,
            'PRECISION': True,
            'PROMOTETOMULTI': False,
            'SCHEMA': 'comercial_umc',
            'TABLE': 'v_lote',
            'SKIPFAILURES': False
        }, feedback=feedback)


class ReportGenerator:
    """Gerador de relatórios"""
    
    @staticmethod
    def generate_processing_report(relatorio):
        """Gera relatório de processamento"""
        mensagem_partes = []
        
        if relatorio['processadas']:
            mensagem_partes.append(f"✅ {len(relatorio['processadas'])} QUADRA(S) PROCESSADA(S):")
            for item in relatorio['processadas']:
                mensagem_partes.append(f"   • Insc: {item['inscricao']} → {item['lotes']} lote(s)")
            mensagem_partes.append(f"\n📊 TOTAL: {relatorio['total_lotes']} lotes gerados")
        
        if relatorio['ignoradas']:
            mensagem_partes.append(f"\n\n❌ {len(relatorio['ignoradas'])} QUADRA(S) IGNORADA(S):")
            for item in relatorio['ignoradas']:
                mensagem_partes.append(f"   • Insc: {item['inscricao']}")
                mensagem_partes.append(f"     Motivo: {item['motivo']}")
        
        return "\n".join(mensagem_partes)
    
    @staticmethod
    def generate_removal_report(relatorio):
        """Gera relatório de remoção"""
        mensagem_partes = [
            "🗑️  RELATÓRIO DE REMOÇÃO DE LOTES",
            "=" * 50
        ]
        
        if relatorio['processadas']:
            mensagem_partes.append(f"\n✅ {len(relatorio['processadas'])} QUADRA(S) COM LOTES REMOVIDOS:")
            for item in relatorio['processadas']:
                mensagem_partes.append(
                    f"  • Quadra: {item['inscricao']} teve {item['lotes_removidos']} lote(s) removido(s)"
                )
            mensagem_partes.append(f"\n📊 TOTAL: {relatorio['total_removidos']} lotes removidos")
        
        if relatorio['ignoradas']:
            mensagem_partes.append(f"\n\n❌ {len(relatorio['ignoradas'])} QUADRA(S) SEM REMOÇÃO:")
            for item in relatorio['ignoradas']:
                mensagem_partes.append(f"  • Quadra: {item['inscricao']} Motivo: {item['motivo']}")
                print(item['motivo'])
        
        mensagem_partes.extend([
            f"\n{'=' * 50}",
            f"Total de quadras processadas: {len(relatorio['processadas']) + len(relatorio['ignoradas'])}"
        ])
        
        return "\n".join(mensagem_partes)


# ==================== MAP TOOL ====================

class MapToolSelectQuadra(QgsMapTool):
    """Ferramenta de seleção de quadras com polígono e CTRL+Clique"""

    def __init__(self, canvas, layer, callback, parent):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.callback_atualizar = callback
        self.parent_plugin = parent
        self.setCursor(Qt.CrossCursor)
        self.is_drawing_polygon = False
        self.polygon_points = []
        self.rubberBand = None
        self.primeira_selecao_ctrl = True
        # ✅ Inicializa o notification manager
        self.notification_mgr = get_notification_manager()
        self.criar_rubber_band()

    def criar_rubber_band(self):
        if not self.rubberBand:
            self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            self.rubberBand.setColor(Qt.red)
            self.rubberBand.setFillColor(Qt.transparent)
            self.rubberBand.setWidth(2)

    def _atualizar_barra_status(self):
        num = self.layer.selectedFeatureCount()
        self.parent_plugin.iface.messageBar().clearWidgets()
        self.parent_plugin.iface.messageBar().pushMessage(
            "Seleção de Quadras",
            f"📊 {num} selecionada(s) | 🖱️ Clique=polígono | ⌨️ CTRL+Clique=individual | ⏎ ENTER=confirmar",
            level=0, duration=0
        )

    def canvasPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier and event.button() == Qt.LeftButton:
            self.selecionar_individual(event)
        elif event.button() == Qt.LeftButton:
            self.adicionar_ponto_poligono(event)
        elif event.button() == Qt.RightButton:
            self.finalizar_poligono()

    def canvasMoveEvent(self, event):
        if self.is_drawing_polygon and self.polygon_points:
            if not self.rubberBand:
                self.criar_rubber_band()
            self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
            for point in self.polygon_points:
                self.rubberBand.addPoint(point, False)
            self.rubberBand.addPoint(self.toMapCoordinates(event.pos()), True)
            self.rubberBand.show()

    def adicionar_ponto_poligono(self, event):
        point = self.toMapCoordinates(event.pos())
        self.polygon_points.append(point)
        self.is_drawing_polygon = True
        if not self.rubberBand:
            self.criar_rubber_band()
        self.rubberBand.addPoint(point, False)
        self.rubberBand.show()
        if len(self.polygon_points) == 1:
            show_notification("Desenhando", "Continue clicando. Botão DIREITO finaliza.", "info", 2000)
        self.parent_plugin.iface.messageBar().clearWidgets()
        self.parent_plugin.iface.messageBar().pushMessage(
            "Desenhando",
            f"{len(self.polygon_points)} pontos | Botão DIREITO=finalizar | ⏎ ENTER=confirmar",
            level=0, duration=0
        )

    def finalizar_poligono(self):
        if len(self.polygon_points) < 3:
            if self.polygon_points:
                show_notification("Polígono Inválido", "Mínimo 3 pontos necessários.", "warning", 2000)
            self.limpar_poligono()
            return
        polygon_geom = QgsGeometry.fromPolygonXY([self.polygon_points])
        count = sum(1 for f in self.layer.getFeatures(QgsFeatureRequest().setFilterRect(polygon_geom.boundingBox()))
                   if polygon_geom.intersects(f.geometry()) and self.layer.select(f.id()) is None)
        if count:
            show_notification("Seleção Concluída", f"{count} quadra(s) selecionadas. ENTER confirma.", "info", 5000)
        self._atualizar_barra_status()
        self.limpar_poligono()

    def limpar_poligono(self):
        self.polygon_points.clear()
        self.is_drawing_polygon = False
        if self.rubberBand:
            self.rubberBand.reset(QgsWkbTypes.PolygonGeometry)
            self.rubberBand.hide()

    def selecionar_individual(self, event):
        results = QgsMapToolIdentify(self.canvas).identify(
            event.x(), event.y(), [self.layer], QgsMapToolIdentify.TopDownStopAtFirst
        )
        if results:
            feature = results[0].mFeature
            foi_adicionada = feature.id() not in self.layer.selectedFeatureIds()
            if foi_adicionada:
                self.layer.select(feature.id())
            else:
                self.layer.deselect(feature.id())
            if self.primeira_selecao_ctrl:
                self.primeira_selecao_ctrl = False
                show_notification("Seleção Individual",
                    "💡 CTRL+Clique adiciona/remove. ENTER finaliza.", "info", 2500)
            else:
                # ✅ USA show_notification com debounce
                show_notification(
                    "Seleção Atualizada",
                    f"Quadra {'adicionada' if foi_adicionada else 'removida'}. Total: {self.layer.selectedFeatureCount()}",
                    "info", 1200, debounce=500
                )
            self._atualizar_barra_status()
            if self.callback_atualizar:
                self.callback_atualizar()
        else:
            self.notification_mgr.cancel()
            show_notification("Nenhuma Quadra", "Nenhuma quadra neste ponto", "warning", 1500)

    def deactivate(self):
        self.notification_mgr.clear()  # Força limpeza ao desativar
        self.limpar_poligono()
        if self.rubberBand:
            self.canvas.scene().removeItem(self.rubberBand)
            self.rubberBand = None
        # Limpa barra de mensagens também
        if self.parent_plugin and self.parent_plugin.iface:
            self.parent_plugin.iface.messageBar().clearWidgets()
        super().deactivate()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.limpar_poligono()
            if self.layer:
                self.layer.removeSelection()
                self.notification_mgr.show_notification("Cancelado", "Polígono e seleção limpos", "info", 1200, 1000)
            self._atualizar_barra_status()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.notification_mgr.cancel()
            self.limpar_poligono()
            self.parent_plugin.confirmar_selecao_e_reabrir_dialogo()
            return
        event.ignore()


# ==================== PLUGIN PRINCIPAL ====================

class PoligonizadorLinhaCorte:
    """Plugin de Poligonização - Refatorado"""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.toolbar = None
        
        # Managers
        self.db_manager = DatabaseManager()
        self.layer_manager = LayerManager()
        self.quadra_manager = QuadraManager(self.layer_manager)
        # ✅ USA o NotificationManager do services/Notification.py
        self.notification_mgr = get_notification_manager()
        
        # Estado
        self.actions = []
        self.menu = self.tr(u'&Poligonizador de Linha de Corte')
        self.first_start = None
        self.map_tool = None
        self.previous_map_tool = None
        self.custom_map_tool = None
        
        self._setup_translator()

    def _setup_translator(self):
        """Configura tradutor"""
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', f'PoligonizadorLinhaCorte_{locale}.qm')
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def tr(self, message):
        return QCoreApplication.translate('PoligonizadorLinhaCorte', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        action = QAction(QIcon(icon_path), text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        if status_tip:
            action.setStatusTip(status_tip)
        if whats_this:
            action.setWhatsThis(whats_this)
        if add_to_toolbar:
            self.toolbar.addAction(action)
        if add_to_menu:
            self.iface.addPluginToVectorMenu(self.menu, action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Inicializa a interface do plugin"""
        # Procurar pelo toolbar UMCGEO existente
        self.toolbar = None
        for toolbar in self.iface.mainWindow().findChildren(QToolBar):
            if toolbar.objectName() == 'UMCGEO' or toolbar.windowTitle() == 'UMCGEO':
                self.toolbar = toolbar
                self._log("Toolbar UMCGEO encontrado!")
                break
        
        # Se não encontrar, criar um novo toolbar
        if self.toolbar is None:
            self.toolbar = self.iface.addToolBar('UMCGEO')
            self.toolbar.setObjectName('UMCGEO')
            self._log("Toolbar UMCGEO criado!")
        
        # Adicionar ação ao toolbar
        icon_path = os.path.join(self.plugin_dir, "icon.png")
        if not os.path.exists(icon_path):
            self._log(f"Ícone não encontrado em: {icon_path}", Qgis.Warning)
        
        self.add_action(
            icon_path,
            text=self.tr(u'Poligonizar Corte'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )
        self.first_start = True

    def _log(self, message, level=Qgis.Info):
            """Helper para logging"""
            QgsMessageLog.logMessage(message, 'OrganizadorDeLotes', level)
            
    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.menu, action)
            if self.toolbar:
                self.toolbar.removeAction(action)
        if self.previous_map_tool:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
        self.custom_map_tool = None

    def popular_conexoes(self):
        """Popula combo de conexões"""
        self.dlg.combo_conexao.clear()
        connection_names = self.db_manager.get_connection_names()
        
        for name in connection_names:
            self.dlg.combo_conexao.addItem(name, name)
        
        if not connection_names:
            QMessageBox.warning(self.dlg, "Aviso",
                "Nenhuma conexão PostgreSQL!\nConfigure no Gerenciador de Fontes.")

    def selecionar_quadra(self):
        """Inicia modo de seleção de quadras"""
        quadra_layer = self.quadra_manager.get_quadra_layer()
        if not quadra_layer:
            show_notification("Aviso", "Camada 'Quadra' não encontrada", "warning")
            return
        
        self.iface.setActiveLayer(quadra_layer)
        if not self.previous_map_tool:
            self.previous_map_tool = self.iface.mapCanvas().mapTool()
        
        self.custom_map_tool = MapToolSelectQuadra(
            self.iface.mapCanvas(), quadra_layer, self.atualizar_info_selecao, self
        )
        self.iface.mapCanvas().setMapTool(self.custom_map_tool)
        
        try:
            quadra_layer.selectionChanged.connect(self.atualizar_info_selecao)
        except:
            pass
        
        self.iface.messageBar().pushMessage(
            "Seleção Ativa",
            "🖱️ Polígono (botão direito finaliza) | ⌨️ CTRL+Clique individual | ⏎ ENTER confirma",
            level=0, duration=0
        )
        # ✅ USA show_notification com debounce
        show_notification(
            "Modo Seleção",
            "🖱️ Cliques múltiplos=polígono\n⌨️ CTRL+Clique=individual\n⏎ ENTER=confirmar",
            "info", 5000, debounce=1000
        )

    def confirmar_selecao_e_reabrir_dialogo(self):
        """Confirma seleção e reabre diálogo"""
        num = self.quadra_manager.get_selected_count()
        self.iface.messageBar().clearWidgets()
        
        quadra_layer = self.quadra_manager.get_quadra_layer()
        if quadra_layer:
            try:
                quadra_layer.selectionChanged.disconnect(self.atualizar_info_selecao)
            except:
                pass
        
        if self.previous_map_tool:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
            self.previous_map_tool = None
        self.custom_map_tool = None
        
        texto = f"📊 {num} quadra(s) selecionada(s)" if num else "Nenhuma quadra selecionada"
        if hasattr(self.dlg, 'lblQuadraSelecionada'):
            self.dlg.lblQuadraSelecionada.setText(texto)
        if hasattr(self.dlg, 'txtQuadraSelecionada'):
            self.dlg.txtQuadraSelecionada.setText(texto)
        
        show_notification(
            "Seleção Confirmada" if num else "Aviso",
            texto,
            "success" if num else "warning",
            3000 if num else 2000
        )
        
        # Usa QTimer para garantir que o diálogo apareça após todas as operações
        QTimer.singleShot(500, self._mostrar_dialogo)
    
    def _mostrar_dialogo(self):
        """Mostra o diálogo com foco garantido"""
        self.dlg.setWindowState(self.dlg.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()
        self.dlg.setFocus()

    def atualizar_info_selecao(self):
        pass

    def finalizar_selecao_quadras(self):
        """Finaliza seleção e inicia poligonização"""
        if self.quadra_manager.get_selected_count() == 0:
            show_notification("Aviso", "Selecione ao menos uma quadra!", "warning", 3000)
            return
        
        num = self.quadra_manager.get_selected_count()
        conexao = self.dlg.combo_conexao.currentData()
        if not conexao:
            show_notification("Aviso", "Selecione uma conexão PostgreSQL!", "warning", 3000)
            return
        
        resposta = QMessageBox.question(
            self.dlg, "Confirmar Poligonização",
            f"Executar poligonização de {num} quadra(s)?\n\nConexão: {conexao}\n",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if resposta == QMessageBox.No:
            show_notification("Cancelado", "Operação cancelada", "info", 2000)
            return
        
        self.dlg.close()
        self.executar_poligonizacao(conexao)
        self.resetar_estado_plugin()

    def on_cancelar(self):
        """Handler de cancelamento"""
        self.resetar_estado_plugin()
        self.dlg.close()
        show_notification("Cancelado", "Operação cancelada. Plugin resetado.", "info", 2000)

    def atualizar_camada_lotes(self, conexao_nome):
        """Atualiza ou cria camada de lotes"""
        try:
            existing = self.layer_manager.get_layer_by_name("Lote")
            if existing:
                existing.reload()
                self.iface.mapCanvas().refresh()
            else:
                uri = self.db_manager.build_postgres_uri(conexao_nome, "comercial_umc", "v_lote")
                layer = self.layer_manager.create_postgres_layer(uri, "Lote")
                if layer:
                    show_notification("Sucesso", f"Lote criado: {layer.featureCount()} feições", "success")
                else:
                    show_notification("Aviso", "Falha ao carregar Lote", "warning")
        except Exception as e:
            show_notification("Erro", f"Erro ao atualizar Lote: {e}", "error")

    def executar_poligonizacao(self, conexao_nome):
        """Executa pipeline de poligonização"""
        try:
            quadra_layer = self.quadra_manager.get_quadra_layer()
            if not quadra_layer or self.quadra_manager.get_selected_count() == 0:
                show_notification("Erro", "Nenhuma quadra selecionada!", "error")
                return [False, 0]
            
            linhas_layer = self.layer_manager.get_layer_by_name('Linhas_corte')
            if not linhas_layer:
                show_notification("Erro", "Camada 'Linhas_corte' não encontrada!", "error")
                return [False, 0]
            
            relatorio_quadras = {'processadas': [], 'ignoradas': [], 'total_lotes': 0}
            
            for quadra_feature in self.quadra_manager.get_selected_features():
                try:
                    quadra_info = self.quadra_manager.get_quadra_info(quadra_feature)
                    quadra_geom = quadra_info['geometry']
                    
                    # Verifica se há linhas de corte
                    linhas_dentro = [f for f in linhas_layer.getFeatures() 
                                   if f.geometry().intersects(quadra_geom)]
                    
                    if not linhas_dentro:
                        relatorio_quadras['ignoradas'].append({
                            'inscricao': quadra_info['inscricao'],
                            'id': quadra_info['id'],
                            'motivo': 'Sem linhas de corte'
                        })
                        continue
                    
                    # Seleciona quadra atual
                    quadra_layer.selectByIds([quadra_feature.id()])
                    
                    # Executa pipeline
                    lotes_gerados = self._processar_quadra_pipeline(
                        quadra_layer, linhas_layer, conexao_nome
                    )
                    
                    if lotes_gerados > 0:
                        relatorio_quadras['processadas'].append({
                            'inscricao': quadra_info['inscricao'],
                            'id': quadra_info['id'],
                            'lotes': lotes_gerados
                        })
                        relatorio_quadras['total_lotes'] += lotes_gerados
                    else:
                        relatorio_quadras['ignoradas'].append({
                            'inscricao': quadra_info['inscricao'],
                            'id': quadra_info['id'],
                            'motivo': 'Linhas não alcançam a borda'
                        })
                
                except Exception as e:
                    print(f"Erro ao processar quadra: {traceback.format_exc()}")
                    relatorio_quadras['ignoradas'].append({
                        'inscricao': quadra_info.get('inscricao', 'N/A'),
                        'id': quadra_info.get('id', 'N/A'),
                        'motivo': f'Erro: {str(e)[:50]}'
                    })
            
            if relatorio_quadras['total_lotes'] > 0:
                self.atualizar_camada_lotes(conexao_nome)
            
            return exibir_relatorio_processamento(relatorio_quadras)
        
        except Exception as e:
            show_notification("Erro", f"Falha na poligonização:\n{e}", "error")
            return [False, 0]

    def _processar_quadra_pipeline(self, quadra_layer, linhas_layer, conexao_nome):
        """Executa pipeline de processamento para uma quadra"""
        try:
            feedback = QgsProcessingMultiStepFeedback(16, None)
            
            # Executa pipeline completo usando a classe ProcessingPipeline
            outputs = ProcessingPipeline.executar_pipeline_completo(
                quadra_layer, linhas_layer, conexao_nome, feedback
            )
            
            lotes_gerados = outputs['EditarCampos']['OUTPUT'].featureCount()
            
            if lotes_gerados > 0:
                # Importa para o banco usando a classe ProcessingPipeline
                ProcessingPipeline.importar_para_banco(
                    outputs['EditarCampos']['OUTPUT'],
                    conexao_nome,
                    feedback
                )
                
                # Adiciona linhas temporárias
                self.layer_manager.add_temporary_layer(
                    outputs['EstenderLinhas']['OUTPUT'],
                    "Linhas_corte_processadas"
                )
            
            return lotes_gerados
            
        except Exception as e:
            print(f"Erro no pipeline: {traceback.format_exc()}")
            raise e

    def _exibir_relatorio_processamento(self, relatorio):
        """Exibe relatório de processamento"""
        mensagem = ReportGenerator.generate_processing_report(relatorio)
        
        if not relatorio['processadas']:
            exibir_relatorio_processamento()
            QMessageBox.information(None, "📊 Relatório de Processamento", mensagem)
            return [False, 0]
        elif relatorio['ignoradas']:
            QMessageBox.information(None, "📊 Relatório de Processamento", mensagem)
            return [True, 3]
        else:
            QMessageBox.information(None, "📊 Relatório de Processamento", mensagem)
            return [True, relatorio['total_lotes']]

    def remover_lotes_da_quadra_selecionada(self):
        try:
            if self.quadra_manager.get_selected_count() == 0:
                show_notification("Aviso", "Selecione ao menos uma quadra!", "warning", 3000)
                return

            num_quadras = self.quadra_manager.get_selected_count()
            conexao_nome = self.dlg.combo_conexao.currentData()

            if not conexao_nome:
                show_notification("Aviso", "Selecione uma conexão PostgreSQL!", "warning", 3000)
                return

            resposta = QMessageBox.question(
                self.dlg, "Confirmar Remoção",
                f"Remover todos os lotes de {num_quadras} quadra(s) selecionada(s)?\n\nConexão: {conexao_nome}\n",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if resposta == QMessageBox.No:
                show_notification("Cancelado", "Remoção cancelada.", "info", 2000)
                return

            self.dlg.close()
            relatorio_remocao = {'processadas': [], 'ignoradas': [], 'total_removidos': 0}

            print(f"\n{'='*60}")
            print(f"🗑️  INICIANDO REMOÇÃO DE LOTES")
            print(f"{'='*60}")

            for quadra_feature in self.quadra_manager.get_selected_features():
                try:
                    quadra_info = self.quadra_manager.get_quadra_info(quadra_feature)
                    quadra_id = quadra_info['id']
                    ins_quadra = quadra_info['inscricao']

                    print(f"\n📍 Processando Quadra: {ins_quadra} (ID: {quadra_id})")

                    # Obtém os IDs dos lotes associados à quadra
                    lotes_query = f"""
                        SELECT id FROM comercial_umc.v_lote
                        WHERE id_quadra = {quadra_id}
                    """
                    resultado_lotes = self.db_manager.execute_sql(conexao_nome, lotes_query)
                    ids_lotes = [str(lote[0]) for lote in resultado_lotes] if resultado_lotes else []

                    if not ids_lotes:
                        relatorio_remocao['ignoradas'].append({
                            'inscricao': ins_quadra,
                            'id': quadra_id,
                            'motivo': 'Nenhum lote encontrado'
                        })
                        print(f"   ⚠️  Ignorada - sem lotes")
                        continue

                    # Remove registros na tabela slote associados aos lotes
                    ids_lotes_str = ",".join(ids_lotes)
                    delete_slote_query = f"""
                        DELETE FROM comercial_umc.slote
                        WHERE id_lote IN ({ids_lotes_str})
                    """
                    self.db_manager.execute_sql(conexao_nome, delete_slote_query)
                    print(f"   ✅ Registros na tabela 'slote' removidos para {len(ids_lotes)} lote(s)")

                    # Remove cálculos de testada associados aos lotes
                    delete_calculo_query = f"""
                        DELETE FROM comercial_umc.v_calcular_testada
                        WHERE id_lote IN ({ids_lotes_str})
                    """
                    self.db_manager.execute_sql(conexao_nome, delete_calculo_query)
                    print(f"   ✅ Cálculos de testada removidos para {len(ids_lotes)} lote(s)")

                    # Remove os lotes
                    delete_query = f"""
                        DELETE FROM comercial_umc.v_lote
                        WHERE id IN ({ids_lotes_str})
                    """
                    self.db_manager.execute_sql(conexao_nome, delete_query)

                    # Verifica remoção
                    verificacao = self.db_manager.execute_sql(conexao_nome, f"""
                        SELECT COUNT(*) FROM comercial_umc.v_lote
                        WHERE id IN ({ids_lotes_str})
                    """)
                    lotes_restantes = verificacao[0][0] if verificacao and len(verificacao) > 0 else 0

                    if lotes_restantes == 0:
                        relatorio_remocao['processadas'].append({
                            'inscricao': ins_quadra,
                            'id': quadra_id,
                            'lotes_removidos': len(ids_lotes)
                        })
                        relatorio_remocao['total_removidos'] += len(ids_lotes)
                        print(f"   ✅ {len(ids_lotes)} lote(s) removido(s)")
                    else:
                        lotes_removidos = len(ids_lotes) - lotes_restantes
                        if lotes_removidos > 0:
                            relatorio_remocao['processadas'].append({
                                'inscricao': ins_quadra,
                                'id': quadra_id,
                                'lotes_removidos': lotes_removidos
                            })
                            relatorio_remocao['total_removidos'] += lotes_removidos

                        relatorio_remocao['ignoradas'].append({
                            'inscricao': ins_quadra,
                            'id': quadra_id,
                            'motivo': f'Remoção parcial: {lotes_restantes} lote(s) permaneceram'
                        })
                        print(f"   ⚠️  Remoção parcial")

                except Exception as e:
                    print(f"   ❌ Erro: {traceback.format_exc()}")
                    relatorio_remocao['ignoradas'].append({
                        'inscricao': quadra_info.get('inscricao', 'N/A'),
                        'id': quadra_info.get('id', 'N/A'),
                        'motivo': f'Erro: {str(e)[:50]}'
                    })

            print(f"{'='*60}\n")

            # Atualiza camada
            if relatorio_remocao['total_removidos'] > 0:
                self.layer_manager.reload_layer('Lote')
                self.iface.mapCanvas().refresh()

            # Exibe relatório
            exibir_relatorio_remocao(relatorio_remocao)
            self.resetar_estado_plugin()

        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ ERRO GERAL: {traceback.format_exc()}")
            print(f"{'='*60}\n")
            show_notification("Erro", f"Falha ao remover lotes: {str(e)[:100]}", "error", 5000)






    def _exibir_relatorio_remocao(self, relatorio):
        """Exibe relatório de remoção"""
        mensagem = ReportGenerator.generate_removal_report(relatorio)
        
        if not relatorio['processadas']:
            titulo = "⚠️  Nenhum Lote Removido"
            QMessageBox.warning(None, titulo, mensagem)
            print(f";{mensagem}")
        elif relatorio['ignoradas']:
            titulo = "📊 Remoção Parcial"
            QMessageBox.information(None, titulo, mensagem)
        else:
            titulo = "✅ Remoção Concluída"
            QMessageBox.information(None, titulo, mensagem)

    def resetar_estado_plugin(self):
        """Reseta estado do plugin"""
        try:
            # ✅ Limpa notificações usando função do services
            clear_all_notifications()
            
            self.quadra_manager.clear_selection()
            quadra_layer = self.quadra_manager.get_quadra_layer()
            if quadra_layer:
                try:
                    quadra_layer.selectionChanged.disconnect(self.atualizar_info_selecao)
                except:
                    pass
            
            self.custom_map_tool = None
            if self.previous_map_tool:
                self.iface.mapCanvas().setMapTool(self.previous_map_tool)
                self.previous_map_tool = None
            
            self.iface.messageBar().clearWidgets()
            
            if hasattr(self, 'dlg'):
                if hasattr(self.dlg, 'lblQuadraSelecionada'):
                    self.dlg.lblQuadraSelecionada.setText("Nenhuma quadra selecionada")
                if hasattr(self.dlg, 'txtQuadraSelecionada'):
                    self.dlg.txtQuadraSelecionada.setText("")
                if hasattr(self.dlg, 'combo_conexao') and self.dlg.combo_conexao.count():
                    self.dlg.combo_conexao.setCurrentIndex(0)
        except Exception as e:
            print(f"Erro ao resetar: {e}")

    def run(self):
        """Executa o plugin"""
        if self.first_start:
            self.first_start = False
            self.dlg = PoligonizadorDialog()
            
            # Conecta botões
            if hasattr(self.dlg, 'btn_selecionar'):
                self.dlg.btn_selecionar.clicked.connect(self.selecionar_quadra)
            if hasattr(self.dlg, 'btn_cancelar'):
                self.dlg.btn_cancelar.clicked.connect(self.on_cancelar)
            if hasattr(self.dlg, 'btn_ok'):
                self.dlg.btn_ok.clicked.connect(self.finalizar_selecao_quadras)
            if hasattr(self.dlg, 'btn_remover_lotes'):
                self.dlg.btn_remover_lotes.clicked.connect(self.remover_lotes_da_quadra_selecionada)
        
        self.resetar_estado_plugin()
        self.popular_conexoes()
        self.dlg.show()
        return {}