"""
Pestana para gestion de devoluciones/reembolsos
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QHeaderView, QCheckBox, QSpinBox, QDateEdit,
                             QFrame, QComboBox)
from qfluentwidgets import SearchLineEdit
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QFont
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.i18n import tr
from app.ui.transparent_buttons import apply_transparent_button_style, apply_btn_primary, set_btn_icon
from qfluentwidgets import FluentIcon
from app.db.database import Database
from app.modules.devolucion_manager import DevolucionManager


class CajaDevolucionesTab(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.devolucion_manager = DevolucionManager(self.db)
        self.venta_actual = None
        self.setup_ui()
        self.cargar_historial()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)

        # Header
        header_label = QLabel(tr("Devoluciones y Reembolsos"))
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 5px 0; color: #ffffff;")
        layout.addWidget(header_label)

        # Seccion de busqueda — compacta y alineada
        search_title = QLabel(tr("Buscar Venta"))
        search_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        layout.addWidget(search_title)

        search_input_layout = QHBoxLayout()
        search_input_layout.setAlignment(Qt.AlignVCenter)
        search_input_layout.setContentsMargins(0, 0, 0, 0)
        search_input_layout.setSpacing(8)

        lbl_ticket = QLabel(tr("Número de Ticket") + ":")
        lbl_ticket.setFixedHeight(36)
        search_input_layout.addWidget(lbl_ticket)

        self.ticket_input = SearchLineEdit()
        self.ticket_input.setPlaceholderText("Ej: T00001")
        self.ticket_input.setMaximumWidth(200)
        self.ticket_input.setFixedHeight(36)
        self.ticket_input.returnPressed.connect(self.buscar_venta)
        search_input_layout.addWidget(self.ticket_input)

        btn_buscar = QPushButton(tr("Buscar"))
        btn_buscar.clicked.connect(self.buscar_venta)
        apply_transparent_button_style(btn_buscar)
        set_btn_icon(btn_buscar, FluentIcon.SEARCH, color="#88C0D0")
        btn_buscar.setFixedHeight(36)
        search_input_layout.addWidget(btn_buscar)

        search_input_layout.addStretch()
        layout.addLayout(search_input_layout)

        # Seccion de detalles de venta (oculta inicialmente)
        self.detalles_widget = QWidget()
        detalles_layout = QVBoxLayout(self.detalles_widget)
        detalles_layout.setContentsMargins(0, 8, 0, 0)
        detalles_layout.setSpacing(6)

        # Info de la venta
        info_label = QLabel(tr("Información de la Venta"))
        info_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        detalles_layout.addWidget(info_label)

        self.venta_info_label = QLabel()
        self.venta_info_label.setStyleSheet("""
            background-color: #2E3440;
            padding: 12px;
            border-radius: 5px;
            border: 1px solid #4C566A;
            color: #D8DEE9;
        """)
        self.venta_info_label.setWordWrap(True)
        detalles_layout.addWidget(self.venta_info_label)

        # Tabla de items
        items_label = QLabel(tr("Items de la Venta"))
        items_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #ffffff;")
        detalles_layout.addWidget(items_label)

        self.tabla_items = QTableWidget()
        self.tabla_items.setColumnCount(8)
        self.tabla_items.setHorizontalHeaderLabels([
            "", tr("Producto"), tr("Precio Unit."), tr("Cant. Original"),
            tr("Devuelta"), tr("Disponible"), tr("Devolver"), tr("Total")
        ])

        header = self.tabla_items.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Producto
        for i in range(2, 8):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.tabla_items.setColumnWidth(0, 40)
        self.tabla_items.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_items.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla_items.verticalHeader().setDefaultSectionSize(60)
        self.tabla_items.verticalHeader().setVisible(False)
        self.tabla_items.setStyleSheet("QTableWidget::item { padding: 0px; }")
        self.tabla_items.setMinimumHeight(250)
        self.tabla_items.setMaximumHeight(350)

        detalles_layout.addWidget(self.tabla_items)

        # Seccion de proceso de devolucion
        proceso_layout = QHBoxLayout()

        # Motivo
        motivo_layout = QVBoxLayout()
        motivo_layout.addWidget(QLabel(tr("Motivo de la Devolución") + ":"))
        self.motivo_input = QTextEdit()
        self.motivo_input.setMaximumHeight(80)
        self.motivo_input.setPlaceholderText(tr("Describe el motivo de la devolución..."))
        self.motivo_input.setStyleSheet("""
            QTextEdit {
                background-color: #3B4252;
                color: #ffffff;
                border: 1px solid #4C566A;
                border-radius: 5px;
                padding: 8px;
            }
            QTextEdit:focus { border: 1px solid #5E81AC; }
        """)
        motivo_layout.addWidget(self.motivo_input)
        proceso_layout.addLayout(motivo_layout, 2)

        # Resumen
        resumen_layout = QVBoxLayout()

        self.total_devolver_label = QLabel(tr("Total a Devolver") + ": 0.00 €")
        self.total_devolver_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            padding: 15px;
            background-color: #2E3440;
            border-radius: 5px;
            border: 1px solid #4C566A;
            color: #88C0D0;
        """)
        self.total_devolver_label.setAlignment(Qt.AlignCenter)
        resumen_layout.addWidget(self.total_devolver_label)

        # Selector de método de devolución
        metodo_label = QLabel(tr("Método de Reembolso") + ":")
        metodo_label.setStyleSheet("color: #D8DEE9; font-weight: bold; margin-top: 10px;")
        resumen_layout.addWidget(metodo_label)

        self.metodo_selector = QComboBox()
        self.metodo_selector.addItems(['efectivo', 'tarjeta', 'bizum', 'vale'])
        resumen_layout.addWidget(self.metodo_selector)

        self.btn_procesar = QPushButton(tr("Procesar Devolución"))
        self.btn_procesar.clicked.connect(self.procesar_devolucion)
        self.btn_procesar.setEnabled(False)
        self.btn_procesar.setStyleSheet("""
            QPushButton {
                background-color: #BF616A;
                color: white;
                font-weight: bold;
                padding: 12px 25px;
                border: none;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #BF616A; }
            QPushButton:disabled { background-color: #4C566A; color: #7B88A0; }
        """)
        resumen_layout.addWidget(self.btn_procesar)

        self.btn_limpiar = QPushButton("✗ " + tr("Cancelar") + "/" + tr("Limpiar"))
        self.btn_limpiar.clicked.connect(self.limpiar_formulario)
        self.btn_limpiar.setStyleSheet("""
            QPushButton {
                background-color: #D8DEE9;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #7B88A0; }
        """)
        resumen_layout.addWidget(self.btn_limpiar)

        proceso_layout.addLayout(resumen_layout, 1)

        detalles_layout.addLayout(proceso_layout)

        layout.addWidget(self.detalles_widget)
        self.detalles_widget.setVisible(False)

        # Historial de devoluciones
        historial_label = QLabel(tr("Historial de Devoluciones"))
        historial_label.setStyleSheet("font-weight: bold; font-size: 14px; padding-top: 5px; color: #ffffff;")
        layout.addWidget(historial_label)

        # Filtros de historial — alineados verticalmente
        filtros_layout = QHBoxLayout()
        filtros_layout.setAlignment(Qt.AlignVCenter)
        filtros_layout.setSpacing(8)

        lbl_desde = QLabel(tr("Desde") + ":")
        lbl_desde.setFixedHeight(36)
        filtros_layout.addWidget(lbl_desde)

        self.filtro_fecha_desde = QDateEdit()
        self.filtro_fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.filtro_fecha_desde.setCalendarPopup(True)
        self.filtro_fecha_desde.setMaximumWidth(130)
        self.filtro_fecha_desde.setFixedHeight(36)
        filtros_layout.addWidget(self.filtro_fecha_desde)

        lbl_hasta = QLabel(tr("Hasta") + ":")
        lbl_hasta.setFixedHeight(36)
        filtros_layout.addWidget(lbl_hasta)

        self.filtro_fecha_hasta = QDateEdit()
        self.filtro_fecha_hasta.setDate(QDate.currentDate())
        self.filtro_fecha_hasta.setCalendarPopup(True)
        self.filtro_fecha_hasta.setMaximumWidth(130)
        self.filtro_fecha_hasta.setFixedHeight(36)
        filtros_layout.addWidget(self.filtro_fecha_hasta)

        btn_buscar_hist = QPushButton(tr("Buscar"))
        btn_buscar_hist.clicked.connect(self.cargar_historial)
        apply_btn_primary(btn_buscar_hist)
        set_btn_icon(btn_buscar_hist, FluentIcon.SEARCH, color="#5E81AC")
        btn_buscar_hist.setFixedHeight(36)
        filtros_layout.addWidget(btn_buscar_hist)

        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)

        # Tabla historial
        self.tabla_historial = QTableWidget()
        self.tabla_historial.setColumnCount(6)
        self.tabla_historial.setHorizontalHeaderLabels([
            tr("Fecha"), "Ticket", tr("Monto"), tr("Método"), tr("Motivo"), tr("Usuario")
        ])

        header_hist = self.tabla_historial.horizontalHeader()
        for i in range(6):
            header_hist.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        header_hist.setSectionResizeMode(4, QHeaderView.Stretch)  # Motivo

        self.tabla_historial.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_historial.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla_historial.verticalHeader().setDefaultSectionSize(60)
        self.tabla_historial.verticalHeader().setVisible(False)
        self.tabla_historial.setStyleSheet("QTableWidget::item { padding: 0px; }")
        self.tabla_historial.setMinimumHeight(200)
        self.tabla_historial.setMaximumHeight(350)

        layout.addWidget(self.tabla_historial)

    def buscar_venta(self):
        """Busca venta por ticket y muestra detalles"""
        numero_ticket = self.ticket_input.text().strip().upper()

        if not numero_ticket:
            notify_warning(self, tr("Error"), tr("Introduce número de ticket"))
            return

        venta = self.devolucion_manager.buscar_venta_por_ticket(numero_ticket)

        if not venta:
            notify_warning(
                self,
                tr("No Encontrado"),
                tr("No se encontró venta con ticket") + f": {numero_ticket}\n\n"
                + tr("Verifica que el ticket sea correcto y la venta esté completada.")
            )
            return

        # Check if already fully refunded
        if venta['total_devuelto'] >= venta['total']:
            notify_success(
                self,
                tr("Venta Totalmente Devuelta"),
                tr("Esta venta ya fue completamente reembolsada.") + "\n\n"
                + tr("Total original") + f": {venta['total']:.2f} €\n"
                + tr("Total devuelto") + f": {venta['total_devuelto']:.2f} €"
            )
            # Continuar mostrando para informacion, pero deshabilitar proceso
            self.venta_actual = venta
            self.mostrar_detalles_venta()
            self.btn_procesar.setEnabled(False)
            return

        self.venta_actual = venta
        self.mostrar_detalles_venta()

    def mostrar_detalles_venta(self):
        """Muestra detalles de la venta y sus items"""
        if not self.venta_actual:
            return

        # Mostrar info de la venta
        from datetime import datetime
        fecha = datetime.fromisoformat(self.venta_actual['fecha']).strftime('%d/%m/%Y %H:%M')

        info_text = (
            f"Ticket: {self.venta_actual['numero_ticket']}  |  "
            f"{tr('Fecha')}: {fecha}  |  "
            f"{tr('Total')}: {self.venta_actual['total']:.2f} €  |  "
            f"{tr('Método')}: {self.venta_actual['metodo_pago'].upper()}  |  "
            f"{tr('Ya Devuelto')}: {self.venta_actual['total_devuelto']:.2f} €"
        )
        self.venta_info_label.setText(info_text)

        # Seleccionar método de pago original por defecto en el selector
        metodo_original = self.venta_actual['metodo_pago']
        index = self.metodo_selector.findText(metodo_original)
        if index >= 0:
            self.metodo_selector.setCurrentIndex(index)

        # Llenar tabla de items
        self.tabla_items.setRowCount(0)
        for item in self.venta_actual['items']:
            row = self.tabla_items.rowCount()
            self.tabla_items.insertRow(row)
            self.tabla_items.setRowHeight(row, 60)

            cantidad_disponible = item['cantidad_disponible']

            # Checkbox - Centrado Bulletproof
            checkbox = QCheckBox()
            checkbox.setEnabled(cantidad_disponible > 0)
            checkbox.stateChanged.connect(self.actualizar_total_devolver)
            
            container_cb = QWidget()
            v_layout_cb = QVBoxLayout(container_cb)
            v_layout_cb.setContentsMargins(0, 0, 0, 4) # Un pelín para checkbox
            v_layout_cb.setAlignment(Qt.AlignCenter)
            v_layout_cb.addWidget(checkbox)
            self.tabla_items.setCellWidget(row, 0, container_cb)

            # Producto
            p_item = QTableWidgetItem(item['nombre_producto'])
            p_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_items.setItem(row, 1, p_item)

            # Precio unitario
            precio_item = QTableWidgetItem(f"{item['precio_unitario']:.2f} €")
            precio_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_items.setItem(row, 2, precio_item)

            # Cantidad original
            cant_orig_item = QTableWidgetItem(str(item['cantidad']))
            cant_orig_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_items.setItem(row, 3, cant_orig_item)

            # Cantidad devuelta
            cant_dev_item = QTableWidgetItem(str(item.get('cantidad_devuelta', 0)))
            cant_dev_item.setTextAlignment(Qt.AlignCenter)
            cant_dev_item.setForeground(QColor('#BF616A'))
            self.tabla_items.setItem(row, 4, cant_dev_item)

            # Cantidad disponible
            cant_disp_item = QTableWidgetItem(str(cantidad_disponible))
            cant_disp_item.setTextAlignment(Qt.AlignCenter)
            if cantidad_disponible > 0:
                cant_disp_item.setForeground(QColor('#A3BE8C'))
            else:
                cant_disp_item.setForeground(QColor('#D8DEE9'))
            self.tabla_items.setItem(row, 5, cant_disp_item)

            # SpinBox - Centrado Bulletproof
            spinbox = QSpinBox()
            spinbox.setMinimum(0)
            spinbox.setMaximum(cantidad_disponible)
            spinbox.setValue(cantidad_disponible if cantidad_disponible > 0 else 0)
            spinbox.setEnabled(cantidad_disponible > 0)
            spinbox.valueChanged.connect(self.actualizar_total_devolver)
            spinbox.setFixedSize(60, 32)
            
            container_sb = QWidget()
            v_layout_sb = QVBoxLayout(container_sb)
            v_layout_sb.setContentsMargins(0, 0, 0, 10)
            v_layout_sb.setAlignment(Qt.AlignCenter)
            v_layout_sb.addWidget(spinbox)
            self.tabla_items.setCellWidget(row, 6, container_sb)

            # Total item
            total_item = QTableWidgetItem(f"{item['total_item']:.2f} €")
            total_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_items.setItem(row, 7, total_item)

            # Guardar referencia al item original
            self.tabla_items.item(row, 1).setData(Qt.UserRole, item)

        # Mostrar seccion de detalles
        self.detalles_widget.setVisible(True)
        self.actualizar_total_devolver()

    def actualizar_total_devolver(self):
        """Calcula total a devolver segun items seleccionados"""
        total = 0.0
        items_seleccionados = 0

        for row in range(self.tabla_items.rowCount()):
            checkbox_widget = self.tabla_items.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            spinbox = self.tabla_items.cellWidget(row, 6)

            if checkbox and checkbox.isChecked() and spinbox:
                cantidad_devolver = spinbox.value()
                if cantidad_devolver > 0:
                    item = self.tabla_items.item(row, 1).data(Qt.UserRole)
                    total += item['precio_unitario'] * cantidad_devolver
                    items_seleccionados += 1

        # VALIDAR que el total a devolver no exceda el total disponible
        if self.venta_actual:
            total_original = self.venta_actual.get('total', 0.0)
            total_ya_devuelto = self.venta_actual.get('total_devuelto', 0.0)
            total_disponible = total_original - total_ya_devuelto

            if total > total_disponible:
                # Excede el disponible - mostrar error
                self.total_devolver_label.setText(
                    f"⚠️ {tr('Total a Devolver')}: {total:.2f} € ({tr('EXCEDE DISPONIBLE')}: {total_disponible:.2f} €)"
                )
                self.total_devolver_label.setStyleSheet("color: #BF616A; font-weight: bold; font-size: 14px;")
                self.btn_procesar.setEnabled(False)
            else:
                # Válido
                self.total_devolver_label.setText(f"{tr('Total a Devolver')}: {total:.2f} €")
                self.total_devolver_label.setStyleSheet("color: #A3BE8C; font-weight: bold; font-size: 14px;")
                self.btn_procesar.setEnabled(items_seleccionados > 0)
        else:
            self.total_devolver_label.setText(f"{tr('Total a Devolver')}: {total:.2f} €")
            self.btn_procesar.setEnabled(items_seleccionados > 0)

    def procesar_devolucion(self):
        """Procesa la devolucion"""
        if not self.venta_actual:
            return

        # Obtener items seleccionados
        items_devolver = self.obtener_items_seleccionados()

        if not items_devolver:
            notify_warning(self, tr("Error"), tr("Selecciona al menos un item para devolver"))
            return

        # Validar motivo
        motivo = self.motivo_input.toPlainText().strip()
        if not motivo:
            notify_warning(self, tr("Error"), tr("Debes indicar el motivo de la devolución"))
            return

        # Confirmar
        total_devolver = sum(item['total'] for item in items_devolver)
        metodo_devolucion = self.metodo_selector.currentText()

        # Advertir si el método es diferente al original
        metodo_original = self.venta_actual['metodo_pago']
        advertencia_metodo = ""
        if metodo_devolucion != metodo_original:
            advertencia_metodo = f"\n⚠️ {tr('NOTA')}: {tr('La venta original fue')} {metodo_original.upper()}, {tr('pero se reembolsará en')} {metodo_devolucion.upper()}\n"

        respuesta = ask_confirm(self, tr("Confirmar Devolución"), tr("¿Procesar devolución?") + "\n\n"
            + f"Ticket: {self.venta_actual['numero_ticket']}\n"
            + tr("Items a devolver") + f": {len(items_devolver)}\n"
            + tr("Total a reembolsar") + f": {total_devolver:.2f} €\n"
            + tr("Método de Reembolso") + f": {metodo_devolucion.upper()}{advertencia_metodo}\n"
            + tr("Motivo") + f": {motivo}")

        if not respuesta:
            return

        # Get user ID
        usuario_id = None
        if self.auth_manager:
            usuario = self.auth_manager.obtener_usuario_actual()
            if usuario:
                usuario_id = usuario['id']

        # Process
        resultado, error = self.devolucion_manager.procesar_devolucion(
            venta_id=self.venta_actual['id'],
            items_devolver=items_devolver,
            motivo=motivo,
            usuario_id=usuario_id,
            metodo_devolucion=metodo_devolucion
        )

        if resultado:
            notify_success(
                self,
                tr("Devolución Procesada"),
                tr("Devolución registrada correctamente") + "\n\n"
                + f"ID: {resultado['id']}\n"
                + tr("Monto") + f": {resultado['monto_total']:.2f} €\n"
                + "Items: " + f"{resultado['items_count']}"
            )

            self.limpiar_formulario()
            self.cargar_historial()
        else:
            notify_error(self, tr("Error"), tr("Error procesando devolución") + f":\n{error}")

    def obtener_items_seleccionados(self):
        """Retorna lista de items seleccionados para devolver"""
        items = []

        for row in range(self.tabla_items.rowCount()):
            checkbox_widget = self.tabla_items.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            spinbox = self.tabla_items.cellWidget(row, 6)

            if checkbox and checkbox.isChecked() and spinbox:
                cantidad_devolver = spinbox.value()
                if cantidad_devolver > 0:
                    item_original = self.tabla_items.item(row, 1).data(Qt.UserRole)

                    from config import calcular_desglose_iva
                    precio_total = item_original['precio_unitario'] * cantidad_devolver
                    subtotal, iva, _ = calcular_desglose_iva(precio_total)

                    items.append({
                        'venta_item_id': item_original['id'],
                        'cantidad_devolver': cantidad_devolver,
                        'producto_id': item_original.get('producto_id'),
                        'compra_item_id': item_original.get('compra_item_id'),
                        'origen': item_original.get('origen', 'productos'),
                        'precio_unitario': item_original['precio_unitario'],
                        'subtotal': subtotal,
                        'iva': iva,
                        'total': precio_total
                    })

        return items

    def limpiar_formulario(self):
        """Limpia el formulario con confirmación si hay datos"""
        # Verificar si hay datos ingresados
        tiene_datos = (
            self.venta_actual is not None or
            self.ticket_input.text().strip() != "" or
            self.motivo_input.toPlainText().strip() != ""
        )

        if tiene_datos:
            # Pedir confirmación
            if not ask_confirm(self, tr("Limpiar Formulario"),
                tr("¿Está seguro de limpiar el formulario?") + "\n\n"
                + tr("Se perderán todos los datos no guardados.")):
                return  # No limpiar

        # Limpiar
        self.ticket_input.clear()
        self.motivo_input.clear()
        self.venta_actual = None
        self.detalles_widget.setVisible(False)
        self.ticket_input.setFocus()

    def cargar_historial(self):
        """Carga el historial de devoluciones"""
        filtros = {
            'fecha_desde': self.filtro_fecha_desde.date().toString('yyyy-MM-dd'),
            'fecha_hasta': self.filtro_fecha_hasta.date().toString('yyyy-MM-dd')
        }

        devoluciones = self.devolucion_manager.obtener_devoluciones(filtros)

        self.tabla_historial.setRowCount(0)

        for dev in devoluciones:
            row = self.tabla_historial.rowCount()
            self.tabla_historial.insertRow(row)
            self.tabla_historial.setRowHeight(row, 60)

            from datetime import datetime
            fecha = datetime.fromisoformat(dev['fecha_creacion']).strftime('%d/%m/%Y %H:%M')

            # Fecha
            f_item = QTableWidgetItem(fecha)
            f_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_historial.setItem(row, 0, f_item)

            # Ticket
            t_item = QTableWidgetItem(dev['numero_ticket'])
            t_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_historial.setItem(row, 1, t_item)

            # Monto
            monto_item = QTableWidgetItem(f"{dev['monto_devuelto']:.2f} €")
            monto_item.setTextAlignment(Qt.AlignCenter)
            monto_item.setForeground(QColor('#BF616A'))
            monto_item.setFont(QFont("", -1, QFont.Bold))
            self.tabla_historial.setItem(row, 2, monto_item)

            # Método
            met_item = QTableWidgetItem(dev['metodo_devolucion'].upper())
            met_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_historial.setItem(row, 3, met_item)

            # Motivo
            mot_item = QTableWidgetItem(dev['motivo'])
            mot_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_historial.setItem(row, 4, mot_item)

            # Usuario
            u_item = QTableWidgetItem(dev.get('usuario_nombre', '-'))
            u_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_historial.setItem(row, 5, u_item)

    def closeEvent(self, event):
        """Cierra la conexion a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
