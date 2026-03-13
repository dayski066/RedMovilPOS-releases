"""
Diálogo mejorado para crear/editar productos con EAN, IMEI, categorías, marcas y modelos
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QDoubleSpinBox,
                             QComboBox, QSpinBox, QCheckBox, QGroupBox, QInputDialog)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.modules.producto_manager import ProductoManager
from app.modules.categoria_manager import CategoriaManager
from app.modules.marca_modelo_manager import MarcaModeloManager
from app.ui.transparent_buttons import apply_btn_success, apply_btn_danger, apply_btn_cancel, apply_btn_info


class ProductoDialogNuevo(QDialog):
    def __init__(self, db, producto=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.producto = producto
        self.producto_manager = ProductoManager(db)
        self.categoria_manager = CategoriaManager(db)
        self.marca_modelo_manager = MarcaModeloManager(db)

        self.setWindowTitle("Nuevo Producto" if not producto else "Editar Producto")
        self.setModal(True)
        self.setMinimumWidth(650)
        self.setup_ui()

        if producto:
            self.cargar_datos()
        else:
            # Generar EAN automático
            self.ean_input.setText(self.producto_manager.generar_codigo_ean())

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Grupo de información básica
        info_group = QGroupBox("Información del Producto")
        form_layout = QFormLayout()

        # Categoría (PRIMERO)
        categoria_layout = QHBoxLayout()
        self.categoria_combo = QComboBox()
        self.cargar_categorias()
        self.categoria_combo.currentTextChanged.connect(self.on_categoria_changed)
        categoria_layout.addWidget(self.categoria_combo)
        form_layout.addRow("Categoría:", categoria_layout)

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

        # Modelo con botones + y - (filtrado por marca)
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

        # Código EAN
        ean_layout = QHBoxLayout()
        self.ean_input = QLineEdit()
        self.ean_input.setPlaceholderText("Escanear código de barras o dejar automático")
        ean_layout.addWidget(self.ean_input)

        btn_generar_ean = QPushButton("Generar")
        btn_generar_ean.clicked.connect(self.generar_ean)
        btn_generar_ean.setMaximumWidth(80)
        apply_btn_info(btn_generar_ean)
        ean_layout.addWidget(btn_generar_ean)

        form_layout.addRow("Código EAN:", ean_layout)

        # Descripción
        self.descripcion_input = QLineEdit()
        self.descripcion_input.setPlaceholderText("Nombre del producto o servicio")
        form_layout.addRow("Descripción:", self.descripcion_input)

        # IMEI (opcional - solo para móviles)
        self.imei_input = QLineEdit()
        self.imei_input.setPlaceholderText("Solo disponible para móviles")
        self.imei_input.setEnabled(False)
        form_layout.addRow("IMEI:", self.imei_input)

        # RAM (solo para móviles)
        self.ram_combo = QComboBox()
        self.ram_combo.addItems(["", "1 GB", "2 GB", "3 GB", "4 GB", "6 GB", "8 GB", "12 GB", "16 GB", "32 GB"])
        self.ram_combo.setEnabled(False)
        form_layout.addRow("RAM:", self.ram_combo)

        # Almacenamiento (solo para móviles)
        self.almacenamiento_combo = QComboBox()
        self.almacenamiento_combo.addItems(["", "16 GB", "32 GB", "64 GB", "128 GB", "256 GB", "512 GB", "1 TB"])
        self.almacenamiento_combo.setEnabled(False)
        form_layout.addRow("Almacenamiento:", self.almacenamiento_combo)

        # Estado (solo para móviles)
        self.estado_combo = QComboBox()
        self.estado_combo.addItems(["", "Nuevo", "Usado", "KM0"])
        self.estado_combo.setEnabled(False)
        form_layout.addRow("Estado:", self.estado_combo)

        # Precio Compra (Nuevo)
        self.precio_compra_input = QDoubleSpinBox()
        self.precio_compra_input.setMinimum(0)
        self.precio_compra_input.setMaximum(999999)
        self.precio_compra_input.setDecimals(2)
        self.precio_compra_input.setSuffix(" €")
        form_layout.addRow("Precio Costo:", self.precio_compra_input)

        # Precio Venta
        self.precio_input = QDoubleSpinBox()
        self.precio_input.setMinimum(0)
        self.precio_input.setMaximum(999999)
        self.precio_input.setDecimals(2)
        self.precio_input.setSuffix(" €")
        form_layout.addRow("Precio Venta (PVP):", self.precio_input)

        # Stock
        self.stock_input = QSpinBox()
        self.stock_input.setMinimum(0)
        self.stock_input.setMaximum(999999)
        form_layout.addRow("Stock:", self.stock_input)

        info_group.setLayout(form_layout)
        layout.addWidget(info_group)

        # Ayuda
        help_label = QLabel("💡 Selecciona primero la categoría, luego la marca y modelo. Si no existen, usa los botones + para añadirlos.")
        help_label.setStyleSheet("color: #7B88A0; font-size: 11px; padding: 10px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton("Guardar")
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_categorias(self):
        """Carga las categorías en el combo"""
        self.categoria_combo.clear()
        self.categoria_combo.addItem("Sin categoría", None)

        categorias = self.categoria_manager.obtener_todas()
        for categoria in categorias:
            self.categoria_combo.addItem(categoria['nombre'], categoria['id'])

    def cargar_marcas(self):
        """Carga las marcas en el combo"""
        self.marca_combo.clear()
        self.marca_combo.addItem("Sin marca", None)

        marcas = self.marca_modelo_manager.obtener_todas_marcas()
        for marca in marcas:
            self.marca_combo.addItem(marca['nombre'], marca['id'])

    def cargar_modelos(self, marca_id=None):
        """Carga los modelos en el combo, filtrados por marca"""
        self.modelo_combo.clear()
        self.modelo_combo.addItem("Sin modelo", None)

        if marca_id:
            modelos = self.marca_modelo_manager.obtener_todos_modelos(marca_id)
            for modelo in modelos:
                self.modelo_combo.addItem(modelo['nombre'], modelo['id'])

    def on_marca_changed(self):
        """Al cambiar la marca, filtrar los modelos"""
        marca_id = self.marca_combo.currentData()
        self.cargar_modelos(marca_id)

    def agregar_marca(self):
        """Diálogo para añadir nueva marca"""
        nombre, ok = QInputDialog.getText(
            self,
            "Nueva Marca",
            "Nombre de la marca:"
        )

        if ok and nombre.strip():
            marca_id = self.marca_modelo_manager.crear_marca(nombre.strip())
            if marca_id:
                notify_success(self, tr("Éxito"), tr("Marca creada correctamente"))
                self.cargar_marcas()
                # Seleccionar la marca recién creada
                index = self.marca_combo.findData(marca_id)
                if index >= 0:
                    self.marca_combo.setCurrentIndex(index)
            else:
                notify_error(self, tr("Error"), tr("No se pudo crear la marca.") + "\n" + tr("¿Ya existe una marca con ese nombre?"))

    def eliminar_marca(self):
        """Elimina la marca seleccionada"""
        marca_id = self.marca_combo.currentData()

        if not marca_id:
            notify_warning(self, tr("Advertencia"), tr("Selecciona una marca para eliminar"))
            return
            
        respuesta = ask_confirm(self, tr("Confirmar Eliminación"), tr("¿Estás seguro de eliminar la marca '{marca}'?").format(marca=self.marca_combo.currentText()) + "\n\n" +
            tr("ADVERTENCIA: Se eliminarán también todos los modelos asociados a esta marca."))

        if not respuesta:
            return

        exito, mensaje = self.marca_modelo_manager.eliminar_marca(marca_id)

        if exito:
            notify_success(self, tr("Éxito"), tr(mensaje))
            self.cargar_marcas()
            self.cargar_modelos()
        else:
            notify_warning(self, tr("Advertencia"), tr(mensaje))

    def agregar_modelo(self):
        """Diálogo para añadir nuevo modelo"""
        marca_id = self.marca_combo.currentData()

        if not marca_id:
            notify_warning(self, "Advertencia", "Primero selecciona una marca")
            return

        nombre, ok = QInputDialog.getText(
            self,
            "Nuevo Modelo",
            f"Nombre del modelo para '{self.marca_combo.currentText()}':"
        )

        if ok and nombre.strip():
            modelo_id = self.marca_modelo_manager.crear_modelo(nombre.strip(), marca_id)
            if modelo_id:
                notify_success(self, "Éxito", "Modelo creado correctamente")
                self.cargar_modelos(marca_id)
                # Seleccionar el modelo recién creado
                index = self.modelo_combo.findData(modelo_id)
                if index >= 0:
                    self.modelo_combo.setCurrentIndex(index)
            else:
                notify_error(self, "Error", "No se pudo crear el modelo.\n¿Ya existe un modelo con ese nombre para esta marca?")

    def eliminar_modelo(self):
        """Elimina el modelo seleccionado"""
        modelo_id = self.modelo_combo.currentData()

        if not modelo_id:
            notify_warning(self, "Advertencia", "Selecciona un modelo para eliminar")
            return

        if not ask_confirm(self, "Confirmar Eliminación",
            f"¿Estás seguro de eliminar el modelo '{self.modelo_combo.currentText()}'?"):
            return

        exito, mensaje = self.marca_modelo_manager.eliminar_modelo(modelo_id)

        if exito:
            notify_success(self, "Éxito", mensaje)
            marca_id = self.marca_combo.currentData()
            self.cargar_modelos(marca_id)
        else:
            notify_warning(self, "Advertencia", mensaje)

    def generar_ean(self):
        """Genera un nuevo código EAN"""
        self.ean_input.setText(self.producto_manager.generar_codigo_ean())

    def on_categoria_changed(self, categoria_nombre):
        """Activa/desactiva los campos específicos de móviles según la categoría"""
        # Los campos solo están habilitados para la categoría "Móviles"
        es_movil = categoria_nombre.lower() == "móviles" or categoria_nombre.lower() == "moviles"

        # IMEI
        self.imei_input.setEnabled(es_movil)
        if es_movil:
            self.imei_input.setPlaceholderText("Introduce el IMEI del móvil")
        else:
            self.imei_input.setPlaceholderText("Solo disponible para móviles")
            self.imei_input.clear()

        # RAM
        self.ram_combo.setEnabled(es_movil)
        self.ram_combo.setEditable(True)  # Permitir texto personalizado
        if not es_movil:
            self.ram_combo.setCurrentIndex(0)

        # Almacenamiento
        self.almacenamiento_combo.setEnabled(es_movil)
        self.almacenamiento_combo.setEditable(True)  # Permitir texto personalizado
        if not es_movil:
            self.almacenamiento_combo.setCurrentIndex(0)

        # Estado
        self.estado_combo.setEnabled(es_movil)
        self.estado_combo.setEditable(True)  # Permitir texto personalizado
        if not es_movil:
            self.estado_combo.setCurrentIndex(0)

        # Stock (máximo 1 para móviles)
        if es_movil:
            # Limitar el máximo de stock a 1 para móviles
            self.stock_input.setMaximum(1)
            # Solo forzar a 1 si es nuevo producto (sin ID), no cuando editamos
            if not self.producto:
                self.stock_input.setValue(1)
        else:
            self.stock_input.setMaximum(999999)  # Sin límite para otros productos
            self.stock_input.setEnabled(True)

    def cargar_datos(self):
        """Carga los datos del producto en el formulario"""
        self.ean_input.setText(self.producto['codigo_ean'] or '')
        self.descripcion_input.setText(self.producto['descripcion'])
        self.imei_input.setText(self.producto['imei'] or '')

        # --- RECUPERACIÓN DE DATOS FALTANTES (FALLBACK) ---
        ram = self.producto.get('ram')
        almac = self.producto.get('almacenamiento')
        estado = self.producto.get('estado')

        # Si faltan datos, intentar buscarlos en el historial de compras
        if not (ram and almac and estado):
            imei = self.producto.get('imei')
            ean = self.producto.get('codigo_ean')
            
            compra_item = None
            if imei:
                compra_item = self.db.fetch_one("SELECT ram, almacenamiento, estado FROM compras_items WHERE imei = ? ORDER BY id DESC LIMIT 1", (imei,))
            
            if not compra_item and ean:
                compra_item = self.db.fetch_one("SELECT ram, almacenamiento, estado FROM compras_items WHERE codigo_ean = ? ORDER BY id DESC LIMIT 1", (ean,))

            if compra_item:
                if not ram: ram = compra_item.get('ram')
                if not almac: almac = compra_item.get('almacenamiento')
                if not estado: estado = compra_item.get('estado')

        # Cargar RAM (con soporte para texto personalizado)
        if ram:
            index = self.ram_combo.findText(ram)
            if index >= 0:
                self.ram_combo.setCurrentIndex(index)
            else:
                self.ram_combo.setCurrentText(ram)

        # Cargar Almacenamiento (con soporte para texto personalizado)
        if almac:
            index = self.almacenamiento_combo.findText(almac)
            if index >= 0:
                self.almacenamiento_combo.setCurrentIndex(index)
            else:
                self.almacenamiento_combo.setCurrentText(almac)

        # Cargar Estado (con soporte para texto personalizado)
        if estado:
            index = self.estado_combo.findText(estado)
            if index >= 0:
                self.estado_combo.setCurrentIndex(index)
            else:
                self.estado_combo.setCurrentText(estado)

        # --- MIGRACIÓN DE PRECIO ---
        # Si el precio de compra es 0 y hay precio de venta, asumimos que es un dato antiguo
        # donde el "Precio" guardaba el Costo.
        p_venta_actual = float(self.producto['precio'])
        p_compra_actual = float(self.producto.get('precio_compra') or 0)
        
        if p_compra_actual == 0 and p_venta_actual > 0:
            # Caso Legacy: Mover el valor de Venta a Compra (Costo)
            self.precio_compra_input.setValue(p_venta_actual)
            self.precio_input.setValue(0) # Dejar PVP a 0 para que el usuario lo establezca
        else:
            # Caso Normal
            self.precio_compra_input.setValue(p_compra_actual)
            self.precio_input.setValue(p_venta_actual)

        self.stock_input.setValue(self.producto['stock'])

        # Seleccionar categoría
        if self.producto['categoria_id']:
            index = self.categoria_combo.findData(self.producto['categoria_id'])
            if index >= 0:
                self.categoria_combo.setCurrentIndex(index)
                # Activar/desactivar IMEI según la categoría
                self.on_categoria_changed(self.categoria_combo.currentText())

        # Seleccionar marca
        if self.producto.get('marca_id'):
            index = self.marca_combo.findData(self.producto['marca_id'])
            if index >= 0:
                self.marca_combo.setCurrentIndex(index)

        # Seleccionar modelo
        if self.producto.get('modelo_id'):
            # Primero cargar modelos de la marca
            marca_id = self.producto.get('marca_id')
            if marca_id:
                self.cargar_modelos(marca_id)
            # Luego seleccionar el modelo
            index = self.modelo_combo.findData(self.producto['modelo_id'])
            if index >= 0:
                self.modelo_combo.setCurrentIndex(index)

    def guardar(self):
        """Guarda el producto"""
        descripcion = self.descripcion_input.text().strip()

        codigo_ean = self.ean_input.text().strip()

        # Si no hay EAN, generar uno
        if not codigo_ean:
            codigo_ean = self.producto_manager.generar_codigo_ean()

        # Validación para productos móviles
        categoria_nombre = self.categoria_combo.currentText().strip().lower()
        es_movil = categoria_nombre == "móviles" or categoria_nombre == "moviles"

        if es_movil:
            # IMEI obligatorio para móviles
            imei = self.imei_input.text().strip()
            if not imei:
                notify_warning(self, "Error", "El IMEI es obligatorio para productos móviles")
                return
            
            # RAM ya no obligatoria, pero recomendada. No bloqueamos.
            
            # Precio venta obligatorio
            precio = self.precio_input.value()
            if precio <= 0:
                notify_warning(self, "Error", "El Precio de Venta es obligatorio")
                return

        datos = {
            'codigo_ean': codigo_ean,
            'descripcion': descripcion,
            'precio': self.precio_input.value(),
            'precio_compra': self.precio_compra_input.value(),
            'categoria_id': self.categoria_combo.currentData(),
            'marca_id': self.marca_combo.currentData(),
            'modelo_id': self.modelo_combo.currentData(),
            'imei': self.imei_input.text().strip() or None,
            'ram': self.ram_combo.currentText().strip() if self.ram_combo.currentText().strip() else None,
            'almacenamiento': self.almacenamiento_combo.currentText().strip() if self.almacenamiento_combo.currentText().strip() else None,
            'estado': self.estado_combo.currentText().strip() if self.estado_combo.currentText().strip() else None,
            'stock': self.stock_input.value()
        }

        try:
            if self.producto:
                # Actualizar
                self.producto_manager.actualizar_producto(self.producto['id'], datos)
                notify_success(self, "Éxito", "Producto actualizado correctamente")
            else:
                # Verificar duplicados antes de crear
                imei = self.imei_input.text().strip() or None
                duplicado = self.producto_manager.verificar_duplicado(codigo_ean, imei)
                
                if duplicado['existe']:
                    prod = duplicado['producto']
                    tipo = duplicado['tipo'].upper()
                    estado = "ACTIVO" if duplicado['activo'] else "ELIMINADO"
                    
                    # Construir mensaje descriptivo
                    marca = prod.get('marca_nombre') or ''
                    modelo = prod.get('modelo_nombre') or ''
                    nombre_prod = f"{marca} {modelo}".strip() or prod.get('descripcion') or 'Sin nombre'
                    
                    if duplicado['activo']:
                        # Producto activo - no permitir duplicado
                        notify_warning(
                            self, 
                            "Producto Duplicado",
                            f"Ya existe un producto {estado} con el mismo {tipo}:\n\n"
                            f"• Producto: {nombre_prod}\n"
                            f"• {tipo}: {codigo_ean if tipo == 'EAN' else imei}\n"
                            f"• PVP: {prod.get('precio', 0):.2f} €\n\n"
                            f"No se puede crear un duplicado."
                        )
                        return
                    else:
                        from app.utils.notify import ask_three_options
                        resultado = ask_three_options(
                            self,
                            "Producto Encontrado",
                            f"Se encontró un producto ELIMINADO con el mismo {tipo}:\n\n"
                            f"• Producto: {nombre_prod}\n"
                            f"• {tipo}: {codigo_ean if tipo == 'EAN' else imei}\n"
                            f"• PVP anterior: {prod.get('precio', 0):.2f} €\n\n"
                            f"¿Qué desea hacer?",
                            "Solo Reactivar",
                            "Actualizar y Activar",
                            "Cancelar"
                        )

                        if resultado == 2:  # Cancelar
                            return
                        elif resultado == 0:  # Solo Reactivar
                            # Solo reactivar sin cambiar datos
                            self.producto_manager.reactivar_producto(prod['id'])
                            notify_success(self, "Éxito", f"Producto reactivado: {nombre_prod}")
                            self.accept()
                            return
                        elif clicked == btn_actualizar:
                            # Actualizar datos y reactivar (usar crear_producto que ya hace esto)
                            pass  # Continuar con crear_producto que actualiza y reactiva
                
                # Crear (o reactivar+actualizar si estaba eliminado)
                self.producto_manager.crear_producto(datos)
                notify_success(self, "Éxito", f"Producto creado con código EAN: {codigo_ean}")

            self.accept()

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, "Error", f"No se pudo guardar el producto:\n{str(e)}")
