"""
Pestaña para historial de facturas
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel,
                             QHeaderView, QDateEdit, QGroupBox,
                             QFileDialog, QGridLayout)
from qfluentwidgets import SearchLineEdit
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel, set_btn_icon
from qfluentwidgets import FluentIcon
from PyQt5.QtCore import Qt, QDate
from app.db.database import Database
from app.i18n import tr
from app.modules.factura_manager import FacturaManager
from app.ui.widgets.pagination_widget import PaginationWidget
import os
import shutil
import tempfile
from datetime import datetime


class HistorialTab(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.factura_manager = FacturaManager(self.db)
        self._filtros_actuales = None
        self.setup_ui()
        self.cargar_facturas()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(tr("Historial de Facturas"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Filtros
        filtros_title = QLabel(tr("FILTROS DE BÚSQUEDA"))
        filtros_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; padding: 5px 0; background: transparent;")
        layout.addWidget(filtros_title)

        filtros_group = QGroupBox()
        filtros_layout = QGridLayout()
        filtros_layout.setSpacing(10)

        # Fila 0: Nº Factura y Cliente
        # Búsqueda por número
        filtros_layout.addWidget(QLabel(tr("Nº Factura") + ":"), 0, 0)
        self.numero_input = SearchLineEdit()
        self.numero_input.setPlaceholderText("UB...")
        self.numero_input.setMinimumWidth(120)
        self.numero_input.returnPressed.connect(lambda: self._buscar_por('numero', self.numero_input.text()))
        self.numero_input.searchSignal.connect(lambda: self._buscar_por('numero', self.numero_input.text()))
        filtros_layout.addWidget(self.numero_input, 0, 1)

        # Búsqueda por cliente
        filtros_layout.addWidget(QLabel(tr("Cliente") + ":"), 0, 2)
        self.cliente_input = SearchLineEdit()
        self.cliente_input.setPlaceholderText(tr("Nombre del cliente"))
        self.cliente_input.setMinimumWidth(150)
        self.cliente_input.returnPressed.connect(lambda: self._buscar_por('cliente', self.cliente_input.text()))
        self.cliente_input.searchSignal.connect(lambda: self._buscar_por('cliente', self.cliente_input.text()))
        filtros_layout.addWidget(self.cliente_input, 0, 3)
        
        # Búsqueda por IMEI (Movido a fila 0)
        filtros_layout.addWidget(QLabel("IMEI:"), 0, 4)
        self.imei_input = SearchLineEdit()
        self.imei_input.setPlaceholderText("IMEI...")
        self.imei_input.setMinimumWidth(150)
        self.imei_input.returnPressed.connect(lambda: self._buscar_por('imei', self.imei_input.text()))
        self.imei_input.searchSignal.connect(lambda: self._buscar_por('imei', self.imei_input.text()))
        filtros_layout.addWidget(self.imei_input, 0, 5)

        # Búsqueda por EAN (Movido a fila 0)
        filtros_layout.addWidget(QLabel("EAN:"), 0, 6)
        self.ean_input = SearchLineEdit()
        self.ean_input.setPlaceholderText("EAN...")
        self.ean_input.setMinimumWidth(150)
        self.ean_input.returnPressed.connect(lambda: self._buscar_por('ean', self.ean_input.text()))
        self.ean_input.searchSignal.connect(lambda: self._buscar_por('ean', self.ean_input.text()))
        filtros_layout.addWidget(self.ean_input, 0, 7)

        # Fila 1: Fechas, IMEI, EAN
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

        # Tabla de facturas
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(7)
        self.tabla.setHorizontalHeaderLabels([
            tr("Nº Factura"), tr("Fecha"), tr("Cliente"), tr("Dispositivos"), "IMEI/SN", tr("Total"), tr("Acciones")
        ])

        # Configurar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Nº Factura
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Fecha
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Cliente
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Dispositivos
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # IMEI/SN
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Total
        header.setSectionResizeMode(6, QHeaderView.Fixed)             # Acciones
        self.tabla.setColumnWidth(6, 270)  # Acciones (5 botones)
        
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)

        layout.addWidget(self.tabla)

        # Paginación
        self.pagination = PaginationWidget()
        self.pagination.page_changed.connect(self._on_page_changed)
        layout.addWidget(self.pagination)

        # Resumen
        resumen_layout = QHBoxLayout()
        resumen_layout.addStretch()
        self.total_facturas_label = QLabel(tr("Total facturas") + ": 0")
        self.total_importe_label = QLabel(tr("Importe total") + ": 0.00 €")
        self.total_facturas_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.total_importe_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #A3BE8C;")
        resumen_layout.addWidget(self.total_facturas_label)
        resumen_layout.addSpacing(20)
        resumen_layout.addWidget(self.total_importe_label)
        layout.addLayout(resumen_layout)

    def _on_page_changed(self, offset, limit):
        """Callback cuando cambia la página"""
        self.cargar_facturas(self._filtros_actuales)

    def cargar_facturas(self, filtros=None):
        """Carga facturas con paginación"""
        self._filtros_actuales = filtros
        facturas, total = self.factura_manager.buscar_facturas_paginado(
            filtros, limit=self.pagination.limit, offset=self.pagination.offset
        )
        self.pagination.update_total(total)

        self.tabla.setRowCount(0)
        total_importe = 0

        for factura in facturas:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)

            num_item = QTableWidgetItem(factura['numero_factura'])
            num_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, num_item)

            # Convertir fecha (SQLite devuelve string)
            fecha_str = factura['fecha']
            if isinstance(fecha_str, str):
                try:
                    fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
                    fecha_display = fecha_dt.strftime('%d/%m/%Y')
                except (OSError, ValueError, RuntimeError):
                    fecha_display = fecha_str
            else:
                fecha_display = fecha_str.strftime('%d/%m/%Y')

            fecha_item = QTableWidgetItem(fecha_display)
            fecha_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, fecha_item)

            cliente_item = QTableWidgetItem(factura['cliente_nombre'] or tr('Sin nombre'))
            cliente_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, cliente_item)

            # Obtener items de la factura para mostrar dispositivos
            items = self.db.fetch_all(
                "SELECT descripcion, imei_sn FROM factura_items WHERE factura_id = ?",
                (factura['id'],)
            )

            # Concatenar descripciones e IMEIs con saltos de línea
            if items:
                dispositivos = "\n".join([item['descripcion'] for item in items])
                imeis = "\n".join([item['imei_sn'] or '-' for item in items])
                # Calcular altura de fila: 25px por cada item, mínimo 60px
                altura_fila = max(60, len(items) * 25 + 20)
            else:
                dispositivos = tr("Sin items")
                imeis = "-"
                altura_fila = 60
            
            # Establecer altura de fila dinámica
            self.tabla.setRowHeight(row, altura_fila)

            dispositivos_item = QTableWidgetItem(dispositivos)
            dispositivos_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, dispositivos_item)

            imeis_item = QTableWidgetItem(imeis)
            imeis_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, imeis_item)

            total_item = QTableWidgetItem(f"{float(factura['total']):.2f} €")
            total_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 5, total_item)

            total_importe += float(factura['total'])

            # Botones de acción - Centrado estructural
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(10)
            # Asegurar centrado absoluto con espaciadores dinámicos
            h_layout.addStretch()

            from app.ui.styles import estilizar_btn_ver, estilizar_btn_imprimir, estilizar_btn_eliminar, estilizar_btn_descargar, estilizar_btn_garantia

            btn_ver = QPushButton()
            btn_ver.setToolTip(tr("Ver"))
            btn_ver.clicked.connect(lambda checked, f_id=factura['id']: self.ver_detalle(f_id))
            estilizar_btn_ver(btn_ver)
            h_layout.addWidget(btn_ver)

            btn_imprimir = QPushButton()
            btn_imprimir.setToolTip(tr("Imprimir factura"))
            btn_imprimir.clicked.connect(lambda checked, f_id=factura['id'], f_num=factura['numero_factura']: self.imprimir_factura(f_id, f_num))
            estilizar_btn_imprimir(btn_imprimir)
            h_layout.addWidget(btn_imprimir)

            # Botón garantía: solo activo si la venta tiene algún artículo de categoría Móviles
            tiene_movil = self.db.fetch_one(
                """SELECT 1 FROM factura_items fi
                   JOIN productos p ON fi.producto_id = p.id
                   JOIN categorias c ON p.categoria_id = c.id
                   WHERE fi.factura_id = ? AND LOWER(c.nombre) LIKE '%m_vil%'
                   LIMIT 1""",
                (factura['id'],)
            ) is not None

            btn_garantia = QPushButton()
            btn_garantia.setEnabled(tiene_movil)
            btn_garantia.setToolTip(
                tr("Imprimir garantía") if tiene_movil
                else tr("Solo disponible para ventas de móviles")
            )
            btn_garantia.clicked.connect(lambda checked, f_id=factura['id']: self.imprimir_garantia(f_id))
            estilizar_btn_garantia(btn_garantia)
            h_layout.addWidget(btn_garantia)

            btn_descargar = QPushButton()
            btn_descargar.setToolTip(tr("Descargar Tícket A4"))
            btn_descargar.clicked.connect(lambda checked, f_id=factura['id'], f_num=factura['numero_factura']: self.descargar_factura(f_id, f_num))
            estilizar_btn_descargar(btn_descargar)
            h_layout.addWidget(btn_descargar)

            btn_eliminar = QPushButton()
            btn_eliminar.setToolTip(tr("Eliminar"))
            btn_eliminar.clicked.connect(lambda checked, f_id=factura['id']: self.eliminar_factura(f_id))
            estilizar_btn_eliminar(btn_eliminar)
            h_layout.addWidget(btn_eliminar)
            
            h_layout.addStretch() # Segundo espaciador para centrar el bloque

            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 6, container)


        # Actualizar resumen
        self.total_facturas_label.setText(f"{tr('Total facturas')}: {total}")
        self.total_importe_label.setText(f"{tr('Importe total')}: {total_importe:.2f} €")

    def _buscar_por(self, campo, valor):
        """Busca facturas por un solo campo, sin combinar con otros filtros"""
        filtros = {}
        if valor:
            filtros[campo] = valor
        self.pagination.reset()
        self.cargar_facturas(filtros)

    def buscar(self):
        """Busca facturas solo por rango de fechas (botón Buscar)"""
        filtros = {
            'fecha_desde': self.fecha_desde.date().toPyDate(),
            'fecha_hasta': self.fecha_hasta.date().toPyDate(),
        }
        self.pagination.reset()
        self.cargar_facturas(filtros)

    def limpiar_filtros(self):
        """Limpia todos los filtros y recarga"""
        self.numero_input.clear()
        self.cliente_input.clear()
        self.imei_input.clear()
        self.ean_input.clear()
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_hasta.setDate(QDate.currentDate())
        self.pagination.reset()
        self.cargar_facturas()

    def _generar_pdf_temporal(self, factura_id):
        """Genera el PDF de la factura desde la BD en archivo temporal"""
        # Siempre genera desde la BD - no depende de archivos locales
        return self.factura_manager.generar_pdf_desde_bd(factura_id)

    def imprimir_factura(self, factura_id, numero_factura):
        """Imprime la factura generándola desde la BD"""
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

            # Generar PDF
            pdf_path = self._generar_pdf_temporal(factura_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF de la factura"))
                return

            # Usar diálogo unificado en modo SOLO IMPRIMIR
            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_PRINT_ONLY, tr("Imprimiendo Factura"))
            progress.set_pdf_path(pdf_path)
            progress.set_printer_config(printer_name)
            progress.execute()

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al imprimir factura") + f":\n{str(e)}")

    def imprimir_garantia(self, factura_id):
        """Imprime el documento de garantía generándolo desde la BD"""
        try:
            from app.ui.unified_progress_dialog import UnifiedProgressDialog

            result = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'printer_general'"
            )
            printer_name = result['valor'] if result and result['valor'] and '---' not in result['valor'] else None

            if not printer_name:
                notify_warning(self, tr("Sin Impresora"),
                    tr("No hay impresora general configurada.") + "\n" +
                    tr("Ve a Ajustes > Impresoras para configurarla."))
                return

            pdf_path = self.factura_manager.generar_garantia_desde_bd(factura_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF de la garantía"))
                return

            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_PRINT_ONLY, tr("Imprimiendo Garantía"))
            progress.set_pdf_path(pdf_path)
            progress.set_printer_config(printer_name)
            progress.execute()

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al imprimir garantía") + f":\n{str(e)}")

    def descargar_factura(self, factura_id, numero_factura):
        """Descarga el PDF de la factura generándolo desde la BD"""
        try:
            # Primero preguntar dónde guardar
            nombre_sugerido = f"Factura_{numero_factura}.pdf"
            destino, _ = QFileDialog.getSaveFileName(
                self,
                tr("Guardar Factura"),
                nombre_sugerido,
                tr("Archivos PDF") + " (*.pdf)"
            )

            if not destino:
                return  # Usuario canceló

            # Generar PDF temporal
            pdf_path = self._generar_pdf_temporal(factura_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF de la factura"))
                return

            # Copiar al destino elegido
            shutil.copy2(pdf_path, destino)

            # Eliminar temporal
            try:
                os.remove(pdf_path)
            except (OSError, ValueError, RuntimeError):
                pass

            notify_success(self, tr("Descargado"), tr("Factura guardada en") + f":\n{destino}")

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al descargar factura") + f":\n{str(e)}")

    def ver_detalle(self, factura_id):
        """Muestra el detalle de una factura"""
        from app.ui.factura_detalle_dialog import FacturaDetalleDialog
        dialog = FacturaDetalleDialog(self.db, factura_id, parent=self)
        dialog.exec_()

    def eliminar_factura(self, factura_id):
        """Elimina una factura con verificación de permisos y contraseña"""
        factura = self.factura_manager.obtener_factura(factura_id)
        if not factura:
            return

        # Verificar permisos y pedir contraseña
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

            if not confirmar_accion_sensible(
                self.auth_manager,
                'ventas.eliminar',
                tr('Eliminar') + ' ' + tr('Venta'),
                tr("¿Eliminar la factura?") + f" {factura.get('numero_factura')}\n\n" +
                f"{tr('Cliente')}: {factura.get('cliente_nombre', 'N/A')}\n" +
                f"{tr('Total')}: {factura.get('total', 0):.2f} €",
                self
            ):
                return

        # Preguntar si restaurar stock
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QDialogButtonBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Opciones de Eliminación"))
        dialog.setMinimumWidth(350)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"<b>{tr('Factura')}:</b> {factura.get('numero_factura')}"))
        layout.addWidget(QLabel(tr("¿Qué desea hacer con el stock?")))

        rb_restaurar = QRadioButton(tr("Eliminar y restaurar stock (cancelar venta)"))
        rb_restaurar.setChecked(True)
        rb_restaurar.setStyleSheet("color: #A3BE8C; font-weight: bold;")
        layout.addWidget(rb_restaurar)

        rb_solo_borrar = QRadioButton(tr("Solo eliminar registro (sin tocar stock)"))
        rb_solo_borrar.setStyleSheet("color: #BF616A;")
        layout.addWidget(rb_solo_borrar)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        restaurar_stock = rb_restaurar.isChecked()
        
        # Obtener usuario_id para auditoría
        usuario_id = None
        if self.auth_manager:
            usuario = self.auth_manager.obtener_usuario_actual()
            if usuario:
                usuario_id = usuario.get('id')
        
        ok, msg = self.factura_manager.eliminar_factura(factura_id, restaurar_stock=restaurar_stock, usuario_id=usuario_id)

        if ok:
            notify_success(self, tr("Éxito"), msg)
            self.cargar_facturas()
        else:
            notify_error(self, tr("Error"), msg)

    def showEvent(self, event):
        """Se ejecuta automáticamente cuando se muestra la pestaña"""
        super().showEvent(event)
        # Actualizar historial automáticamente al entrar
        self.cargar_facturas()

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
