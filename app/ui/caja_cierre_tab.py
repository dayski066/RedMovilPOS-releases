"""
Pestaña para cierres de caja diarios
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
                             QDateEdit, QHeaderView, QTextEdit, QDoubleSpinBox,
                             QScrollArea, QFrame)
from PyQt5.QtCore import QDate, Qt, QTimer
from PyQt5.QtGui import QColor
from app.i18n import tr
from app.db.database import Database
from app.modules.caja_manager import CajaManager
from config import CIERRE_TOLERANCIA_MAXIMA
from app.ui.confirmar_accion_dialog import ConfirmarAccionDialog
from app.ui.transparent_buttons import apply_btn_success, apply_btn_danger, apply_btn_cancel, apply_btn_warning, apply_btn_primary, set_btn_icon
from qfluentwidgets import FluentIcon


class CajaCierreTab(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.caja_manager = CajaManager(self.db)
        self.totales_dia = None
        self.setup_ui()
        # Inicializar datos SIN mostrar diálogos (el aviso de caja pendiente
        # se mostrará desde MainWindow después de que esté visible)
        self.calcular_totales(mostrar_avisos=False)
        self.cargar_cierres()

    def setup_ui(self):
        # Layout principal
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.NoFrame)
        
        # Widget contenedor
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_label = QLabel(tr("Cierre de Caja Diario"))
        header_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: #ffffff;")
        layout.addWidget(header_label)

        # Selector de fecha (editable para poder cerrar días anteriores)
        fecha_layout = QHBoxLayout()
        fecha_layout.addWidget(QLabel(tr("Fecha del Cierre") + ":"))
        self.fecha_input = QDateEdit()
        self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setMaximumDate(QDate.currentDate())  # No permitir fechas futuras
        self.fecha_input.setMaximumWidth(150)
        self.fecha_input.dateChanged.connect(self._on_fecha_changed)
        fecha_layout.addWidget(self.fecha_input)

        # Botón para detectar día pendiente
        btn_detectar = QPushButton(tr("Detectar Pendiente"))
        btn_detectar.clicked.connect(self.detectar_dia_pendiente)
        apply_btn_warning(btn_detectar)
        btn_detectar.setToolTip(tr("Buscar si hay un día anterior sin cerrar"))
        fecha_layout.addWidget(btn_detectar)

        btn_calcular = QPushButton(tr("Calcular Totales"))
        btn_calcular.clicked.connect(self.calcular_totales)
        apply_btn_primary(btn_calcular)
        fecha_layout.addWidget(btn_calcular)

        fecha_layout.addStretch()
        layout.addLayout(fecha_layout)

        # Resumen del día con tarjetas por método de pago
        resumen_group = QGroupBox(tr("Resumen del Día"))
        resumen_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        resumen_layout = QVBoxLayout()

        # Saldo inicial
        self.saldo_inicial_label = QLabel(tr("Saldo Inicial") + ": " + tr("Calculando..."))
        self.saldo_inicial_label.setStyleSheet("font-size: 14px; padding: 8px; color: #D8DEE9;")
        resumen_layout.addWidget(self.saldo_inicial_label)

        # === TARJETAS DE INGRESOS POR MÉTODO ===
        cards_frame = QFrame()
        cards_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2E3440, stop:1 #3B4252);
                border-radius: 10px;
                padding: 15px;
            }
        """)
        cards_layout = QHBoxLayout(cards_frame)
        cards_layout.setSpacing(15)

        # Tarjeta Efectivo
        self.card_efectivo = self._crear_card_metodo("💵", tr("Efectivo"), "#A3BE8C")
        cards_layout.addWidget(self.card_efectivo)

        # Tarjeta Tarjeta
        self.card_tarjeta = self._crear_card_metodo("💳", tr("Tarjeta"), "#5E81AC")
        cards_layout.addWidget(self.card_tarjeta)

        # Tarjeta Bizum
        self.card_bizum = self._crear_card_metodo("📱", "Bizum", "#B48EAD")
        cards_layout.addWidget(self.card_bizum)

        resumen_layout.addWidget(cards_frame)

        # Total egresos y saldo esperado
        self.total_egresos_label = QLabel(tr("Total Egresos") + ": " + tr("Calculando..."))
        self.total_egresos_label.setStyleSheet("font-size: 14px; padding: 8px; color: #BF616A;")
        resumen_layout.addWidget(self.total_egresos_label)

        self.saldo_esperado_label = QLabel(tr("Saldo Esperado") + ": " + tr("Calculando..."))
        self.saldo_esperado_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 10px; color: #88C0D0; "
            "background-color: #2E3440; border-radius: 5px; border: 1px solid #4C566A;"
        )
        resumen_layout.addWidget(self.saldo_esperado_label)

        resumen_group.setLayout(resumen_layout)
        layout.addWidget(resumen_group)

        # Efectivo contado
        efectivo_group = QGroupBox(tr("Efectivo Contado"))
        efectivo_layout = QVBoxLayout()

        efectivo_form_layout = QHBoxLayout()
        efectivo_form_layout.addWidget(QLabel(tr("Efectivo Real en Caja") + ":"))
        self.efectivo_contado_input = QDoubleSpinBox()
        self.efectivo_contado_input.setMinimum(0)
        self.efectivo_contado_input.setMaximum(999999)
        self.efectivo_contado_input.setDecimals(2)
        self.efectivo_contado_input.setSuffix(" €")
        self.efectivo_contado_input.setValue(0)
        self.efectivo_contado_input.setMinimumWidth(150)
        self.efectivo_contado_input.valueChanged.connect(self.calcular_diferencia)
        efectivo_form_layout.addWidget(self.efectivo_contado_input)
        efectivo_form_layout.addStretch()

        efectivo_layout.addLayout(efectivo_form_layout)

        # Diferencia calculada
        self.diferencia_label = QLabel(tr("Diferencia") + ": 0.00 €")
        self.diferencia_label.setStyleSheet(
            "font-size: 18px; font-weight: bold; padding: 15px; color: #ffffff; "
            "background-color: #2E3440; border-radius: 5px; border: 1px solid #4C566A;"
        )
        self.diferencia_label.setAlignment(Qt.AlignCenter)
        efectivo_layout.addWidget(self.diferencia_label)

        efectivo_group.setLayout(efectivo_layout)
        layout.addWidget(efectivo_group)

        # Notas
        notas_layout = QVBoxLayout()
        notas_layout.addWidget(QLabel(tr("Notas / Observaciones") + ":"))
        self.notas_input = QTextEdit()
        self.notas_input.setMaximumHeight(80)
        self.notas_input.setPlaceholderText(tr("Añadir notas sobre el cierre, especialmente si hay diferencia..."))
        notas_layout.addWidget(self.notas_input)
        layout.addLayout(notas_layout)

        # Botón de guardar cierre
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_guardar = QPushButton("💾 " + tr("Realizar Cierre de Caja"))
        self.btn_guardar.clicked.connect(self.realizar_cierre)
        apply_btn_success(self.btn_guardar)
        btn_layout.addWidget(self.btn_guardar)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Historial de cierres
        historial_label = QLabel(tr("Historial de Cierres"))
        historial_label.setStyleSheet("font-weight: bold; font-size: 14px; padding-top: 20px; color: #ffffff;")
        layout.addWidget(historial_label)

        # Filtros de historial
        filtros_layout = QHBoxLayout()

        filtros_layout.addWidget(QLabel(tr("Desde") + ":"))
        self.filtro_fecha_desde = QDateEdit()
        self.filtro_fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.filtro_fecha_desde.setCalendarPopup(True)
        self.filtro_fecha_desde.setMaximumWidth(120)
        filtros_layout.addWidget(self.filtro_fecha_desde)

        filtros_layout.addWidget(QLabel(tr("Hasta") + ":"))
        self.filtro_fecha_hasta = QDateEdit()
        self.filtro_fecha_hasta.setDate(QDate.currentDate())
        self.filtro_fecha_hasta.setCalendarPopup(True)
        self.filtro_fecha_hasta.setMaximumWidth(120)
        filtros_layout.addWidget(self.filtro_fecha_hasta)

        btn_buscar = QPushButton(tr("Buscar"))
        btn_buscar.clicked.connect(self.cargar_cierres)
        apply_btn_primary(btn_buscar)
        set_btn_icon(btn_buscar, FluentIcon.SEARCH, color="#5E81AC")
        filtros_layout.addWidget(btn_buscar)

        filtros_layout.addStretch()
        layout.addLayout(filtros_layout)

        # Tabla de cierres
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            tr("Fecha"), tr("Saldo Inicial"), tr("Ingresos"), tr("Egresos"),
            tr("Esperado"), tr("Contado"), tr("Diferencia"), tr("Usuario")
        ])

        header = self.tabla.horizontalHeader()
        for i in range(8):
            header.setSectionResizeMode(i, QHeaderView.Stretch if i in [0, 7] else QHeaderView.ResizeToContents)

        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSortingEnabled(True)
        
        # Estilo Global de Tabla
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")
        self.tabla.setMinimumHeight(300) # Un poco más para alojar filas de 60px
        self.tabla.setMaximumHeight(400)
        self.tabla.cellDoubleClicked.connect(self.mostrar_detalles_cierre)

        layout.addWidget(self.tabla)

        # Finalizar scroll area
        self.scroll.setWidget(content_widget)
        main_layout.addWidget(self.scroll)

    def _crear_card_metodo(self, icono, titulo, color):
        """Crea una tarjeta para mostrar ingresos por método de pago"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(3)

        # Título
        header = QLabel(f"{icono} {titulo}")
        header.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # Total
        total_label = QLabel("0.00 €")
        total_label.setObjectName("total")
        total_label.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        layout.addWidget(total_label)

        # Desglose
        desglose_frame = QFrame()
        desglose_frame.setStyleSheet("background: transparent;")
        desglose_layout = QVBoxLayout(desglose_frame)
        desglose_layout.setContentsMargins(0, 5, 0, 0)
        desglose_layout.setSpacing(2)

        tpv_label = QLabel("TPV: 0.00 €")
        tpv_label.setObjectName("tpv")
        tpv_label.setStyleSheet("color: #7B88A0; font-size: 11px;")
        desglose_layout.addWidget(tpv_label)

        ventas_label = QLabel("Ventas: 0.00 €")
        ventas_label.setObjectName("ventas")
        ventas_label.setStyleSheet("color: #7B88A0; font-size: 11px;")
        desglose_layout.addWidget(ventas_label)

        rep_label = QLabel("Reparaciones: 0.00 €")
        rep_label.setObjectName("reparaciones")
        rep_label.setStyleSheet("color: #7B88A0; font-size: 11px;")
        desglose_layout.addWidget(rep_label)

        layout.addWidget(desglose_frame)

        return card

    def _on_fecha_changed(self):
        """Manejador cuando el usuario cambia la fecha manualmente - NO auto-detectar"""
        self.calcular_totales(auto_detectar=False)

    def _actualizar_card_metodo(self, card, datos):
        """Actualiza los valores de una tarjeta de método de pago"""
        total_label = card.findChild(QLabel, "total")
        tpv_label = card.findChild(QLabel, "tpv")
        ventas_label = card.findChild(QLabel, "ventas")
        rep_label = card.findChild(QLabel, "reparaciones")

        if total_label:
            total_label.setText(f"{datos['total']:.2f} €")
        if tpv_label:
            tpv_label.setText(f"TPV: {datos['tpv']:.2f} €")
        if ventas_label:
            ventas_label.setText(f"Ventas: {datos['ventas']:.2f} €")
        if rep_label:
            rep_label.setText(f"Reparaciones: {datos['reparaciones']:.2f} €")

    def calcular_totales(self, auto_detectar=True, mostrar_avisos=True):
        """Calcula los totales del día seleccionado

        Args:
            auto_detectar: Si True, detecta automáticamente días pendientes
            mostrar_avisos: Si True, muestra avisos al usuario (False durante inicialización)
        """
        fecha = self.fecha_input.date().toString('yyyy-MM-dd')
        fecha_hoy = QDate.currentDate().toString('yyyy-MM-dd')

        # AUTO-DETECTAR: Si la fecha es hoy y no hay apertura de hoy, buscar día pendiente
        if auto_detectar and fecha == fecha_hoy:
            apertura_pendiente = self.caja_manager.obtener_apertura_sin_cierre()
            if apertura_pendiente and apertura_pendiente['fecha'] != fecha_hoy:
                # Hay un día anterior pendiente de cerrar - solo notificar si mostrar_avisos=True
                if mostrar_avisos:
                    fecha_pendiente = apertura_pendiente['fecha']
                    notify_warning(
                        self,
                        tr("Cierre de Caja Pendiente"),
                        tr("Hay una caja del día") + f" {fecha_pendiente} " + tr("sin cerrar.") + "\n\n" +
                        tr("Debe cerrar esa caja antes de continuar.") + "\n\n" +
                        "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n" +
                        "👉 " + tr("Use el botón") + " 🔒 " + tr("Cerrar Caja")
                    )
                return

        # Verificar si ya existe un cierre para esta fecha
        if self.caja_manager.verificar_cierre_existente(fecha):
            if mostrar_avisos:
                notify_warning(
                    self,
                    tr("Cierre Existente"),
                    tr("Ya existe un cierre de caja para la fecha") + f" {fecha}.\n\n" +
                    tr("Seleccione otra fecha para realizar un nuevo cierre.")
                )
            self.btn_guardar.setEnabled(False)
            self.saldo_inicial_label.setText(tr("Saldo Inicial") + ": " + tr("Ya cerrado"))
            self.total_egresos_label.setText(tr("Total Egresos") + ": " + tr("Ya cerrado"))
            self.saldo_esperado_label.setText(tr("Saldo Esperado") + ": " + tr("Ya cerrado"))
            return

        self.btn_guardar.setEnabled(True)

        try:
            self.totales_dia = self.caja_manager.calcular_totales_dia(fecha)

            # Obtener desglose por método de pago
            ingresos_metodo = self.caja_manager.calcular_ingresos_por_metodo(fecha)

            self.saldo_inicial_label.setText(f"{tr('Saldo Inicial')}: {self.totales_dia['saldo_inicial']:.2f} €")

            # Actualizar tarjetas de métodos de pago
            if ingresos_metodo:
                self._actualizar_card_metodo(self.card_efectivo, ingresos_metodo.get('efectivo', {'total': 0, 'tpv': 0, 'ventas': 0, 'reparaciones': 0}))
                self._actualizar_card_metodo(self.card_tarjeta, ingresos_metodo.get('tarjeta', {'total': 0, 'tpv': 0, 'ventas': 0, 'reparaciones': 0}))
                self._actualizar_card_metodo(self.card_bizum, ingresos_metodo.get('bizum', {'total': 0, 'tpv': 0, 'ventas': 0, 'reparaciones': 0}))

            self.total_egresos_label.setText(f"{tr('Total Egresos')}: {self.totales_dia['total_egresos']:.2f} €")
            self.total_egresos_label.setStyleSheet("font-size: 14px; padding: 8px; color: #BF616A;")

            self.saldo_esperado_label.setText(f"{tr('Saldo Esperado')}: {self.totales_dia['saldo_esperado']:.2f} €")

            # Sugerir el saldo esperado como efectivo contado
            self.efectivo_contado_input.setValue(self.totales_dia['saldo_esperado'])
        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al calcular totales") + f":\n{str(e)}")

    def calcular_diferencia(self):
        """Calcula la diferencia entre efectivo contado y esperado"""
        if not self.totales_dia:
            return

        efectivo_contado = self.efectivo_contado_input.value()
        diferencia = efectivo_contado - self.totales_dia['saldo_esperado']

        self.diferencia_label.setText(f"{tr('Diferencia')}: {diferencia:+.2f} €")

        # Cambiar color según la diferencia - DARK MODE
        if abs(diferencia) < 0.01:  # Menor a 1 céntimo
            self.diferencia_label.setStyleSheet(
                "font-size: 18px; font-weight: bold; padding: 15px; "
                "background-color: rgba(163, 190, 140, 0.15); color: #A3BE8C; border-radius: 5px; border: 1px solid #A3BE8C;"
            )
        elif diferencia > 0:
            self.diferencia_label.setStyleSheet(
                "font-size: 18px; font-weight: bold; padding: 15px; "
                "background-color: rgba(235, 203, 139, 0.15); color: #EBCB8B; border-radius: 5px; border: 1px solid #EBCB8B;"
            )
        else:
            self.diferencia_label.setStyleSheet(
                "font-size: 18px; font-weight: bold; padding: 15px; "
                "background-color: rgba(191, 97, 106, 0.15); color: #BF616A; border-radius: 5px; border: 1px solid #BF616A;"
            )

    def realizar_cierre(self):
        """Realiza el cierre de caja"""
        if not self.totales_dia:
            notify_warning(self, tr("Error"), tr("Primero debe calcular los totales del día"))
            return

        fecha_cierre = self.fecha_input.date().toString('yyyy-MM-dd')

        # VERIFICAR que NO exista ya un cierre para esta fecha (doble verificación por seguridad)
        if self.caja_manager.verificar_cierre_existente(fecha_cierre):
            notify_warning(
                self,
                tr("Cierre Duplicado"),
                tr("Ya existe un cierre de caja para la fecha") + f" {fecha_cierre}.\n\n" +
                tr("No se puede cerrar dos veces el mismo día.")
            )
            return

        fecha_hoy = QDate.currentDate().toString('yyyy-MM-dd')

        # VERIFICAR apertura: buscar apertura para el día seleccionado O apertura pendiente
        apertura = self.caja_manager.db.fetch_one(
            "SELECT id, fecha FROM aperturas_caja WHERE fecha = ?",
            (fecha_cierre,)
        )

        # Si no hay apertura para la fecha seleccionada, buscar apertura pendiente
        apertura_pendiente = None
        if not apertura:
            apertura_pendiente = self.caja_manager.obtener_apertura_sin_cierre()

            # Si hay una apertura pendiente de OTRA fecha, solo notificar
            if apertura_pendiente and apertura_pendiente['fecha'] != fecha_cierre:
                fecha_pendiente = apertura_pendiente['fecha']
                notify_warning(
                    self,
                    tr("Cierre de Caja Pendiente"),
                    tr("Hay una caja del día") + f" {fecha_pendiente} " + tr("sin cerrar.") + "\n\n" +
                    tr("Debe cerrar esa caja antes de continuar.") + "\n\n" +
                    "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n" +
                    "👉 " + tr("Use el botón") + " 🔒 " + tr("Cerrar Caja")
                )
                return

        # Si no hay apertura, verificar si hay movimientos de ese día
        movimientos_del_dia = self.caja_manager.db.fetch_one(
            "SELECT COUNT(*) as total FROM caja_movimientos WHERE fecha = ?",
            (fecha_cierre,)
        )
        tiene_movimientos = movimientos_del_dia and movimientos_del_dia['total'] > 0

        # Solo bloquear si NO hay ni apertura ni movimientos
        if not apertura and not tiene_movimientos:
            notify_warning(
                self,
                tr("Sin Datos para Cerrar"),
                tr("No existe apertura ni movimientos para el") + f" {fecha_cierre}.\n\n" +
                tr("No hay nada que cerrar para esta fecha.") + "\n\n" +
                tr("Tip: Use el botón 'Detectar Pendiente' para encontrar días sin cerrar.")
            )
            return

        # Si no hay apertura pero sí movimientos, advertir pero permitir cerrar
        if not apertura and tiene_movimientos:
            notify_success(
                self,
                tr("Cierre Sin Apertura Formal"),
                tr("El día") + f" {fecha_cierre} " + tr("no tiene apertura formal pero tiene movimientos registrados.") + "\n\n" +
                tr("El sistema calculará el saldo inicial basado en el primer movimiento del día.")
            )

        efectivo_contado = self.efectivo_contado_input.value()
        diferencia = efectivo_contado - self.totales_dia['saldo_esperado']

        # Confirmar si hay diferencia significativa
        if abs(diferencia) > 0.01:
            # VALIDAR TOLERANCIA MÁXIMA
            if abs(diferencia) > CIERRE_TOLERANCIA_MAXIMA:
                # Diferencia EXCEDE tolerancia → Requiere autenticación
                notify_warning(
                    self,
                    tr("Diferencia Excesiva"),
                    tr("La diferencia de") + f" {diferencia:+.2f} € " + tr("excede la tolerancia máxima de") + f" {CIERRE_TOLERANCIA_MAXIMA:.2f} €.\n\n" +
                    tr("Se requiere autenticación con contraseña para aprobar este cierre.")
                )

                # Requiere contraseña
                confirmar_dialog = ConfirmarAccionDialog(
                    self.auth_manager,
                    tr("Aprobar cierre con diferencia de") + f" {diferencia:+.2f} €",
                    parent=self
                )

                if not confirmar_dialog.exec_():
                    return  # Usuario canceló o contraseña incorrecta

            else:
                # Diferencia dentro de tolerancia → Solo confirmación simple
                if not ask_confirm(self, tr("Confirmar Cierre con Diferencia"), tr("Hay una diferencia de") + f" {diferencia:+.2f} €\n\n" +
                    tr("Saldo Esperado") + f": {self.totales_dia['saldo_esperado']:.2f} €\n" +
                    tr("Efectivo Contado") + f": {efectivo_contado:.2f} €\n\n" +
                    tr("¿Desea continuar con el cierre?") + "\n" +
                    tr("(Se registrará un movimiento de ajuste)")):
                    return

            # Verificar que haya notas si hay diferencia
            if not self.notas_input.toPlainText().strip():
                if not ask_confirm(self, tr("Sin Notas"),
                    tr("Hay diferencia pero no hay notas explicativas.") + "\n\n" + tr("¿Desea continuar sin notas?")):
                    return

        # Obtener usuario actual
        usuario_actual = 'admin'
        if self.auth_manager:
            user = self.auth_manager.obtener_usuario_actual()
            if user:
                usuario_actual = user.get('username', 'admin')

        datos = {
            'fecha': self.fecha_input.date().toString('yyyy-MM-dd'),
            'efectivo_contado': efectivo_contado,
            'notas': self.notas_input.toPlainText(),
            'usuario': usuario_actual
        }

        try:
            cierre_id = self.caja_manager.realizar_cierre(datos)

            if cierre_id:
                notify_success(
                    self,
                    tr("Éxito"),
                    tr("Cierre de caja realizado correctamente") + "\n\n" +
                    tr("Fecha") + f": {datos['fecha']}\n" +
                    tr("Efectivo Contado") + f": {efectivo_contado:.2f} €\n" +
                    tr("Diferencia") + f": {diferencia:+.2f} €"
                )

                # Limpiar y recargar
                self.limpiar_formulario()
                self.cargar_cierres()

                # SI el cierre fue de un día ANTERIOR, notificar que puede abrir desde Movimientos
                if datos['fecha'] != fecha_hoy:
                    notify_success(
                        self,
                        tr("Apertura de Caja"),
                        tr("Ahora puede abrir la caja de hoy.") + "\n\n" +
                        "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n" +
                        "👉 " + tr("Use el botón") + " 🔓 " + tr("Abrir Caja")
                    )
            else:
                notify_error(self, tr("Error"), tr("No se pudo realizar el cierre"))
        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al realizar el cierre") + f":\n{str(e)}")

    def cargar_cierres(self):
        """Carga el historial de cierres"""
        filtros = {
            'fecha_desde': self.filtro_fecha_desde.date().toString('yyyy-MM-dd'),
            'fecha_hasta': self.filtro_fecha_hasta.date().toString('yyyy-MM-dd')
        }

        cierres = self.caja_manager.obtener_cierres(filtros)

        self.tabla.setRowCount(0)

        for cierre in cierres:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Fecha
            fecha_item = QTableWidgetItem(cierre['fecha'])
            fecha_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, fecha_item)

            # Valores numéricos
            for col, key in enumerate(['saldo_inicial', 'total_ingresos', 'total_egresos',
                                       'saldo_final', 'saldo_efectivo_contado', 'diferencia'], 1):
                item = QTableWidgetItem(f"{float(cierre.get(key, 0)):.2f} €")
                item.setTextAlignment(Qt.AlignCenter)

                # Colorear diferencia
                if key == 'diferencia':
                    diff = float(cierre[key])
                    if abs(diff) < 0.01:
                        item.setForeground(QColor('#A3BE8C'))
                    elif diff > 0:
                        item.setForeground(QColor('#EBCB8B'))
                    else:
                        item.setForeground(QColor('#BF616A'))

                self.tabla.setItem(row, col, item)

            # Usuario
            usuario_nombre = cierre.get('usuario') or cierre.get('usuario_nombre') or str(cierre.get('usuario_id', '-'))
            user_item = QTableWidgetItem(usuario_nombre)
            user_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 7, user_item)

    def mostrar_detalles_cierre(self, row, column):
        """Muestra detalles completos de un cierre en un diálogo"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton

        # Obtener datos del cierre desde la tabla
        fecha = self.tabla.item(row, 0).text()

        # Buscar el cierre en la base de datos
        cierre = self.db.fetch_one("""
            SELECT c.*, u.username as usuario_nombre,
                   a.saldo_inicial as apertura_saldo
            FROM caja_cierres c
            LEFT JOIN usuarios u ON c.usuario_id = u.id
            LEFT JOIN aperturas_caja a ON c.apertura_id = a.id
            WHERE c.fecha = ?
        """, (fecha,))

        if not cierre:
            notify_warning(self, tr("Error"), tr("No se encontró el cierre"))
            return

        # Crear diálogo
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Detalles del Cierre") + f" - {fecha}")
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        # Contenido de detalles
        detalles_text = QTextEdit()
        detalles_text.setReadOnly(True)

        contenido = f"""
<h2>📊 {tr('Detalles del Cierre de Caja')}</h2>
<hr>
<h3>{tr('Información General')}</h3>
<table style="width:100%; border-collapse: collapse;">
    <tr><td><b>{tr('Fecha')}:</b></td><td>{cierre['fecha']}</td></tr>
    <tr><td><b>{tr('Usuario')}:</b></td><td>{cierre.get('usuario_nombre', 'N/A')}</td></tr>
    <tr><td><b>{tr('Fecha de registro')}:</b></td><td>{cierre.get('fecha_creacion', 'N/A')}</td></tr>
</table>

<h3>{tr('Movimientos del Día')}</h3>
<table style="width:100%; border-collapse: collapse;">
    <tr style="background-color: #2E3440;">
        <td><b>{tr('Saldo Inicial')}:</b></td>
        <td style="text-align: right;"><b>{cierre['saldo_inicial']:.2f} €</b></td>
    </tr>
    <tr style="background-color: rgba(163, 190, 140, 0.15);">
        <td><b>{tr('Total Ingresos')}:</b></td>
        <td style="text-align: right; color: #A3BE8C;"><b>+{cierre['total_ingresos']:.2f} €</b></td>
    </tr>
    <tr style="background-color: rgba(191, 97, 106, 0.12);">
        <td><b>{tr('Total Egresos')}:</b></td>
        <td style="text-align: right; color: #BF616A;"><b>-{cierre['total_egresos']:.2f} €</b></td>
    </tr>
</table>

<h3>{tr('Resultado del Cierre')}</h3>
<table style="width:100%; border-collapse: collapse;">
    <tr style="background-color: #3B4252;">
        <td><b>{tr('Saldo Esperado')}:</b></td>
        <td style="text-align: right;"><b>{cierre['saldo_esperado']:.2f} €</b></td>
    </tr>
    <tr style="background-color: #3B4252;">
        <td><b>{tr('Efectivo Contado')}:</b></td>
        <td style="text-align: right;"><b>{cierre['saldo_final']:.2f} €</b></td>
    </tr>
    <tr style="background-color: {'rgba(163, 190, 140, 0.15)' if abs(cierre.get('diferencia', 0)) < 0.01 else 'rgba(235, 203, 139, 0.15)' if cierre.get('diferencia', 0) > 0 else 'rgba(191, 97, 106, 0.12)'};">
        <td><b>{tr('Diferencia')}:</b></td>
        <td style="text-align: right; color: {'#A3BE8C' if abs(cierre.get('diferencia', 0)) < 0.01 else '#EBCB8B' if cierre.get('diferencia', 0) > 0 else '#BF616A'};"><b>{cierre.get('diferencia', 0):+.2f} €</b></td>
    </tr>
</table>

<h3>{tr('Notas')}</h3>
<p style="background-color: #2E3440; padding: 10px; border-radius: 5px;">
{cierre.get('notas', tr('Sin notas')) if cierre.get('notas') else '<i>' + tr('Sin notas') + '</i>'}
</p>
        """

        detalles_text.setHtml(contenido)
        layout.addWidget(detalles_text)

        # Botón cerrar
        btn_cerrar = QPushButton(tr("Cerrar"))
        btn_cerrar.clicked.connect(dialog.accept)
        apply_btn_cancel(btn_cerrar)
        layout.addWidget(btn_cerrar)

        dialog.exec_()

    def detectar_dia_pendiente(self):
        """Detecta si hay un día con apertura pero sin cierre"""
        # Buscar la última apertura
        ultima_apertura = self.caja_manager.obtener_ultima_apertura()

        if not ultima_apertura:
            notify_success(
                self,
                tr("Sin Aperturas"),
                tr("No hay ninguna apertura de caja registrada.")
            )
            return

        fecha_apertura = ultima_apertura['fecha']

        # Verificar si ya tiene cierre
        tiene_cierre = self.caja_manager.verificar_cierre_existente(fecha_apertura)

        if tiene_cierre:
            notify_success(
                self,
                tr("Todo Cerrado"),
                tr("La última apertura") + f" ({fecha_apertura}) " + tr("ya tiene su cierre correspondiente.") + "\n\n" +
                tr("No hay días pendientes de cerrar.")
            )
        else:
            # Hay un día pendiente de cerrar
            if ask_confirm(self, tr("Día Pendiente Detectado"),
                tr("Se encontró una apertura sin cerrar") + f":\n\n" +
                tr("Fecha") + f": {fecha_apertura}\n" +
                tr("Saldo Inicial") + f": {ultima_apertura['saldo_inicial']:.2f} €\n\n" +
                tr("¿Desea seleccionar esta fecha para cerrarla?")):
                # Convertir string a QDate y establecer
                from PyQt5.QtCore import QDate
                partes = fecha_apertura.split('-')
                qdate = QDate(int(partes[0]), int(partes[1]), int(partes[2]))
                self.fecha_input.setDate(qdate)
                self.calcular_totales()

    def limpiar_formulario(self):
        """Limpia el formulario"""
        self.fecha_input.setDate(QDate.currentDate())
        self.efectivo_contado_input.setValue(0)
        self.notas_input.clear()
        self.totales_dia = None
        self.calcular_totales(auto_detectar=False)

    def _ofrecer_apertura_hoy(self, saldo_cierre_anterior):
        """
        Ofrece al usuario abrir la caja de hoy después de cerrar un día anterior.

        Args:
            saldo_cierre_anterior: El efectivo contado del cierre anterior (sugerido como saldo inicial)
        """
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox, QPushButton

        fecha_hoy = QDate.currentDate().toString('yyyy-MM-dd')

        # Verificar si ya existe apertura para hoy
        if self.caja_manager.verificar_apertura_existente(fecha_hoy):
            return  # Ya hay apertura, no ofrecer

        if not ask_confirm(self, tr("Abrir Caja de Hoy"),
            tr("Ha cerrado la caja de un día anterior.") + "\n\n" +
            tr("¿Desea abrir la caja para hoy?") + f" ({fecha_hoy})\n\n" +
            tr("Saldo sugerido") + f": {saldo_cierre_anterior:.2f} €"):
            return

        # Diálogo para ingresar saldo inicial
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Apertura de Caja") + f" - {fecha_hoy}")
        dialog.setMinimumWidth(350)

        layout = QVBoxLayout(dialog)

        # Instrucciones
        info_label = QLabel(tr("Ingrese el saldo inicial para abrir la caja de hoy:"))
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Saldo inicial
        saldo_layout = QHBoxLayout()
        saldo_layout.addWidget(QLabel(tr("Saldo Inicial") + ":"))
        saldo_input = QDoubleSpinBox()
        saldo_input.setMinimum(0)
        saldo_input.setMaximum(999999)
        saldo_input.setDecimals(2)
        saldo_input.setSuffix(" €")
        saldo_input.setValue(saldo_cierre_anterior)  # Sugerir el saldo del cierre anterior
        saldo_input.setMinimumWidth(150)
        saldo_layout.addWidget(saldo_input)
        saldo_layout.addStretch()
        layout.addLayout(saldo_layout)

        # Botones
        btn_layout = QHBoxLayout()
        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(dialog.reject)
        apply_btn_danger(btn_cancelar)
        btn_layout.addWidget(btn_cancelar)

        btn_abrir = QPushButton(tr("Abrir Caja"))
        btn_abrir.clicked.connect(dialog.accept)
        apply_btn_success(btn_abrir)
        btn_layout.addWidget(btn_abrir)
        layout.addLayout(btn_layout)

        if dialog.exec_() == QDialog.Accepted:
            saldo_inicial = saldo_input.value()

            # Registrar apertura
            datos_apertura = {
                'fecha': fecha_hoy,
                'saldo_inicial': saldo_inicial,
                'notas': tr('Apertura después de cierre de día anterior')
            }

            apertura_id = self.caja_manager.registrar_apertura(datos_apertura)

            if apertura_id:
                notify_success(
                    self,
                    tr("Caja Abierta"),
                    tr("La caja de hoy ha sido abierta correctamente.") + "\n\n" +
                    tr("Fecha") + f": {fecha_hoy}\n" +
                    tr("Saldo Inicial") + f": {saldo_inicial:.2f} €"
                )
            else:
                notify_error(
                    self,
                    tr("Error"),
                    tr("No se pudo abrir la caja. Inténtelo desde Caja Movimientos.")
                )
