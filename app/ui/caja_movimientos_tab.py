"""
Pestaña para gestión de movimientos de caja
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
                             QDateEdit, QHeaderView, QRadioButton,
                             QComboBox, QTextEdit, QDoubleSpinBox, QButtonGroup, QFileDialog,
                             QScrollArea)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor, QFont
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.i18n import tr
from app.db.database import Database
from app.modules.caja_manager import CajaManager
from app.ui.widgets.pagination_widget import PaginationWidget
from config import CASH_INCOME_CATEGORIES, CASH_EXPENSE_CATEGORIES, EXPENSE_TYPES
from app.utils.logger import logger
from app.ui.transparent_buttons import apply_btn_success, apply_btn_danger, apply_btn_cancel, apply_btn_primary, set_btn_icon
from qfluentwidgets import FluentIcon


class CajaMovimientosTab(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.caja_manager = CajaManager(self.db)
        self.setup_ui()
        self.actualizar_saldo()
        self.cargar_movimientos()

    def setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area para ventanas pequeñas
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        
        # Widget contenedor dentro del scroll
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Saldo actual - Grande y prominente
        saldo_group = QGroupBox()
        saldo_group.setStyleSheet("QGroupBox { border: 2px solid #5E81AC; border-radius: 5px; padding: 15px; }")
        saldo_layout = QVBoxLayout()

        saldo_titulo = QLabel(tr("SALDO ACTUAL EN CAJA"))
        saldo_titulo.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        saldo_titulo.setAlignment(Qt.AlignCenter)
        saldo_layout.addWidget(saldo_titulo)

        self.saldo_label = QLabel("0.00 €")
        self.saldo_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #A3BE8C; padding: 10px;")
        self.saldo_label.setAlignment(Qt.AlignCenter)
        saldo_layout.addWidget(self.saldo_label)

        # Saldo inicial del día (para evitar confusión)
        self.saldo_inicial_label = QLabel(tr("Saldo inicial del día") + ": 0.00 €")
        self.saldo_inicial_label.setStyleSheet("font-size: 12px; color: #7B88A0; padding: 5px;")
        self.saldo_inicial_label.setAlignment(Qt.AlignCenter)
        saldo_layout.addWidget(self.saldo_inicial_label)

        # Botones de Apertura y Cierre de Caja
        botones_caja_layout = QHBoxLayout()
        botones_caja_layout.addStretch()

        self.btn_abrir_caja = QPushButton("🔓 " + tr("Abrir Caja"))
        self.btn_abrir_caja.clicked.connect(self.abrir_caja)
        apply_btn_success(self.btn_abrir_caja)
        botones_caja_layout.addWidget(self.btn_abrir_caja)

        self.btn_cerrar_caja = QPushButton(tr("Cerrar Caja"))
        self.btn_cerrar_caja.clicked.connect(self.cerrar_caja)
        apply_btn_danger(self.btn_cerrar_caja)
        botones_caja_layout.addWidget(self.btn_cerrar_caja)

        botones_caja_layout.addStretch()
        saldo_layout.addLayout(botones_caja_layout)

        saldo_group.setLayout(saldo_layout)
        layout.addWidget(saldo_group)

        # Formulario de nuevo egreso (no permitimos ingresos manuales)
        form_group = QGroupBox(tr("Registrar Egreso"))
        form_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; }")
        form_layout = QVBoxLayout()

        # Info: Los ingresos se registran automáticamente
        info_ingresos = QLabel("ℹ️ " + tr("Los ingresos se registran automáticamente desde TPV, Ventas y SAT"))
        info_ingresos.setStyleSheet("color: #D8DEE9; font-size: 11px; font-style: italic; padding: 5px;")
        form_layout.addWidget(info_ingresos)

        # Selector de tipo de egreso (siempre visible)
        tipo_egreso_layout = QHBoxLayout()
        self.tipo_egreso_label = QLabel(tr("Tipo de Egreso") + ":")
        tipo_egreso_layout.addWidget(self.tipo_egreso_label)

        self.tipo_egreso_combo = QComboBox()
        self.tipo_egreso_combo.addItem(tr("Gastos"), "gastos")
        self.tipo_egreso_combo.addItem(tr("Retiros"), "retiros")
        self.tipo_egreso_combo.addItem(tr("Pagos"), "pagos")
        self.tipo_egreso_combo.setMinimumWidth(150)
        tipo_egreso_layout.addWidget(self.tipo_egreso_combo)

        tipo_egreso_layout.addStretch()
        form_layout.addLayout(tipo_egreso_layout)

        # Selector de método de pago (siempre visible)
        metodo_pago_layout = QHBoxLayout()
        metodo_pago_layout.addWidget(QLabel(tr("Método de Pago") + ":"))

        self.metodo_pago_combo = QComboBox()
        self.metodo_pago_combo.addItem("💵 " + tr("Efectivo"), "efectivo")
        self.metodo_pago_combo.addItem("💳 " + tr("Tarjeta"), "tarjeta")
        self.metodo_pago_combo.addItem("📱 Bizum", "bizum")
        self.metodo_pago_combo.setMinimumWidth(150)
        metodo_pago_layout.addWidget(self.metodo_pago_combo)

        # Info label para aclarar
        info_metodo = QLabel("ℹ️ " + tr("Solo EFECTIVO afecta el saldo de caja"))
        info_metodo.setStyleSheet("color: #D8DEE9; font-size: 11px; font-style: italic;")
        metodo_pago_layout.addWidget(info_metodo)

        metodo_pago_layout.addStretch()
        form_layout.addLayout(metodo_pago_layout)

        # Concepto (motivo del gasto/retiro/pago)
        concepto_layout = QVBoxLayout()
        concepto_layout.addWidget(QLabel(tr("Concepto / Motivo") + ":"))
        self.concepto_input = QLineEdit()
        self.concepto_input.setPlaceholderText("Ej: Pago alquiler diciembre, Retiro para banco, Compra material oficina...")
        concepto_layout.addWidget(self.concepto_input)
        form_layout.addLayout(concepto_layout)

        # Monto
        monto_layout = QHBoxLayout()
        monto_layout.addWidget(QLabel(tr("Monto") + ":"))
        self.monto_input = QDoubleSpinBox()
        self.monto_input.setMinimum(0)
        self.monto_input.setMaximum(999999)
        self.monto_input.setDecimals(2)
        self.monto_input.setSuffix(" €")
        self.monto_input.setValue(0)
        self.monto_input.setMinimumWidth(200)
        monto_layout.addWidget(self.monto_input)
        monto_layout.addStretch()
        form_layout.addLayout(monto_layout)

        # Fecha del movimiento
        fecha_layout = QHBoxLayout()
        fecha_layout.addWidget(QLabel(tr("Fecha") + ":"))
        self.fecha_input = QDateEdit()
        self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setMaximumDate(QDate.currentDate())  # No permitir fechas futuras
        self.fecha_input.setDisplayFormat('dd/MM/yyyy')
        self.fecha_input.setMinimumWidth(150)
        fecha_layout.addWidget(self.fecha_input)
        fecha_info = QLabel("ℹ️ " + tr("Puede registrar movimientos pasados"))
        fecha_info.setStyleSheet("color: #7B88A0; font-size: 11px;")
        fecha_layout.addWidget(fecha_info)
        fecha_layout.addStretch()
        form_layout.addLayout(fecha_layout)

        # Notas
        form_layout.addWidget(QLabel(tr("Notas") + " (" + tr("opcional") + "):"))
        self.notas_input = QTextEdit()
        self.notas_input.setMaximumHeight(60)
        self.notas_input.setPlaceholderText(tr("Notas adicionales..."))
        form_layout.addWidget(self.notas_input)

        # Botón guardar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_guardar = QPushButton("💾 " + tr("Registrar Egreso"))
        btn_guardar.clicked.connect(self.guardar_movimiento)
        apply_btn_danger(btn_guardar)
        btn_layout.addWidget(btn_guardar)

        form_layout.addLayout(btn_layout)

        form_group.setLayout(form_layout)
        layout.addWidget(form_group)

        # Filtros para la tabla
        filtros_layout = QHBoxLayout()

        filtros_layout.addWidget(QLabel(tr("Filtrar") + ":"))

        self.filtro_tipo_combo = QComboBox()
        self.filtro_tipo_combo.addItem(tr("Todos"), "")
        self.filtro_tipo_combo.addItem(tr("Ingresos"), "ingreso")
        self.filtro_tipo_combo.addItem(tr("Egresos"), "egreso")
        self.filtro_tipo_combo.setMaximumWidth(120)
        filtros_layout.addWidget(self.filtro_tipo_combo)

        filtros_layout.addWidget(QLabel(tr("Desde") + ":"))
        self.filtro_fecha_desde = QDateEdit()
        self.filtro_fecha_desde.setDate(QDate.currentDate().addMonths(-1))  # 1 mes atrás
        self.filtro_fecha_desde.setCalendarPopup(True)
        self.filtro_fecha_desde.setDisplayFormat('dd/MM/yyyy')
        self.filtro_fecha_desde.setMaximumWidth(120)
        filtros_layout.addWidget(self.filtro_fecha_desde)

        filtros_layout.addWidget(QLabel(tr("Hasta") + ":"))
        self.filtro_fecha_hasta = QDateEdit()
        self.filtro_fecha_hasta.setDate(QDate.currentDate())
        self.filtro_fecha_hasta.setCalendarPopup(True)
        self.filtro_fecha_hasta.setDisplayFormat('dd/MM/yyyy')
        self.filtro_fecha_hasta.setMaximumWidth(120)
        filtros_layout.addWidget(self.filtro_fecha_hasta)

        self.btn_buscar = QPushButton(tr("Buscar"))
        self.btn_buscar.clicked.connect(self.cargar_movimientos)
        apply_btn_primary(self.btn_buscar)
        set_btn_icon(self.btn_buscar, FluentIcon.SEARCH, color="#5E81AC")
        self.btn_buscar.setMinimumHeight(35)
        filtros_layout.addWidget(self.btn_buscar)

        btn_exportar_csv = QPushButton(tr("Exportar CSV"))
        btn_exportar_csv.clicked.connect(self.exportar_csv)
        apply_btn_success(btn_exportar_csv)
        set_btn_icon(btn_exportar_csv, FluentIcon.DOWNLOAD, color="#A3BE8C")
        filtros_layout.addWidget(btn_exportar_csv)

        filtros_layout.addStretch()

        layout.addLayout(filtros_layout)

        # Tabla de movimientos
        movimientos_label = QLabel(tr("Movimientos Recientes"))
        movimientos_label.setStyleSheet("font-weight: bold; font-size: 14px; padding-top: 10px;")
        layout.addWidget(movimientos_label)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            tr("Fecha"), tr("Tipo"), tr("Método"), tr("Categoría"), tr("Concepto"), tr("Monto"), tr("Saldo"), tr("Ref.")
        ])

        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Fecha
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Tipo
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Método
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Categoría
        header.setSectionResizeMode(4, QHeaderView.Stretch)           # Concepto
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Monto
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Saldo
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Ref

        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSortingEnabled(True)
        
        # Estilo Global de Tabla
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        layout.addWidget(self.tabla)

        # Paginación
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination)

        # Finalizar scroll area
        self.scroll.setWidget(content_widget)
        main_layout.addWidget(self.scroll)

    def actualizar_saldo(self):
        """Actualiza el saldo actual mostrado"""
        saldo = self.caja_manager.obtener_saldo_actual()
        self.saldo_label.setText(f"{saldo:.2f} €")

        # Cambiar color según el saldo
        if saldo < 0:
            self.saldo_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #BF616A; padding: 10px;")
        else:
            self.saldo_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #A3BE8C; padding: 10px;")

        # Mostrar saldo inicial del día (solo de la apertura oficial)
        from PyQt5.QtCore import QDate
        fecha_hoy = QDate.currentDate().toString('yyyy-MM-dd')
        
        # Buscar apertura oficial del día
        apertura_hoy = self.db.fetch_one(
            "SELECT saldo_inicial FROM aperturas_caja WHERE fecha = ?",
            (fecha_hoy,)
        )
        
        if apertura_hoy:
            # Hay apertura oficial de hoy
            self.saldo_inicial_label.setText(f"{tr('Saldo inicial del día')}: {apertura_hoy['saldo_inicial']:.2f} €")
            self.saldo_inicial_label.setStyleSheet("font-size: 12px; color: #7B88A0; padding: 5px;")
        else:
            # Verificar si hay cierre pendiente de días anteriores
            estado_caja, data = self.caja_manager.verificar_estado_caja_completo(fecha_hoy)
            
            if estado_caja == 'cierre_pendiente':
                fecha_pendiente = data['fecha'] if data else 'anterior'
                self.saldo_inicial_label.setText(f"⚠️ {tr('Cierre pendiente del día')} {fecha_pendiente}")
                self.saldo_inicial_label.setStyleSheet("font-size: 12px; color: #D08770; padding: 5px; font-weight: bold;")
            elif estado_caja in ['apertura_requerida', 'apertura_nueva_dia']:
                self.saldo_inicial_label.setText(f"📋 {tr('Apertura de caja pendiente')}")
                self.saldo_inicial_label.setStyleSheet("font-size: 12px; color: #5E81AC; padding: 5px; font-weight: bold;")
            else:
                # Estado OK pero sin apertura formal (primera vez o situación rara)
                totales = self.caja_manager.calcular_totales_dia(fecha_hoy)
                self.saldo_inicial_label.setText(f"{tr('Saldo inicial del día')}: {totales['saldo_inicial']:.2f} €")
                self.saldo_inicial_label.setStyleSheet("font-size: 12px; color: #7B88A0; padding: 5px;")

    def guardar_movimiento(self):
        """Guarda un nuevo egreso en caja"""
        if not self.concepto_input.text().strip():
            notify_warning(self, tr("Error"), tr("Debe ingresar un concepto/motivo"))
            return

        if self.monto_input.value() <= 0:
            notify_warning(self, tr("Error"), tr("El monto debe ser mayor a 0"))
            return

        # Generar categoría basada en el tipo de egreso
        tipo_egreso = self.tipo_egreso_combo.currentText()  # "Gastos", "Retiros", "Pagos"

        datos = {
            'tipo': 'egreso',  # Siempre egreso (los ingresos se registran automáticamente)
            'categoria': tipo_egreso,  # Gastos, Retiros o Pagos
            'concepto': self.concepto_input.text().strip(),
            'monto': self.monto_input.value(),
            'fecha': self.fecha_input.date().toString('yyyy-MM-dd'),  # Fecha seleccionada (puede ser retroactiva)
            'notas': self.notas_input.toPlainText().strip(),
            'metodo_pago': self.metodo_pago_combo.currentData()
        }

        # VALIDAR SALDO NEGATIVO si es egreso en efectivo
        if datos['metodo_pago'] == 'efectivo':
            saldo_actual = self.caja_manager.obtener_saldo_actual()
            nuevo_saldo = saldo_actual - datos['monto']

            if nuevo_saldo < 0:
                if not ask_confirm(self, tr("Saldo Negativo"),
                    f"⚠️ {tr('ADVERTENCIA')}: {tr('Esta operación dejará el saldo de caja NEGATIVO')}\n\n"
                    f"{tr('Saldo actual')}: {saldo_actual:.2f} €\n"
                    f"{tr('Egreso')}: {datos['monto']:.2f} €\n"
                    f"{tr('Saldo Resultante')}: {nuevo_saldo:.2f} €\n\n"
                    f"{tr('¿Está seguro de continuar?')}"):
                    return  # Cancelar operación

        try:
            movimiento_id = self.caja_manager.registrar_movimiento(datos)

            if movimiento_id:
                notify_success(
                    self,
                    tr("Éxito"),
                    tr("Movimiento registrado correctamente") + "\n\n"
                    + tr("Tipo") + f": {datos['tipo'].upper()}\n"
                    + tr("Monto") + f": {datos['monto']:.2f} €"
                )

                self.limpiar_formulario()
                self.actualizar_saldo()
                self.cargar_movimientos()
            else:
                notify_error(self, tr("Error"), tr("No se pudo registrar el movimiento"))
        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al guardar") + f":\n{str(e)}")

    def _on_page_changed(self, offset, limit):
        """Callback cuando cambia la página"""
        self.cargar_movimientos()

    def cargar_movimientos(self):
        """Carga los movimientos con paginación"""
        filtros = {}

        tipo = self.filtro_tipo_combo.currentData()
        if tipo:
            filtros['tipo'] = tipo

        filtros['fecha_desde'] = self.filtro_fecha_desde.date().toString('yyyy-MM-dd')
        filtros['fecha_hasta'] = self.filtro_fecha_hasta.date().toString('yyyy-MM-dd')

        logger.debug(f"Filtros aplicados: {filtros}")

        movimientos, total = self.caja_manager.obtener_movimientos_paginado(
            filtros, limit=self.pagination.limit, offset=self.pagination.offset
        )
        self.pagination.update_total(total)
        logger.debug(f"Movimientos encontrados: {len(movimientos)}")

        self.tabla.setRowCount(0)

        for mov in movimientos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Fecha
            fecha_item = QTableWidgetItem(mov['fecha'])
            fecha_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, fecha_item)

            # Tipo con color
            tipo_item = QTableWidgetItem(mov['tipo'].upper())
            if mov['tipo'] == 'ingreso':
                tipo_item.setForeground(QColor('#A3BE8C'))
            else:
                tipo_item.setForeground(QColor('#BF616A'))
            tipo_item.setTextAlignment(Qt.AlignCenter)
            tipo_item.setFont(QFont("", -1, QFont.Bold))
            self.tabla.setItem(row, 1, tipo_item)

            # Método de pago
            metodo = mov.get('metodo_pago', 'efectivo')
            metodo_icons = {'efectivo': '💵', 'tarjeta': '💳', 'bizum': '📱'}
            met_text = f"{metodo_icons.get(metodo, '💵')} {metodo.capitalize()}"
            metodo_item = QTableWidgetItem(met_text)
            metodo_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, metodo_item)

            # Categoría
            cat_item = QTableWidgetItem(mov['categoria'] or tr('N/A'))
            cat_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, cat_item)

            # Concepto
            concepto_text = mov['concepto']
            if mov['notas']:
                concepto_text += f" ({mov['notas'][:30]}...)" if len(mov['notas']) > 30 else f" ({mov['notas']})"
            concepto_item = QTableWidgetItem(concepto_text)
            concepto_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, concepto_item)

            # Monto con color
            monto_item = QTableWidgetItem(f"{float(mov['monto']):.2f} €")
            if mov['tipo'] == 'ingreso':
                monto_item.setForeground(QColor('#A3BE8C'))
            else:
                monto_item.setForeground(QColor('#BF616A'))
            monto_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 5, monto_item)

            # Saldo nuevo
            saldo_item = QTableWidgetItem(f"{float(mov['saldo_nuevo']):.2f} €")
            saldo_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 6, saldo_item)

            # Referencia
            ref_text = "Manual"
            if mov['referencia_tipo']:
                ref_text = f"{mov['referencia_tipo'].upper()}"
            ref_item = QTableWidgetItem(ref_text)
            ref_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 7, ref_item)

    def exportar_csv(self):
        """Exporta los movimientos actuales a un archivo CSV"""
        import csv
        from datetime import datetime

        if self.tabla.rowCount() == 0:
            notify_warning(self, tr("Sin datos"), tr("No hay movimientos para exportar"))
            return

        # Diálogo para elegir ubicación
        fecha_desde = self.filtro_fecha_desde.date().toString('yyyy-MM-dd')
        fecha_hasta = self.filtro_fecha_hasta.date().toString('yyyy-MM-dd')
        nombre_sugerido = f"movimientos_caja_{fecha_desde}_a_{fecha_hasta}.csv"

        ruta, _ = QFileDialog.getSaveFileName(
            self,
            tr("Exportar Movimientos a CSV"),
            nombre_sugerido,
            tr("Archivos CSV") + " (*.csv)"
        )

        if not ruta:
            return  # Usuario canceló

        try:
            # Obtener datos de la base de datos
            filtros = {
                'fecha_desde': fecha_desde,
                'fecha_hasta': fecha_hasta
            }
            movimientos = self.caja_manager.obtener_movimientos(filtros)

            # Escribir CSV
            with open(ruta, 'w', newline='', encoding='utf-8-sig') as f:  # utf-8-sig para Excel
                writer = csv.writer(f, delimiter=';')  # Punto y coma para Excel español

                # Encabezados
                writer.writerow([
                    'Fecha', 'Tipo', 'Método', 'Categoría', 'Concepto',
                    'Monto', 'Saldo Anterior', 'Saldo Nuevo', 'Referencia', 'Notas'
                ])

                # Datos
                for mov in movimientos:
                    writer.writerow([
                        mov['fecha'],
                        mov['tipo'].upper(),
                        mov.get('metodo_pago', 'N/A').capitalize(),
                        mov.get('categoria', 'N/A'),
                        mov.get('concepto', 'N/A'),
                        f"{float(mov['monto']):.2f}",
                        f"{float(mov.get('saldo_anterior', 0)):.2f}",
                        f"{float(mov.get('saldo_nuevo', 0)):.2f}",
                        f"{mov.get('referencia_tipo', '')} {mov.get('referencia_id', '')}".strip(),
                        mov.get('notas', '')
                    ])

            notify_success(
                self,
                tr("Exportado"),
                tr("Movimientos exportados exitosamente a") + f":\n{ruta}\n\n"
                + tr("Total de registros") + f": {len(movimientos)}"
            )

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(
                self,
                tr("Error al exportar"),
                tr("No se pudo exportar el archivo") + f":\n{str(e)}"
            )

    def limpiar_formulario(self):
        """Limpia el formulario de nuevo egreso"""
        self.concepto_input.clear()
        self.monto_input.setValue(0)
        self.fecha_input.setDate(QDate.currentDate())  # Resetear a hoy
        self.notas_input.clear()
        self.metodo_pago_combo.setCurrentIndex(0)  # Resetear a efectivo
        self.tipo_egreso_combo.setCurrentIndex(0)  # Resetear a Gastos
        self.concepto_input.setFocus()  # Poner foco en concepto

    def abrir_caja(self):
        """Abre la caja del día actual"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QDoubleSpinBox
        from PyQt5.QtCore import QDate

        # Verificar permisos y pedir contraseña (OBLIGATORIO)
        if not self.auth_manager:
            notify_warning(
                self,
                tr("Error de Seguridad"),
                tr("No se puede verificar permisos.") + "\n" +
                tr("Sistema de autenticación no disponible.")
            )
            return

        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

        if not confirmar_accion_sensible(
            self.auth_manager,
            'caja.abrir',
            tr('Abrir Caja'),
            tr("¿Abrir la caja del día de hoy?") + "\n\n" +
            tr("Esta acción registrará una nueva apertura de caja."),
            self
        ):
            return

        fecha_hoy = QDate.currentDate().toString('yyyy-MM-dd')

        # Verificar si ya existe apertura para hoy
        if self.caja_manager.verificar_apertura_existente(fecha_hoy):
            notify_success(
                self,
                tr("Caja Ya Abierta"),
                tr("La caja de hoy ya está abierta.")
            )
            return

        # Verificar si hay cierre pendiente de día anterior
        apertura_pendiente = self.caja_manager.obtener_apertura_sin_cierre()
        if apertura_pendiente and apertura_pendiente['fecha'] != fecha_hoy:
            notify_warning(
                self,
                tr("Cierre Pendiente"),
                tr("Antes de abrir la caja de hoy, debe cerrar la caja del día") + f" {apertura_pendiente['fecha']}.\n\n" +
                tr("Use el botón 'Cerrar Caja' para cerrar el día pendiente.")
            )
            return

        # Sugerir saldo basado en último cierre
        ultimo_cierre = self.caja_manager.obtener_ultimo_cierre()
        saldo_sugerido = ultimo_cierre['saldo_efectivo_contado'] if ultimo_cierre else 0.0

        # Diálogo para ingresar saldo inicial
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Apertura de Caja") + f" - {fecha_hoy}")
        dialog.setMinimumWidth(350)

        layout = QVBoxLayout(dialog)

        info_label = QLabel(tr("Ingrese el saldo inicial para abrir la caja de hoy:"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        saldo_layout = QHBoxLayout()
        saldo_layout.addWidget(QLabel(tr("Saldo Inicial") + ":"))
        saldo_input = QDoubleSpinBox()
        saldo_input.setMinimum(0)
        saldo_input.setMaximum(999999)
        saldo_input.setDecimals(2)
        saldo_input.setSuffix(" €")
        saldo_input.setValue(saldo_sugerido)
        saldo_input.setMinimumWidth(150)
        saldo_layout.addWidget(saldo_input)
        saldo_layout.addStretch()
        layout.addLayout(saldo_layout)

        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(dialog.reject)
        apply_btn_cancel(btn_cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_abrir = QPushButton(tr("Abrir Caja"))
        btn_abrir.clicked.connect(dialog.accept)
        apply_btn_success(btn_abrir)
        btn_layout.addWidget(btn_abrir)
        layout.addLayout(btn_layout)

        if dialog.exec_() == QDialog.Accepted:
            datos_apertura = {
                'fecha': fecha_hoy,
                'saldo_inicial': saldo_input.value(),
                'notas': tr('Apertura manual desde Movimientos')
            }

            apertura_id = self.caja_manager.registrar_apertura(datos_apertura)

            if apertura_id:
                notify_success(
                    self,
                    tr("Caja Abierta"),
                    tr("La caja de hoy ha sido abierta correctamente.") + "\n\n" +
                    tr("Saldo Inicial") + f": {saldo_input.value():.2f} €"
                )
                self.actualizar_saldo()
            else:
                notify_error(self, tr("Error"), tr("No se pudo abrir la caja"))

    def cerrar_caja(self):
        """Cierra la caja - detecta automáticamente qué día cerrar"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QTextEdit
        from PyQt5.QtCore import QDate

        # Verificar permisos y pedir contraseña (OBLIGATORIO)
        if not self.auth_manager:
            notify_warning(
                self,
                tr("Error de Seguridad"),
                tr("No se puede verificar permisos.") + "\n" +
                tr("Sistema de autenticación no disponible.")
            )
            return

        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

        if not confirmar_accion_sensible(
            self.auth_manager,
            'caja.cerrar',
            tr('Cerrar Caja'),
            tr("¿Cerrar la caja?") + "\n\n" +
            tr("Esta acción registrará el cierre de caja."),
            self
        ):
            return

        fecha_hoy = QDate.currentDate().toString('yyyy-MM-dd')

        # Buscar apertura sin cierre (puede ser de hoy o de un día anterior)
        apertura_pendiente = self.caja_manager.obtener_apertura_sin_cierre()

        if not apertura_pendiente:
            notify_success(
                self,
                tr("Sin Caja Abierta"),
                tr("No hay ninguna caja abierta para cerrar.")
            )
            return

        fecha_cierre = apertura_pendiente['fecha']

        # Verificar si ya existe cierre para esa fecha
        if self.caja_manager.verificar_cierre_existente(fecha_cierre):
            notify_success(
                self,
                tr("Ya Cerrada"),
                tr("La caja del día") + f" {fecha_cierre} " + tr("ya está cerrada.")
            )
            return

        # Calcular totales del día a cerrar
        totales = self.caja_manager.calcular_totales_dia(fecha_cierre)

        # Diálogo de cierre
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Cierre de Caja") + f" - {fecha_cierre}")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # Info del día
        if fecha_cierre != fecha_hoy:
            aviso = QLabel(f"⚠️ {tr('Cerrando caja de día ANTERIOR')}: {fecha_cierre}")
            aviso.setStyleSheet("color: #EBCB8B; font-weight: bold; padding: 10px;")
            layout.addWidget(aviso)

        # Resumen
        resumen = QLabel(
            f"<b>{tr('Resumen del día')} {fecha_cierre}:</b><br><br>"
            f"{tr('Saldo Inicial')}: {totales['saldo_inicial']:.2f} €<br>"
            f"{tr('Total Ingresos')}: <span style='color:#A3BE8C'>+{totales['total_ingresos']:.2f} €</span><br>"
            f"{tr('Total Egresos')}: <span style='color:#BF616A'>-{totales['total_egresos']:.2f} €</span><br>"
            f"<br><b>{tr('Saldo Esperado')}: {totales['saldo_esperado']:.2f} €</b>"
        )
        resumen.setStyleSheet("background-color: #2E3440; padding: 15px; border-radius: 5px;")
        layout.addWidget(resumen)

        # Efectivo contado
        efectivo_layout = QHBoxLayout()
        efectivo_layout.addWidget(QLabel(tr("Efectivo Contado") + ":"))
        efectivo_input = QDoubleSpinBox()
        efectivo_input.setMinimum(0)
        efectivo_input.setMaximum(999999)
        efectivo_input.setDecimals(2)
        efectivo_input.setSuffix(" €")
        efectivo_input.setValue(totales['saldo_esperado'])
        efectivo_input.setMinimumWidth(150)
        efectivo_layout.addWidget(efectivo_input)
        efectivo_layout.addStretch()
        layout.addLayout(efectivo_layout)

        # Notas
        layout.addWidget(QLabel(tr("Notas") + ":"))
        notas_input = QTextEdit()
        notas_input.setMaximumHeight(60)
        notas_input.setPlaceholderText(tr("Notas sobre el cierre..."))
        layout.addWidget(notas_input)

        # Botones
        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(dialog.reject)
        apply_btn_cancel(btn_cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_cerrar = QPushButton(tr("Realizar Cierre"))
        btn_cerrar.clicked.connect(dialog.accept)
        apply_btn_danger(btn_cerrar)
        btn_layout.addWidget(btn_cerrar)
        layout.addLayout(btn_layout)

        if dialog.exec_() == QDialog.Accepted:
            efectivo_contado = efectivo_input.value()
            diferencia = efectivo_contado - totales['saldo_esperado']

            # Confirmar si hay diferencia
            if abs(diferencia) > 0.01:
                if not ask_confirm(self, tr("Confirmar Diferencia"), tr("Hay una diferencia de") + f" {diferencia:+.2f} €\n\n" +
                    tr("¿Desea continuar con el cierre?")):
                    return


            # Obtener usuario actual para auditoría
            usuario_id = None
            if self.auth_manager:
                usuario_actual = self.auth_manager.obtener_usuario_actual()
                if usuario_actual:
                    usuario_id = usuario_actual.get('id')

            datos_cierre = {
                'fecha': fecha_cierre,
                'efectivo_contado': efectivo_contado,
                'notas': notas_input.toPlainText(),
                'usuario_id': usuario_id
            }


            cierre_id = self.caja_manager.realizar_cierre(datos_cierre)

            if cierre_id:
                mensaje = (
                    tr("Cierre de caja realizado correctamente.") + "\n\n" +
                    tr("Fecha") + f": {fecha_cierre}\n" +
                    tr("Efectivo Contado") + f": {efectivo_contado:.2f} €\n" +
                    tr("Diferencia") + f": {diferencia:+.2f} €"
                )

                # Si cerró un día anterior, añadir aviso en el mismo mensaje
                if fecha_cierre != fecha_hoy:
                    if not self.caja_manager.verificar_apertura_existente(fecha_hoy):
                        mensaje += (
                            "\n\n" + tr("Ha cerrado la caja de un día anterior.") +
                            "\n" + tr("Ahora puede abrir la caja de hoy usando el botón") +
                            " 🔓 " + tr("Abrir Caja")
                        )

                notify_success(self, tr("Caja Cerrada"), mensaje)

                self.actualizar_saldo()
                self.cargar_movimientos()
            else:
                notify_error(self, tr("Error"), tr("No se pudo realizar el cierre"))

    def _ofrecer_apertura_hoy(self, saldo_sugerido):
        """Notifica al usuario que puede abrir la caja de hoy"""
        from PyQt5.QtCore import QDate

        fecha_hoy = QDate.currentDate().toString('yyyy-MM-dd')

        if self.caja_manager.verificar_apertura_existente(fecha_hoy):
            return

        # Solo notificación - el usuario usará el botón Abrir Caja
        notify_success(
            self,
            tr("Apertura de Caja"),
            tr("Ha cerrado la caja de un día anterior.") + "\n\n" +
            tr("Ahora puede abrir la caja de hoy usando el botón") + " 🔓 " + tr("Abrir Caja")
        )

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
