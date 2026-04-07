"""
Terminal Punto de Venta (TPV) - Interfaz moderna para ventas rápidas
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QDialog,
                             QScrollArea, QFrame, QComboBox,
                             QDoubleSpinBox, QSpinBox, QGroupBox, QHeaderView, QTextEdit,
                             QSizePolicy)
from qfluentwidgets import SearchLineEdit
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from app.ui.transparent_buttons import apply_btn_danger, apply_btn_success, apply_btn_warning, apply_btn_primary, apply_btn_cancel
from app.ui.theme import COLOR_DANGER, COLOR_WARNING, COLOR_ACCENT, COLOR_PRIMARY
from app.utils.notify import notify_success, notify_error, notify_warning, notify_info, ask_confirm
from app.i18n import tr
from app.db.database import Database
from app.modules.caja_tpv_manager import CajaTpvManager
from app.modules.producto_manager import ProductoManager
from app.modules.caja_manager import CajaManager
from config import calcular_desglose_iva
from datetime import datetime


class CajaTPVTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.StrongFocus)
        self.db = Database()
        self.db.connect()
        self.tpv_manager = CajaTpvManager(self.db)
        self.producto_manager = ProductoManager(self.db)
        self.caja_manager = CajaManager(self.db)

        # Estado del TPV
        self.carrito = []  # Lista de items: {producto_id, nombre, precio_unit, cantidad, subtotal, iva, total}
        self.cantidad_actual = 0  # Cantidad tecleada para próximo producto (0 = vacío, usar 1 al añadir)

        # Timer para debouncing en búsqueda
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.buscar_producto_ean)

        # Timer para auto-reset de cantidad después de inactividad
        self.reset_timer = QTimer()
        self.reset_timer.setSingleShot(True)
        self.reset_timer.timeout.connect(self.auto_reset_cantidad)
        self.tiempo_inactividad_ms = 30000  # 30 segundos de inactividad

        self.setup_ui()
        self.cargar_favoritos()
        self.actualizar_saldo_caja()  # Cargar saldo inicial

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Columna izquierda: Carrito + Totales
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        # Scanner EAN
        scanner_layout = QHBoxLayout()
        scanner_label = QLabel(tr("Escanear EAN") + ":")
        scanner_label.setStyleSheet("font-weight: bold; font-family: 'Segoe UI', Arial, sans-serif;")
        self.ean_input = SearchLineEdit()
        self.ean_input.setPlaceholderText(tr("Código de barras o buscar..."))
        self.ean_input.setFont(QFont("Segoe UI", 12))
        self.ean_input.returnPressed.connect(self.buscar_producto_ean)
        self.ean_input.textChanged.connect(self.on_search_text_changed)  # Debouncing
        scanner_layout.addWidget(scanner_label)
        scanner_layout.addWidget(self.ean_input, 1)
        left_layout.addLayout(scanner_layout)

        # Tabla de productos en el carrito
        self.tabla_carrito = QTableWidget()
        self.tabla_carrito.setColumnCount(7)  # Añadida columna para botón eliminar
        self.tabla_carrito.setHorizontalHeaderLabels([
            tr("Producto"), tr("Precio"), tr("Cant."), tr("Subtotal"), tr("IVA"), tr("Total"), ""
        ])
        self.tabla_carrito.setStyleSheet("""
            QTableWidget {
                background-color: #2E3440;
                color: #ECEFF4;
                border: 2px solid #4C566A;
                border-radius: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 12px;
                gridline-color: #4C566A;
            }
            QTableWidget::item {
                color: #ECEFF4;
            }
            QHeaderView::section {
                background-color: #3B4252;
                color: #88C0D0;
                padding: 8px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial, sans-serif;
                border: none;
                border-bottom: 2px solid #88C0D0;
            }
        """)
        header = self.tabla_carrito.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.tabla_carrito.setColumnWidth(6, 60) # Botón eliminar
        
        self.tabla_carrito.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_carrito.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla_carrito.verticalHeader().setDefaultSectionSize(60)
        self.tabla_carrito.verticalHeader().setVisible(False)
        self.tabla_carrito.setStyleSheet("QTableWidget::item { padding: 0px; }")
        
        left_layout.addWidget(self.tabla_carrito, 1)

        # Saldo de caja actual - INFO
        saldo_caja_frame = QFrame()
        saldo_caja_frame.setObjectName("cardPanel")
        saldo_caja_layout = QHBoxLayout(saldo_caja_frame)
        saldo_caja_label_text = QLabel(f"💰 <b>{tr('Saldo Caja')}:</b>")
        saldo_caja_label_text.setStyleSheet("font-family: 'Segoe UI', Arial, sans-serif; color: #D8DEE9; font-size: 13px;")
        saldo_caja_layout.addWidget(saldo_caja_label_text)
        saldo_caja_layout.addStretch()
        self.saldo_caja_label = QLabel("0.00 €")
        self.saldo_caja_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.saldo_caja_label.setStyleSheet("font-family: 'Segoe UI', Arial, sans-serif; color: #88C0D0;")
        saldo_caja_layout.addWidget(self.saldo_caja_label)
        left_layout.addWidget(saldo_caja_frame)

        # Panel de totales - Card UI
        totales_frame = QFrame()
        totales_frame.setObjectName("cardPanel")
        totales_layout = QGridLayout(totales_frame)

        # Labels de totales
        label_subtotal = QLabel(f"<b>{tr('Subtotal')}:</b>")
        label_subtotal.setStyleSheet("font-family: 'Segoe UI', Arial, sans-serif; color: #D8DEE9;")
        totales_layout.addWidget(label_subtotal, 0, 0)

        self.subtotal_label = QLabel("0.00 €")
        self.subtotal_label.setAlignment(Qt.AlignRight)
        self.subtotal_label.setFont(QFont("Segoe UI", 13))
        self.subtotal_label.setStyleSheet("font-family: 'Segoe UI', Arial, sans-serif; color: #ffffff;")
        totales_layout.addWidget(self.subtotal_label, 0, 1)

        label_iva = QLabel(f"<b>{tr('IVA')} (21%):</b>")
        label_iva.setStyleSheet("font-family: 'Segoe UI', Arial, sans-serif; color: #D8DEE9;")
        totales_layout.addWidget(label_iva, 1, 0)

        self.iva_label = QLabel("0.00 €")
        self.iva_label.setAlignment(Qt.AlignRight)
        self.iva_label.setFont(QFont("Segoe UI", 13))
        self.iva_label.setStyleSheet("font-family: 'Segoe UI', Arial, sans-serif; color: #ffffff;")
        totales_layout.addWidget(self.iva_label, 1, 1)

        label_total = QLabel(f"<b style='font-size: 16px;'>{tr('Total').upper()}:</b>")
        label_total.setStyleSheet("font-family: 'Segoe UI', Arial, sans-serif; color: #ffffff;")
        totales_layout.addWidget(label_total, 2, 0)

        self.total_label = QLabel("0.00 €")
        self.total_label.setAlignment(Qt.AlignRight)
        self.total_label.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.total_label.setStyleSheet("color: #88C0D0; font-family: 'Segoe UI', Arial, sans-serif;")
        totales_layout.addWidget(self.total_label, 2, 1)

        left_layout.addWidget(totales_frame)

        layout.addLayout(left_layout, 2)

        # Columna derecha: Teclado (arriba) + Favoritos (abajo)
        right_layout = QVBoxLayout()

        # === TECLADO NUMÉRICO (ARRIBA) ===

        # Cantidad a añadir
        cant_frame = QFrame()
        cant_frame.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px; padding: 10px;")
        cant_layout = QVBoxLayout(cant_frame)
        cant_label = QLabel(tr("Cantidad") + ":")
        cant_label.setStyleSheet("color: white; font-weight: bold;")
        self.cantidad_display = QLabel("0")
        self.cantidad_display.setAlignment(Qt.AlignCenter)
        self.cantidad_display.setStyleSheet("""
            color: white;
            font-size: 36px;
            font-weight: bold;
            background-color: #2E3440;
            border-radius: 8px;
            padding: 10px;
        """)
        cant_layout.addWidget(cant_label)
        cant_layout.addWidget(self.cantidad_display)
        right_layout.addWidget(cant_frame)

        # Teclado numérico
        teclado_frame = QFrame()
        teclado_layout = QGridLayout(teclado_frame)
        teclado_layout.setSpacing(8)

        # Botones numéricos
        numeros = [
            ['7', '8', '9'],
            ['4', '5', '6'],
            ['1', '2', '3'],
            ['C', '0', '.']
        ]

        for row_idx, row in enumerate(numeros):
            for col_idx, num in enumerate(row):
                btn = QPushButton(num)
                btn.setFont(QFont("", 18, QFont.Bold))
                btn.setMinimumSize(70, 70)
                if num == 'C':
                    apply_btn_danger(btn)
                    btn.clicked.connect(self.limpiar_cantidad)
                elif num == '.':
                    btn.setEnabled(False)  # Deshabilitado por ahora
                    btn.setStyleSheet("background-color: transparent; color: #4C566A; border: 2px solid #4C566A; border-radius: 6px;")
                else:
                    apply_btn_primary(btn)
                    btn.clicked.connect(lambda checked, n=num: self.tecla_numero(n))

                teclado_layout.addWidget(btn, row_idx, col_idx)

        right_layout.addWidget(teclado_frame)

        # Botones de acción
        acciones_layout = QGridLayout()
        acciones_layout.setSpacing(8)

        # Botón + (Añadir producto manual)
        btn_add = QPushButton("+")
        btn_add.setFont(QFont("", 24, QFont.Bold))
        btn_add.setMinimumHeight(70)
        apply_btn_success(btn_add)
        btn_add.clicked.connect(self.abrir_producto_manual)
        btn_add.setShortcut("F2")  # Atajo de teclado
        acciones_layout.addWidget(btn_add, 0, 0)

        # Botón = (Cobrar)
        btn_cobrar = QPushButton("=")
        btn_cobrar.setFont(QFont("", 24, QFont.Bold))
        btn_cobrar.setMinimumHeight(70)
        apply_btn_warning(btn_cobrar)
        btn_cobrar.clicked.connect(self.abrir_cobro)
        btn_cobrar.setShortcut("F5")  # Atajo de teclado (F5 en lugar de F1)
        acciones_layout.addWidget(btn_cobrar, 0, 1)

        # Botón limpiar carrito - F1
        btn_limpiar = QPushButton(tr("Limpiar (F1)") + "\n" + tr("Carrito"))
        btn_limpiar.setFont(QFont("", 12, QFont.Bold))
        btn_limpiar.setMinimumHeight(70)
        apply_btn_danger(btn_limpiar)
        btn_limpiar.clicked.connect(self.limpiar_carrito)
        btn_limpiar.setShortcut("F1") # Atajo F1
        acciones_layout.addWidget(btn_limpiar, 1, 0, 1, 2)

        right_layout.addLayout(acciones_layout)

        # === FAVORITOS (ABAJO) ===

        fav_header = QHBoxLayout()
        fav_label = QLabel(tr("Productos Favoritos"))
        fav_label.setFont(QFont("", 14, QFont.Bold))
        fav_header.addWidget(fav_label)

        btn_add_fav = QPushButton("+ " + tr("Agregar"))
        apply_btn_primary(btn_add_fav)
        btn_add_fav.clicked.connect(self.agregar_favorito)
        fav_header.addWidget(btn_add_fav)

        right_layout.addLayout(fav_header)

        # Scroll area para favoritos
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 2px solid #4C566A; border-radius: 8px; }")

        self.favoritos_widget = QWidget()
        self.favoritos_layout = QGridLayout(self.favoritos_widget)
        self.favoritos_layout.setSpacing(8)
        self.favoritos_layout.setContentsMargins(5, 5, 5, 5)
        self.favoritos_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        scroll.setWidget(self.favoritos_widget)
        right_layout.addWidget(scroll, 1)

        layout.addLayout(right_layout, 1)

    def tecla_numero(self, numero):
        """Añade un número a la cantidad actual"""
        if self.cantidad_actual == 0:
            self.cantidad_actual = int(numero)
        else:
            self.cantidad_actual = int(str(self.cantidad_actual) + numero)

        self.cantidad_display.setText(str(self.cantidad_actual))

        # Reiniciar timer de auto-reset
        self.reset_timer.stop()
        self.reset_timer.start(self.tiempo_inactividad_ms)

    def on_search_text_changed(self):
        """Maneja el cambio de texto en búsqueda con debouncing"""
        # Reiniciar el timer cada vez que se escribe
        # Solo buscará 500ms después de la última tecla
        self.search_timer.stop()
        if self.ean_input.text().strip():  # Solo si hay texto
            self.search_timer.start(500)  # 500ms delay

    def limpiar_cantidad(self):
        """Resetea la cantidad a 0"""
        self.cantidad_actual = 0
        self.cantidad_display.setText("0")

        # Detener timer de auto-reset ya que se limpió manualmente
        self.reset_timer.stop()

    def auto_reset_cantidad(self):
        """Auto-resetea la cantidad a 0 después de inactividad"""
        if self.cantidad_actual != 0:
            self.cantidad_actual = 0
            self.cantidad_display.setText("0")
            # Opcional: mostrar indicador visual temporal
            self.cantidad_display.setStyleSheet("""
                color: #EBCB8B;
                font-size: 36px;
                font-weight: bold;
                background-color: #2E3440;
                border-radius: 8px;
                padding: 10px;
            """)
            # Volver al estilo normal después de 1 segundo
            QTimer.singleShot(1000, lambda: self.cantidad_display.setStyleSheet("""
                color: white;
                font-size: 36px;
                font-weight: bold;
                background-color: #2E3440;
                border-radius: 8px;
                padding: 10px;
            """))

    def buscar_producto_ean(self):
        """Busca producto por código EAN y lo añade al carrito"""
        ean = self.ean_input.text().strip()
        if not ean:
            # Si se presiona Enter sin escanear nada y hay productos, ir al cobro rápido
            if self.carrito:
                self.abrir_cobro()
            return

        # Buscar producto en BD
        producto = self.db.fetch_one(
            "SELECT * FROM productos WHERE codigo_ean = ? AND activo = 1",
            (ean,)
        )

        if producto:
            self.añadir_al_carrito(
                producto_id=producto['id'],
                nombre=producto['descripcion'],
                precio=producto['precio'],
                cantidad=self.cantidad_actual or 1
            )
            self.ean_input.clear()
            self.limpiar_cantidad()
            self.setFocus()
        else:
            notify_warning(self, tr("Producto No Encontrado"),
                              tr("No se encontró ningún producto con EAN/IMEI") + f": {ean}")
            self.ean_input.selectAll()
            self.setFocus()

    def añadir_al_carrito(self, producto_id, nombre, precio, cantidad=1):
        """Añade un producto al carrito"""
        # VALIDAR STOCK si es un producto del inventario
        if producto_id:
            producto = self.db.fetch_one(
                "SELECT stock FROM productos WHERE id = ?",
                (producto_id,)
            )

            if producto:
                stock_disponible = producto['stock']

                # Verificar cuánto ya hay en el carrito
                cantidad_en_carrito = 0
                for item in self.carrito:
                    if item.get('producto_id') == producto_id:
                        cantidad_en_carrito = item['cantidad']
                        break

                # Validar que la cantidad total no exceda el stock
                cantidad_total = cantidad_en_carrito + cantidad

                if stock_disponible <= 0:
                    notify_warning(
                        self,
                        tr("Sin Stock"),
                        tr("El producto no tiene stock disponible") + f": '{nombre}'"
                    )
                    return

                if cantidad_total > stock_disponible:
                    notify_warning(
                        self,
                        tr("Stock Insuficiente"),
                        f"{tr('Stock disponible')}: {stock_disponible}\n"
                        f"{tr('Ya en carrito')}: {cantidad_en_carrito}\n"
                        f"{tr('Intentando añadir')}: {cantidad}\n"
                        f"{tr('Total necesario')}: {cantidad_total}\n\n"
                        f"{tr('No hay suficiente stock para')} '{nombre}'"
                    )
                    return

        # Calcular desglose IVA (precio incluye IVA)
        total_item = precio * cantidad
        subtotal, iva, total = calcular_desglose_iva(total_item)

        # Buscar si ya existe en el carrito
        for item in self.carrito:
            if item.get('producto_id') == producto_id:
                # Incrementar cantidad
                item['cantidad'] += cantidad
                # Calcular total primero (precio * cantidad)
                total_item = item['precio_unit'] * item['cantidad']
                # Luego calcular desglose IVA
                sub, iv, tot = calcular_desglose_iva(total_item)
                item['subtotal'] = sub
                item['iva'] = iv
                item['total'] = tot
                self.actualizar_tabla_carrito()
                self.calcular_totales()
                return

        # Agregar nuevo item
        self.carrito.append({
            'producto_id': producto_id,
            'nombre': nombre,
            'precio_unit': precio,
            'cantidad': cantidad,
            'subtotal': subtotal,
            'iva': iva,
            'total': total,
            'origen': 'productos' if producto_id else 'manual',
            'compra_item_id': None
        })

        self.actualizar_tabla_carrito()
        self.calcular_totales()

        # Reiniciar timer de auto-reset (el usuario está activamente trabajando)
        self.reset_timer.stop()
        self.reset_timer.start(self.tiempo_inactividad_ms)

    def actualizar_tabla_carrito(self):
        """Actualiza la tabla del carrito"""
        # Desconectar signals de widgets embebidos antes de limpiar filas
        for row in range(self.tabla_carrito.rowCount()):
            for col in range(self.tabla_carrito.columnCount()):
                widget = self.tabla_carrito.cellWidget(row, col)
                if widget:
                    widget.deleteLater()
        self.tabla_carrito.setRowCount(0)

        for idx, item in enumerate(self.carrito):
            row = self.tabla_carrito.rowCount()
            self.tabla_carrito.insertRow(row)
            self.tabla_carrito.setRowHeight(row, 60)

            # Nombre
            n_item = QTableWidgetItem(item['nombre'])
            n_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_carrito.setItem(row, 0, n_item)

            # Precio
            p_item = QTableWidgetItem(f"{item['precio_unit']:.2f} €")
            p_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_carrito.setItem(row, 1, p_item)

            # Cantidad editable - Widget con botones + y - visibles
            # Cantidad editable - [ - ] número [ + ] en horizontal
            btn_cant_style = """
                QPushButton {
                    background-color: #3B4252;
                    color: #ffffff;
                    border: 1px solid #4C566A;
                    border-radius: 3px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 0px;
                    margin: 0px;
                    text-align: center;
                }
                QPushButton:hover { background-color: #5E81AC; }
                QPushButton:pressed { background-color: #4C6E9A; }
            """

            container_cant = QWidget()
            container_cant.setStyleSheet("background: transparent;")
            h_layout_cant = QHBoxLayout(container_cant)
            h_layout_cant.setContentsMargins(4, 5, 4, 0)
            h_layout_cant.setSpacing(4)

            btn_menos = QPushButton("-")
            btn_menos.setFixedSize(26, 26)
            btn_menos.setStyleSheet(btn_cant_style)

            cant_label = QLabel(str(item['cantidad']))
            cant_label.setFixedSize(28, 26)
            cant_label.setAlignment(Qt.AlignCenter)
            cant_label.setStyleSheet("color: #ffffff; font-size: 12px; font-weight: bold; font-family: 'Segoe UI', Arial, sans-serif; background: transparent; padding-bottom: 3px;")

            btn_mas = QPushButton("+")
            btn_mas.setFixedSize(26, 26)
            btn_mas.setStyleSheet(btn_cant_style)

            btn_menos.clicked.connect(lambda checked, lbl=cant_label, i=idx: self._incrementar_cantidad(lbl, i, -1))
            btn_mas.clicked.connect(lambda checked, lbl=cant_label, i=idx: self._incrementar_cantidad(lbl, i, 1))

            h_layout_cant.addStretch()
            h_layout_cant.addWidget(btn_menos, 0, Qt.AlignTop)
            h_layout_cant.addWidget(cant_label, 0, Qt.AlignVCenter)
            h_layout_cant.addWidget(btn_mas, 0, Qt.AlignTop)
            h_layout_cant.addStretch()

            self.tabla_carrito.setCellWidget(row, 2, container_cant)

            # Subtotal
            sub_item = QTableWidgetItem(f"{item['subtotal']:.2f} €")
            sub_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_carrito.setItem(row, 3, sub_item)

            # IVA
            iva_item = QTableWidgetItem(f"{item['iva']:.2f} €")
            iva_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_carrito.setItem(row, 4, iva_item)

            # Total
            tot_item = QTableWidgetItem(f"{item['total']:.2f} €")
            tot_item.setTextAlignment(Qt.AlignCenter)
            tot_item.setFont(QFont("Segoe UI", 11, QFont.Bold))
            tot_item.setForeground(QColor('#88C0D0'))
            self.tabla_carrito.setItem(row, 5, tot_item)

            # Botón eliminar - Centrado estructural
            container_del = QWidget()
            v_layout_del = QVBoxLayout(container_del)
            v_layout_del.setContentsMargins(0, 0, 0, 10)
            v_layout_del.setAlignment(Qt.AlignCenter)

            btn_eliminar = QPushButton()
            btn_eliminar.setFixedSize(36, 36)
            from app.ui.styles import estilizar_btn_eliminar
            estilizar_btn_eliminar(btn_eliminar)
            btn_eliminar.clicked.connect(lambda checked, i=idx: self.eliminar_item_carrito(i))
            
            v_layout_del.addWidget(btn_eliminar)
            self.tabla_carrito.setCellWidget(row, 6, container_del)

    def _incrementar_cantidad(self, label, item_idx, delta):
        """Incrementa o decrementa la cantidad de un item con los botones +/-"""
        if 0 <= item_idx < len(self.carrito):
            nueva = self.carrito[item_idx]['cantidad'] + delta
            if nueva < 1:
                return
            label.setText(str(nueva))
            self.cambiar_cantidad(item_idx, nueva)

    def cambiar_cantidad(self, item_idx, nueva_cantidad):
        """Cambia la cantidad de un item en el carrito"""
        # VALIDAR que haya apertura de caja antes de modificar carrito
        from datetime import date
        fecha_hoy = date.today().strftime('%Y-%m-%d')
        estado, data = self.caja_manager.verificar_necesita_apertura(fecha_hoy)

        if estado != 'ok':
            notify_warning(
                self,
                tr("Apertura Requerida"),
                tr("No se puede modificar el carrito sin apertura de caja.") + "\n\n"
                + tr("Por favor, realice la apertura de caja antes de continuar.")
            )
            return

        if 0 <= item_idx < len(self.carrito):
            item = self.carrito[item_idx]

            # VALIDAR STOCK si es un producto del inventario
            if item.get('producto_id'):
                producto = self.db.fetch_one(
                    "SELECT stock FROM productos WHERE id = ?",
                    (item['producto_id'],)
                )

                if producto:
                    stock_disponible = producto['stock']

                    if nueva_cantidad > stock_disponible:
                        notify_warning(
                            self,
                            tr("Stock Insuficiente"),
                            f"{tr('Stock disponible')}: {stock_disponible}\n"
                            f"{tr('Cantidad solicitada')}: {nueva_cantidad}\n\n"
                            f"{tr('No hay suficiente stock para')} '{item['nombre']}'"
                        )
                        # Restaurar la cantidad anterior
                        self.actualizar_tabla_carrito()
                        return

            item['cantidad'] = nueva_cantidad
            total_item = item['precio_unit'] * nueva_cantidad
            sub, iv, tot = calcular_desglose_iva(total_item)
            item['subtotal'] = sub
            item['iva'] = iv
            item['total'] = tot

            self.actualizar_tabla_carrito()
            self.calcular_totales()

    def eliminar_item_carrito(self, item_idx):
        """Elimina un item específico del carrito"""
        if 0 <= item_idx < len(self.carrito):
            item = self.carrito[item_idx]

            # Confirmar eliminación
            if ask_confirm(self, tr("Eliminar Item"),
                          tr("¿Eliminar del carrito?") + f" '{item['nombre']}'"):
                # Eliminar del carrito
                self.carrito.pop(item_idx)
                self.actualizar_tabla_carrito()
                self.calcular_totales()

    def calcular_totales(self):
        """Calcula y muestra los totales del carrito"""
        # Sumar todos los valores de los artículos
        subtotal = 0.0
        iva = 0.0
        total = 0.0
        
        for item in self.carrito:
            subtotal += float(item.get('subtotal', 0))
            iva += float(item.get('iva', 0))
            total += float(item.get('total', 0))
        
        # Redondear a 2 decimales
        subtotal = round(subtotal, 2)
        iva = round(iva, 2)
        total = round(total, 2)

        # Formatear con punto decimal explícito - construir string manualmente
        def formatear_numero(num):
            """Formatea un número con punto decimal explícito usando punto ASCII"""
            # Separar parte entera y decimal
            entero = int(abs(num))
            decimal = int(round((abs(num) - entero) * 100))
            signo = "-" if num < 0 else ""
            # Construir string con punto explícito (carácter ASCII 46)
            return f"{signo}{entero}{chr(46)}{decimal:02d}"
        
        self.subtotal_label.setText(formatear_numero(subtotal) + " €")
        self.iva_label.setText(formatear_numero(iva) + " €")
        self.total_label.setText(formatear_numero(total) + " €")

    def limpiar_carrito(self):
        """Limpia todos los productos del carrito"""
        if self.carrito:
            if ask_confirm(self, tr("Limpiar Carrito"),
                          tr("¿Estás seguro de vaciar el carrito?")):
                self.carrito = []
                self.actualizar_tabla_carrito()
                self.calcular_totales()
                self.limpiar_cantidad()
                self.setFocus()

    def abrir_producto_manual(self):
        """Abre diálogo para añadir producto manual"""
        if self.cantidad_actual == 0:
            notify_warning(self, tr("Cantidad inválida"), tr("Introduce una cantidad antes de añadir un producto"))
            return
        from app.ui.tpv_producto_manual_dialog import TPVProductoManualDialog
        dialog = TPVProductoManualDialog(self.cantidad_actual, parent=self)
        if dialog.exec_():
            datos = dialog.get_datos()
            self.añadir_al_carrito(
                producto_id=None,
                nombre=datos['nombre'],
                precio=datos['precio'],
                cantidad=datos['cantidad']
            )
            self.limpiar_cantidad()

    def abrir_cobro(self):
        """Abre diálogo de cobro"""
        if not self.carrito:
            notify_warning(self, tr("Carrito vacío"), tr("Añade productos antes de cobrar"))
            return

        from app.ui.tpv_cobro_dialog import TPVCobroDialog
        total = sum(item['total'] for item in self.carrito)
        dialog = TPVCobroDialog(total, parent=self)

        if dialog.exec_():
            datos_cobro = dialog.get_datos()
            self.procesar_venta(datos_cobro)

    def procesar_venta(self, datos_cobro):
        """Procesa y guarda la venta"""
        try:
            # Calcular totales
            subtotal = sum(item['subtotal'] for item in self.carrito)
            iva = sum(item['iva'] for item in self.carrito)
            total = sum(item['total'] for item in self.carrito)

            # Obtener usuario_id si está disponible (desde parent window)
            usuario_id = None
            try:
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'auth_manager'):
                        usuario_actual = parent.auth_manager.obtener_usuario_actual()
                        if usuario_actual:
                            usuario_id = usuario_actual.get('id')
                        break
                    parent = parent.parent()
            except (OSError, ValueError, RuntimeError):
                pass

            # Guardar venta (llamar directamente a guardar_venta para capturar errores)
            resultado, error = self.tpv_manager.guardar_venta(
                items=self.carrito,
                metodo_pago=datos_cobro['metodo_pago'],
                usuario_id=usuario_id,
                cantidad_recibida=datos_cobro.get('cantidad_recibida'),
                cambio_devuelto=datos_cobro.get('cambio_devuelto')
            )

            # Verificar si se requiere apertura de caja o hay cierre pendiente
            if error and error.startswith("APERTURA_REQUIRED:"):
                partes = error.split(":")
                estado = partes[1]
                # Para cierre_pendiente, extraer la fecha del día sin cerrar
                if len(partes) > 2:
                    datos_cobro['fecha_pendiente'] = partes[2]
                self.manejar_apertura_requerida(estado, datos_cobro)
                return

            if resultado:
                numero_ticket = resultado.get('numero_ticket')

                # Imprimir ticket si se solicitó
                if datos_cobro['imprimir']:
                    self.imprimir_ticket(numero_ticket)

                notify_success(self, tr("Venta completada"),
                                      tr("Venta registrada correctamente") + f"\nTicket: {numero_ticket}")

                # Limpiar carrito
                self.carrito = []
                self.actualizar_tabla_carrito()
                self.calcular_totales()
                self.limpiar_cantidad()
                self.setFocus()

                # Actualizar saldo de caja
                self.actualizar_saldo_caja()
            else:
                error_msg = error if error else tr("No se pudo completar la venta")
                notify_error(self, tr("Error"), error_msg)

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al procesar venta") + f":\n{str(e)}")

    def imprimir_ticket(self, numero_ticket):
        """Imprime el ticket de venta"""
        try:
            from app.modules.ticket_printer import TicketPrinter

            # Verificar si hay impresora de tickets configurada
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_ticket'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                # Sin impresora: solo avisar
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora de tickets configurada.") + "\n"
                    + tr("Ve a Ajustes > Impresoras para configurarla."))
                return

            # Buscar la venta por número de ticket
            venta = self.db.fetch_one(
                "SELECT id FROM ventas_caja WHERE numero_ticket = ?",
                (numero_ticket,)
            )

            if not venta:
                notify_warning(self, tr("Error"), tr("No se encontró la venta con ticket") + f" {numero_ticket}")
                return

            # Obtener los datos completos de la venta
            venta_completa = self.tpv_manager.obtener_venta(venta['id'])

            if not venta_completa:
                notify_warning(self, tr("Error"), tr("No se pudieron obtener los datos de la venta"))
                return

            # Imprimir directamente a la impresora térmica
            ticket_printer = TicketPrinter(self.db)
            exito, mensaje = ticket_printer.imprimir_a_impresora_windows(venta_completa, printer_name)

            if exito:
                notify_success(self, tr("Impreso"), f"Ticket {numero_ticket} " + tr("enviado a") + f" {printer_name}")
            else:
                notify_warning(self, tr("Error"), mensaje)

        except (OSError, ValueError, RuntimeError) as e:
            notify_warning(self, tr("Error al imprimir"), tr("No se pudo imprimir") + f":\n{str(e)}")

    def actualizar_saldo_caja(self):
        """Actualiza el display del saldo de caja actual"""
        try:
            saldo = self.caja_manager.obtener_saldo_actual()
            self.saldo_caja_label.setText(f"{saldo:.2f} €")

            # Cambiar color según el saldo (constantes Nord)
            base_style = "font-family: 'Segoe UI', Arial, sans-serif; font-weight: bold;"
            if saldo < 0:
                self.saldo_caja_label.setStyleSheet(f"{base_style} color: {COLOR_DANGER};")
            elif saldo < 100:
                self.saldo_caja_label.setStyleSheet(f"{base_style} color: {COLOR_WARNING};")
            else:
                self.saldo_caja_label.setStyleSheet(f"{base_style} color: {COLOR_ACCENT};")
        except (OSError, ValueError, RuntimeError) as e:
            self.saldo_caja_label.setText("Error")
            self.saldo_caja_label.setStyleSheet(f"font-family: 'Segoe UI', Arial, sans-serif; color: {COLOR_DANGER};")

    def cargar_favoritos(self):
        """Carga los productos favoritos en grid de 4 columnas con validación de stock"""
        favoritos = self.db.fetch_all(
            "SELECT * FROM productos_favoritos ORDER BY orden, nombre"
        )

        # Limpiar layout
        while self.favoritos_layout.count() > 0:
            item = self.favoritos_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Añadir botones de favoritos en grid de 4 columnas
        COLUMNAS = 4
        for idx, fav in enumerate(favoritos):
            row = idx // COLUMNAS
            col = idx % COLUMNAS

            # VALIDAR STOCK si el favorito está vinculado a un producto
            stock_disponible = None
            sin_stock = False
            stock_bajo = False

            if fav.get('producto_id'):
                producto = self.db.fetch_one(
                    "SELECT stock FROM productos WHERE id = ? AND activo = 1",
                    (fav['producto_id'],)
                )

                if producto is not None:
                    stock_disponible = producto['stock']
                    sin_stock = (stock_disponible <= 0)
                    stock_bajo = (0 < stock_disponible <= 5)

            # Construir texto del botón con indicador de stock
            texto_boton = fav['nombre']
            if stock_disponible is not None:
                if sin_stock:
                    texto_boton = f"{fav['nombre']}\n⚠ {tr('SIN STOCK')}"
                elif stock_bajo:
                    texto_boton = f"{fav['nombre']}\n({stock_disponible})"

            btn = QPushButton(texto_boton)
            btn.setFixedHeight(50)
            btn.setFixedWidth(85)
            btn.setFont(QFont("", 8, QFont.Bold))

            # Determinar color según estado de stock
            if sin_stock:
                # Sin stock: gris oscuro con borde rojo
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #434C5E;
                        color: #D8DEE9;
                        border: 2px solid #BF616A;
                        border-radius: 8px;
                        text-align: center;
                        padding: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: #4C566A;
                    }}
                """)
                # Aún permitir clic (mostrará error al añadir)
                btn.setEnabled(True)
            elif stock_bajo:
                # Stock bajo: naranja
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #D08770;
                        color: white;
                        border: 2px solid #BF6B50;
                        border-radius: 8px;
                        text-align: center;
                        padding: 8px;
                    }}
                    QPushButton:hover {{
                        background-color: #BF6B50;
                    }}
                """)
            else:
                # Stock normal o producto manual: color original
                color = fav.get('color', COLOR_PRIMARY)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        color: white;
                        border: 2px solid transparent;
                        border-radius: 8px;
                        text-align: center;
                        padding: 8px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #ECEFF4;
                    }}
                """)

            btn.clicked.connect(lambda checked, f=fav: self.añadir_favorito_al_carrito(f))
            self.favoritos_layout.addWidget(btn, row, col)

        # Añadir stretch vertical al final para empujar todo hacia arriba
        if favoritos:
            last_row = (len(favoritos) - 1) // COLUMNAS + 1
            self.favoritos_layout.setRowStretch(last_row, 1)

    def añadir_favorito_al_carrito(self, favorito):
        """Añade un producto favorito al carrito"""
        self.añadir_al_carrito(
            producto_id=favorito.get('producto_id'),
            nombre=favorito['nombre'],
            precio=favorito['precio'],
            cantidad=1
        )

    def agregar_favorito(self):
        """Abre diálogo para agregar nuevo favorito"""
        from app.ui.tpv_agregar_favorito_dialog import TPVAgregarFavoritoDialog
        dialog = TPVAgregarFavoritoDialog(self.db, parent=self)
        if dialog.exec_():
            self.cargar_favoritos()

    def manejar_apertura_requerida(self, estado, datos_cobro):
        """
        Maneja los casos donde se requiere apertura/cierre de caja.
        BLOQUEA la operación y dirige al usuario a Caja Movimientos.

        estados: 'apertura_requerida', 'reapertura_requerida', 'apertura_nueva_dia', 'cierre_pendiente'
        """
        from datetime import date
        fecha_hoy = date.today().strftime('%Y-%m-%d')

        # CASO 1: Cierre pendiente de día anterior
        if estado == 'cierre_pendiente':
            fecha_pendiente = datos_cobro.get('fecha_pendiente', tr('anterior'))
            notify_warning(
                self,
                tr("Cierre de Caja Pendiente"),
                tr("Hay una caja del día") + f" {fecha_pendiente} " + tr("sin cerrar.") + "\n\n"
                + tr("Debe cerrar esa caja antes de realizar ventas.") + "\n\n"
                + "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n"
                + "👉 " + tr("Use el botón") + " 🔒 " + tr("Cerrar Caja")
            )
            return

        # CASO 2: Caja de hoy ya cerrada - necesita reapertura
        if estado == 'reapertura_requerida':
            notify_warning(
                self,
                tr("Caja Ya Cerrada"),
                tr("La caja de hoy ya fue cerrada.") + "\n\n"
                + tr("Para realizar ventas debe reabrir la caja.") + "\n\n"
                + "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n"
                + "👉 " + tr("Y reabra la caja del día")
            )
            return

        # CASO 3: Caja de hoy no abierta - necesita apertura
        if estado in ['apertura_requerida', 'apertura_nueva_dia']:
            notify_warning(
                self,
                tr("Apertura de Caja Requerida"),
                tr("La caja de hoy no está abierta.") + "\n\n"
                + tr("Debe abrir la caja antes de realizar ventas.") + "\n\n"
                + "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n"
                + "👉 " + tr("Use el botón") + " 🔓 " + tr("Abrir Caja")
            )
            return

        # Si llegamos aquí con otro estado no manejado, mostrar error genérico
        notify_warning(
            self,
            tr("Error de Caja"),
            tr("No se puede procesar la venta.") + "\n"
            + tr("Estado de caja") + f": {estado}\n\n"
            + "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos")
        )

    def keyPressEvent(self, event):
        """Captura teclado físico: dígitos → cantidad, + → añadir, Enter → cobrar"""
        key = event.key()
        if key in (Qt.Key_0, Qt.Key_1, Qt.Key_2, Qt.Key_3, Qt.Key_4,
                   Qt.Key_5, Qt.Key_6, Qt.Key_7, Qt.Key_8, Qt.Key_9):
            self.tecla_numero(str(key - Qt.Key_0))
        elif key == Qt.Key_Plus:
            self.abrir_producto_manual()
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            if self.ean_input.text().strip():
                self.buscar_producto_ean()
            else:
                self.abrir_cobro()
        elif key in (Qt.Key_Backspace, Qt.Key_Delete):
            self.limpiar_cantidad()
        else:
            super().keyPressEvent(event)

    def showEvent(self, event):
        """Evento al mostrar la pestaña"""
        super().showEvent(event)
        self.setFocus()

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
