"""
Diálogo para añadir dispositivos a una orden de reparación con múltiples averías
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QDoubleSpinBox,
                             QComboBox, QGroupBox, QPlainTextEdit, QInputDialog,
                             QTableWidget, QTableWidgetItem, QHeaderView, QWidget)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_warning, ask_confirm
from app.modules.marca_modelo_manager import MarcaModeloManager
from app.modules.averia_manager import AveriaManager
from app.modules.solucion_manager import SolucionManager
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel, apply_btn_success, apply_btn_danger
from app.ui.styles import estilizar_btn_eliminar
from app.ui.averia_dialog import AveriaDialog
from app.ui.solucion_dialog import SolucionDialog
from app.i18n import tr


class AveriaItemDialog(QDialog):
    """Diálogo para añadir una avería individual"""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.averia_manager = AveriaManager(db)
        self.solucion_manager = SolucionManager(db)

        self.setWindowTitle("Añadir Avería")
        self.setModal(True)
        self.setMinimumWidth(450)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Avería con botones + y -
        averia_layout = QHBoxLayout()
        self.averia_combo = QComboBox()
        self.cargar_averias()
        self.averia_combo.currentIndexChanged.connect(self.on_averia_changed)
        averia_layout.addWidget(self.averia_combo)

        btn_add_averia = QPushButton("+")
        btn_add_averia.setMaximumWidth(35)
        btn_add_averia.setToolTip("Añadir nueva avería")
        btn_add_averia.clicked.connect(self.agregar_averia)
        apply_btn_success(btn_add_averia)
        averia_layout.addWidget(btn_add_averia)

        btn_del_averia = QPushButton("-")
        btn_del_averia.setMaximumWidth(35)
        btn_del_averia.setToolTip("Eliminar avería seleccionada")
        btn_del_averia.clicked.connect(self.eliminar_averia_combo)
        apply_btn_danger(btn_del_averia)
        averia_layout.addWidget(btn_del_averia)

        form_layout.addRow("Avería:", averia_layout)

        # Solución con botones + y -
        solucion_layout = QHBoxLayout()
        self.solucion_combo = QComboBox()
        self.solucion_combo.setEnabled(False)
        solucion_layout.addWidget(self.solucion_combo)

        btn_add_solucion = QPushButton("+")
        btn_add_solucion.setMaximumWidth(35)
        btn_add_solucion.setToolTip("Añadir nueva solución")
        btn_add_solucion.clicked.connect(self.agregar_solucion)
        btn_add_solucion.setEnabled(False)
        apply_btn_success(btn_add_solucion)
        self.btn_add_solucion = btn_add_solucion
        solucion_layout.addWidget(btn_add_solucion)

        btn_del_solucion = QPushButton("-")
        btn_del_solucion.setMaximumWidth(35)
        btn_del_solucion.setToolTip("Eliminar solución seleccionada")
        btn_del_solucion.clicked.connect(self.eliminar_solucion)
        btn_del_solucion.setEnabled(False)
        apply_btn_danger(btn_del_solucion)
        self.btn_del_solucion = btn_del_solucion
        solucion_layout.addWidget(btn_del_solucion)

        form_layout.addRow("Solución:", solucion_layout)

        # Precio
        self.precio_input = QDoubleSpinBox()
        self.precio_input.setRange(0, 99999)
        self.precio_input.setDecimals(2)
        self.precio_input.setSuffix(" €")
        form_layout.addRow("Precio:", self.precio_input)

        layout.addLayout(form_layout)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_aceptar = QPushButton("Añadir")
        btn_aceptar.clicked.connect(self.accept_averia)
        apply_btn_primary(btn_aceptar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_aceptar)
        layout.addLayout(btn_layout)

    def cargar_averias(self):
        """Carga las averías activas en el combo"""
        self.averia_combo.clear()
        self.averia_combo.addItem("-- Seleccionar avería --", None)
        averias = self.averia_manager.obtener_averias_activas()
        for averia in averias:
            self.averia_combo.addItem(averia['nombre'], averia['id'])

    def cargar_soluciones(self, averia_id=None):
        """Carga las soluciones de una avería específica"""
        self.solucion_combo.clear()
        self.solucion_combo.addItem("-- Seleccionar solución --", None)
        if averia_id:
            soluciones = self.solucion_manager.obtener_soluciones_por_averia(averia_id)
            for solucion in soluciones:
                self.solucion_combo.addItem(solucion['nombre'], solucion['id'])

    def on_averia_changed(self):
        """Actualiza soluciones al cambiar avería"""
        averia_id = self.averia_combo.currentData()
        if averia_id:
            self.cargar_soluciones(averia_id)
            self.solucion_combo.setEnabled(True)
            self.btn_add_solucion.setEnabled(True)
            self.btn_del_solucion.setEnabled(True)
        else:
            self.solucion_combo.clear()
            self.solucion_combo.addItem("-- Seleccionar solución --", None)
            self.solucion_combo.setEnabled(False)
            self.btn_add_solucion.setEnabled(False)
            self.btn_del_solucion.setEnabled(False)

    def agregar_averia(self):
        """Abre el diálogo para añadir una nueva avería"""
        dialog = AveriaDialog(self.db, parent=self)
        if dialog.exec_():
            self.cargar_averias()
            averias = self.averia_manager.obtener_averias_activas()
            if averias:
                ultima_averia = averias[-1]
                index = self.averia_combo.findData(ultima_averia['id'])
                if index >= 0:
                    self.averia_combo.setCurrentIndex(index)

    def agregar_solucion(self):
        """Abre el diálogo para añadir una nueva solución"""
        averia_id = self.averia_combo.currentData()
        if not averia_id:
            notify_warning(self, tr("Error"), tr("Selecciona una avería primero"))
            return

        dialog = SolucionDialog(self.db, averia_id=averia_id, parent=self)
        if dialog.exec_():
            self.cargar_soluciones(averia_id)
            soluciones = self.solucion_manager.obtener_soluciones_por_averia(averia_id)
            if soluciones:
                ultima_solucion = soluciones[-1]
                index = self.solucion_combo.findData(ultima_solucion['id'])
                if index >= 0:
                    self.solucion_combo.setCurrentIndex(index)

    def eliminar_averia_combo(self):
        """Elimina la avería seleccionada del combo"""
        averia_id = self.averia_combo.currentData()
        if not averia_id:
            notify_warning(self, tr("Error"), tr("Selecciona una avería para eliminar"))
            return

        averia_nombre = self.averia_combo.currentText()
        if ask_confirm(self, tr("Confirmar Eliminación"), tr("¿Estás seguro de eliminar la avería '{averia}'?").format(averia=averia_nombre) + "\n\n"
            + tr("También se eliminarán todas sus soluciones asociadas.")):
            if self.averia_manager.eliminar_averia(averia_id):
                notify_success(self, tr("Éxito"), tr("Avería '{averia}' eliminada").format(averia=averia_nombre))
                self.cargar_averias()
                self.solucion_combo.clear()
                self.solucion_combo.addItem("-- " + tr("Seleccionar solución") + " --", None)
                self.solucion_combo.setEnabled(False)
                self.btn_add_solucion.setEnabled(False)
                self.btn_del_solucion.setEnabled(False)
            else:
                notify_warning(self, tr("Error"), tr("No se pudo eliminar la avería.\nPuede tener reparaciones asociadas."))

    def eliminar_solucion(self):
        """Elimina la solución seleccionada"""
        solucion_id = self.solucion_combo.currentData()
        if not solucion_id:
            notify_warning(self, tr("Error"), tr("Selecciona una solución para eliminar"))
            return

        solucion_nombre = self.solucion_combo.currentText()
        if ask_confirm(self, tr("Confirmar Eliminación"),
            tr("¿Estás seguro de eliminar la solución '{solucion}'?").format(solucion=solucion_nombre)):
            if self.solucion_manager.eliminar_solucion(solucion_id):
                notify_success(self, tr("Éxito"), tr("Solución '{solucion}' eliminada").format(solucion=solucion_nombre))
                averia_id = self.averia_combo.currentData()
                self.cargar_soluciones(averia_id)
            else:
                notify_warning(self, tr("Error"), tr("No se pudo eliminar la solución.\nPuede tener reparaciones asociadas."))

    def accept_averia(self):
        """Valida y guarda"""
        if not self.averia_combo.currentData():
            notify_warning(self, tr("Error"), tr("Debes seleccionar una avería"))
            return

        if not self.solucion_combo.currentData():
            notify_warning(self, tr("Error"), tr("Debes seleccionar una solución"))
            return

        if self.precio_input.value() <= 0:
            notify_warning(self, tr("Error"), tr("El precio debe ser mayor que 0"))
            return

        self.resultado = {
            'averia_texto': self.averia_combo.currentText(),
            'solucion_texto': self.solucion_combo.currentText(),
            'precio': self.precio_input.value()
        }
        self.accept()

    def obtener_resultado(self):
        return getattr(self, 'resultado', None)


class ReparacionItemDialog(QDialog):
    def __init__(self, db, item=None, parent=None):
        """
        Dialog para añadir dispositivos a reparar con múltiples averías
        item: dict con datos pre-cargados (para editar)
        """
        super().__init__(parent)
        self.db = db
        self.item = item
        self.marca_modelo_manager = MarcaModeloManager(db)
        self.averias = []  # Lista de averías del dispositivo

        self.setWindowTitle("Añadir Dispositivo a Reparar" if not item else "Editar Dispositivo")
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()

        if item:
            self.cargar_datos()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Grupo de información del dispositivo
        info_group = QGroupBox("Detalles del Dispositivo")
        form_layout = QFormLayout()

        # Marca con botones + y -
        marca_layout = QHBoxLayout()
        self.marca_combo = QComboBox()
        self.cargar_marcas()
        self.marca_combo.currentIndexChanged.connect(self.on_marca_changed)
        marca_layout.addWidget(self.marca_combo)

        btn_add_marca = QPushButton("+")
        btn_add_marca.setMaximumWidth(35)
        btn_add_marca.setToolTip("Añadir nueva marca")
        btn_add_marca.clicked.connect(self.agregar_marca)
        apply_btn_success(btn_add_marca)
        marca_layout.addWidget(btn_add_marca)

        btn_del_marca = QPushButton("-")
        btn_del_marca.setMaximumWidth(35)
        btn_del_marca.setToolTip("Eliminar marca seleccionada")
        btn_del_marca.clicked.connect(self.eliminar_marca)
        apply_btn_danger(btn_del_marca)
        marca_layout.addWidget(btn_del_marca)

        form_layout.addRow("Marca:", marca_layout)

        # Modelo con botones + y -
        modelo_layout = QHBoxLayout()
        self.modelo_combo = QComboBox()
        modelo_layout.addWidget(self.modelo_combo)

        btn_add_modelo = QPushButton("+")
        btn_add_modelo.setMaximumWidth(35)
        btn_add_modelo.setToolTip("Añadir nuevo modelo")
        btn_add_modelo.clicked.connect(self.agregar_modelo)
        apply_btn_success(btn_add_modelo)
        modelo_layout.addWidget(btn_add_modelo)

        btn_del_modelo = QPushButton("-")
        btn_del_modelo.setMaximumWidth(35)
        btn_del_modelo.setToolTip("Eliminar modelo seleccionado")
        btn_del_modelo.clicked.connect(self.eliminar_modelo)
        apply_btn_danger(btn_del_modelo)
        modelo_layout.addWidget(btn_del_modelo)

        form_layout.addRow("Modelo:", modelo_layout)

        # IMEI
        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("IMEI o Número de Serie")
        form_layout.addRow("IMEI/SN:", self.imei_input)

        # Código Pantalla / Patrón
        self.patron_input = QLineEdit()
        self.patron_input.setPlaceholderText("Código de desbloqueo o patrón")
        form_layout.addRow("Cód. Pantalla:", self.patron_input)

        # Nota Interna
        self.nota_input = QPlainTextEdit()
        self.nota_input.setPlaceholderText("Notas internas, estado físico, observaciones...")
        self.nota_input.setMaximumHeight(60)
        form_layout.addRow("Nota:", self.nota_input)

        info_group.setLayout(form_layout)
        layout.addWidget(info_group)

        # === SECCIÓN DE AVERÍAS ===
        averias_group = QGroupBox("Averías del Dispositivo")
        averias_layout = QVBoxLayout()

        # Tabla de averías
        self.tabla_averias = QTableWidget()
        self.tabla_averias.setColumnCount(4)
        self.tabla_averias.setHorizontalHeaderLabels(["Avería", "Solución", "Precio", "Acciones"])
        header = self.tabla_averias.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tabla_averias.setColumnWidth(3, 80) # Botón eliminar
        
        self.tabla_averias.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Estilo Global de Tabla
        self.tabla_averias.verticalHeader().setDefaultSectionSize(60)
        self.tabla_averias.verticalHeader().setVisible(False)
        self.tabla_averias.setStyleSheet("QTableWidget::item { padding: 0px; }")
        
        self.tabla_averias.setMaximumHeight(200)
        averias_layout.addWidget(self.tabla_averias)

        # Botón añadir avería y total
        btn_averias_layout = QHBoxLayout()

        btn_add_averia = QPushButton("+ Añadir Avería")
        apply_btn_success(btn_add_averia)
        btn_add_averia.clicked.connect(self.abrir_dialogo_averia)
        btn_averias_layout.addWidget(btn_add_averia)

        btn_averias_layout.addStretch()

        self.lbl_total = QLabel("Total: 0.00 €")
        self.lbl_total.setStyleSheet("font-weight: bold; font-size: 16px; color: #BF616A;")
        btn_averias_layout.addWidget(self.lbl_total)

        averias_layout.addLayout(btn_averias_layout)
        averias_group.setLayout(averias_layout)
        layout.addWidget(averias_group)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton("Añadir Dispositivo")
        btn_guardar.clicked.connect(self.accept_item)
        apply_btn_primary(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_marcas(self):
        """Carga las marcas en el combo"""
        self.marca_combo.clear()
        self.marca_combo.addItem("Seleccionar Marca", None)
        marcas = self.marca_modelo_manager.obtener_todas_marcas()
        for marca in marcas:
            self.marca_combo.addItem(marca['nombre'], marca['id'])

    def cargar_modelos(self, marca_id=None):
        """Carga los modelos en el combo"""
        self.modelo_combo.clear()
        self.modelo_combo.addItem("Seleccionar Modelo", None)
        if marca_id:
            modelos = self.marca_modelo_manager.obtener_todos_modelos(marca_id)
            for modelo in modelos:
                self.modelo_combo.addItem(modelo['nombre'], modelo['id'])

    def on_marca_changed(self):
        """Actualiza modelos al cambiar marca"""
        marca_id = self.marca_combo.currentData()
        self.cargar_modelos(marca_id)

    def agregar_marca(self):
        """Añade una nueva marca"""
        nombre, ok = QInputDialog.getText(self, "Nueva Marca", "Nombre de la marca:")
        if ok and nombre.strip():
            if self.marca_modelo_manager.crear_marca(nombre.strip()):
                self.cargar_marcas()
                index = self.marca_combo.findText(nombre.strip())
                if index >= 0: self.marca_combo.setCurrentIndex(index)

    def agregar_modelo(self):
        """Añade un nuevo modelo a la marca seleccionada"""
        marca_id = self.marca_combo.currentData()
        if not marca_id:
            notify_warning(self, tr("Error"), tr("Selecciona una marca primero"))
            return

        nombre, ok = QInputDialog.getText(self, tr("Nuevo Modelo"), tr("Nombre del modelo:"))
        if ok and nombre.strip():
            if self.marca_modelo_manager.crear_modelo(nombre.strip(), marca_id):
                self.cargar_modelos(marca_id)
                index = self.modelo_combo.findText(nombre.strip())
                if index >= 0: self.modelo_combo.setCurrentIndex(index)

    def eliminar_marca(self):
        """Elimina la marca seleccionada"""
        marca_id = self.marca_combo.currentData()
        if not marca_id:
            notify_warning(self, tr("Error"), tr("Selecciona una marca para eliminar"))
            return

        marca_nombre = self.marca_combo.currentText()
        if ask_confirm(self, tr("Confirmar Eliminación"),
            tr("¿Estás seguro de eliminar la marca '{marca}'?").format(marca=marca_nombre) + "\n\n" +
            tr("También se eliminarán todos sus modelos asociados.")):
            if self.marca_modelo_manager.eliminar_marca(marca_id):
                notify_success(self, tr("Éxito"), tr("Marca '{marca}' eliminada").format(marca=marca_nombre))
                self.cargar_marcas()
                self.cargar_modelos(None)
            else:
                notify_warning(self, tr("Error"), tr("No se pudo eliminar la marca.\nPuede tener reparaciones asociadas."))

    def eliminar_modelo(self):
        """Elimina el modelo seleccionado"""
        modelo_id = self.modelo_combo.currentData()
        if not modelo_id:
            notify_warning(self, tr("Error"), tr("Selecciona un modelo para eliminar"))
            return

        modelo_nombre = self.modelo_combo.currentText()
        if ask_confirm(self, tr("Confirmar Eliminación"),
            tr("¿Estás seguro de eliminar el modelo '{modelo}'?").format(modelo=modelo_nombre)):
            if self.marca_modelo_manager.eliminar_modelo(modelo_id):
                notify_success(self, tr("Éxito"), tr("Modelo '{modelo}' eliminado").format(modelo=modelo_nombre))
                marca_id = self.marca_combo.currentData()
                self.cargar_modelos(marca_id)
            else:
                notify_warning(self, tr("Error"), tr("No se pudo eliminar el modelo.\nPuede tener reparaciones asociadas."))

    def abrir_dialogo_averia(self):
        """Abre el diálogo para añadir una avería"""
        dialog = AveriaItemDialog(self.db, parent=self)
        if dialog.exec_():
            averia = dialog.obtener_resultado()
            if averia:
                self.averias.append(averia)
                self.refrescar_tabla_averias()

    def refrescar_tabla_averias(self):
        """Refresca la tabla de averías"""
        self.tabla_averias.setRowCount(0)
        total = 0

        for i, averia in enumerate(self.averias):
            self.tabla_averias.insertRow(i)
            self.tabla_averias.setRowHeight(i, 60)

            # Avería
            a_item = QTableWidgetItem(averia['averia_texto'])
            a_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_averias.setItem(i, 0, a_item)

            # Solución
            s_item = QTableWidgetItem(averia['solucion_texto'])
            s_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_averias.setItem(i, 1, s_item)

            # Precio
            precio = averia['precio']
            total += precio
            precio_item = QTableWidgetItem(f"{precio:.2f} €")
            precio_item.setTextAlignment(Qt.AlignCenter)
            self.tabla_averias.setItem(i, 2, precio_item)

            # Botón eliminar - Centrado estructural
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            btn_del = QPushButton()
            btn_del.setToolTip(tr("Eliminar"))
            btn_del.clicked.connect(lambda checked, idx=i: self.eliminar_averia(idx))
            estilizar_btn_eliminar(btn_del)
            
            v_layout.addWidget(btn_del)
            self.tabla_averias.setCellWidget(i, 3, container)

        self.lbl_total.setText(f"Total: {total:.2f} €")

    def eliminar_averia(self, index):
        """Elimina una avería de la lista"""
        if 0 <= index < len(self.averias):
            self.averias.pop(index)
            self.refrescar_tabla_averias()

    def cargar_datos(self):
        """Carga datos para editar"""
        if self.item.get('marca_id'):
            idx = self.marca_combo.findData(self.item['marca_id'])
            self.marca_combo.setCurrentIndex(idx)

        if self.item.get('modelo_id'):
            idx = self.modelo_combo.findData(self.item['modelo_id'])
            self.modelo_combo.setCurrentIndex(idx)

        self.imei_input.setText(self.item.get('imei', ''))
        self.patron_input.setText(self.item.get('patron_codigo', ''))
        self.nota_input.setPlainText(self.item.get('notas', ''))

        # Cargar averías si existen
        if self.item.get('averias'):
            self.averias = self.item['averias']
            self.refrescar_tabla_averias()

    def accept_item(self):
        """Valida y guarda"""
        marca_id = self.marca_combo.currentData()
        modelo_id = self.modelo_combo.currentData()

        if not marca_id or not modelo_id:
            notify_warning(self, "Error", "Debes seleccionar Marca y Modelo")
            return

        if not self.averias:
            notify_warning(self, "Error", "Debes añadir al menos una avería")
            return

        # Calcular precio total
        precio_total = sum(a['precio'] for a in self.averias)

        self.resultado = {
            'marca_id': marca_id,
            'marca_nombre': self.marca_combo.currentText(),
            'modelo_id': modelo_id,
            'modelo_nombre': self.modelo_combo.currentText(),
            'imei': self.imei_input.text().strip(),
            'patron_codigo': self.patron_input.text().strip(),
            'notas': self.nota_input.toPlainText().strip(),
            'precio_estimado': precio_total,
            'averias': self.averias  # Lista de averías
        }
        self.accept()

    def obtener_resultado(self):
        return getattr(self, 'resultado', None)
