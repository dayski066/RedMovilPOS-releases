"""
Pestaña para historial de compras
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel,
                             QHeaderView, QDateEdit, QGroupBox,
                             QFileDialog, QGridLayout)
from qfluentwidgets import SearchLineEdit
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont
from app.db.database import Database
from app.i18n import tr
from app.modules.compra_manager import CompraManager
from app.ui.widgets.pagination_widget import PaginationWidget
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel, set_btn_icon
from qfluentwidgets import FluentIcon
import os
import shutil


class ComprasHistorialTab(QWidget):
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.compra_manager = CompraManager(self.db)
        self._filtros_actuales = None
        self.setup_ui()
        self.cargar_compras()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(tr("Historial de Compras"))
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

        # Fila 0: Nº Compra y Proveedor
        # Búsqueda por número
        filtros_layout.addWidget(QLabel(tr("Nº Compra") + ":"), 0, 0)
        self.numero_input = SearchLineEdit()
        self.numero_input.setPlaceholderText("COM...")
        self.numero_input.setMinimumWidth(120)
        self.numero_input.returnPressed.connect(lambda: self._buscar_por('numero', self.numero_input.text()))
        self.numero_input.searchSignal.connect(lambda: self._buscar_por('numero', self.numero_input.text()))
        filtros_layout.addWidget(self.numero_input, 0, 1)

        # Búsqueda por proveedor
        filtros_layout.addWidget(QLabel(tr("Proveedor") + ":"), 0, 2)
        self.proveedor_input = SearchLineEdit()
        self.proveedor_input.setPlaceholderText(tr("Nombre del proveedor"))
        self.proveedor_input.setMinimumWidth(150)
        self.proveedor_input.returnPressed.connect(lambda: self._buscar_por('proveedor', self.proveedor_input.text()))
        self.proveedor_input.searchSignal.connect(lambda: self._buscar_por('proveedor', self.proveedor_input.text()))
        filtros_layout.addWidget(self.proveedor_input, 0, 3)
        
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

        # Tabla de compras
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(8)
        self.tabla.setHorizontalHeaderLabels([
            tr("Nº Compra"), tr("Fecha"), tr("Cliente"), tr("Dispositivo"), "IMEI", "RAM/Alm.", tr("Total"), tr("Acciones")
        ])

        # Configurar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Nº Compra
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Fecha
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Cliente
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Dispositivo - variable
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # IMEI
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # RAM/Alm
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Total
        header.setSectionResizeMode(7, QHeaderView.Fixed)             # Acciones
        self.tabla.setColumnWidth(7, 220)  # Acciones
        
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
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
        self.total_compras_label = QLabel(tr("Total compras") + ": 0")
        self.total_importe_label = QLabel(tr("Importe total") + ": 0.00 €")
        self.total_compras_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.total_importe_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #BF616A;")
        resumen_layout.addWidget(self.total_compras_label)
        resumen_layout.addSpacing(20)
        resumen_layout.addWidget(self.total_importe_label)
        layout.addLayout(resumen_layout)

    def _on_page_changed(self, offset, limit):
        """Callback cuando cambia la página"""
        self.cargar_compras(self._filtros_actuales)

    def cargar_compras(self, filtros=None):
        """Carga compras con paginación"""
        self._filtros_actuales = filtros
        compras, total = self.compra_manager.buscar_compras_paginado(
            filtros, limit=self.pagination.limit, offset=self.pagination.offset
        )
        self.pagination.update_total(total)

        self.tabla.setRowCount(0)
        total_importe = 0

        for compra in compras:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # Nº Compra
            num_item = QTableWidgetItem(compra['numero_compra'])
            num_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, num_item)

            # Fecha
            fecha_item = QTableWidgetItem(compra['fecha'])
            fecha_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, fecha_item)

            # Proveedor
            prov_item = QTableWidgetItem(compra['proveedor_nombre'])
            prov_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, prov_item)

            # Obtener items para dispositivos
            items = self.db.fetch_all(
                """SELECT ci.*, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
                   FROM compras_items ci
                   LEFT JOIN marcas ma ON ci.marca_id = ma.id
                   LEFT JOIN modelos mo ON ci.modelo_id = mo.id
                   WHERE ci.compra_id = ?""",
                (compra['id'],)
            )

            # Columnas: Dispositivo | IMEI | RAM/Alm
            disp_text = ""
            imei_text = ""
            specs_text = ""

            if items:
                # Mostrar hasta 3 líneas
                limit = 3
                for i, item in enumerate(items[:limit]):
                    # Dispositivo (Marca + Modelo o Descripción)
                    marca = item.get('marca_nombre') or ''
                    modelo = item.get('modelo_nombre') or ''
                    
                    if marca and modelo:
                        disp_text += f"• {marca} {modelo}\n"
                    else:
                        disp_text += f"• {item['descripcion']}\n"

                    # IMEI
                    imei = item.get('imei') or '-'
                    imei_text += f"{imei}\n"

                    # RAM/Alm
                    ram = item.get('ram') or ''
                    almacenamiento = item.get('almacenamiento') or ''
                    specs = []
                    if ram: specs.append(ram)
                    if almacenamiento: specs.append(almacenamiento)
                    
                    if specs:
                        specs_text += f"{'/'.join(specs)}\n"
                    else:
                        specs_text += "-\n"
                
                if len(items) > limit:
                    disp_text += f"... (+{len(items)-limit})"

            else:
                disp_text = tr("Sin dispositivos")

            # Dispositivo
            disp_item = QTableWidgetItem(disp_text.strip())
            disp_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 3, disp_item)

            # IMEI
            imei_item = QTableWidgetItem(imei_text.strip())
            imei_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, imei_item)

            # Specs
            specs_item = QTableWidgetItem(specs_text.strip())
            specs_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 5, specs_item)

            # Total
            total_item = QTableWidgetItem(f"{float(compra['total']):.2f} €")
            total_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 6, total_item)

            total_importe += float(compra['total'])

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
            btn_ver.clicked.connect(lambda checked, c_id=compra['id']: self.ver_detalle(c_id))
            estilizar_btn_ver(btn_ver)

            btn_print = QPushButton()
            btn_print.setToolTip(tr("Imprimir"))
            btn_print.clicked.connect(lambda checked, c_id=compra['id'], c_num=compra['numero_compra']: self.imprimir_contrato(c_id, c_num))
            estilizar_btn_imprimir(btn_print)

            btn_descargar = QPushButton()
            btn_descargar.setToolTip(tr("Descargar PDF"))
            btn_descargar.clicked.connect(lambda checked, c_id=compra['id'], c_num=compra['numero_compra']: self.descargar_contrato(c_id, c_num))
            estilizar_btn_descargar(btn_descargar)

            btn_del = QPushButton()
            btn_del.setToolTip(tr("Eliminar"))
            btn_del.clicked.connect(lambda checked, c_id=compra['id']: self.eliminar_compra(c_id))
            estilizar_btn_eliminar(btn_del)

            h_layout.addWidget(btn_ver)
            h_layout.addWidget(btn_print)
            h_layout.addWidget(btn_descargar)
            h_layout.addWidget(btn_del)

            h_layout.addStretch()
            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 7, container)

        # Actualizar resumen
        self.total_compras_label.setText(f"{tr('Total compras')}: {total}")
        self.total_importe_label.setText(f"{tr('Importe total')}: {total_importe:.2f} €")

    def _buscar_por(self, campo, valor):
        """Busca compras por un solo campo, sin combinar con otros filtros"""
        filtros = {}
        if valor:
            filtros[campo] = valor
        self.pagination.reset()
        self.cargar_compras(filtros)

    def buscar(self):
        """Busca compras solo por rango de fechas (botón Buscar)"""
        filtros = {
            'fecha_desde': self.fecha_desde.date().toString('yyyy-MM-dd'),
            'fecha_hasta': self.fecha_hasta.date().toString('yyyy-MM-dd'),
        }
        self.pagination.reset()
        self.cargar_compras(filtros)

    def limpiar_filtros(self):
        """Limpia todos los filtros y recarga"""
        self.numero_input.clear()
        self.proveedor_input.clear()
        self.imei_input.clear()
        self.ean_input.clear()
        self.fecha_desde.setDate(QDate.currentDate().addMonths(-1))
        self.fecha_hasta.setDate(QDate.currentDate())
        self.pagination.reset()
        self.cargar_compras()

    def refrescar(self):
        """Refresca el historial de compras"""
        self.cargar_compras()

    def ver_detalle(self, compra_id):
        """Muestra el detalle de una compra"""
        compra = self.compra_manager.obtener_compra(compra_id)
        if not compra:
            notify_warning(self, tr("Error"), tr("No se pudo cargar la compra"))
            return

        # Crear mensaje de detalle
        mensaje = f"""
