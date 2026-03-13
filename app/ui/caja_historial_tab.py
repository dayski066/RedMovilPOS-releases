"""
Pestaña de Historial de Caja/TPV
Muestra las ventas del día con sus totales
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QFrame, QHeaderView, QDateEdit,
                             QDialog, QGridLayout, QFileDialog, QInputDialog)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont, QColor
from app.db.database import Database
from app.modules.caja_tpv_manager import CajaTpvManager
from app.i18n import tr
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.ui.styles import app_icon
from PyQt5.QtCore import QSize
from datetime import datetime


class CajaHistorialTab(QWidget):
    """Historial de ventas de caja"""

    def __init__(self):
        super().__init__()
        self.db = Database()
        self.db.connect()
        self.caja_manager = CajaTpvManager(self.db)

        # Paginación
        self.pagina_actual = 1
        self.items_por_pagina = 50
        self.total_registros = 0

        # Timer para auto-refresh cada 30 segundos
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.cargar_ventas)
        self.refresh_timer.start(30000)  # 30 segundos

        self.setup_ui()
        self.cargar_ventas()
    
    def showEvent(self, event):
        """Se ejecuta cada vez que la pestaña se muestra - refresca los datos"""
        super().showEvent(event)
        self.cargar_ventas()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # === RESUMEN DEL DÍA ===
        resumen_frame = self.crear_resumen()
        layout.addWidget(resumen_frame)

        # === FILTROS ===
        filtros_frame = self.crear_filtros()
        layout.addWidget(filtros_frame)

        # === TABLA DE VENTAS ===
        self.tabla = self.crear_tabla()
        layout.addWidget(self.tabla)

        # === PAGINACIÓN ===
        paginacion_frame = self.crear_paginacion()
        layout.addWidget(paginacion_frame)
    
    def crear_resumen(self):
        """Crea el panel de resumen del día"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2E3440, stop:1 #3B4252);
                border-radius: 10px;
                padding: 20px;
            }
        """)
        layout = QHBoxLayout(frame)
        
        # Número de ventas
        card_ventas = self.crear_card_resumen("🧾", "Ventas", "0", "#5E81AC")
        layout.addWidget(card_ventas)
        self.label_num_ventas = card_ventas.findChild(QLabel, "valor")
        
        # Subtotal
        card_subtotal = self.crear_card_resumen("📦", "Subtotal", "0.00 €", "#B48EAD")
        layout.addWidget(card_subtotal)
        self.label_subtotal = card_subtotal.findChild(QLabel, "valor")
        
        # IVA
        card_iva = self.crear_card_resumen("📊", "IVA (21%)", "0.00 €", "#EBCB8B")
        layout.addWidget(card_iva)
        self.label_iva = card_iva.findChild(QLabel, "valor")
        
        # Total
        card_total = self.crear_card_resumen("💰", "Total", "0.00 €", "#A3BE8C")
        layout.addWidget(card_total)
        self.label_total = card_total.findChild(QLabel, "valor")
        
        return frame
    
    def crear_card_resumen(self, icono, titulo, valor, color):
        """Crea una tarjeta de resumen"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        
        # Icono y título
        header = QLabel(f"{icono} {titulo}")
        header.setStyleSheet("color: #7B88A0; font-size: 12px;")
        layout.addWidget(header)
        
        # Valor
        valor_label = QLabel(valor)
        valor_label.setObjectName("valor")
        valor_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        layout.addWidget(valor_label)
        
        return card
    
    def crear_filtros(self):
        """Crea los filtros de fecha"""
        frame = QFrame()
        frame.setObjectName("cardPanel")
        layout = QHBoxLayout(frame)
        
        layout.addWidget(QLabel("📅 Fecha:"))
        
        self.fecha_filtro = QDateEdit()
        self.fecha_filtro.setDate(QDate.currentDate())
        self.fecha_filtro.setCalendarPopup(True)
        self.fecha_filtro.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #4C566A;
                border-radius: 5px;
                font-size: 13px;
                background-color: #3B4252;
                color: #ffffff;
            }
        """)
        self.fecha_filtro.dateChanged.connect(self.cargar_ventas)
        layout.addWidget(self.fecha_filtro)
        
        btn_hoy = QPushButton(tr("Hoy"))
        btn_hoy.clicked.connect(self.ir_a_hoy)
        layout.addWidget(btn_hoy)
        
        layout.addStretch()
        
        btn_refrescar = QPushButton(tr("Refrescar"))
        btn_refrescar.setIcon(app_icon("fa5s.sync-alt", color="#A3BE8C", size=16))
        btn_refrescar.setIconSize(QSize(16, 16))
        btn_refrescar.clicked.connect(self.cargar_ventas)
        layout.addWidget(btn_refrescar)
        
        return frame
    
    def crear_tabla(self):
        """Crea la tabla de ventas"""
        tabla = QTableWidget()
        tabla.setColumnCount(7)
        tabla.setHorizontalHeaderLabels([
            'Ticket', 'Hora', 'Items', 'Subtotal', 'IVA', 'Total', 'Acciones'
        ])
        
        tabla.setStyleSheet("""
            QTableWidget {
                background-color: #2E3440;
                color: #ffffff;
                border: 1px solid #4C566A;
                border-radius: 8px;
                gridline-color: #4C566A;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 10px;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #5E81AC;
                color: white;
                padding: 12px;
                font-weight: bold;
                border: none;
            }
        """)
        
        header = tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        tabla.setColumnWidth(6, 220)  # Acciones
        
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setSortingEnabled(True)
        
        # Estilo Global de Tabla
        tabla.verticalHeader().setDefaultSectionSize(60)
        tabla.verticalHeader().setVisible(False)
        tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        return tabla

    def crear_paginacion(self):
        """Crea los controles de paginación"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #2E3440;
                border-radius: 8px;
                padding: 10px;
            }
            QLabel {
                color: #D8DEE9;
            }
        """)
        layout = QHBoxLayout(frame)

        # Selector de items por página
        layout.addWidget(QLabel("Mostrar:"))

        from PyQt5.QtWidgets import QComboBox
        self.items_combo = QComboBox()
        self.items_combo.addItems(['25', '50', '100', '200', 'Todos'])
        self.items_combo.setCurrentText(str(self.items_por_pagina))
        self.items_combo.currentTextChanged.connect(self.cambiar_items_por_pagina)
        layout.addWidget(self.items_combo)

        layout.addWidget(QLabel("registros"))

        layout.addStretch()

        # Info de paginación
        self.paginacion_info = QLabel("Mostrando 0-0 de 0")
        self.paginacion_info.setStyleSheet("color: #D8DEE9; font-weight: bold;")
        layout.addWidget(self.paginacion_info)

        layout.addSpacing(15)

        # Botones de navegación (compactos, solo icono - misma forma que PaginationWidget)
        self.btn_primera = QPushButton()
        self.btn_primera.setIcon(app_icon("fa5s.angle-double-left", color="#88C0D0", size=14))
        self.btn_primera.setIconSize(QSize(14, 14))
        self.btn_primera.setFixedWidth(36)
        self.btn_primera.setToolTip(tr("Primera página"))
        self.btn_primera.clicked.connect(self.ir_primera_pagina)
        layout.addWidget(self.btn_primera)

        self.btn_anterior = QPushButton()
        self.btn_anterior.setIcon(app_icon("fa5s.angle-left", color="#88C0D0", size=14))
        self.btn_anterior.setIconSize(QSize(14, 14))
        self.btn_anterior.setFixedWidth(36)
        self.btn_anterior.setToolTip(tr("Anterior"))
        self.btn_anterior.clicked.connect(self.pagina_anterior)
        layout.addWidget(self.btn_anterior)

        self.pagina_label = QLabel("1 / 1")
        self.pagina_label.setAlignment(Qt.AlignCenter)
        self.pagina_label.setMinimumWidth(80)
        self.pagina_label.setStyleSheet("color: #ECEFF4; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.pagina_label)

        self.btn_siguiente = QPushButton()
        self.btn_siguiente.setIcon(app_icon("fa5s.angle-right", color="#88C0D0", size=14))
        self.btn_siguiente.setIconSize(QSize(14, 14))
        self.btn_siguiente.setFixedWidth(36)
        self.btn_siguiente.setToolTip(tr("Siguiente"))
        self.btn_siguiente.clicked.connect(self.pagina_siguiente)
        layout.addWidget(self.btn_siguiente)

        self.btn_ultima = QPushButton()
        self.btn_ultima.setIcon(app_icon("fa5s.angle-double-right", color="#88C0D0", size=14))
        self.btn_ultima.setIconSize(QSize(14, 14))
        self.btn_ultima.setFixedWidth(36)
        self.btn_ultima.setToolTip(tr("Última página"))
        self.btn_ultima.clicked.connect(self.ir_ultima_pagina)
        layout.addWidget(self.btn_ultima)

        return frame

    def cambiar_items_por_pagina(self, texto):
        """Cambia el número de items por página"""
        if texto == 'Todos':
            self.items_por_pagina = -1  # -1 significa todos
        else:
            self.items_por_pagina = int(texto)

        self.pagina_actual = 1  # Volver a la primera página
        self.cargar_ventas()

    def ir_primera_pagina(self):
        """Va a la primera página"""
        self.pagina_actual = 1
        self.cargar_ventas()

    def pagina_anterior(self):
        """Va a la página anterior"""
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
            self.cargar_ventas()

    def pagina_siguiente(self):
        """Va a la página siguiente"""
        total_paginas = self.calcular_total_paginas()
        if self.pagina_actual < total_paginas:
            self.pagina_actual += 1
            self.cargar_ventas()

    def ir_ultima_pagina(self):
        """Va a la última página"""
        total_paginas = self.calcular_total_paginas()
        if total_paginas > 0:
            self.pagina_actual = total_paginas
            self.cargar_ventas()

    def calcular_total_paginas(self):
        """Calcula el total de páginas"""
        if self.items_por_pagina == -1:  # Todos
            return 1
        if self.total_registros == 0:
            return 1
        import math
        return math.ceil(self.total_registros / self.items_por_pagina)

    def actualizar_controles_paginacion(self):
        """Actualiza el estado de los controles de paginación"""
        total_paginas = self.calcular_total_paginas()

        # Deshabilitar botones según posición
        self.btn_primera.setEnabled(self.pagina_actual > 1)
        self.btn_anterior.setEnabled(self.pagina_actual > 1)
        self.btn_siguiente.setEnabled(self.pagina_actual < total_paginas)
        self.btn_ultima.setEnabled(self.pagina_actual < total_paginas)

        # Actualizar etiquetas
        self.pagina_label.setText(f"Página {self.pagina_actual} de {total_paginas}")

        # Calcular rango de registros mostrados
        if self.items_por_pagina == -1:
            inicio = 1
            fin = self.total_registros
        else:
            inicio = (self.pagina_actual - 1) * self.items_por_pagina + 1
            fin = min(inicio + self.items_por_pagina - 1, self.total_registros)

        if self.total_registros == 0:
            inicio = 0
            fin = 0

        self.paginacion_info.setText(f"Mostrando {inicio}-{fin} de {self.total_registros}")

    def ir_a_hoy(self):
        """Va a la fecha de hoy"""
        self.fecha_filtro.setDate(QDate.currentDate())
    
    def cargar_ventas(self):
        """Carga las ventas de la fecha seleccionada con paginación"""
        fecha = self.fecha_filtro.date().toString('yyyy-MM-dd')

        # Obtener resumen
        resumen = self.caja_manager.obtener_total_dia(fecha)
        self.label_num_ventas.setText(str(resumen['num_ventas'] or 0))
        self.label_subtotal.setText(f"{resumen['subtotal'] or 0:.2f} €")
        self.label_iva.setText(f"{resumen['iva'] or 0:.2f} €")
        self.label_total.setText(f"{resumen['total'] or 0:.2f} €")

        # Contar total de registros
        total_count = self.db.fetch_one(
            "SELECT COUNT(*) as total FROM ventas_caja WHERE DATE(fecha) = ?",
            (fecha,)
        )
        self.total_registros = total_count['total'] if total_count else 0

        # Calcular LIMIT y OFFSET
        if self.items_por_pagina == -1:
            # Mostrar todos
            limit = self.total_registros
            offset = 0
        else:
            limit = self.items_por_pagina
            offset = (self.pagina_actual - 1) * self.items_por_pagina

        # Cargar ventas en tabla con paginación
        ventas = self.db.fetch_all("""
            SELECT *
            FROM ventas_caja
            WHERE DATE(fecha) = ?
            ORDER BY fecha DESC, id DESC
            LIMIT ? OFFSET ?
        """, (fecha, limit, offset))

        self.tabla.setRowCount(0)
        
        for venta in ventas:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)
            
            # Número ticket
            ticket_item = QTableWidgetItem(venta['numero_ticket'])
            ticket_item.setFont(QFont("", -1, QFont.Bold))
            ticket_item.setTextAlignment(Qt.AlignCenter)
            if venta['estado'] == 'anulada':
                ticket_item.setForeground(QColor('#BF616A'))
            self.tabla.setItem(row, 0, ticket_item)
            
            # Hora
            hora = venta['fecha'].split(' ')[1][:5] if ' ' in venta['fecha'] else venta['fecha']
            hora_item = QTableWidgetItem(hora)
            hora_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, hora_item)
            
            # Items
            items = self.db.fetch_all(
                "SELECT nombre_producto, cantidad FROM ventas_caja_items WHERE venta_caja_id = ?",
                (venta['id'],)
            )
            items_texto = ", ".join([f"{i['cantidad']}x {i['nombre_producto'][:20]}" for i in items])
            items_item = QTableWidgetItem(items_texto[:50] + "..." if len(items_texto) > 50 else items_texto)
            items_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, items_item)
            
            # Subtotal
            subtotal_item = QTableWidgetItem(f"{venta['subtotal']:.2f} €")
            subtotal_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, subtotal_item)
            
            # IVA
            iva_item = QTableWidgetItem(f"{venta['iva']:.2f} €")
            iva_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, iva_item)
            
            # Total
            total_item = QTableWidgetItem(f"{venta['total']:.2f} €")
            total_item.setTextAlignment(Qt.AlignCenter)
            total_item.setFont(QFont("", -1, QFont.Bold))
            total_item.setForeground(QColor('#A3BE8C'))
            self.tabla.setItem(row, 5, total_item)
            
            # Botones de acción - Centrado estructural
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(10)
            h_layout.addStretch()

            from app.ui.styles import estilizar_btn_ver, estilizar_btn_imprimir, estilizar_btn_eliminar, estilizar_btn_descargar

            btn_ver = QPushButton()
            btn_ver.setToolTip(tr("Ver"))
            btn_ver.clicked.connect(lambda checked, v=venta: self.ver_detalle(v))
            estilizar_btn_ver(btn_ver)
            h_layout.addWidget(btn_ver)

            btn_print = QPushButton()
            btn_print.setToolTip(tr("Imprimir"))
            btn_print.clicked.connect(lambda checked, v=venta: self.imprimir_ticket(v))
            estilizar_btn_imprimir(btn_print)
            h_layout.addWidget(btn_print)

            btn_descargar = QPushButton()
            btn_descargar.setToolTip(tr("Descargar"))
            btn_descargar.clicked.connect(lambda checked, v=venta: self.descargar_ticket(v))
            estilizar_btn_descargar(btn_descargar)
            h_layout.addWidget(btn_descargar)

            if venta['estado'] != 'anulada':
                btn_anular = QPushButton()
                btn_anular.setToolTip(tr("Anular"))
                btn_anular.clicked.connect(lambda checked, v=venta: self.anular_venta(v))
                estilizar_btn_eliminar(btn_anular)
                h_layout.addWidget(btn_anular)

            h_layout.addStretch()
            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 6, container)

        # Actualizar controles de paginación
        self.actualizar_controles_paginacion()

    def ver_detalle(self, venta):
        """Muestra el detalle de una venta"""
        venta_completa = self.caja_manager.obtener_venta(venta['id'])
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Ticket {venta['numero_ticket']}")
        dialog.setMinimumSize(400, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Info general
        info = QLabel(f"""
            <h2>🧾 {venta['numero_ticket']}</h2>
            <p><b>Fecha:</b> {venta['fecha']}</p>
            <p><b>Método:</b> {venta['metodo_pago'].capitalize()}</p>
            <p><b>Estado:</b> {venta['estado'].capitalize()}</p>
        """)
        layout.addWidget(info)
        
        # Tabla de items
        tabla_items = QTableWidget()
        tabla_items.setColumnCount(4)
        tabla_items.setHorizontalHeaderLabels(['Producto', 'Cant.', 'Precio', 'Total'])
        tabla_items.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        for item in venta_completa.get('items', []):
            row = tabla_items.rowCount()
            tabla_items.insertRow(row)
            tabla_items.setItem(row, 0, QTableWidgetItem(item['nombre_producto']))
            tabla_items.setItem(row, 1, QTableWidgetItem(str(item['cantidad'])))
            tabla_items.setItem(row, 2, QTableWidgetItem(f"{item['precio_unitario']:.2f}€"))
            tabla_items.setItem(row, 3, QTableWidgetItem(f"{item['total_item']:.2f}€"))
        
        layout.addWidget(tabla_items)
        
        # Totales
        totales = QLabel(f"""
            <p style="text-align: right"><b>Subtotal:</b> {venta['subtotal']:.2f}€</p>
            <p style="text-align: right"><b>IVA:</b> {venta['iva']:.2f}€</p>
            <p style="text-align: right; font-size: 18px"><b>TOTAL:</b> {venta['total']:.2f}€</p>
        """)
        layout.addWidget(totales)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        layout.addWidget(btn_cerrar)
        
        dialog.exec_()
    
    def imprimir_ticket(self, venta):
        """Imprime el ticket de la venta regenerándolo desde la BD"""
        try:
            from app.modules.ticket_printer import TicketPrinter

            # Obtener impresora configurada
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_ticket'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                # Sin impresora: solo avisar y salir
                notify_warning(self, "Sin Impresora",
                    "No hay impresora de tickets configurada.\n"
                    "Ve a Ajustes > Impresoras para configurarla.")
                return

            # Obtener datos completos de la venta desde la BD
            venta_completa = self.caja_manager.obtener_venta(venta['id'])
            if not venta_completa:
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora de tickets configurada.\n"
                    "Ve a Ajustes > Impresoras para configurarla."))
                return

            # Obtener datos completos de la venta desde la BD
            venta_completa = self.caja_manager.obtener_venta(venta['id'])
            if not venta_completa:
                notify_warning(self, tr("Error"), tr("No se pudo cargar la venta"))
                return

            # Crear impresora de tickets e imprimir
            ticket_printer = TicketPrinter(self.db)
            exito, mensaje = ticket_printer.imprimir_a_impresora_windows(venta_completa, printer_name)

            if exito:
                notify_success(self, tr("Impreso"), tr("Ticket") + f" {venta['numero_ticket']} " + tr("enviado a") + f" {printer_name}")
            else:
                notify_warning(self, tr("Error"), mensaje)

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al imprimir ticket") + f":\n{str(e)}")

    def descargar_ticket(self, venta):
        """Descarga una copia del ticket como archivo TXT"""
        try:
            from app.modules.ticket_printer import TicketPrinter

            # Obtener datos completos de la venta desde la BD
            venta_completa = self.caja_manager.obtener_venta(venta['id'])
            if not venta_completa:
                notify_warning(self, tr("Error"), tr("No se pudo cargar la venta"))
                return

            # Crear impresora de tickets para generar contenido
            ticket_printer = TicketPrinter(self.db)
            contenido = ticket_printer.generar_contenido_ticket(venta_completa)

            # Mostrar diálogo para elegir destino
            nombre_sugerido = f"Ticket_{venta['numero_ticket'].replace('/', '_')}.txt"
            destino, _ = QFileDialog.getSaveFileName(
                self,
                "Guardar Ticket",
                nombre_sugerido,
                "Archivos de Texto (*.txt)"
            )

            if destino:
                with open(destino, 'w', encoding='utf-8') as f:
                    f.write(contenido)
                notify_success(self, "Descargado", f"Ticket guardado en:\n{destino}")

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, "Error", f"Error al descargar ticket:\n{str(e)}")

    def anular_venta(self, venta):
        """Anula una venta con motivo obligatorio"""
        # Pedir motivo de anulación (obligatorio)
        motivo, ok = QInputDialog.getText(
            self,
            "Motivo de Anulación",
            f"Ingrese el motivo para anular el ticket {venta['numero_ticket']}:\n\n"
            "(Este motivo quedará registrado para auditoría)",
            text=""
        )

        if not ok:
            return  # Usuario canceló

        if not motivo.strip():
            notify_warning(
                self,
                "Motivo Obligatorio",
                "Debe ingresar un motivo para anular la venta."
            )
            return

        # Confirmar anulación
        if ask_confirm(self, "Confirmar Anulación", f"¿Confirma anular el ticket {venta['numero_ticket']}?\n\n"
            f"Motivo: {motivo}\n\n"
            "Se restaurará el stock de los productos."):
            # TODO: Pasar el motivo al manager cuando se añada soporte
            exito, mensaje = self.caja_manager.anular_venta(venta['id'])
            if exito:
                notify_success(
                    self, "Éxito",
                    f"{mensaje}\n\nMotivo registrado: {motivo}"
                )
                self.cargar_ventas()
            else:
                notify_error(self, "Error", mensaje)


    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
