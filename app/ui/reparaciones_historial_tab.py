"""
Pestaña para historial de reparaciones (SAT)
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLineEdit, QLabel,
                             QHeaderView, QDateEdit, QGroupBox, QComboBox,
                             QFileDialog, QGridLayout, QSpinBox)
from qfluentwidgets import SearchLineEdit
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont
from app.db.database import Database
from app.i18n import tr
from app.modules.reparacion_manager import ReparacionManager
from app.ui.widgets.pagination_widget import PaginationWidget
from config import REPAIR_STATUSES
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel, apply_btn_success, set_btn_icon
from qfluentwidgets import FluentIcon
import os
import shutil


class ReparacionesHistorialTab(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.reparacion_manager = ReparacionManager(self.db)
        self._filtros_actuales = None
        self.setup_ui()
        self.cargar_reparaciones()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(tr("Historial de Reparaciones"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Filtros
        filtros_title = QLabel(tr("FILTROS DE BÚSQUEDA"))
        filtros_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; padding: 5px 0; background: transparent;")
        layout.addWidget(filtros_title)

        filtros_group = QGroupBox()
        filtros_group.setObjectName("cardGroup")
        filtros_layout = QGridLayout()
        filtros_layout.setSpacing(10)

        # Fila 0: Estado, Cliente, IMEI, QR
        # Estado
        filtros_layout.addWidget(QLabel(tr("Estado") + ":"), 0, 0)
        self.estado_combo = QComboBox()
        self.estado_combo.addItem(tr("Todos"), "")
        for value, label, color in REPAIR_STATUSES:
            self.estado_combo.addItem(label, value)
        self.estado_combo.setMinimumWidth(120)
        filtros_layout.addWidget(self.estado_combo, 0, 1)

        # Búsqueda por cliente
        filtros_layout.addWidget(QLabel(tr("Cliente") + ":"), 0, 2)
        self.cliente_input = SearchLineEdit()
        self.cliente_input.setPlaceholderText(tr("Nombre del cliente"))
        self.cliente_input.setMinimumWidth(150)
        self.cliente_input.returnPressed.connect(lambda: self._buscar_por('cliente', self.cliente_input.text()))
        self.cliente_input.searchSignal.connect(lambda: self._buscar_por('cliente', self.cliente_input.text()))
        filtros_layout.addWidget(self.cliente_input, 0, 3)

        # Búsqueda por IMEI
        filtros_layout.addWidget(QLabel("IMEI:"), 0, 4)
        self.imei_input = SearchLineEdit()
        self.imei_input.setPlaceholderText(tr("IMEI o Nº Serie"))
        self.imei_input.setMinimumWidth(150)
        self.imei_input.returnPressed.connect(lambda: self._buscar_por('imei', self.imei_input.text()))
        self.imei_input.searchSignal.connect(lambda: self._buscar_por('imei', self.imei_input.text()))
        filtros_layout.addWidget(self.imei_input, 0, 5)

        # Búsqueda por QR
        filtros_layout.addWidget(QLabel("QR:"), 0, 6)
        self.qr_input = SearchLineEdit()
        self.qr_input.setPlaceholderText(tr("Escanear código QR"))
        self.qr_input.setMinimumWidth(150)
        self.qr_input.returnPressed.connect(self.buscar_por_qr)
        self.qr_input.searchSignal.connect(self.buscar_por_qr)
        filtros_layout.addWidget(self.qr_input, 0, 7)

        # Fila 1: Fechas y Botones
        # Rango de fechas: Desde
        filtros_layout.addWidget(QLabel(tr("Desde") + ":"), 1, 0)
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_desde.setMinimumWidth(120)
        filtros_layout.addWidget(self.fecha_desde, 1, 1)

        # Rango de fechas: Hasta
        filtros_layout.addWidget(QLabel(tr("Hasta") + ":"), 1, 2)
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)
        self.fecha_hasta.setMinimumWidth(120)
        filtros_layout.addWidget(self.fecha_hasta, 1, 3)

        # Espacio flexible para empujar botones a la derecha
        filtros_layout.setColumnStretch(5, 1)

        # Botones de filtro
        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(10)
        btns_layout.addStretch()

        btn_buscar = QPushButton(tr("Buscar"))
        btn_buscar.setFixedWidth(100)
        btn_buscar.clicked.connect(self.buscar)
        apply_btn_primary(btn_buscar)
        set_btn_icon(btn_buscar, FluentIcon.SEARCH, color="#5E81AC")

        btn_limpiar = QPushButton(tr("Limpiar"))
        btn_limpiar.setFixedWidth(100)
        btn_limpiar.clicked.connect(self.limpiar_filtros)
        apply_btn_cancel(btn_limpiar)
        set_btn_icon(btn_limpiar, FluentIcon.DELETE, color="#4C566A")

        btns_layout.addWidget(btn_buscar)
        btns_layout.addWidget(btn_limpiar)

        filtros_layout.addLayout(btns_layout, 1, 4, 1, 4)

        filtros_group.setLayout(filtros_layout)
        layout.addWidget(filtros_group)

        # Tabla de reparaciones
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            tr("Nº Orden"), tr("Fecha"), tr("Cliente"), tr("Dispositivo"), "IMEI", tr("Precio"), tr("Estado"), tr("Acciones")
        ])

        # Configurar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents) # Nº Orden
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # Fecha
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Cliente
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Dispositivo (Variable)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # IMEI
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # Precio
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # Estado
        header.setSectionResizeMode(7, QHeaderView.Fixed)            # Acciones
        self.tabla.setColumnWidth(7, 280)  # Acciones (6 botones)
        
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Altura de fila de máxima gama
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        layout.addWidget(self.tabla)

        # Paginación
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination)

        # Resumen
        resumen_layout = QHBoxLayout()
        resumen_layout.addStretch()
        self.total_reparaciones_label = QLabel(tr("Total reparaciones") + ": 0")
        self.total_reparaciones_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        resumen_layout.addWidget(self.total_reparaciones_label)
        layout.addLayout(resumen_layout)

    def _on_page_changed(self, offset, limit):
        """Callback cuando cambia la página"""
        self.cargar_reparaciones(self._filtros_actuales)

    def cargar_reparaciones(self, filtros=None):
        """Carga reparaciones con paginación"""
        self._filtros_actuales = filtros
        reparaciones, total = self.reparacion_manager.buscar_reparaciones_paginado(
            filtros, limit=self.pagination.limit, offset=self.pagination.offset
        )
        self.pagination.update_total(total)

        self.tabla.setRowCount(0)

        # Crear diccionario de estados para colores
        estados_dict = {value: (label, color) for value, label, color in REPAIR_STATUSES}

        for reparacion in reparaciones:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Nº Orden
            numero = reparacion.get('numero_orden') or reparacion.get('numero', '')
            numero_item = QTableWidgetItem(numero)
            numero_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, numero_item)
            
            # Fecha
            fecha_item = QTableWidgetItem(reparacion['fecha_entrada'])
            fecha_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, fecha_item)

            # Cliente
            cliente_item = QTableWidgetItem(reparacion['cliente_nombre'] or tr('Sin nombre'))
            cliente_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, cliente_item)

            # Dispositivo
            dispositivo = reparacion.get('dispositivo', 'Varios/Desconocido')
            disp_item = QTableWidgetItem(dispositivo)
            disp_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, disp_item)
            
            # IMEI
            imei_item = QTableWidgetItem(reparacion.get('imei') or 'N/A')
            imei_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, imei_item)

            # Precio
            precio = float(reparacion.get('costo_estimado', 0))
            precio_item = QTableWidgetItem(f"{precio:.2f} €")
            precio_item.setTextAlignment(Qt.AlignCenter)
            font = precio_item.font()
            font.setBold(True)
            precio_item.setFont(font)
            precio_item.setForeground(QColor('#A3BE8C'))
            self.tabla.setItem(row, 5, precio_item)

            # Estado con color
            estado_value = reparacion['estado']
            estado_label, estado_color = estados_dict.get(estado_value, (estado_value, '#D8DEE9'))

            estado_item = QTableWidgetItem(estado_label)
            estado_item.setForeground(QColor(estado_color))
            estado_item.setFont(QFont("", -1, QFont.Bold))
            estado_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 6, estado_item)

            # Botones de acción - Centrado estructural para 5 botones
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(8)
            h_layout.addStretch()

            from app.ui.styles import estilizar_btn_ver, estilizar_btn_imprimir, estilizar_btn_estado, estilizar_btn_eliminar, estilizar_btn_descargar, estilizar_btn_factura

            # Usar numero_orden
            numero_orden = reparacion.get('numero_orden') or reparacion.get('numero', '')

            btn_ver = QPushButton()
            btn_ver.setToolTip(tr("Ver"))
            btn_ver.clicked.connect(lambda checked, r_id=reparacion['id']: self.ver_detalle(r_id))
            estilizar_btn_ver(btn_ver)

            btn_print = QPushButton()
            btn_print.setToolTip(tr("Imprimir Orden"))
            btn_print.clicked.connect(lambda checked, r_id=reparacion['id'], r_num=numero_orden: self.imprimir_orden(r_id, r_num))
            estilizar_btn_imprimir(btn_print)

            btn_factura = QPushButton()
            btn_factura.setToolTip(tr("Imprimir Factura"))
            btn_factura.clicked.connect(lambda checked, r_id=reparacion['id']: self.imprimir_factura_reparacion(r_id))
            estilizar_btn_factura(btn_factura)
            # Solo habilitar factura si está entregado (ya cobrado)
            if estado_value != 'entregado':
                btn_factura.setEnabled(False)
                btn_factura.setToolTip(tr("Solo disponible cuando el estado es Entregado"))

            btn_descargar = QPushButton()
            btn_descargar.setToolTip(tr("Descargar PDF"))
            btn_descargar.clicked.connect(lambda checked, r_id=reparacion['id'], r_num=numero_orden: self.descargar_orden(r_id, r_num))
            estilizar_btn_descargar(btn_descargar)

            btn_estado = QPushButton()
            btn_estado.setToolTip(tr("Cambiar Estado"))
            btn_estado.clicked.connect(lambda checked, r_id=reparacion['id']: self.cambiar_estado(r_id))
            estilizar_btn_estado(btn_estado)

            btn_del = QPushButton()
            btn_del.setToolTip(tr("Eliminar"))
            btn_del.clicked.connect(lambda checked, r_id=reparacion['id']: self.eliminar_reparacion(r_id))
            estilizar_btn_eliminar(btn_del)

            h_layout.addWidget(btn_ver)
            h_layout.addWidget(btn_print)
            h_layout.addWidget(btn_factura)
            h_layout.addWidget(btn_descargar)
            h_layout.addWidget(btn_estado)
            h_layout.addWidget(btn_del)

            h_layout.addStretch()
            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 7, container)

        # Actualizar resumen
        self.total_reparaciones_label.setText(f"{tr('Total reparaciones')}: {total}")

    def buscar_por_qr(self):
        """Busca una reparación por código QR escaneado"""
        qr_data = self.qr_input.text().strip()

        if not qr_data:
            return

        # Buscar la reparación por QR
        reparacion = self.reparacion_manager.buscar_por_qr(qr_data)

        if reparacion:
            # Limpiar la tabla y mostrar solo la reparación encontrada
            self.tabla.setRowCount(0)
            self.agregar_fila_reparacion(reparacion, 0)
            self.tabla.setRowCount(1)

            # Mostrar mensaje de éxito
            notify_success(
                self,
                tr("Orden Encontrada"),
                f"{tr('Nº Orden')} {reparacion['numero_orden']} {tr('encontrada')}\n"
                f"{tr('Cliente')}: {reparacion['cliente_nombre']}\n"
                f"{tr('Estado')}: {reparacion['estado']}"
            )

            # Limpiar campo QR
            self.qr_input.clear()
        else:
            notify_warning(
                self,
                tr("No Encontrado"),
                tr("No se encontró ninguna orden con el código QR") + f":\n{qr_data}"
            )

    def _buscar_por(self, campo, valor):
        """Busca reparaciones por un solo campo, sin combinar con otros filtros"""
        filtros = {}
        if valor:
            filtros[campo] = valor
        self.pagination.reset()
        self.cargar_reparaciones(filtros)

    def buscar(self):
        """Busca reparaciones solo por rango de fechas y estado (botón Buscar)"""
        filtros = {
            'fecha_desde': self.fecha_desde.date().toString('yyyy-MM-dd'),
            'fecha_hasta': self.fecha_hasta.date().toString('yyyy-MM-dd'),
        }
        estado = self.estado_combo.currentData()
        if estado:
            filtros['estado'] = estado
        self.pagination.reset()
        self.cargar_reparaciones(filtros)

    def limpiar_filtros(self):
        """Limpia todos los filtros y recarga"""
        self.estado_combo.setCurrentIndex(0)
        self.cliente_input.clear()
        self.imei_input.clear()
        self.qr_input.clear()
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_hasta.setDate(QDate.currentDate())
        self.pagination.reset()
        self.cargar_reparaciones()

    def ver_detalle(self, reparacion_id):
        """Muestra el detalle de una reparación"""
        from app.ui.reparacion_detalle_dialog import ReparacionDetalleDialog
        dialog = ReparacionDetalleDialog(self.db, reparacion_id, parent=self)
        if dialog.exec_():
            # Recargar si hubo cambios
            self.cargar_reparaciones()

    def _generar_pdf_temporal(self, reparacion_id):
        """Genera el PDF de la orden desde la BD"""
        reparacion = self.reparacion_manager.obtener_reparacion(reparacion_id)
        if not reparacion:
            return None

        from app.modules.pdf_generator import PDFGenerator
        generator = PDFGenerator(self.db)
        return generator.generar_orden_reparacion(reparacion)

    def imprimir_orden(self, reparacion_id, numero_orden):
        """Imprime la orden generándola desde la BD"""
        try:
            from app.ui.unified_progress_dialog import UnifiedProgressDialog

            # Verificar impresora ANTES de generar
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_general'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora general configurada.") + "\n" +
                    tr("Ve a Ajustes > Impresoras para configurarla."))
                return

            pdf_path = self._generar_pdf_temporal(reparacion_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF de la orden"))
                return

            # Usar diálogo unificado en modo SOLO IMPRIMIR
            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_PRINT_ONLY, tr("Imprimiendo Orden"))
            progress.set_pdf_path(pdf_path)
            progress.set_printer_config(printer_name)
            progress.execute()

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al imprimir orden") + f":\n{str(e)}")

    def descargar_orden(self, reparacion_id, numero_orden):
        """Descarga el PDF de la orden generándolo desde la BD"""
        try:
            # Primero preguntar dónde guardar
            nombre_sugerido = f"Orden_{numero_orden}.pdf"
            destino, _ = QFileDialog.getSaveFileName(
                self,
                tr("Guardar Orden de Reparación"),
                nombre_sugerido,
                tr("Archivos PDF") + " (*.pdf)"
            )

            if not destino:
                return  # Usuario canceló

            # Generar PDF temporal
            pdf_path = self._generar_pdf_temporal(reparacion_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF de la orden"))
                return

            # Copiar al destino elegido
            shutil.copy2(pdf_path, destino)

            # Eliminar temporal
            try:
                os.remove(pdf_path)
            except (OSError, ValueError, RuntimeError):
                pass

            notify_success(self, tr("Descargado"), tr("Orden guardada en") + f":\n{destino}")

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al descargar orden") + f":\n{str(e)}")

    def imprimir_factura_reparacion(self, reparacion_id):
        """Genera y registra una factura formal a partir de una reparación"""
        try:
            from app.modules.factura_manager import FacturaManager
            from app.modules.pdf_generator import PDFGenerator
            from app.ui.unified_progress_dialog import UnifiedProgressDialog
            from config import calcular_desglose_iva
            from datetime import date

            # Obtener reparación completa
            reparacion = self.reparacion_manager.obtener_reparacion(reparacion_id)
            if not reparacion:
                notify_warning(self, tr("Error"), tr("No se pudo cargar la reparación"))
                return

            # Verificar impresora ANTES de procesar
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_general'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora general configurada.") + "\n" +
                    tr("Ve a Ajustes > Impresoras para configurarla."))
                return

            # Convertir reparación a formato de factura
            factura_manager = FacturaManager(self.db)
            numero_factura = factura_manager.obtener_siguiente_numero()

            # Construir items de factura desde averías de reparación
            items_factura = []
            for item in reparacion.get('items', []):
                dispositivo = f"{item.get('marca_nombre', '')} {item.get('modelo_nombre', '')}".strip()
                if not dispositivo:
                    dispositivo = tr("Dispositivo")

                for averia in item.get('averias', []):
                    precio = float(averia.get('precio', 0))
                    # Solo añadir si tiene precio > 0
                    if precio > 0:
                        descripcion = f"{dispositivo} - {averia.get('descripcion_averia', averia.get('averia', tr('Reparación')))}"
                        items_factura.append({
                            'descripcion': descripcion,
                            'imei': item.get('imei', ''),
                            'cantidad': 1,
                            'precio': precio  # IVA incluido
                        })

            if not items_factura:
                notify_warning(self, tr("Error"), tr("La reparación no tiene averías con precio"))
                return

            # Calcular totales (precios son IVA incluido)
            total_con_iva = sum(i['precio'] for i in items_factura)
            
            if total_con_iva <= 0:
                notify_warning(self, tr("Error"), tr("El total debe ser mayor a 0"))
                return
                
            subtotal, iva, total = calcular_desglose_iva(total_con_iva)


            # Preparar datos de factura
            datos_factura = {
                'numero': numero_factura,
                'fecha': date.today(),
                'cliente': {
                    'nombre': reparacion.get('cliente_nombre', ''),
                    'nif': reparacion.get('cliente_nif', ''),
                    'direccion': reparacion.get('cliente_direccion', ''),
                    'telefono': reparacion.get('cliente_telefono', ''),
                    'codigo_postal': '',
                    'ciudad': ''
                },
                'items': items_factura,
                'totales': {
                    'subtotal': subtotal,
                    'iva': iva,
                    'total': total
                }
            }

            # Guardar factura en BD
            factura_id = factura_manager.guardar_factura(datos_factura)

            if not factura_id:
                notify_error(self, tr("Error"), tr("No se pudo guardar la factura en la base de datos"))
                return

            # Generar PDF
            pdf_generator = PDFGenerator(self.db)
            pdf_path = pdf_generator.generar_factura(datos_factura, factura_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF de la factura"))
                return

            # Imprimir usando diálogo unificado
            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_PRINT_ONLY, tr("Imprimiendo Factura"))
            progress.set_pdf_path(pdf_path)
            progress.set_printer_config(printer_name)
            progress.execute()

            notify_success(
                self,
                tr("Factura Generada"),
                tr("Factura") + f" {numero_factura} " + tr("registrada correctamente") + f"\n\n" +
                tr("Total") + f": {total:.2f} €"
            )

        except (OSError, ValueError, RuntimeError) as e:
            import traceback
            traceback.print_exc()
            notify_error(self, tr("Error"), tr("Error al generar factura") + f":\n{str(e)}")

    def cambiar_estado(self, reparacion_id):
        """Abre diálogo para cambiar el estado con soporte para recambios"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QComboBox, QTextEdit, QPushButton, QHBoxLayout, QDoubleSpinBox, QFrame

        # Obtener reparación actual
        reparacion = self.reparacion_manager.obtener_reparacion(reparacion_id)
        if not reparacion:
            notify_warning(self, tr("Error"), tr("No se pudo cargar la reparación"))
            return

        # Verificar permisos y pedir contraseña
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

            if not confirmar_accion_sensible(
                self.auth_manager,
                'sat.editar',
                tr('Editar Reparación'),
                tr("¿Cambiar estado de la orden?") + f" {reparacion.get('numero_orden')}\n\n" +
                tr("Cliente") + f": {reparacion.get('cliente_nombre', 'N/A')}\n" +
                tr("Estado actual") + f": {reparacion.get('estado', 'N/A')}",
                self
            ):
                return

        # Lista para almacenar recambios añadidos
        recambios_lista = []

        # Crear diálogo - TAMAÑO FIJO GRANDE
        dialog = QDialog(self)
        dialog.setWindowTitle(f"{tr('Cambiar Estado')} - {reparacion.get('numero_orden')}")
        dialog.setFixedSize(600, 780)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Info de la reparación
        info_frame = QFrame()
        info_frame.setStyleSheet("QFrame { background-color: #3B4252; border-radius: 6px; padding: 8px; }")
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(10, 8, 10, 8)
        info_layout.addWidget(QLabel(f"<b>{tr('Cliente')}:</b> {reparacion.get('cliente_nombre')}"))
        info_layout.addWidget(QLabel(f"<b>{tr('Dispositivo')}:</b> {reparacion.get('dispositivo', 'Varios')}"))
        info_layout.addWidget(QLabel(f"<b>{tr('Estado actual')}:</b> {reparacion['estado']}"))
        layout.addWidget(info_frame)

        # Selector de estado
        estado_layout = QHBoxLayout()
        estado_layout.addWidget(QLabel(tr("Nuevo Estado") + ":"))
        estado_combo = QComboBox()
        estado_combo.setMinimumWidth(200)
        for value, label, color in REPAIR_STATUSES:
            estado_combo.addItem(label, value)
        for i in range(estado_combo.count()):
            if estado_combo.itemData(i) == reparacion['estado']:
                estado_combo.setCurrentIndex(i)
                break
        estado_layout.addWidget(estado_combo)
        estado_layout.addStretch()
        layout.addLayout(estado_layout)

        # === SECCIÓN DE RECAMBIOS ===
        recambios_frame = QFrame()
        recambios_frame.setStyleSheet("QFrame#recambiosFrame { border: 2px solid #5E81AC; border-radius: 8px; }")
        recambios_frame.setObjectName("recambiosFrame")
        recambios_vlayout = QVBoxLayout(recambios_frame)
        recambios_vlayout.setSpacing(8)
        recambios_vlayout.setContentsMargins(12, 12, 12, 12)

        # Título
        recambios_title = QLabel(tr("RECAMBIOS UTILIZADOS"))
        recambios_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #5E81AC;")
        recambios_vlayout.addWidget(recambios_title)

        # Fila 1: Buscar por EAN
        ean_row = QHBoxLayout()
        ean_row.addWidget(QLabel(tr("Buscar por EAN") + ":"))
        ean_input = QLineEdit()
        ean_input.setPlaceholderText(tr("Escanear código") + " + Enter")
        ean_row.addWidget(ean_input)
        recambios_vlayout.addLayout(ean_row)

        # Fila 2: Descripción manual
        desc_row = QHBoxLayout()
        desc_row.addWidget(QLabel(tr("Descripción") + ":"))
        desc_input = QLineEdit()
        desc_input.setPlaceholderText(tr("Nombre del recambio manual"))
        desc_row.addWidget(desc_input)
        recambios_vlayout.addLayout(desc_row)

        # Fila 3: Cantidad + Precio + Botón
        add_row = QHBoxLayout()
        add_row.addWidget(QLabel(tr("Cantidad") + ":"))
        cant_input = QSpinBox()
        cant_input.setMinimum(1)
        cant_input.setMaximum(999)
        cant_input.setValue(1)
        cant_input.setFixedWidth(70)
        add_row.addWidget(cant_input)
        add_row.addSpacing(20)
        add_row.addWidget(QLabel(tr("Precio") + ":"))
        precio_input = QDoubleSpinBox()
        precio_input.setMinimum(0)
        precio_input.setMaximum(99999)
        precio_input.setDecimals(2)
        precio_input.setSuffix(" €")
        precio_input.setFixedWidth(100)
        add_row.addWidget(precio_input)
        add_row.addStretch()
        btn_add = QPushButton("+ " + tr("Añadir"))
        btn_add.setStyleSheet("background-color: #5E81AC; color: white; border: none; border-radius: 4px; padding: 6px 16px;")
        btn_add.setAutoDefault(False)  # Evitar que Enter en otros campos active este botón
        btn_add.setDefault(False)
        add_row.addWidget(btn_add)
        recambios_vlayout.addLayout(add_row)

        # Tabla de recambios - altura fija
        tabla_recambios = QTableWidget()
        tabla_recambios.setColumnCount(5)
        tabla_recambios.setHorizontalHeaderLabels([tr("Descripción"), tr("Cant"), tr("Precio"), tr("Total"), ""])
        tabla_recambios.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        tabla_recambios.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tabla_recambios.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        tabla_recambios.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        tabla_recambios.horizontalHeader().setSectionResizeMode(4, QHeaderView.Fixed)
        tabla_recambios.setColumnWidth(4, 50)
        tabla_recambios.setFixedHeight(130)
        tabla_recambios.verticalHeader().setVisible(False)
        tabla_recambios.verticalHeader().setDefaultSectionSize(55)  # Altura de filas
        tabla_recambios.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Scroll cuando hay más filas
        recambios_vlayout.addWidget(tabla_recambios)

        # Total recambios
        total_recambios_label = QLabel(tr("Total Recambios") + ": 0.00 €")
        total_recambios_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #5E81AC;")
        total_recambios_label.setAlignment(Qt.AlignRight)
        recambios_vlayout.addWidget(total_recambios_label)

        def actualizar_total_recambios():
            """Actualiza el label del total de recambios"""
            total = sum(r['cantidad'] * r['precio_unitario'] for r in recambios_lista)
            total_recambios_label.setText(f"{tr('Total Recambios')}: {total:.2f} €")

        def actualizar_tabla_recambios():
            """Actualiza la tabla con los recambios actuales"""
            tabla_recambios.setRowCount(0)
            for idx, recambio in enumerate(recambios_lista):
                row = tabla_recambios.rowCount()
                tabla_recambios.insertRow(row)

                # Descripción
                desc_item = QTableWidgetItem(recambio['descripcion'])
                tabla_recambios.setItem(row, 0, desc_item)

                # Cantidad
                cant_item = QTableWidgetItem(str(recambio['cantidad']))
                cant_item.setTextAlignment(Qt.AlignCenter)
                tabla_recambios.setItem(row, 1, cant_item)

                # Precio unitario
                precio_item = QTableWidgetItem(f"{recambio['precio_unitario']:.2f} €")
                precio_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                tabla_recambios.setItem(row, 2, precio_item)

                # Total
                total = recambio['cantidad'] * recambio['precio_unitario']
                total_item = QTableWidgetItem(f"{total:.2f} €")
                total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                total_item.setForeground(QColor('#A3BE8C'))
                tabla_recambios.setItem(row, 3, total_item)

                # Botón eliminar - usando estilo del historial
                from app.ui.styles import estilizar_btn_eliminar
                btn_del = QPushButton()
                btn_del.setToolTip(tr("Eliminar"))
                btn_del.clicked.connect(lambda checked, i=idx: eliminar_recambio(i))
                estilizar_btn_eliminar(btn_del)
                # Contenedor para posicionar el botón arriba
                btn_container = QWidget()
                btn_lay = QVBoxLayout(btn_container)
                btn_lay.setContentsMargins(5, 2, 5, 0)
                btn_lay.setSpacing(0)
                btn_lay.addWidget(btn_del, 0, Qt.AlignHCenter | Qt.AlignTop)
                btn_lay.addStretch()
                tabla_recambios.setCellWidget(row, 4, btn_container)

            actualizar_total_recambios()

        def eliminar_recambio(indice):
            """Elimina un recambio de la lista"""
            if 0 <= indice < len(recambios_lista):
                recambios_lista.pop(indice)
                actualizar_tabla_recambios()

        def añadir_recambio_manual():
            """Añade un recambio manual a la lista"""
            descripcion = desc_input.text().strip()
            if not descripcion:
                notify_warning(dialog, tr("Error"), tr("Debe indicar una descripción"))
                return

            recambio = {
                'descripcion': descripcion,
                'cantidad': cant_input.value(),
                'precio_unitario': precio_input.value(),
                'producto_id': None,
                'codigo_ean': ''
            }
            recambios_lista.append(recambio)
            actualizar_tabla_recambios()

            # Limpiar campos
            desc_input.clear()
            cant_input.setValue(1)
            precio_input.setValue(0)

        def buscar_por_ean():
            """Busca producto por EAN y lo añade a la lista"""
            codigo = ean_input.text().strip()
            if not codigo:
                return

            producto = self.reparacion_manager.buscar_producto_por_ean(codigo)
            if producto:
                stock = producto.get('stock', 0) or 0
                if stock < 1:
                    notify_warning(dialog, tr("Sin Stock"),
                        f"{tr('El producto')} '{producto['descripcion']}' {tr('no tiene stock disponible')}.\n"
                        f"{tr('Stock actual')}: {stock}")
                    ean_input.clear()
                    return

                recambio = {
                    'descripcion': producto['descripcion'],
                    'cantidad': 1,
                    'precio_unitario': float(producto.get('precio', 0)),
                    'producto_id': producto['id'],
                    'codigo_ean': producto.get('codigo_ean', '')
                }
                recambios_lista.append(recambio)
                actualizar_tabla_recambios()
                ean_input.clear()
                ean_input.setFocus()  # Mantener foco para escanear más
            else:
                notify_warning(dialog, tr("No Encontrado"),
                    tr("No se encontró producto con EAN") + f": {codigo}")
                ean_input.clear()

        # Conectar eventos
        btn_add.clicked.connect(añadir_recambio_manual)
        ean_input.returnPressed.connect(buscar_por_ean)

        layout.addWidget(recambios_frame)
        recambios_frame.setVisible(False)  # Oculto inicialmente

        # === SECCIÓN DE COBRO (solo visible cuando estado = entregado) ===
        cobro_frame = QFrame()
        cobro_frame.setStyleSheet("QFrame { border: 2px solid #A3BE8C; border-radius: 8px; padding: 10px; }")
        cobro_layout = QVBoxLayout(cobro_frame)

        cobro_title = QLabel(tr("COBRO DE REPARACIÓN"))
        cobro_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #A3BE8C; border: none;")
        cobro_layout.addWidget(cobro_title)

        # Precio de la reparación
        precio_reparacion = float(reparacion.get('costo_estimado', 0))
        precio_label = QLabel(f"<b>{tr('Precio Reparación')}:</b> {precio_reparacion:.2f} €")
        precio_label.setStyleSheet("font-size: 16px; border: none;")
        cobro_layout.addWidget(precio_label)

        # Método de pago
        metodo_layout = QHBoxLayout()
        metodo_layout.addWidget(QLabel(tr("Método de Pago") + ":"))
        metodo_combo = QComboBox()
        metodo_combo.addItem(tr("Efectivo"), "efectivo")
        metodo_combo.addItem(tr("Tarjeta"), "tarjeta")
        metodo_combo.addItem("Bizum", "bizum")
        metodo_layout.addWidget(metodo_combo)
        metodo_layout.addStretch()
        cobro_layout.addLayout(metodo_layout)

        # Sección de efectivo (recibido y cambio)
        efectivo_frame = QFrame()
        efectivo_frame.setStyleSheet("border: none;")
        efectivo_layout = QVBoxLayout(efectivo_frame)
        efectivo_layout.setContentsMargins(0, 5, 0, 0)

        recibido_layout = QHBoxLayout()
        recibido_layout.addWidget(QLabel(tr("Recibido") + ":"))
        recibido_input = QDoubleSpinBox()
        recibido_input.setMinimum(0)
        recibido_input.setMaximum(99999)
        recibido_input.setDecimals(2)
        recibido_input.setSuffix(" €")
        recibido_input.setValue(precio_reparacion)
        recibido_input.setMinimumWidth(120)
        recibido_layout.addWidget(recibido_input)
        recibido_layout.addStretch()
        efectivo_layout.addLayout(recibido_layout)

        cambio_label = QLabel(f"{tr('Cambio')}: 0.00 €")
        cambio_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #A3BE8C;")
        efectivo_layout.addWidget(cambio_label)

        cobro_layout.addWidget(efectivo_frame)

        # Función para calcular cambio
        def calcular_cambio():
            recibido = recibido_input.value()
            cambio = recibido - precio_reparacion
            if cambio >= 0:
                cambio_label.setText(f"{tr('Cambio')}: {cambio:.2f} €")
                cambio_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #A3BE8C;")
            else:
                cambio_label.setText(f"{tr('Falta')}: {abs(cambio):.2f} €")
                cambio_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #BF616A;")

        recibido_input.valueChanged.connect(calcular_cambio)

        # Mostrar/ocultar sección efectivo según método
        def on_metodo_changed(index):
            metodo = metodo_combo.currentData()
            efectivo_frame.setVisible(metodo == 'efectivo')

        metodo_combo.currentIndexChanged.connect(on_metodo_changed)

        layout.addWidget(cobro_frame)
        cobro_frame.setVisible(False)  # Oculto inicialmente

        # Mostrar/ocultar secciones según estado
        def on_estado_changed(index):
            nuevo_estado = estado_combo.currentData()
            recambios_frame.setVisible(nuevo_estado == 'reparado')
            cobro_frame.setVisible(nuevo_estado == 'entregado')

        estado_combo.currentIndexChanged.connect(on_estado_changed)

        layout.addWidget(QLabel(tr("Notas") + " (" + tr("opcional") + "):"))
        notas_input = QTextEdit()
        notas_input.setMaximumHeight(50)
        notas_input.setPlaceholderText(tr("Añadir notas sobre el cambio de estado") + "...")
        layout.addWidget(notas_input)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(dialog.reject)
        apply_btn_cancel(btn_cancelar)
        btn_cancelar.setAutoDefault(False)

        btn_guardar = QPushButton(tr("Guardar"))
        btn_guardar.clicked.connect(dialog.accept)
        apply_btn_success(btn_guardar)
        btn_guardar.setAutoDefault(False)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

        if dialog.exec_():
            nuevo_estado = estado_combo.currentData()
            notas = notas_input.toPlainText()

            # Obtener usuario_id para auditoría
            usuario_id = None
            if self.auth_manager:
                usuario = self.auth_manager.obtener_usuario_actual()
                if usuario:
                    usuario_id = usuario.get('id')

            # === GUARDAR RECAMBIOS SI HAY (cuando estado = reparado) ===
            if nuevo_estado == 'reparado' and recambios_lista:
                try:
                    self.reparacion_manager.guardar_recambios(reparacion_id, recambios_lista, usuario_id)
                except (OSError, ValueError, RuntimeError) as e:
                    notify_error(self, tr("Error"),
                        tr("Error al guardar recambios") + f":\n{str(e)}")
                    return

            # Obtener método de pago si es entregado
            metodo_pago = 'efectivo'
            if nuevo_estado == 'entregado' and precio_reparacion > 0:
                metodo_pago = metodo_combo.currentData()

                # ========== VERIFICACIÓN DE CAJA (igual que TPV y Ventas) ==========
                from app.modules.caja_manager import CajaManager
                from datetime import date

                caja_manager = CajaManager(self.db)
                fecha_hoy = date.today().strftime('%Y-%m-%d')
                estado_caja, data_caja = caja_manager.verificar_estado_caja_completo(fecha_hoy)

                # CASO 1: Cierre pendiente de día anterior
                if estado_caja == 'cierre_pendiente':
                    fecha_pendiente = data_caja['fecha'] if data_caja else 'anterior'
                    notify_warning(
                        self,
                        tr("Cierre de Caja Pendiente"),
                        tr("Hay una caja del día") + f" {fecha_pendiente} " + tr("sin cerrar.") + "\n\n"
                        + tr("Debe cerrar esa caja antes de cobrar.") + "\n\n"
                        + tr("Vaya a") + ": " + tr("Caja") + " - " + tr("Movimientos") + "\n"
                        + tr("Use el botón") + " " + tr("Cerrar Caja")
                    )
                    return

                # CASO 2: Caja de hoy no abierta
                if estado_caja in ['apertura_requerida', 'apertura_nueva_dia']:
                    notify_warning(
                        self,
                        tr("Apertura de Caja Requerida"),
                        tr("La caja de hoy no está abierta.") + "\n\n"
                        + tr("Debe abrir la caja antes de cobrar.") + "\n\n"
                        + tr("Vaya a") + ": " + tr("Caja") + " - " + tr("Movimientos") + "\n"
                        + tr("Use el botón") + " " + tr("Abrir Caja")
                    )
                    return

                # CASO 3: Caja ya cerrada hoy
                if estado_caja == 'reapertura_requerida':
                    notify_warning(
                        self,
                        tr("Caja Ya Cerrada"),
                        tr("La caja de hoy ya fue cerrada.") + "\n\n"
                        + tr("Para cobrar debe reabrir la caja.") + "\n\n"
                        + tr("Vaya a") + ": " + tr("Caja") + " - " + tr("Movimientos")
                    )
                    return
                # ========== FIN VERIFICACIÓN DE CAJA ==========

            try:
                # Actualizar estado (el manager se encarga de registrar en caja transaccionalmente)
                self.reparacion_manager.actualizar_estado(reparacion_id, nuevo_estado, metodo_pago, usuario_id=usuario_id)

                # Mensaje de éxito
                if nuevo_estado == 'reparado' and recambios_lista:
                    total_recambios = sum(r['cantidad'] * r['precio_unitario'] for r in recambios_lista)
                    notify_success(self, tr("Éxito"),
                        tr("Estado actualizado a 'Reparado'") + "\n\n" +
                        f"{tr('Recambios guardados')}: {len(recambios_lista)}\n" +
                        f"{tr('Total recambios')}: {total_recambios:.2f} €")
                elif nuevo_estado == 'entregado' and precio_reparacion > 0:
                    if metodo_pago == 'efectivo':
                        cambio = recibido_input.value() - precio_reparacion
                        notify_success(self, tr("Éxito"),
                            tr("Estado actualizado y cobro registrado") + "\n\n" +
                            f"{tr('Total')}: {precio_reparacion:.2f} €\n" +
                            f"{tr('Recibido')}: {recibido_input.value():.2f} €\n" +
                            f"{tr('Cambio')}: {cambio:.2f} €")
                    else:
                        notify_success(self, tr("Éxito"),
                            tr("Estado actualizado y cobro registrado") + "\n\n" +
                            f"{tr('Total')}: {precio_reparacion:.2f} €\n" +
                            f"{tr('Método')}: {metodo_pago.upper()}")
                else:
                    notify_success(self, tr("Éxito"), tr("Estado actualizado correctamente"))

                self.cargar_reparaciones()
            except (OSError, ValueError, RuntimeError) as e:
                notify_error(self, tr("Error"), tr("Error al actualizar estado") + f":\n{str(e)}")

    def eliminar_reparacion(self, reparacion_id):
        """Elimina una reparación con verificación de permisos y contraseña"""
        reparacion = self.reparacion_manager.obtener_reparacion(reparacion_id)
        if not reparacion:
            return

        # Verificar permisos y pedir contraseña
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

            if not confirmar_accion_sensible(
                self.auth_manager,
                'sat.eliminar',
                tr('Eliminar Reparación'),
                tr("¿Eliminar la orden?") + f" {reparacion.get('numero_orden')}\n\n" +
                tr("Cliente") + f": {reparacion.get('cliente_nombre', 'N/A')}\n" +
                tr("Dispositivo") + f": {reparacion.get('dispositivo', 'N/A')}\n" +
                tr("Estado") + f": {reparacion.get('estado', 'N/A')}",
                self
            ):
                return

        # Obtener usuario_id para auditoría
        usuario_id = None
        if self.auth_manager:
            usuario = self.auth_manager.obtener_usuario_actual()
            if usuario:
                usuario_id = usuario.get('id')

        ok, msg = self.reparacion_manager.eliminar_reparacion(reparacion_id, usuario_id=usuario_id)
        if ok:
            notify_success(self, tr("Éxito"), msg)
            self.cargar_reparaciones()
        else:
            notify_warning(self, tr("Error"), msg)

    def showEvent(self, event):
        """Se ejecuta automáticamente cuando se muestra la pestaña"""
        super().showEvent(event)
        # Actualizar historial automáticamente al entrar
        self.cargar_reparaciones()

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
