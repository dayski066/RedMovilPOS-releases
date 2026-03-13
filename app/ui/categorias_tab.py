"""
Pestaña para gestión de categorías
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                             QTableWidgetItem, QPushButton, QLabel, QHeaderView, QInputDialog)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.i18n import tr
from app.db.database import Database
from app.modules.categoria_manager import CategoriaManager
from app.ui.transparent_buttons import apply_btn_success, set_btn_icon
from qfluentwidgets import FluentIcon


class CategoriasTab(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.db.connect()
        self.categoria_manager = CategoriaManager(self.db)
        self.setup_ui()
        self.cargar_categorias()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel(tr("Gestión de Categorías"))
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        # Botón nueva categoría
        btn_nueva = QPushButton(tr("Nueva Categoría"))
        btn_nueva.clicked.connect(self.nueva_categoria)
        apply_btn_success(btn_nueva)
        set_btn_icon(btn_nueva, FluentIcon.ADD, color="#A3BE8C")
        header_layout.addWidget(btn_nueva)

        layout.addLayout(header_layout)

        # Tabla de categorías
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels([
            "ID", tr("Nombre"), tr("Nº Productos"), tr("Acciones")
        ])

        # Configurar columnas
        header = self.tabla.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        self.tabla.setColumnWidth(3, 120)
        
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # Altura de fila de máxima gama
        self.tabla.verticalHeader().setDefaultSectionSize(60)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setStyleSheet("QTableWidget::item { padding: 0px; }")

        layout.addWidget(self.tabla)

    def cargar_categorias(self):
        """Carga todas las categorías en la tabla"""
        categorias = self.categoria_manager.obtener_todas()

        self.tabla.setRowCount(0)

        for categoria in categorias:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            self.tabla.setRowHeight(row, 60)

            # ID
            id_item = QTableWidgetItem(str(categoria['id']))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 0, id_item)

            # Nombre
            nombre_item = QTableWidgetItem(categoria['nombre'])
            nombre_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 1, nombre_item)

            # Contar productos
            num_productos = self.categoria_manager.contar_productos(categoria['id'])
            productos_item = QTableWidgetItem(str(num_productos))
            productos_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 2, productos_item)

            # Botones de acción - Centrado estructural
            container = QWidget()
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(8, 0, 8, 10)
            v_layout.setAlignment(Qt.AlignCenter)

            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(0, 0, 0, 0)
            h_layout.setSpacing(15)
            h_layout.setAlignment(Qt.AlignCenter)

            from app.ui.styles import estilizar_btn_editar, estilizar_btn_eliminar
            
            btn_editar = QPushButton()
            btn_editar.setToolTip(tr("Editar"))
            btn_editar.clicked.connect(lambda checked, c=categoria: self.editar_categoria(c))
            estilizar_btn_editar(btn_editar)

            btn_eliminar = QPushButton()
            btn_eliminar.setToolTip(tr("Eliminar"))
            btn_eliminar.clicked.connect(lambda checked, c_id=categoria['id']: self.eliminar_categoria(c_id))
            estilizar_btn_eliminar(btn_eliminar)

            h_layout.addWidget(btn_editar)
            h_layout.addWidget(btn_eliminar)

            v_layout.addLayout(h_layout)
            self.tabla.setCellWidget(row, 3, container)

    def nueva_categoria(self):
        """Crea una nueva categoría"""
        nombre, ok = QInputDialog.getText(
            self, tr("Nueva Categoría"), tr("Nombre de la categoría") + ":"
        )

        if ok and nombre.strip():
            descripcion, ok2 = QInputDialog.getText(
                self, tr("Nueva Categoría"), tr("Descripción (opcional)") + ":"
            )

            categoria_id = self.categoria_manager.crear(nombre.strip(), descripcion.strip() if ok2 else None)

            if categoria_id:
                notify_success(self, tr("Éxito"), tr("Categoría creada correctamente"))
                self.cargar_categorias()
            else:
                notify_error(self, tr("Error"), tr("No se pudo crear la categoría.") + "\n" + tr("¿Ya existe una categoría con ese nombre?"))

    def editar_categoria(self, categoria):
        """Edita una categoría existente"""
        nombre, ok = QInputDialog.getText(
            self, tr("Editar Categoría"), tr("Nombre de la categoría") + ":",
            text=categoria['nombre']
        )

        if ok and nombre.strip():
            descripcion, ok2 = QInputDialog.getText(
                self, tr("Editar Categoría"), tr("Descripción (opcional)") + ":",
                text=categoria['descripcion'] or ''
            )

            result = self.categoria_manager.actualizar(
                categoria['id'],
                nombre.strip(),
                descripcion.strip() if ok2 else None
            )

            if result is not None:
                notify_success(self, tr("Éxito"), tr("Categoría actualizada correctamente"))
                self.cargar_categorias()
            else:
                notify_error(self, tr("Error"), tr("No se pudo actualizar la categoría"))

    def eliminar_categoria(self, categoria_id):
        """Elimina una categoría"""
        if ask_confirm(self, tr("Confirmar eliminación"), tr("¿Está seguro de eliminar esta categoría?")):
            exito, mensaje = self.categoria_manager.eliminar(categoria_id)

            if exito:
                notify_success(self, tr("Éxito"), tr(mensaje))
                self.cargar_categorias()
            else:
                notify_warning(self, tr("Advertencia"), tr(mensaje))

    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
