# -*- coding: utf-8 -*-
"""
PoligonizadorLinhaCorte - Plugin QGIS otimizado
Plugin para poligonizar linhas de corte e gerar lotes automaticamente
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox, QToolBar, QApplication
from qgis.core import (QgsProcessing, QgsProcessingMultiStepFeedback,
                       QgsProviderRegistry, QgsCoordinateReferenceSystem,
                       QgsProject, QgsVectorLayer, QgsWkbTypes,
                       QgsFeatureRequest, QgsGeometry, QgsPointXY)
from qgis.gui import QgsMapToolIdentify, QgsMapTool, QgsRubberBand
import processing
from .resources import *
from .poligonizador_linha_corte_dialog import PoligonizadorDialog
from .services.Notification import show_notification
import os.path
import math

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

        self.notification_timer = QTimer()
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(self._mostrar_notificacao_acumulada)
        self.pending_notification = None
        self.criar_rubber_band()

    def criar_rubber_band(self):
        if not self.rubberBand:
            self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
            self.rubberBand.setColor(Qt.red)
            self.rubberBand.setFillColor(Qt.transparent)
            self.rubberBand.setWidth(2)

    def _mostrar_notificacao_acumulada(self):
        if self.pending_notification:
            show_notification(**self.pending_notification)
            self.pending_notification = None

    def _agendar_notificacao(self, titulo, mensagem, tipo="info", duracao=1500, delay=300):
        self.pending_notification = {'titulo': titulo, 'mensagem': mensagem, 'tipo': tipo, 'duracao': duracao}

        self.notification_timer.stop()
        self.notification_timer.start(delay)

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
                self._agendar_notificacao(
                    "Seleção Atualizada",
                    f"Quadra {'adicionada' if foi_adicionada else 'removida'}. Total: {self.layer.selectedFeatureCount()}",
                    "info", 1200, 500
                )
            self._atualizar_barra_status()
            if self.callback_atualizar:
                self.callback_atualizar()
        else:
            self.notification_timer.stop()
            self.pending_notification = None
            show_notification("Nenhuma Quadra", "Nenhuma quadra neste ponto", "warning", 1500)

    def deactivate(self):
        if hasattr(self, 'notification_timer'):
            self.notification_timer.stop()
        self.limpar_poligono()
        if self.rubberBand:
            self.canvas.scene().removeItem(self.rubberBand)
            self.rubberBand = None
        super().deactivate()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.limpar_poligono()
            if self.layer:
                self.layer.removeSelection()
                self._agendar_notificacao("Cancelado", "Polígono e seleção limpos", "info", 1200, 1000)
            self._atualizar_barra_status()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.notification_timer.stop()
            self.limpar_poligono()
            self.parent_plugin.confirmar_selecao_e_reabrir_dialogo()
            return
        event.ignore()

class PoligonizadorLinhaCorte:
    """Plugin de Poligonização"""

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.toolbar = None
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(self.plugin_dir, 'i18n', f'PoligonizadorLinhaCorte_{locale}.qm')
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)
        self.actions = []
        self.menu = self.tr(u'&Poligonizador de Linha de Corte')
        self.first_start = None
        self.quadra_selecionada = None
        self.map_tool = None
        self.previous_map_tool = None
        self.custom_map_tool = None
        self.quadra_layer_ref = None
        self.notification_timer = QTimer()
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(self._mostrar_notificacao_acumulado)
        self.pending_notification = None

    def _mostrar_notificacao_acumulado(self):
        if self.pending_notification:
            show_notification(**self.pending_notification)
            self.pending_notification = None

    def _agendar_notificacao(self, titulo, mensagem, tipo="info", duracao=1500, delay=300):
        self.pending_notification = {'titulo': titulo, 'mensagem': mensagem, 'tipo': tipo, 'duracao': duracao}
        self.notification_timer.stop()
        self.notification_timer.start(delay)

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
        self.toolbar = next((tb for tb in self.iface.mainWindow().findChildren(QToolBar)
                            if tb.objectName() == 'UMCGEO' or tb.windowTitle() == 'UMCGEO'), None)
        if not self.toolbar:
            self.toolbar = self.iface.addToolBar('UMCGEO')
            self.toolbar.setObjectName('UMCGEO')
        self.add_action(
            ':/plugins/poligonizador_linha_corte/icon.png',
            text=self.tr(u'Desenhar Lote'),
            callback=self.run,
            parent=self.iface.mainWindow()
        )
        self.first_start = True

    def unload(self):
        for action in self.actions:
            self.iface.removePluginVectorMenu(self.tr(u'&Poligonizador de Linha de Corte'), action)
            if self.toolbar:
                self.toolbar.removeAction(action)
        if self.previous_map_tool:
            self.iface.mapCanvas().setMapTool(self.previous_map_tool)
        self.custom_map_tool = None

    def popular_conexoes(self):
        self.dlg.combo_conexao.clear()
        metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
        if metadata:
            for name in metadata.connections().keys():
                self.dlg.combo_conexao.addItem(name, name)
        if self.dlg.combo_conexao.count() == 0:
            QMessageBox.warning(self.dlg, "Aviso",
                "Nenhuma conexão PostgreSQL!\nConfigure no Gerenciador de Fontes.")

    def selecionar_quadra(self):
        quadra_layers = QgsProject.instance().mapLayersByName('Quadra')
        if not quadra_layers:
            show_notification("Aviso", "Camada 'Quadra' não encontrada", "warning")
            return
        quadra_layer = quadra_layers[0]
        self.iface.setActiveLayer(quadra_layer)
        if not self.previous_map_tool:
            self.previous_map_tool = self.iface.mapCanvas().mapTool()
        self.custom_map_tool = MapToolSelectQuadra(
            self.iface.mapCanvas(), quadra_layer, self.atualizar_info_selecao, self
        )
        self.iface.mapCanvas().setMapTool(self.custom_map_tool)
        self.quadra_layer_ref = quadra_layer
        try:
            quadra_layer.selectionChanged.connect(self.atualizar_info_selecao)
        except:
            pass
        self.iface.messageBar().pushMessage(
            "Seleção Ativa",
            "🖱️ Polígono (botão direito finaliza) | ⌨️ CTRL+Clique individual | ⏎ ENTER confirma",
            level=0, duration=0
        )
        self._agendar_notificacao(
                        "Modo Seleção",
                        f"🖱️ Cliques múltiplos=polígono\n⌨️ CTRL+Clique=individual\n⏎ ENTER=confirmar",
                        "info", 5000,1000
                    )

    def confirmar_selecao_e_reabrir_dialogo(self):
        quadra_layers = QgsProject.instance().mapLayersByName('Quadra')
        if not quadra_layers:
            return
        num = quadra_layers[0].selectedFeatureCount()
        self.iface.messageBar().clearWidgets()
        try:
            quadra_layers[0].selectionChanged.disconnect(self.atualizar_info_selecao)
        except:
            pass
        if hasattr(self, 'quadra_layer_ref'):
            del self.quadra_layer_ref
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
            f"📊 {num} quadra(s) selecionada(s)" if num else "Nenhuma quadra selecionada",
            "success" if num else "warning", 3000 if num else 2000
        )
        self.dlg.show()
        self.dlg.raise_()
        self.dlg.activateWindow()

    def atualizar_info_selecao(self):
        pass

    def finalizar_selecao_quadras(self):
        quadra_layers = QgsProject.instance().mapLayersByName('Quadra')
        if not quadra_layers or quadra_layers[0].selectedFeatureCount() == 0:
            show_notification("Aviso", "Selecione ao menos uma quadra!", "warning", 3000)
            return
        num = quadra_layers[0].selectedFeatureCount()
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
        self.resetar_estado_plugin()
        self.dlg.close()
        show_notification("Cancelado", "Operação cancelada. Plugin resetado.", "info", 2000)

    def adicionar_linhas_corte_temporarias(self, linhas_output):
        try:
            for layer in QgsProject.instance().mapLayersByName("Linhas_corte_processadas"):
                QgsProject.instance().removeMapLayer(layer.id())
            temp_layer = QgsVectorLayer(f"{linhas_output}|layername=output", "Linhas_corte_processadas", "ogr")
            if temp_layer.isValid():
                QgsProject.instance().addMapLayer(temp_layer)
                self.iface.messageBar().pushMessage("Info", f"Linhas processadas: {temp_layer.featureCount()}", level=0, duration=3)
            else:
                print('Falha ao criar camada temporária')
        except Exception as e:
            show_notification("ERRO", f"Erro nas linhas temporárias: {e}", "error")

    def atualizar_camada_lotes(self, lotes_gerados):
        try:
            conexao_nome = self.dlg.combo_conexao.currentData()
            if not conexao_nome:
                show_notification("Atenção", "Conexão não encontrada", "warning")
                return
            metadata = QgsProviderRegistry.instance().providerMetadata('postgres')
            if not metadata:
                return
            connections = metadata.connections()
            if conexao_nome not in connections:
                return
            config = connections[conexao_nome].configuration()
            existing = QgsProject.instance().mapLayersByName("Lote")
            if existing:
                existing[0].reload()
                self.iface.mapCanvas().refresh()
            else:
                uri = (f"dbname='{config['database']}' host='{config['host']}' "
                      f"port='{config['port']}' user='{config['username']}' "
                      f"{'password=' + config['password'] + ' ' if config.get('password') else ''}"
                      f"sslmode=disable key='id' srid=31984 type=Polygon "
                      f"checkPrimaryKeyUnicity='1' "
                      f'table="comercial_umc"."v_lote" (geom)')
                layer = QgsVectorLayer(uri, "Lote", "postgres")
                if layer.isValid():
                    QgsProject.instance().addMapLayer(layer)
                    show_notification("Sucesso", f"Lote criado: {layer.featureCount()} feições", "success")
                else:
                    show_notification("Aviso", f"Falha ao carregar Lote:\n{layer.error().message()}", "warning")
        except Exception as e:
            show_notification("Erro", f"Erro ao atualizar Lote: {e}", "error")

    def executar_poligonizacao(self, conexao_nome):
        try:
            quadra_layer = QgsProject.instance().mapLayersByName('Quadra')
            if not quadra_layer:
                show_notification("Erro", "Camada 'Quadra' não encontrada!", "error")
                return [False, 0]
            quadra_layer = quadra_layer[0]
            if quadra_layer.selectedFeatureCount() == 0:
                show_notification("Aviso", "Selecione ao menos uma quadra!", "warning")
                return [False, 0]
            linhas = QgsProject.instance().mapLayersByName('Linhas_corte')
            if not linhas:
                show_notification("Erro", "Camada 'Linhas_corte' não encontrada!", "error")
                return [False, 0]
            linhas_layer = linhas[0]
            relatorio_quadras = {'processadas': [], 'ignoradas': [], 'total_lotes': 0}

            for quadra_feature in quadra_layer.getSelectedFeatures():
                try:
                    quadra_geom = quadra_feature.geometry()
                    ins_quadra = quadra_feature['ins_quadra'] if 'ins_quadra' in quadra_feature.fields().names() else f"ID {quadra_feature.id()}"
                    quadra_id = quadra_feature['id'] if 'id' in quadra_feature.fields().names() else quadra_feature.id()

                    linhas_dentro = [f for f in linhas_layer.getFeatures() if f.geometry().intersects(quadra_geom)]

                    if not linhas_dentro:
                        relatorio_quadras['ignoradas'].append({'inscricao': ins_quadra, 'id': quadra_id, 'motivo': 'Sem linhas de corte'})
                        continue

                    quadra_layer.selectByIds([quadra_feature.id()])
                    feedback = QgsProcessingMultiStepFeedback(16, None)
                    outputs = {}

                    steps = [
                        ('native:saveselectedfeatures', {'INPUT': quadra_layer}, 'ExtrairFeicoes'),
                        ('native:extractbylocation', {'INPUT': linhas_layer, 'INTERSECT': 'ExtrairFeicoes', 'PREDICATE': [0]}, 'LinhasDentroQuadra'),
                        ('native:extendlines', {'INPUT': 'LinhasDentroQuadra', 'START_DISTANCE': 0.3, 'END_DISTANCE': 0.3}, 'EstenderLinhas'),
                        ('native:polygonstolines', {'INPUT': 'ExtrairFeicoes'}, 'PoligonosParaLinhas'),
                        ('native:mergevectorlayers', {'LAYERS': ['EstenderLinhas', 'PoligonosParaLinhas'], 'CRS': None}, 'MesclarCamadas'),
                        ('native:simplifygeometries', {'INPUT': 'MesclarCamadas', 'METHOD': 0, 'TOLERANCE': 0.001}, 'Simplificar'),
                        ('native:polygonize', {'INPUT': 'Simplificar', 'KEEP_FIELDS': False}, 'Poligonizar'),
                        ('native:removeduplicatevertices', {'INPUT': 'Poligonizar', 'TOLERANCE': 1e-06, 'USE_Z_VALUE': False}, 'RemoverDuplicados1'),
                        ('native:removeduplicatevertices', {'INPUT': 'RemoverDuplicados1', 'TOLERANCE': 1e-06, 'USE_Z_VALUE': False}, 'RemoverDuplicados2'),
                        ('native:snapgeometries', {'INPUT': 'RemoverDuplicados2', 'REFERENCE_LAYER': 'RemoverDuplicados2', 'TOLERANCE': 0.0001, 'BEHAVIOR': 0}, 'AjustarGeometrias'),
                        ('qgis:fieldcalculator', {'INPUT': 'AjustarGeometrias', 'FIELD_NAME': 'area_lote', 'FIELD_TYPE': 0, 'FIELD_LENGTH': 20, 'FIELD_PRECISION': 2, 'FORMULA': '$area'}, 'CalcularAreaLote'),
                        ('qgis:fieldcalculator', {'INPUT': 'ExtrairFeicoes', 'FIELD_NAME': 'area_quadra', 'FIELD_TYPE': 0, 'FIELD_LENGTH': 20, 'FIELD_PRECISION': 2, 'FORMULA': '$area'}, 'CalcularAreaQuadra'),
                        ('native:joinattributesbylocation', {'INPUT': 'CalcularAreaLote', 'JOIN': 'CalcularAreaQuadra', 'PREDICATE': [0], 'JOIN_FIELDS': ['area_quadra'], 'METHOD': 0, 'DISCARD_NONMATCHING': False, 'PREFIX': ''}, 'JoinAreas'),
                        ('native:extractbyexpression', {'INPUT': 'JoinAreas', 'EXPRESSION': '"area_lote" < ("area_quadra" * 0.95)'}, 'FiltrarLotesValidos'),
                        ('qgis:deletecolumn', {'INPUT': 'FiltrarLotesValidos', 'COLUMN': ['area_lote', 'area_quadra']}, 'RemoverCamposAux'),
                    ]

                    for i, (alg, params, key) in enumerate(steps):
                        feedback.setCurrentStep(i)
                        for k, v in params.items():
                            if isinstance(v, str) and v in outputs:
                                params[k] = outputs[v]['OUTPUT']
                            elif isinstance(v, list):
                                params[k] = [outputs[x]['OUTPUT'] if x in outputs else x for x in v]
                        params['OUTPUT'] = QgsProcessing.TEMPORARY_OUTPUT
                        outputs[key] = processing.run(alg, params, feedback=feedback)

                    feedback.setCurrentStep(15)
                    fields_mapping = [
                        {'expression': f'aggregate(layer:=\'Quadra\', aggregate:=\'max\', expression:="{field}", filter:=intersects($geometry, geometry(@parent)))',
                        'length': -1, 'name': name, 'precision': 0, 'type': 4}
                        for field, name in [('id_localidade', 'id_localidade'), ('id_setor', 'id_setor'),
                                        ('id_bairro', 'id_bairro'), ('id', 'id_quadra'), ('ins_quadra', 'ins_quadra')]
                    ] + [
                        {'expression': '\'Habitado\'', 'length': -1, 'name': 'sit_imovel', 'precision': 0, 'type': 10},
                        {'expression': '@user_account_name || \' - \' || @user_full_name', 'length': -1, 'name': 'usuario', 'precision': 0, 'type': 10},
                        {'expression': 'to_date(now())', 'length': -1, 'name': 'data_atual', 'precision': 0, 'type': 14}
                    ]

                    outputs['EditarCampos'] = processing.run('native:refactorfields', {
                        'FIELDS_MAPPING': fields_mapping,
                        'INPUT': outputs['RemoverCamposAux']['OUTPUT'],
                        'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                    }, feedback=feedback)

                    lotes_gerados = outputs['EditarCampos']['OUTPUT'].featureCount()

                    if lotes_gerados > 0:
                        processing.run('gdal:importvectorintopostgisdatabaseavailableconnections', {
                            'ADDFIELDS': False, 'APPEND': True, 'A_SRS': QgsCoordinateReferenceSystem('EPSG:31984'),
                            'DATABASE': conexao_nome, 'GEOCOLUMN': 'geom', 'INPUT': outputs['EditarCampos']['OUTPUT'],
                            'LAUNDER': False, 'OVERWRITE': False, 'PRECISION': True, 'PROMOTETOMULTI': False,
                            'SCHEMA': 'comercial_umc', 'TABLE': 'v_lote', 'SKIPFAILURES': False
                        }, feedback=feedback)

                        relatorio_quadras['processadas'].append({'inscricao': ins_quadra, 'id': quadra_id, 'lotes': lotes_gerados})
                        relatorio_quadras['total_lotes'] += lotes_gerados
                        self.adicionar_linhas_corte_temporarias(outputs['EstenderLinhas']['OUTPUT'])
                    else:
                        relatorio_quadras['ignoradas'].append({'inscricao': ins_quadra, 'id': quadra_id, 'motivo': 'Linhas não alcançam a borda (lote=quadra)'})

                except Exception as e:
                    import traceback
                    erro_detalhado = traceback.format_exc()
                    print(f"Erro ao processar quadra {ins_quadra}: {erro_detalhado}")
                    relatorio_quadras['ignoradas'].append({'inscricao': ins_quadra, 'id': quadra_id, 'motivo': f'Erro: {str(e)[:50]}'})

            if relatorio_quadras['total_lotes'] > 0:
                self.atualizar_camada_lotes(relatorio_quadras['total_lotes'])

            return self._gerar_relatorio_final(relatorio_quadras)

        except Exception as e:
            import traceback
            show_notification("Erro", f"Falha na poligonização:\n{e}\n{traceback.format_exc()}", "error")
            return [False, 0]

    def _gerar_relatorio_final(self, relatorio):
        total_selecionadas = len(relatorio['processadas']) + len(relatorio['ignoradas'])
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
        mensagem_completa = "\n".join(mensagem_partes)
        if not relatorio['processadas']:
            QMessageBox.information(None, "📊 Relatório de Processamento", mensagem_completa)
            return [False, 0]
        elif relatorio['ignoradas']:
            QMessageBox.information(None, "📊 Relatório de Processamento", mensagem_completa)
            return [True,  3]
        else:
            QMessageBox.information(None, "📊 Relatório de Processamento", mensagem_completa)
            return [True, relatorio['total_lotes']]

    def resetar_estado_plugin(self):
        try:
            quadra_layers = QgsProject.instance().mapLayersByName('Quadra')
            if quadra_layers:
                quadra_layers[0].removeSelection()
                try:
                    quadra_layers[0].selectionChanged.disconnect(self.atualizar_info_selecao)
                except:
                    pass
            if hasattr(self, 'quadra_layer_ref'):
                del self.quadra_layer_ref
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
        if self.first_start:
            self.first_start = False
            self.dlg = PoligonizadorDialog()
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

    def remover_lotes_da_quadra_selecionada(self):
        
        try:
            # Verifica se há quadras selecionadas
            quadra_layers = QgsProject.instance().mapLayersByName('Quadra')
            if not quadra_layers or quadra_layers[0].selectedFeatureCount() == 0:
                show_notification("Aviso", "Selecione ao menos uma quadra!", "warning", 3000)
                return

            # Verifica se a camada de lotes existe
            lote_layers = QgsProject.instance().mapLayersByName('Lote')
            if not lote_layers:
                show_notification("Erro", "Camada 'Lote' não encontrada!", "error")
                return

            lote_layer = lote_layers[0]
            quadra_layer = quadra_layers[0]

            # Confirmação do usuário
            resposta = QMessageBox.question(
                self.dlg, "Confirmar Remoção",
                f"Remover todos os lotes das {quadra_layer.selectedFeatureCount()} quadra(s) selecionada(s)?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )

            if resposta == QMessageBox.No:
                show_notification("Cancelado", "Remoção cancelada.", "info", 2000)
                return

            # Inicia a edição da camada de lotes
            lote_layer.startEditing()

            # Itera sobre as quadras selecionadas
            quadras_selecionadas = quadra_layer.getSelectedFeatures()
            lotes_removidos = 0

            for quadra in quadras_selecionadas:
                quadra_geom = quadra.geometry()
                

                # Seleciona todos os lotes que intersectam a quadra
                lote_layer.selectByExpression(f"intersects($geometry, geom_from_wkt('{quadra_geom.asWkt()}'))")

                # Remove os lotes selecionados
                if lote_layer.selectedFeatureCount() > 0:
                    print(lote_layer.selectedFeatureCount())
                    lotes_removidos += lote_layer.selectedFeatureCount()
                    lote_layer.deleteSelectedFeatures()
                    
            
            # Salva as alterações
            lote_layer.commitChanges()

            # Atualiza a camada
            lote_layer.triggerRepaint()
            QgsProject.instance().layerTreeRoot().findLayer(lote_layer.id()).setItemVisibilityChecked(True)

            # Exibe notificação de sucesso
            show_notification("Sucesso", f"{lotes_removidos} lote(s) removido(s).", "success", 3000)

        except Exception as e:
            show_notification("Erro", f"Falha ao remover lotes: {e}", "error")
