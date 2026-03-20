"""
Pestaña para crear compras a proveedores
"""
import os
from app.ui.styles import estilizar_btn_eliminar, THEMES
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
                             QDateEdit, QHeaderView, QDoubleSpinBox, QSpinBox,
                             QComboBox, QApplication, QListWidget, QListWidgetItem)
from app.utils.notify import notify_success, notify_error, notify_warning, notify_info, ask_confirm
from config import IVA_RATE, calcular_desglose_iva
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont
from app.db.database import Database
from app.i18n import tr
from app.modules.compra_manager import CompraManager
from app.ui.articulo_dialog import ArticuloDialog
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel, apply_btn_success, set_btn_icon
from qfluentwidgets import FluentIcon
from qfluentwidgets import SearchLineEdit


class ComprasNuevaTab(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.db.connect()
        self.compra_manager = CompraManager(self.db)
        self.dni_imagen_path = None  # Ruta de la imagen del DNI escaneado
        self.cliente_id_seleccionado = None  # ID del cliente seleccionado
        self.setup_ui()
        self.load_clientes()
        self.cargar_nuevo_numero_compra()

    def _obtener_usuario_id(self):
        """Obtiene el ID del usuario actual para auditoría"""
        try:
            main_window = self.window()
            if hasattr(main_window, 'auth_manager') and main_window.auth_manager:
                usuario = main_window.auth_manager.obtener_usuario_actual()
                if usuario:
                    return usuario.get('id')
        except (OSError, ValueError, RuntimeError):
            pass
        return None

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Header con número y fecha
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        numero_label = QLabel(tr("Nº Compra") + ":")
        numero_label.setStyleSheet("font-weight: bold;")
        self.numero_input = QLineEdit()
        self.numero_input.setReadOnly(True)
        self.numero_input.setMaximumWidth(150)
        self.numero_input.setStyleSheet("color: #ffffff; font-weight: bold;")

        fecha_label = QLabel(tr("Fecha") + ":")
        fecha_label.setStyleSheet("font-weight: bold;")
        self.fecha_input = QDateEdit()
        self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)
        self.fecha_input.setMaximumWidth(150)

        header_layout.addWidget(numero_label)
        header_layout.addWidget(self.numero_input)
        header_layout.addSpacing(20)
        header_layout.addWidget(fecha_label)
        header_layout.addWidget(self.fecha_input)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Datos del cliente con detección automática (solo lectura)
        cliente_title = QLabel(tr("DATOS DEL CLIENTE") + " - " + tr("Detección Automática"))
        cliente_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #ffffff; padding: 2px 0; background: transparent;")
        layout.addWidget(cliente_title)

        cliente_group = QGroupBox()
        cliente_group.setObjectName("cardGroup")
        cliente_layout = QVBoxLayout()
        cliente_layout.setContentsMargins(15, 15, 15, 15)
        cliente_layout.setSpacing(10)

        # Búsqueda rápida por nombre, DNI o Teléfono
        busqueda_layout = QHBoxLayout()
        busqueda_layout.setAlignment(Qt.AlignVCenter)
        busqueda_layout.addWidget(QLabel(tr("Buscar cliente") + ":"))
        self.busqueda_cliente_input = SearchLineEdit()
        self.busqueda_cliente_input.setFixedHeight(36)
        self.busqueda_cliente_input.setPlaceholderText(tr("Nombre, DNI o Teléfono..."))
        self.busqueda_cliente_input.textChanged.connect(self._filtrar_clientes_live)
        self.busqueda_cliente_input.returnPressed.connect(self.buscar_cliente_auto)
        busqueda_layout.addWidget(self.busqueda_cliente_input)

        btn_buscar_cliente = QPushButton(tr("Buscar"))
        btn_buscar_cliente.clicked.connect(self.buscar_cliente_auto)
        apply_btn_primary(btn_buscar_cliente)
        set_btn_icon(btn_buscar_cliente, FluentIcon.SEARCH, color="#5E81AC")
        btn_buscar_cliente.setFixedHeight(36)
        btn_buscar_cliente.setMaximumWidth(100)
        busqueda_layout.addWidget(btn_buscar_cliente)

        cliente_layout.addLayout(busqueda_layout)

        # Lista de sugerencias en tiempo real
        self.lista_sugerencias = QListWidget()
        self.lista_sugerencias.setMaximumHeight(100)
        self.lista_sugerencias.setVisible(False)
        self.lista_sugerencias.setStyleSheet("""
            QListWidget {
                background-color: #2E3440;
                border: 1px solid #5E81AC;
                border-radius: 6px;
                color: #ECEFF4;
                font-size: 13px;
            }
            QListWidget::item { padding: 6px 10px; border-bottom: 1px solid #3B4252; }
            QListWidget::item:hover { background-color: #3B4252; }
            QListWidget::item:selected { background-color: #5E81AC; color: #ffffff; }
        """)
        self.lista_sugerencias.itemClicked.connect(self._seleccionar_cliente_lista)
        cliente_layout.addWidget(self.lista_sugerencias)

        # Selector de cliente existente
        selector_layout = QHBoxLayout()
        selector_layout.setAlignment(Qt.AlignVCenter)
        selector_layout.addWidget(QLabel(tr("O seleccionar") + ":"))
        self.cliente_combo = QComboBox()
        self.cliente_combo.setEditable(True)
        self.cliente_combo.setFixedHeight(36)
        self.cliente_combo.currentIndexChanged.connect(self.on_cliente_selected)
        selector_layout.addWidget(self.cliente_combo)

        btn_nuevo_cliente = QPushButton(tr("Nuevo Cliente"))
        btn_nuevo_cliente.clicked.connect(self.abrir_nuevo_cliente)
        btn_nuevo_cliente.setFixedHeight(36)
        btn_nuevo_cliente.setMaximumWidth(150)
        apply_btn_success(btn_nuevo_cliente)
        set_btn_icon(btn_nuevo_cliente, FluentIcon.ADD, color="#A3BE8C")
        selector_layout.addWidget(btn_nuevo_cliente)

        cliente_layout.addLayout(selector_layout)

        # Campos del cliente (solo lectura) - Layout responsivo
        campos_layout = QHBoxLayout()
        campos_layout.setSpacing(10)

        # Estilo para campos de solo lectura (compacto)
        current_theme = QApplication.instance().property("theme") or "dark"
        t = THEMES[current_theme]
        label_style = f"font-size: 11px; color: {t['text_secondary']}; margin: 0; padding: 0;"
        
        # Estilo para campos de solo lectura (letras blancas)
        readonly_style = f"QLineEdit {{ color: {t['text_main']}; font-weight: bold; }}"

        left_col = QVBoxLayout()
        left_col.setSpacing(2)
        lbl = QLabel(tr("Nombre") + ":")
        lbl.setStyleSheet(label_style)
        left_col.addWidget(lbl)
        self.nombre_input = QLineEdit()
        self.nombre_input.setReadOnly(True)
        self.nombre_input.setStyleSheet(readonly_style)
        left_col.addWidget(self.nombre_input)
        lbl2 = QLabel(tr("NIF/CIF") + ":")
        lbl2.setStyleSheet(label_style)
        left_col.addWidget(lbl2)
        self.nif_input = QLineEdit()
        self.nif_input.setReadOnly(True)
        self.nif_input.setStyleSheet(readonly_style)
        left_col.addWidget(self.nif_input)
        lbl_cp = QLabel(tr("C.P.") + ":")
        lbl_cp.setStyleSheet(label_style)
        left_col.addWidget(lbl_cp)
        self.cp_input = QLineEdit()
        self.cp_input.setReadOnly(True)
        self.cp_input.setStyleSheet(readonly_style)
        left_col.addWidget(self.cp_input)

        right_col = QVBoxLayout()
        right_col.setSpacing(2)
        lbl3 = QLabel(tr("Dirección") + ":")
        lbl3.setStyleSheet(label_style)
        right_col.addWidget(lbl3)
        self.direccion_input = QLineEdit()
        self.direccion_input.setReadOnly(True)
        self.direccion_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.direccion_input)
        lbl_ciudad = QLabel(tr("Ciudad") + ":")
        lbl_ciudad.setStyleSheet(label_style)
        right_col.addWidget(lbl_ciudad)
        self.ciudad_input = QLineEdit()
        self.ciudad_input.setReadOnly(True)
        self.ciudad_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.ciudad_input)
        lbl_provincia = QLabel(tr("Provincia:"))
        lbl_provincia.setStyleSheet(label_style)
        right_col.addWidget(lbl_provincia)
        self.provincia_input = QLineEdit()
        self.provincia_input.setReadOnly(True)
        self.provincia_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.provincia_input)
        lbl4 = QLabel(tr("Teléfono") + ":")
        lbl4.setStyleSheet(label_style)
        right_col.addWidget(lbl4)
        self.telefono_input = QLineEdit()
        self.telefono_input.setReadOnly(True)
        self.telefono_input.setStyleSheet(readonly_style)
        right_col.addWidget(self.telefono_input)

        # Usar stretch 1:1 para que ambas columnas se expandan igual
        campos_layout.addLayout(left_col, 1)
        campos_layout.addLayout(right_col, 1)
        cliente_layout.addLayout(campos_layout)

        # Sección de vista DNI (compacta)
        dni_layout = QHBoxLayout()
        dni_layout.setSpacing(8)

        self.dni_preview_label = QLabel("📋 " + tr("DNI no disponible"))
        self.dni_preview_label.setStyleSheet("""
            QLabel {
                background-color: #3B4252;
                border: 1px dashed #4C566A;
                border-radius: 4px;
                padding: 6px;
                min-height: 40px;
                color: #7B88A0;
                font-size: 11px;
            }
        """)
        self.dni_preview_label.setMinimumWidth(150)
        dni_layout.addWidget(self.dni_preview_label)

        info_label = QLabel("ℹ️ " + tr("Editar cliente para actualizar DNI"))
        info_label.setStyleSheet("color: #7B88A0; font-style: italic; font-size: 10px;")
        dni_layout.addWidget(info_label)

        dni_layout.addStretch()
        cliente_layout.addLayout(dni_layout)

        cliente_group.setLayout(cliente_layout)
        layout.addWidget(cliente_group)

        # Tabla de productos
        productos_label = QLabel(tr("Productos Comprados"))
        productos_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 2px 0;")
        layout.addWidget(productos_label)

        self.tabla_productos = QTableWidget(0, 7)
        self.tabla_productos.setHorizontalHeaderLabels([
            tr("Descripción"), "EAN", "IMEI/SN", tr("Cantidad"), tr("Precio Unit."), tr("Total"), tr("Acciones")
        ])

        header = self.tabla_productos.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.tabla_productos.setColumnWidth(6, 80) # Solo un botón eliminar
        
        self.tabla_productos.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla_productos.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla_productos.verticalHeader().setDefaultSectionSize(60)
        self.tabla_productos.verticalHeader().setVisible(False)
        self.tabla_productos.setStyleSheet("QTableWidget::item { padding: 0px; }")

        # La tabla se expande para llenar el espacio disponible
        layout.addWidget(self.tabla_productos, 1)  # stretch=1 para expandir

        # Botones de productos
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("+ " + tr("Añadir Producto"))
        btn_add.clicked.connect(self.agregar_fila_producto)
        btn_add.setStyleSheet("background-color: transparent; color: #A3BE8C; border: 2px solid #A3BE8C; border-radius: 6px; padding: 4px 10px;")
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Totales (compacto en línea)
        totales_layout = QHBoxLayout()
        totales_layout.addStretch()

        self.subtotal_label = QLabel(tr("Subtotal") + ": 0.00 €")
        self.subtotal_label.setStyleSheet("font-size: 11px; color: #7B88A0; padding: 0 10px;")
        totales_layout.addWidget(self.subtotal_label)

        self.iva_label = QLabel(f"{tr('IVA')} ({int(IVA_RATE*100)}%): 0.00 €")
        self.iva_label.setStyleSheet("font-size: 11px; color: #7B88A0; padding: 0 10px;")
        totales_layout.addWidget(self.iva_label)

        self.total_label = QLabel(tr("Total").upper() + ": 0.00 €")
        self.total_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #BF616A; padding: 0 10px;")
        totales_layout.addWidget(self.total_label)

        layout.addLayout(totales_layout)

        # Botones de acción (compactos)
        acciones_layout = QHBoxLayout()
        acciones_layout.addStretch()

        btn_limpiar = QPushButton(tr("Limpiar"))
        btn_limpiar.clicked.connect(self.limpiar_formulario)
        apply_btn_cancel(btn_limpiar)

        btn_guardar = QPushButton(tr("Registrar Compra"))
        btn_guardar.clicked.connect(self.guardar_compra)
        apply_btn_primary(btn_guardar)

        acciones_layout.addWidget(btn_limpiar)
        acciones_layout.addWidget(btn_guardar)
        layout.addLayout(acciones_layout)

    def agregar_fila_producto(self):
        """Abre diálogo para añadir un nuevo producto con marca y modelo"""
        dialog = ArticuloDialog(self.db, parent=self)

        if dialog.exec_():
            resultado = dialog.obtener_resultado()

            if resultado:
                # Crear fila con los datos del diálogo
                row = self.tabla_productos.rowCount()
                self.tabla_productos.insertRow(row)
                self.tabla_productos.setRowHeight(row, 60)

                # Descripción
                desc_input = QLineEdit()
                desc_input.setText(resultado['descripcion'])
                desc_input.setFixedSize(300, 32)
                
                container_desc = QWidget()
                v_layout_desc = QVBoxLayout(container_desc)
                v_layout_desc.setContentsMargins(5, 0, 5, 10)
                v_layout_desc.setAlignment(Qt.AlignCenter)
                v_layout_desc.addWidget(desc_input)
                self.tabla_productos.setCellWidget(row, 0, container_desc)

                # EAN
                ean_input = QLineEdit()
                ean_input.setText(resultado['ean'] or '')
                ean_input.setFixedSize(120, 32)
                
                container_ean = QWidget()
                v_layout_ean = QVBoxLayout(container_ean)
                v_layout_ean.setContentsMargins(5, 0, 5, 10)
                v_layout_ean.setAlignment(Qt.AlignCenter)
                v_layout_ean.addWidget(ean_input)
                self.tabla_productos.setCellWidget(row, 1, container_ean)

                # IMEI/SN
                imei_input = QLineEdit()
                imei_input.setText(resultado['imei'] or '')
                imei_input.setFixedSize(140, 32)
                
                container_imei = QWidget()
                v_layout_imei = QVBoxLayout(container_imei)
                v_layout_imei.setContentsMargins(5, 0, 5, 10)
                v_layout_imei.setAlignment(Qt.AlignCenter)
                v_layout_imei.addWidget(imei_input)
                self.tabla_productos.setCellWidget(row, 2, container_imei)

                # Cantidad
                cantidad_spin = QSpinBox()
                cantidad_spin.setMinimum(1)
                cantidad_spin.setValue(resultado['cantidad'])
                cantidad_spin.valueChanged.connect(self.calcular_totales)
                cantidad_spin.setFixedSize(60, 32)
                
                container_cant = QWidget()
                v_layout_cant = QVBoxLayout(container_cant)
                v_layout_cant.setContentsMargins(5, 0, 5, 10)
                v_layout_cant.setAlignment(Qt.AlignCenter)
                v_layout_cant.addWidget(cantidad_spin)
                self.tabla_productos.setCellWidget(row, 3, container_cant)

                # Precio unitario
                precio_spin = QDoubleSpinBox()
                precio_spin.setMinimum(0)
                precio_spin.setMaximum(999999)
                precio_spin.setDecimals(2)
                precio_spin.setValue(resultado['precio'])
                precio_spin.valueChanged.connect(self.calcular_totales)
                precio_spin.setFixedSize(100, 32)
                
                container_precio = QWidget()
                v_layout_precio = QVBoxLayout(container_precio)
                v_layout_precio.setContentsMargins(5, 0, 5, 10)
                v_layout_precio.setAlignment(Qt.AlignCenter)
                v_layout_precio.addWidget(precio_spin)
                self.tabla_productos.setCellWidget(row, 4, container_precio)

                # Total
                total = resultado['cantidad'] * resultado['precio']
                total_item = QTableWidgetItem(f"{total:.2f} €")
                total_item.setFlags(Qt.ItemIsEnabled)
                total_item.setTextAlignment(Qt.AlignCenter)
                # Guardar todos los datos del resultado en el item para recuperarlos después
                total_item.setData(Qt.UserRole, resultado)
                self.tabla_productos.setItem(row, 5, total_item)

                # Botones
                self.agregar_botones_fila(row)

                # Recalcular totales
                self.calcular_totales()

    def agregar_botones_fila(self, row):
        """Añade botones de acción a una fila - Centrado estructural"""
        container = QWidget()
        v_layout = QVBoxLayout(container)
        v_layout.setContentsMargins(8, 0, 8, 10)
        v_layout.setAlignment(Qt.AlignCenter)

        # Botón eliminar
        btn_del = QPushButton()
        btn_del.setToolTip(tr("Eliminar"))
        btn_del.clicked.connect(lambda: self.eliminar_fila(row))
        estilizar_btn_eliminar(btn_del)
        
        v_layout.addWidget(btn_del)
        self.tabla_productos.setCellWidget(row, 6, container)

    def eliminar_fila(self, row):
        """Elimina una fila de productos"""
        if self.tabla_productos.rowCount() > 0:
            self.tabla_productos.removeRow(row)
            self.calcular_totales()

    def load_clientes(self):
        """Carga la lista de clientes"""
        self.cliente_combo.clear()
        self.cliente_combo.addItem("-- " + tr("Seleccionar Cliente") + " --", None)

        clientes = self.db.fetch_all("SELECT id, nombre FROM clientes ORDER BY nombre")
        for cliente in clientes:
            self.cliente_combo.addItem(cliente['nombre'], cliente['id'])

    def on_cliente_selected(self, index):
        """Cuando se selecciona un cliente, carga sus datos"""
        cliente_id = self.cliente_combo.currentData()
        self.cliente_id_seleccionado = cliente_id  # Guardar ID del cliente
        if cliente_id:
            cliente = self.db.fetch_one("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            if cliente:
                self.nombre_input.setText(cliente['nombre'])
                self.nif_input.setText(cliente['nif'] or '')
                self.direccion_input.setText(cliente['direccion'] or '')
                self.telefono_input.setText(cliente['telefono'] or '')
                self.cp_input.setText(cliente.get('codigo_postal') or '')
                self.ciudad_input.setText(cliente.get('ciudad') or '')
                self.provincia_input.setText(cliente.get('provincia') or '')

                # Cargar imagen del DNI si existe
                if cliente.get('dni_imagen') and os.path.exists(cliente['dni_imagen']):
                    self.dni_imagen_path = cliente['dni_imagen']
                    self.actualizar_preview_dni()
                else:
                    self.quitar_imagen_dni()

    def abrir_nuevo_cliente(self):
        """Abre diálogo para crear nuevo cliente"""
        from app.ui.cliente_dialog import ClienteDialog
        dialog = ClienteDialog(self.db, parent=self)
        if dialog.exec_():
            self.load_clientes()

    def _filtrar_clientes_live(self, texto):
        """Filtra clientes en tiempo real por nombre, DNI o teléfono"""
        texto = texto.strip()
        self.lista_sugerencias.clear()
        if len(texto) < 2:
            self.lista_sugerencias.setVisible(False)
            return
        like = f'%{texto}%'
        clientes = self.db.fetch_all(
            "SELECT * FROM clientes WHERE nombre LIKE ? OR nif LIKE ? OR telefono LIKE ? LIMIT 8",
            (like, like, like)
        )
        if not clientes:
            self.lista_sugerencias.setVisible(False)
            return
        for c in clientes:
            nombre = c.get('nombre') or ''
            nif = c.get('nif') or '-'
            tel = c.get('telefono') or '-'
            item = QListWidgetItem(f"{nombre}   |   {nif}   |   {tel}")
            item.setData(Qt.UserRole, dict(c))
            self.lista_sugerencias.addItem(item)
        self.lista_sugerencias.setVisible(True)

    def _seleccionar_cliente_lista(self, item):
        """Selecciona un cliente de la lista de sugerencias"""
        cliente = item.data(Qt.UserRole)
        self._rellenar_campos_cliente(cliente)
        self.lista_sugerencias.setVisible(False)
        self.busqueda_cliente_input.clear()

    def _rellenar_campos_cliente(self, cliente):
        """Rellena los campos del formulario con los datos del cliente"""
        self.cliente_id_seleccionado = cliente['id']
        self.nombre_input.setText(cliente['nombre'])
        self.nif_input.setText(cliente.get('nif') or '')
        self.direccion_input.setText(cliente.get('direccion') or '')
        self.telefono_input.setText(cliente.get('telefono') or '')
        self.cp_input.setText(cliente.get('codigo_postal') or '')
        self.ciudad_input.setText(cliente.get('ciudad') or '')
        self.provincia_input.setText(cliente.get('provincia') or '')
        index = self.cliente_combo.findData(cliente['id'])
        if index >= 0:
            self.cliente_combo.setCurrentIndex(index)
        if cliente.get('dni_imagen') and os.path.exists(cliente['dni_imagen']):
            self.dni_imagen_path = cliente['dni_imagen']
            self.actualizar_preview_dni()
        else:
            self.quitar_imagen_dni()

    def buscar_cliente_auto(self):
        """Busca cliente al pulsar Enter o Buscar — selecciona el primero si hay sugerencias"""
        # Si hay sugerencias visibles, seleccionar la primera
        if self.lista_sugerencias.isVisible() and self.lista_sugerencias.count() > 0:
            self._seleccionar_cliente_lista(self.lista_sugerencias.item(0))
            return

        busqueda = self.busqueda_cliente_input.text().strip()
        if not busqueda:
            return

        like = f'%{busqueda}%'
        cliente = self.db.fetch_one(
            "SELECT * FROM clientes WHERE nif LIKE ? OR telefono LIKE ? OR nombre LIKE ? LIMIT 1",
            (like, like, like)
        )

        if cliente:
            self._rellenar_campos_cliente(dict(cliente))
            dni_status = "✓ " + tr("DNI registrado") if cliente.get('dni_imagen') else "⚠️ " + tr("Sin DNI")
            notify_success(self, tr("Cliente Encontrado"), tr("Cliente") + f": {cliente['nombre']}\n{dni_status}")
        else:
            if ask_confirm(
                self,
                tr("Cliente No Encontrado"),
                tr("No se encontró ningún cliente con") + f": {busqueda}\n\n" + tr("¿Desea crear un nuevo cliente?")
            ):
                self.abrir_nuevo_cliente()
                self.busqueda_cliente_input.clear()

    def calcular_totales(self):
        """Calcula y actualiza los totales.
        Los precios introducidos YA incluyen IVA, se extrae el desglose."""
        total_general = 0

        for row in range(self.tabla_productos.rowCount()):
            cantidad_container = self.tabla_productos.cellWidget(row, 3)
            precio_container = self.tabla_productos.cellWidget(row, 4)

            if cantidad_container and precio_container:
                # Buscar los SpinBox dentro de los contenedores
                cantidad_spin = cantidad_container.findChild(QSpinBox)
                precio_spin = precio_container.findChild(QDoubleSpinBox)

                if cantidad_spin and precio_spin:
                    cantidad = cantidad_spin.value()
                    precio_con_iva = precio_spin.value()  # Precio YA incluye IVA
                    total_linea = cantidad * precio_con_iva

                    total_item = self.tabla_productos.item(row, 5)
                    if total_item:
                        total_item.setText(f"{total_linea:.2f} €")

                    total_general += total_linea

        # Extraer IVA del total (el precio introducido YA incluye IVA)
        subtotal, iva, total_general = calcular_desglose_iva(total_general)

        self.subtotal_label.setText(f"{tr('Subtotal')}: {subtotal:.2f} €")
        self.iva_label.setText(f"{tr('IVA')} ({int(IVA_RATE*100)}%): {iva:.2f} €")
        self.total_label.setText(f"{tr('Total').upper()}: {total_general:.2f} €")

    def cargar_nuevo_numero_compra(self):
        """Carga el siguiente número de compra"""
        numero = self.compra_manager.obtener_siguiente_numero()
        self.numero_input.setText(numero)

    def quitar_imagen_dni(self):
        """Resetea la vista de DNI (solo lectura)"""
        self.dni_imagen_path = None
        self.dni_preview_label.setText("📋 " + tr("DNI no disponible"))
        self.dni_preview_label.setStyleSheet("""
            QLabel {
                background-color: #3B4252;
                border: 2px dashed #4C566A;
                border-radius: 5px;
                padding: 10px;
                min-height: 60px;
                color: #7B88A0;
            }
        """)

    def actualizar_preview_dni(self):
        """Actualiza la vista previa del DNI"""
        if self.dni_imagen_path and os.path.exists(self.dni_imagen_path):
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(self.dni_imagen_path)
            # Escalar para vista previa
            scaled = pixmap.scaled(150, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.dni_preview_label.setPixmap(scaled)
            self.dni_preview_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(163, 190, 140, 0.15);
                    border: 2px solid #A3BE8C;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)

    def guardar_compra(self):
        """Guarda la compra en la base de datos"""
        if not self.nombre_input.text().strip():
            notify_warning(self, tr("Error"), tr("Debe ingresar el nombre del cliente"))
            return

        # Validar que el DNI sea obligatorio en compras
        if not self.dni_imagen_path or not os.path.exists(self.dni_imagen_path):
            notify_warning(
                self,
                tr("DNI Obligatorio"),
                tr("La foto del DNI es obligatoria para realizar una compra.") + "\n\n" +
                tr("Por favor, escanee o cargue una imagen del documento de identidad del cliente.")
            )
            return

        datos_compra = {
            'numero': self.numero_input.text(),
            'fecha': self.fecha_input.date().toString('yyyy-MM-dd'),
            'cliente': {
                'nombre': self.nombre_input.text(),
                'nif': self.nif_input.text(),
                'direccion': self.direccion_input.text(),
                'telefono': self.telefono_input.text(),
                'codigo_postal': self.cp_input.text(),
                'ciudad': self.ciudad_input.text(),
                'provincia': self.provincia_input.text()
            },
            'dni_imagen': self.dni_imagen_path,  # Imagen del DNI escaneado
            'items': [],
            'totales': {}
        }

        # Recopilar items
        for row in range(self.tabla_productos.rowCount()):
            desc_container = self.tabla_productos.cellWidget(row, 0)
            ean_container = self.tabla_productos.cellWidget(row, 1)
            imei_container = self.tabla_productos.cellWidget(row, 2)
            cantidad_container = self.tabla_productos.cellWidget(row, 3)
            precio_container = self.tabla_productos.cellWidget(row, 4)
            total_item = self.tabla_productos.item(row, 5)

            if desc_container and cantidad_container and precio_container:
                # Obtener widgets internos de los contenedores
                desc_widget = desc_container.findChild(QLineEdit)
                ean_widget = ean_container.findChild(QLineEdit) if ean_container else None
                imei_widget = imei_container.findChild(QLineEdit) if imei_container else None
                cantidad_widget = cantidad_container.findChild(QSpinBox)
                precio_widget = precio_container.findChild(QDoubleSpinBox)

                if desc_widget and cantidad_widget and precio_widget:
                    descripcion = desc_widget.text()
                    if descripcion.strip():
                        # Recuperar todos los datos almacenados en el item
                        datos_articulo = total_item.data(Qt.UserRole) if total_item else {}

                        item_data = {
                            'descripcion': descripcion,
                            'ean': ean_widget.text() if ean_widget else '',
                            'imei': imei_widget.text() if imei_widget else '',
                            'marca_id': datos_articulo.get('marca_id'),
                            'modelo_id': datos_articulo.get('modelo_id'),
                            'ram': datos_articulo.get('ram'),
                            'almacenamiento': datos_articulo.get('almacenamiento'),
                            'estado': datos_articulo.get('estado'),
                            'cantidad': cantidad_widget.value(),
                            'precio_unitario': precio_widget.value()
                        }
                        datos_compra['items'].append(item_data)

        if not datos_compra['items']:
            notify_warning(self, tr("Error"), tr("Debe añadir al menos un producto"))
            return

        # Calcular totales
        # Los precios YA incluyen IVA, extraer desglose
        total = sum(item['cantidad'] * item['precio_unitario'] for item in datos_compra['items'])
        subtotal, iva, total = calcular_desglose_iva(total)

        datos_compra['totales'] = {
            'subtotal': subtotal,
            'iva': iva,
            'total': total
        }

        # Confirmación
        from app.ui.confirmacion_impresion_dialog import ConfirmacionImpresionDialog
        dialog = ConfirmacionImpresionDialog(titulo=tr("Finalizar Compra"), mensaje=f"{tr('Total')}: {total:.2f} €\n{tr('¿Cómo desea procesar la compra?')}")
        if not dialog.exec_():
            return
        
        accion = dialog.accion

        if accion == 'imprimir':
            # === MODO COMPLETO: Guardar + Imprimir ===
            from app.ui.unified_progress_dialog import UnifiedProgressDialog

            # Verificar impresora ANTES de empezar
            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_general'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora general configurada.") + "\n" +
                    tr("Ve a Ajustes > Impresoras para configurarla."))
                return

            # Variable para guardar el ID
            compra_id_result = [None]

            def do_save():
                usuario_id = self._obtener_usuario_id()
                compra_id_result[0] = self.compra_manager.guardar_compra(datos_compra, usuario_id=usuario_id)
                return compra_id_result[0]

            def do_generate_pdf(compra_id):
                from app.modules.pdf_generator import PDFGenerator
                generator = PDFGenerator(self.db)
                return generator.generar_contrato_compra(datos_compra)

            # Crear y configurar diálogo unificado
            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_FULL, tr("Procesando Compra"))
            progress.set_save_callback(do_save)
            progress.set_pdf_callback(do_generate_pdf)
            progress.set_printer_config(printer_name)

            # Ejecutar (bloquea hasta terminar)
            success = progress.execute()

            # Limpiar si se guardó en BD (aunque impresión falle)
            if progress.save_completed:
                self.limpiar_formulario()

        else:
            # === SOLO GUARDAR (sin imprimir) ===
            try:
                usuario_id = self._obtener_usuario_id()
                compra_id = self.compra_manager.guardar_compra(datos_compra, usuario_id=usuario_id)

                if not compra_id:
                    notify_error(self, tr("Error"), tr("No se pudo guardar la compra"))
                    return

                notify_success(self, tr("Compra Guardada"),
                    tr("¡Compra guardada con éxito!") + f"\n\n{tr('Total')}: {total:.2f} €\n{tr('Stock actualizado automáticamente')}")

                # Preguntar si desea registrar nueva compra
                if ask_confirm(
                    self, tr("Nueva Compra"),
                    tr("¿Desea registrar una nueva compra?")
                ):
                    self.limpiar_formulario()

            except (OSError, ValueError, RuntimeError) as e:
                notify_error(self, tr("Error"), tr("Error al guardar") + f":\n{str(e)}")

    def limpiar_formulario(self):
        """Limpia el formulario para una nueva compra"""
        self.nombre_input.clear()
        self.nif_input.clear()
        self.direccion_input.clear()
        self.telefono_input.clear()
        self.cp_input.clear()
        self.ciudad_input.clear()
        self.provincia_input.clear()
        self.cliente_id_seleccionado = None  # Limpiar cliente seleccionado
        self.cliente_combo.setCurrentIndex(0)  # Resetear combo
        self.busqueda_cliente_input.clear()

        # Limpiar imagen DNI
        self.quitar_imagen_dni()

        # Limpiar tabla
        self.tabla_productos.setRowCount(0)

        # Actualizar número
        self.cargar_nuevo_numero_compra()
        self.fecha_input.setDate(QDate.currentDate())

        self.calcular_totales()

    def generar_pdf_contrato(self, compra_id, datos_compra):
        """Genera un PDF del contrato de compra y lo envía a imprimir"""
        try:
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

            from app.modules.pdf_generator import PDFGenerator
            from app.utils.printer import imprimir_pdf
            import os

            generator = PDFGenerator(self.db)
            filename = generator.generar_contrato_compra(datos_compra)

            imprimir_pdf(filename, self.db, self)
            # El worker borra el archivo automáticamente después de imprimir

        except (OSError, ValueError, RuntimeError) as e:
            notify_warning(self, tr("Error"), tr("No se pudo imprimir el contrato") + f":\n{str(e)}")

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