<h3>{tr('Compra')} {compra['numero_compra']}</h3>
<p><b>{tr('Fecha')}:</b> {compra['fecha']}</p>
<p><b>{tr('Cliente')}:</b> {compra['proveedor_nombre']}</p>
<p><b>{tr('NIF/CIF')}:</b> {compra['proveedor_nif'] or 'N/A'}</p>
<p><b>{tr('Dirección')}:</b> {compra['proveedor_direccion'] or 'N/A'}</p>
<p><b>{tr('Teléfono')}:</b> {compra['proveedor_telefono'] or 'N/A'}</p>

<h4>{tr('Productos')}:</h4>
<table border='1' cellpadding='5' style='border-collapse: collapse; width: 100%;'>
<tr style='background-color: #3B4252;'>
    <th>{tr('Descripción')}</th>
    <th>{tr('Marca')}</th>
    <th>{tr('Modelo')}</th>
    <th>EAN</th>
    <th>IMEI/SN</th>
    <th>RAM</th>
    <th>Alm.</th>
    <th>{tr('Estado')}</th>
    <th>{tr('Cantidad')}</th>
    <th>{tr('Precio Unit.')}</th>
    <th>{tr('Total')}</th>
</tr>
"""

        for item in compra['items']:
            marca = item.get('marca_nombre') or 'N/A'
            modelo = item.get('modelo_nombre') or 'N/A'
            ram = item.get('ram') or '-'
            almacenamiento = item.get('almacenamiento') or '-'

            # Convertir estado a texto legible
            estado_valor = item.get('estado') or ''
            estados_map = {'nuevo': tr('A Estrenar'), 'km0': 'KM0', 'usado': tr('Usado')}
            estado = estados_map.get(estado_valor, '-')

            mensaje += f"""
