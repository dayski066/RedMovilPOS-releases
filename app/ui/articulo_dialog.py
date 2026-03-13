"""
Diálogo para añadir/editar artículos en facturas, compras y reparaciones
Incluye selectores de marca y modelo con botones +/-
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QDoubleSpinBox,
                             QComboBox, QSpinBox, QGroupBox, QInputDialog)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.modules.marca_modelo_manager import MarcaModeloManager
from app.ui.transparent_buttons import apply_btn_success, apply_btn_danger, apply_btn_cancel
from app.i18n import tr
import time


class ArticuloDialog(QDialog):
    def __init__(self, db, articulo=None, parent=None):
        """
        Dialog para añadir artículos
        articulo: dict con datos pre-cargados (para editar)
        """
        super().__init__(parent)
        self.db = db
        self.articulo = articulo
        self.marca_modelo_manager = MarcaModeloManager(db)

        self.setWindowTitle(tr("Añadir Artículo") if not articulo else tr("Editar Artículo"))
        self.setModal(True)
        self.setMinimumWidth(600)
        self.setup_ui()

        if articulo:
            self.cargar_datos()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Grupo de información del artículo
        info_group = QGroupBox(tr("Información del Artículo"))
        form_layout = QFormLayout()

        # Marca con botones + y -
        marca_layout = QHBoxLayout()
        self.marca_combo = QComboBox()
        self.cargar_marcas()
        self.marca_combo.currentIndexChanged.connect(self.on_marca_changed)
        marca_layout.addWidget(self.marca_combo)

        btn_add_marca = QPushButton("+")
        btn_add_marca.setMaximumWidth(35)
        btn_add_marca.setToolTip(tr("Añadir nueva marca"))
        btn_add_marca.clicked.connect(self.agregar_marca)
        apply_btn_success(btn_add_marca)
        marca_layout.addWidget(btn_add_marca)

        btn_del_marca = QPushButton("-")
        btn_del_marca.setMaximumWidth(35)
        btn_del_marca.setToolTip(tr("Eliminar marca seleccionada"))
        btn_del_marca.clicked.connect(self.eliminar_marca)
        apply_btn_danger(btn_del_marca)
        marca_layout.addWidget(btn_del_marca)

        form_layout.addRow(tr("Marca:"), marca_layout)

        # Modelo con botones + y - (filtrado por marca)
        modelo_layout = QHBoxLayout()
        self.modelo_combo = QComboBox()
        modelo_layout.addWidget(self.modelo_combo)

        btn_add_modelo = QPushButton("+")
        btn_add_modelo.setMaximumWidth(35)
        btn_add_modelo.setToolTip(tr("Añadir nuevo modelo"))
        btn_add_modelo.clicked.connect(self.agregar_modelo)
        apply_btn_success(btn_add_modelo)
        modelo_layout.addWidget(btn_add_modelo)

        btn_del_modelo = QPushButton("-")
        btn_del_modelo.setMaximumWidth(35)
        btn_del_modelo.setToolTip(tr("Eliminar modelo seleccionado"))
        btn_del_modelo.clicked.connect(self.eliminar_modelo)
        apply_btn_danger(btn_del_modelo)
        modelo_layout.addWidget(btn_del_modelo)

        form_layout.addRow(tr("Modelo:"), modelo_layout)

        # Descripción
        self.descripcion_input = QLineEdit()
        self.descripcion_input.setPlaceholderText(tr("Descripción del artículo (se generará automáticamente)"))
        form_layout.addRow(tr("Descripción:"), self.descripcion_input)

        # Código EAN (opcional)
        self.ean_input = QLineEdit()
        self.ean_input.setPlaceholderText(tr("Opcional"))
        form_layout.addRow(tr("Código EAN:"), self.ean_input)

        # IMEI/SN (opcional)
        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText(tr("IMEI o Número de Serie (opcional)"))
        form_layout.addRow(tr("IMEI/SN:"), self.imei_input)

        # RAM (opcional)
        self.ram_input = QLineEdit()
        self.ram_input.setPlaceholderText(tr("Ej: 4GB, 8GB, 16GB (opcional)"))
        form_layout.addRow(tr("RAM:"), self.ram_input)

        # Almacenamiento (opcional)
        self.almacenamiento_input = QLineEdit()
        self.almacenamiento_input.setPlaceholderText(tr("Ej: 64GB, 128GB, 256GB, 1TB (opcional)"))
        form_layout.addRow(tr("Almacenamiento:"), self.almacenamiento_input)

        # Estado (opcional)
        estado_layout = QHBoxLayout()
        self.estado_combo = QComboBox()
        self.estado_combo.addItem(tr("Sin especificar"), "")
        self.estado_combo.addItem(tr("A Estrenar"), "nuevo")
        self.estado_combo.addItem("KM0", "km0")
        self.estado_combo.addItem(tr("Usado"), "usado")
        estado_layout.addWidget(self.estado_combo)
        form_layout.addRow(tr("Estado:"), estado_layout)

        # Cantidad
        self.cantidad_input = QSpinBox()
        self.cantidad_input.setMinimum(1)
        self.cantidad_input.setMaximum(999)
        self.cantidad_input.setValue(1)
        self.cantidad_input.valueChanged.connect(self.actualizar_descripcion)
        form_layout.addRow(tr("Cantidad:"), self.cantidad_input)

        # Precio Unitario
        self.precio_input = QDoubleSpinBox()
        self.precio_input.setMinimum(0)
        self.precio_input.setMaximum(999999)
        self.precio_input.setDecimals(2)
        self.precio_input.setSuffix(" €")
        form_layout.addRow(tr("Precio Unitario:"), self.precio_input)

        info_group.setLayout(form_layout)
        layout.addWidget(info_group)

        # Ayuda
        help_label = QLabel(tr("Selecciona marca y modelo. La descripción se generará automáticamente."))
        help_label.setStyleSheet("color: #7B88A0; font-size: 11px; padding: 10px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton(tr("Añadir"))
        btn_guardar.clicked.connect(self.accept_articulo)
        apply_btn_success(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_marcas(self):
        """Carga las marcas en el combo"""
        self.marca_combo.clear()
        self.marca_combo.addItem(tr("Sin marca"), None)

        marcas = self.marca_modelo_manager.obtener_todas_marcas()
        for marca in marcas:
            self.marca_combo.addItem(marca['nombre'], marca['id'])

    def cargar_modelos(self, marca_id=None):
        """Carga los modelos en el combo, filtrados por marca"""
        self.modelo_combo.clear()
        self.modelo_combo.addItem(tr("Sin modelo"), None)

        if marca_id:
            modelos = self.marca_modelo_manager.obtener_todos_modelos(marca_id)
            for modelo in modelos:
                self.modelo_combo.addItem(modelo['nombre'], modelo['id'])

    def on_marca_changed(self):
        """Al cambiar la marca, filtrar los modelos y actualizar descripción"""
        marca_id = self.marca_combo.currentData()
        self.cargar_modelos(marca_id)
        self.actualizar_descripcion()

    def actualizar_descripcion(self):
        """Genera descripción automática basada en marca y modelo"""
        marca = self.marca_combo.currentText()
        modelo = self.modelo_combo.currentText()
        cantidad = self.cantidad_input.value()

        if marca != tr("Sin marca") and modelo != tr("Sin modelo"):
            desc = f"{marca} {modelo}"
            if cantidad > 1:
                desc += f" x{cantidad}"
            self.descripcion_input.setText(desc)
        elif marca != tr("Sin marca"):
            desc = marca
            if cantidad > 1:
                desc += f" x{cantidad}"
            self.descripcion_input.setText(desc)

    def agregar_marca(self):
        """Diálogo para añadir nueva marca"""
        nombre, ok = QInputDialog.getText(
            self,
            tr("Nueva Marca"),
            tr("Nombre de la marca:")
        )

        if ok and nombre.strip():
            marca_id = self.marca_modelo_manager.crear_marca(nombre.strip())
            if marca_id:
                notify_success(self, tr("Éxito"), tr("Marca creada correctamente"))
                self.cargar_marcas()
                index = self.marca_combo.findData(marca_id)
                if index >= 0:
                    self.marca_combo.setCurrentIndex(index)
            else:
                notify_error(self, tr("Error"), tr("No se pudo crear la marca.\n¿Ya existe una marca con ese nombre?"))

    def eliminar_marca(self):
        """Elimina la marca seleccionada"""
        marca_id = self.marca_combo.currentData()

        if not marca_id:
            notify_warning(self, tr("Advertencia"), tr("Selecciona una marca para eliminar"))
            return

        respuesta = ask_confirm(self, tr("Confirmar Eliminación"),
            tr("¿Estás seguro de eliminar la marca '{marca}'?\n\nADVERTENCIA: Se eliminarán también todos los modelos asociados a esta marca.", marca=self.marca_combo.currentText()))

        if not respuesta:
            return

        exito, mensaje = self.marca_modelo_manager.eliminar_marca(marca_id)

        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            self.cargar_marcas()
            self.cargar_modelos()
        else:
            notify_warning(self, tr("Advertencia"), mensaje)

    def agregar_modelo(self):
        """Diálogo para añadir nuevo modelo"""
        marca_id = self.marca_combo.currentData()

        if not marca_id:
            notify_warning(self, tr("Advertencia"), tr("Primero selecciona una marca"))
            return

        nombre, ok = QInputDialog.getText(
            self,
            tr("Nuevo Modelo"),
            tr("Nombre del modelo para '{marca}':", marca=self.marca_combo.currentText())
        )

        if ok and nombre.strip():
            modelo_id = self.marca_modelo_manager.crear_modelo(nombre.strip(), marca_id)
            if modelo_id:
                notify_success(self, tr("Éxito"), tr("Modelo creado correctamente"))
                self.cargar_modelos(marca_id)
                index = self.modelo_combo.findData(modelo_id)
                if index >= 0:
                    self.modelo_combo.setCurrentIndex(index)
                    self.actualizar_descripcion()
            else:
                notify_error(self, tr("Error"), tr("No se pudo crear el modelo.\n¿Ya existe un modelo con ese nombre para esta marca?"))

    def eliminar_modelo(self):
        """Elimina el modelo seleccionado"""
        modelo_id = self.modelo_combo.currentData()

        if not modelo_id:
            notify_warning(self, tr("Advertencia"), tr("Selecciona un modelo para eliminar"))
            return

        if not ask_confirm(self, tr("Confirmar Eliminación"),
            tr("¿Estás seguro de eliminar el modelo '{modelo}'?", modelo=self.modelo_combo.currentText())):
            return

        exito, mensaje = self.marca_modelo_manager.eliminar_modelo(modelo_id)

        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            marca_id = self.marca_combo.currentData()
            self.cargar_modelos(marca_id)
        else:
            notify_warning(self, tr("Advertencia"), mensaje)

    def generar_ean_automatico(self):
        """Genera un código EAN-13 automático único basado en timestamp (solo números)"""
        # Formato: 999 + timestamp (10 dígitos)
        # Ejemplo: 9991234567890 (13 dígitos en total)
        # 999 indica que es un código generado internamente
        timestamp = str(int(time.time() * 1000))[-10:]  # Últimos 10 dígitos del timestamp en milisegundos
        ean = f"999{timestamp}"
        return ean

    def cargar_datos(self):
        """Carga los datos del artículo en el formulario (para editar)"""
        if self.articulo.get('marca_id'):
            index = self.marca_combo.findData(self.articulo['marca_id'])
            if index >= 0:
                self.marca_combo.setCurrentIndex(index)

        if self.articulo.get('modelo_id'):
            marca_id = self.articulo.get('marca_id')
            if marca_id:
                self.cargar_modelos(marca_id)
            index = self.modelo_combo.findData(self.articulo['modelo_id'])
            if index >= 0:
                self.modelo_combo.setCurrentIndex(index)

        self.descripcion_input.setText(self.articulo.get('descripcion', ''))
        self.ean_input.setText(self.articulo.get('ean', ''))
        self.imei_input.setText(self.articulo.get('imei', ''))
        self.ram_input.setText(self.articulo.get('ram', ''))
        self.almacenamiento_input.setText(self.articulo.get('almacenamiento', ''))

        # Cargar estado
        estado = self.articulo.get('estado', '')
        if estado:
            index = self.estado_combo.findData(estado)
            if index >= 0:
                self.estado_combo.setCurrentIndex(index)

        self.cantidad_input.setValue(self.articulo.get('cantidad', 1))
        self.precio_input.setValue(self.articulo.get('precio', 0.0))

    def accept_articulo(self):
        """Valida y acepta el artículo"""
        descripcion = self.descripcion_input.text().strip()

        if not descripcion:
            notify_warning(self, tr("Error"), tr("La descripción es obligatoria"))
            return

        precio = self.precio_input.value()
        if precio <= 0:
            notify_warning(self, tr("Error"), tr("El precio debe ser mayor que 0"))
            return

        # Generar EAN automático si no se proporciona uno
        ean = self.ean_input.text().strip()
        if not ean:
            ean = self.generar_ean_automatico()

        # Guardar los datos en el objeto articulo para que el padre los lea
        self.resultado = {
            'marca_id': self.marca_combo.currentData(),
            'marca_nombre': self.marca_combo.currentText() if self.marca_combo.currentData() else None,
            'modelo_id': self.modelo_combo.currentData(),
            'modelo_nombre': self.modelo_combo.currentText() if self.modelo_combo.currentData() else None,
            'descripcion': descripcion,
            'ean': ean,
            'imei': self.imei_input.text().strip() or None,
            'ram': self.ram_input.text().strip() or None,
            'almacenamiento': self.almacenamiento_input.text().strip() or None,
            'estado': self.estado_combo.currentData() or None,
            'estado_nombre': self.estado_combo.currentText() if self.estado_combo.currentData() else None,
            'cantidad': self.cantidad_input.value(),
            'precio': precio
        }

        self.accept()

    def obtener_resultado(self):
        """Devuelve el resultado del diálogo"""
        return getattr(self, 'resultado', None)
