"""
Pestaña para nueva reparación (SAT)
"""
from app.ui.styles import estilizar_btn_eliminar, THEMES
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTableWidget, QTableWidgetItem, QGroupBox,
                             QDateEdit, QHeaderView, QComboBox, QApplication,
                             QListWidget, QListWidgetItem)
from config import IVA_RATE, calcular_desglose_iva
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.db.database import Database
from app.i18n import tr
from app.modules.reparacion_manager import ReparacionManager
from app.ui.reparacion_item_dialog import ReparacionItemDialog
from app.utils.logger import logger
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel, apply_btn_success, set_btn_icon
from qfluentwidgets import FluentIcon
from qfluentwidgets import SearchLineEdit


class ReparacionesNuevaTab(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.db.connect()
        self.reparacion_manager = ReparacionManager(self.db)
        self.items = []  # Lista temporal de dispositivos
        self.setup_ui()
        self.load_clientes()
        self.cargar_numero()

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

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        lbl_num = QLabel(tr("Nº Orden") + ":")
        lbl_num.setStyleSheet("font-weight: bold;")
        self.numero_input = QLineEdit()
        self.numero_input.setReadOnly(True)
        self.numero_input.setMaximumWidth(150)
        self.numero_input.setStyleSheet("color: #ffffff; font-weight: bold;")

        lbl_fecha = QLabel(tr("Fecha Entrada") + ":")
        self.fecha_input = QDateEdit()
        self.fecha_input.setDate(QDate.currentDate())
        self.fecha_input.setCalendarPopup(True)

        header_layout.addWidget(lbl_num)
        header_layout.addWidget(self.numero_input)
        header_layout.addSpacing(20)
        header_layout.addWidget(lbl_fecha)
        header_layout.addWidget(self.fecha_input)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # Cliente con Detección Automática
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

        # Campos del cliente - Layout compacto
        campos_layout = QHBoxLayout()
        campos_layout.setSpacing(10)

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

        campos_layout.addLayout(left_col, 1)
        campos_layout.addLayout(right_col, 1)
        cliente_layout.addLayout(campos_layout)
        
        cliente_group.setLayout(cliente_layout)
        layout.addWidget(cliente_group)

        # Tabla Dispositivos
        lbl_disp = QLabel(tr("Dispositivos a Reparar"))
        lbl_disp.setStyleSheet("font-weight: bold; font-size: 12px; padding: 2px 0;")
        layout.addWidget(lbl_disp)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            tr("Dispositivo"), "IMEI", tr("Avería"), tr("Solución"), tr("Precio"), tr("Cód. Pantalla"), tr("Acciones")
        ])
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.tabla.setColumnWidth(6, 80) # Botón eliminar
        
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        # La tabla se expande para llenar el espacio disponible
        layout.addWidget(self.tabla, 1)  # stretch=1 para expandir

        # Botones Tabla + Totales en línea
        btn_items_layout = QHBoxLayout()
        btn_add = QPushButton("+ " + tr("Añadir Dispositivo"))
        btn_add.setStyleSheet("background-color: transparent; color: #A3BE8C; border: 2px solid #A3BE8C; border-radius: 6px; padding: 4px 10px;")
        btn_add.clicked.connect(self.agregar_dispositivo)
        btn_items_layout.addWidget(btn_add)
        btn_items_layout.addStretch()

        # Totales compactos en línea
        self.lbl_subtotal = QLabel(tr("Subtotal") + ": 0.00 €")
        self.lbl_subtotal.setStyleSheet("font-size: 11px; color: #7B88A0; padding: 0 8px;")
        btn_items_layout.addWidget(self.lbl_subtotal)

        self.lbl_iva = QLabel(f"{tr('IVA')} ({int(IVA_RATE*100)}%): 0.00 €")
        self.lbl_iva.setStyleSheet("font-size: 11px; color: #7B88A0; padding: 0 8px;")
        btn_items_layout.addWidget(self.lbl_iva)

        self.lbl_total = QLabel(tr("Total") + ": 0.00 €")
        self.lbl_total.setStyleSheet("font-weight: bold; font-size: 14px; color: #BF616A; padding: 0 8px;")
        btn_items_layout.addWidget(self.lbl_total)

        layout.addLayout(btn_items_layout)

        # Footer Botones (compactos)
        footer = QHBoxLayout()
        btn_limpiar = QPushButton(tr("Limpiar"))
        apply_btn_cancel(btn_limpiar)
        btn_limpiar.clicked.connect(self.limpiar)

        btn_guardar = QPushButton(tr("Guardar Orden"))
        apply_btn_primary(btn_guardar)
        btn_guardar.clicked.connect(self.guardar)

        footer.addStretch()
        footer.addWidget(btn_limpiar)
        footer.addWidget(btn_guardar)
        layout.addLayout(footer)

    def load_clientes(self):
        self.cliente_combo.clear()
        self.cliente_combo.addItem("-- " + tr("Seleccionar Cliente") + " --", None)
        clientes = self.db.fetch_all("SELECT id, nombre FROM clientes ORDER BY nombre")
        for c in clientes:
            self.cliente_combo.addItem(c['nombre'], c['id'])

    def on_cliente_selected(self):
        c_id = self.cliente_combo.currentData()
        if c_id:
            cliente = self.db.fetch_one("SELECT * FROM clientes WHERE id=?", (c_id,))
            if cliente:
                self.nombre_input.setText(cliente['nombre'])
                self.nif_input.setText(cliente['nif'] or "")
                self.direccion_input.setText(cliente['direccion'] or "")
                self.telefono_input.setText(cliente['telefono'] or "")
                self.cp_input.setText(cliente.get('codigo_postal') or "")
                self.ciudad_input.setText(cliente.get('ciudad') or "")
                self.provincia_input.setText(cliente.get('provincia') or "")

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
            item = QListWidgetItem(f"{c.get('nombre','')}   |   {c.get('nif','-') or '-'}   |   {c.get('telefono','-') or '-'}")
            item.setData(Qt.UserRole, dict(c))
            self.lista_sugerencias.addItem(item)
        self.lista_sugerencias.setVisible(True)

    def _seleccionar_cliente_lista(self, item):
        cliente = item.data(Qt.UserRole)
        self._rellenar_campos_cliente(cliente)
        self.lista_sugerencias.setVisible(False)
        self.busqueda_cliente_input.clear()

    def _rellenar_campos_cliente(self, cliente):
        self.nombre_input.setText(cliente.get('nombre') or '')
        self.nif_input.setText(cliente.get('nif') or '')
        self.direccion_input.setText(cliente.get('direccion') or '')
        self.telefono_input.setText(cliente.get('telefono') or '')
        self.cp_input.setText(cliente.get('codigo_postal') or '')
        self.ciudad_input.setText(cliente.get('ciudad') or '')
        self.provincia_input.setText(cliente.get('provincia') or '')
        index = self.cliente_combo.findData(cliente['id'])
        if index >= 0:
            self.cliente_combo.setCurrentIndex(index)

    def buscar_cliente_auto(self):
        """Busca cliente al pulsar Enter o Buscar"""
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
            notify_success(self, "✓ " + tr("Cliente Encontrado"), tr("Cliente") + f": {cliente['nombre']}")
        else:
            if ask_confirm(self, tr("Cliente No Encontrado"),
                           tr("No se encontró ningún cliente con") + f": {busqueda}\n" + tr("¿Desea crear un nuevo cliente?")):
                self.abrir_nuevo_cliente()
                self.busqueda_cliente_input.clear()

    def abrir_nuevo_cliente(self):
        from app.ui.cliente_dialog import ClienteDialog
        dialog = ClienteDialog(self.db, parent=self)
        if dialog.exec_():
            self.load_clientes()

    def cargar_numero(self):
        num = self.reparacion_manager.obtener_siguiente_numero()
        self.numero_input.setText(num)

    def agregar_dispositivo(self):
        dialog = ReparacionItemDialog(self.db, parent=self)
        if dialog.exec_():
            item = dialog.obtener_resultado()
            if item:
                self.items.append(item)
                self.refrescar_tabla()

    def refrescar_tabla(self):
        self.tabla.setRowCount(0)
        total_con_iva = 0
        for i, item in enumerate(self.items):
            self.tabla.insertRow(i)
            # Columna 0: Dispositivo
            d_item = QTableWidgetItem(f"{item['marca_nombre']} {item['modelo_nombre']}")
            d_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(i, 0, d_item)
            
            # Columna 1: IMEI
            i_item = QTableWidgetItem(item['imei'])
            i_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(i, 1, i_item)

            # Columnas 2 y 3: Averías y Soluciones
            averias = item.get('averias', [])
            if averias:
                averias_texto = '\n'.join([f"• {a['averia_texto']}" for a in averias])
                soluciones_texto = '\n'.join([f"• {a['solucion_texto']}" for a in averias])
                a_item = QTableWidgetItem(averias_texto)
                s_item = QTableWidgetItem(soluciones_texto)
            else:
                a_item = QTableWidgetItem(item.get('averia_texto') or '-')
                s_item = QTableWidgetItem(item.get('solucion_texto') or '-')
            
            a_item.setTextAlignment(Qt.AlignCenter)
            s_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(i, 2, a_item)
            self.tabla.setItem(i, 3, s_item)

            # Columna 4: Precio
            precio = item['precio_estimado']
            total_con_iva += precio
            p_item = QTableWidgetItem(f"{precio:.2f} €")
            p_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(i, 4, p_item)
            
            # Columna 5: Cód. Pantalla
            c_item = QTableWidgetItem(item['patron_codigo'])
            c_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(i, 5, c_item)

            # Columna 6: Botón eliminar - Centrado estructural
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            btn_del = QPushButton()
            btn_del.setToolTip(tr("Eliminar"))
            btn_del.clicked.connect(lambda checked, idx=i: self.eliminar_item(idx))
            estilizar_btn_eliminar(btn_del)
            
            v_layout.addWidget(btn_del)
            self.tabla.setCellWidget(i, 6, container)

            # Ajustar altura de la fila
            row_h = 60
            if averias and len(averias) > 2:
                row_h = 30 * len(averias)
            self.tabla.setRowHeight(i, row_h)

        # Extraer desglose de IVA (precios ya incluyen IVA)
        subtotal, iva, total = calcular_desglose_iva(total_con_iva)

        self.lbl_subtotal.setText(f"{tr('Subtotal')}: {subtotal:.2f} €")
        self.lbl_iva.setText(f"{tr('IVA')} ({int(IVA_RATE*100)}%): {iva:.2f} €")
        self.lbl_total.setText(f"{tr('Total Estimado')}: {total:.2f} €")

    def eliminar_item(self, index):
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.refrescar_tabla()

    def limpiar(self):
        self.items = []
        self.refrescar_tabla()
        self.nombre_input.clear()
        self.telefono_input.clear()
        self.nif_input.clear()
        self.direccion_input.clear()
        self.cp_input.clear()
        self.ciudad_input.clear()
        self.provincia_input.clear()
        self.cliente_combo.setCurrentIndex(0)
        self.cargar_numero()
        self.busqueda_cliente_input.clear()

    def guardar(self):
        try:
            if not self.nombre_input.text():
                notify_warning(self, tr("Error"), tr("Debe ingresar el nombre del cliente"))
                return
            if not self.items:
                notify_warning(self, tr("Error"), tr("Añade al menos un dispositivo"))
                return

            datos = {
                'numero': self.numero_input.text(),
                'fecha': self.fecha_input.date().toString("yyyy-MM-dd"),
                'cliente': {
                    'id': self.cliente_combo.currentData(),
                    'nombre': self.nombre_input.text(),
                    'telefono': self.telefono_input.text(),
                    'nif': self.nif_input.text(),
                    'direccion': self.direccion_input.text(),
                    'codigo_postal': self.cp_input.text(),
                    'ciudad': self.ciudad_input.text(),
                    'provincia': self.provincia_input.text()
                },
                'items': self.items
            }

            # Confirmación
            from app.ui.confirmacion_impresion_dialog import ConfirmacionImpresionDialog
            dialog = ConfirmacionImpresionDialog(titulo=tr("Guardar Reparación"), mensaje=f"{tr('Nº Orden')}: {datos['numero']}")
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
                reparacion_id_result = [None]

                def do_save():
                    usuario_id = self._obtener_usuario_id()
                    reparacion_id_result[0] = self.reparacion_manager.guardar_reparacion(datos, usuario_id=usuario_id)
                    return reparacion_id_result[0]

                def do_generate_pdf(reparacion_id):
                    from app.modules.pdf_generator import PDFGenerator
                    reparacion = self.reparacion_manager.obtener_reparacion(reparacion_id)
                    generator = PDFGenerator(self.db)
                    return generator.generar_orden_reparacion(reparacion)

                # Crear y configurar diálogo unificado
                progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_FULL, tr("Procesando Orden"))
                progress.set_save_callback(do_save)
                progress.set_pdf_callback(do_generate_pdf)
                progress.set_printer_config(printer_name)

                # Ejecutar (bloquea hasta terminar)
                success = progress.execute()

                # Limpiar si se guardó en BD (aunque impresión falle)
                if progress.save_completed:
                    self.limpiar()

            else:
                # === SOLO GUARDAR (sin imprimir) ===
                try:
                    usuario_id = self._obtener_usuario_id()
                    reparacion_id = self.reparacion_manager.guardar_reparacion(datos, usuario_id=usuario_id)

                    if not reparacion_id:
                        notify_error(self, tr("Error"), tr("No se pudo guardar la orden"))
                        return

                    notify_success(self, tr("Orden Guardada"),
                        tr("¡Orden guardada con éxito!"))

                    self.limpiar()

                except (OSError, ValueError, RuntimeError) as e:
                    notify_error(self, tr("Error"), tr("Error al guardar") + f":\n{str(e)}")

        except (OSError, ValueError, RuntimeError) as e:
            import traceback
            error_completo = traceback.format_exc()
            notify_error(self, tr("Error"), tr("Error al guardar") + f":\n\n{str(e)}")
            logger.error(f"Error guardando reparación:\n{error_completo}")

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