<tr>
    <td>{item['descripcion']}</td>
    <td>{marca}</td>
    <td>{modelo}</td>
    <td>{item.get('codigo_ean') or 'N/A'}</td>
    <td>{item.get('imei') or 'N/A'}</td>
    <td style='text-align: center;'>{ram}</td>
    <td style='text-align: center;'>{almacenamiento}</td>
    <td style='text-align: center;'>{estado}</td>
    <td style='text-align: center;'>{item['cantidad']}</td>
    <td style='text-align: right;'>{float(item['precio_unitario']):.2f} €</td>
    <td style='text-align: right;'>{float(item['total']):.2f} €</td>
</tr>
"""

        mensaje += f"""
</table>

<p style='margin-top: 15px;'>
<b>Subtotal:</b> {float(compra['subtotal']):.2f} €<br>
<b>IVA:</b> {float(compra['iva']):.2f} €<br>
<b style='font-size: 16px; color: #BF616A;'>TOTAL: {float(compra['total']):.2f} €</b>
</p>
"""

        from PyQt5.QtWidgets import QDialog, QTextEdit
        from app.ui.transparent_buttons import apply_btn_primary

        dialog = QDialog(self)
        dialog.setWindowTitle(f"{tr('Detalle Compra')} {compra['numero_compra']}")
        dialog.setMinimumSize(700, 500)
        dlg_layout = QVBoxLayout(dialog)

        text_widget = QTextEdit()
        text_widget.setReadOnly(True)
        text_widget.setHtml(mensaje)
        text_widget.setStyleSheet("""
            QTextEdit {
                background-color: #3B4252;
                border: 1px solid #434C5E;
                border-radius: 8px;
                padding: 15px;
                color: #D8DEE9;
            }
        """)
        dlg_layout.addWidget(text_widget)

        btn_cerrar = QPushButton(tr("Cerrar"))
        apply_btn_primary(btn_cerrar)
        btn_cerrar.clicked.connect(dialog.accept)
        dlg_layout.addWidget(btn_cerrar)

        dialog.exec_()

    def _generar_pdf_temporal(self, compra_id):
        """Genera el PDF del contrato desde la BD"""
        compra = self.compra_manager.obtener_compra(compra_id)
        if not compra:
            return None

        from app.modules.pdf_generator import PDFGenerator
        generator = PDFGenerator(self.db)
        return generator.generar_contrato_compra(compra)

    def imprimir_contrato(self, compra_id, numero_compra):
        """Imprime el contrato generándolo desde la BD"""
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

            pdf_path = self._generar_pdf_temporal(compra_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF del contrato"))
                return

            # Usar diálogo unificado en modo SOLO IMPRIMIR
            progress = UnifiedProgressDialog(self, UnifiedProgressDialog.MODE_PRINT_ONLY, tr("Imprimiendo Contrato"))
            progress.set_pdf_path(pdf_path)
            progress.set_printer_config(printer_name)
            progress.execute()

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al imprimir contrato") + f":\n{str(e)}")

    def descargar_contrato(self, compra_id, numero_compra):
        """Descarga el PDF del contrato generándolo desde la BD"""
        try:
            # Primero preguntar dónde guardar
            nombre_sugerido = f"Contrato_{numero_compra}.pdf"
            destino, _ = QFileDialog.getSaveFileName(
                self,
                tr("Guardar Contrato"),
                nombre_sugerido,
                tr("Archivos PDF") + " (*.pdf)"
            )

            if not destino:
                return  # Usuario canceló

            # Generar PDF temporal
            pdf_path = self._generar_pdf_temporal(compra_id)

            if not pdf_path:
                notify_warning(self, tr("Error"), tr("No se pudo generar el PDF del contrato"))
                return

            # Copiar al destino elegido
            shutil.copy2(pdf_path, destino)

            # Eliminar temporal
            try:
                os.remove(pdf_path)
            except (OSError, ValueError, RuntimeError):
                pass

            notify_success(self, tr("Descargado"), tr("Contrato guardado en") + f":\n{destino}")

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al descargar contrato") + f":\n{str(e)}")

    def eliminar_compra(self, compra_id):
        """Elimina una compra con verificación de permisos y contraseña"""
        compra = self.compra_manager.obtener_compra(compra_id)
        if not compra:
            return

        # Verificar permisos y pedir contraseña
        if self.auth_manager:
            from app.ui.confirmar_accion_dialog import confirmar_accion_sensible

            if not confirmar_accion_sensible(
                self.auth_manager,
                'compras.eliminar',
                tr('Eliminar Compra'),
                tr("¿Eliminar la compra?") + f" {compra['numero_compra']}\n\n" +
                tr("Proveedor") + f": {compra.get('proveedor_nombre', 'N/A')}\n" +
                tr("Total") + f": {compra.get('total', 0):.2f} €",
                self
            ):
                return

        # Preguntar si revertir stock
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QRadioButton, QDialogButtonBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Opciones de Eliminación"))
        dialog.setMinimumWidth(350)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel(f"<b>{tr('Compra')}:</b> {compra['numero_compra']}"))
        layout.addWidget(QLabel(tr("¿Qué desea hacer con el stock?")))

        rb_revertir = QRadioButton(tr("Eliminar y revertir stock (deshacer compra)"))
        rb_revertir.setChecked(True)
        rb_revertir.setStyleSheet("color: #BF616A; font-weight: bold;")
        layout.addWidget(rb_revertir)

        rb_solo_borrar = QRadioButton(tr("Solo eliminar registro (mantener stock)"))
        rb_solo_borrar.setStyleSheet("color: #A3BE8C;")
        layout.addWidget(rb_solo_borrar)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec_() != QDialog.Accepted:
            return

        revertir_stock = rb_revertir.isChecked()
        
        # Obtener usuario_id para auditoría
        usuario_id = None
        if self.auth_manager:
            usuario = self.auth_manager.obtener_usuario_actual()
            if usuario:
                usuario_id = usuario.get('id')
        
        exito, mensaje = self.compra_manager.eliminar_compra(compra_id, revertir_stock=revertir_stock, usuario_id=usuario_id)

        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            self.cargar_compras()
        else:
            notify_warning(self, tr("Error"), mensaje)

    def showEvent(self, event):
        """Se ejecuta automáticamente cuando se muestra la pestaña"""
        super().showEvent(event)
        # Actualizar historial automáticamente al entrar
        self.cargar_compras()

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
