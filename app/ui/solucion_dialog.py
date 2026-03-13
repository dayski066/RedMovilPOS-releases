"""
Diálogo para crear/editar soluciones del sistema SAT
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QTextEdit, QComboBox)
from PyQt5.QtCore import Qt
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel
from app.i18n import tr


class SolucionDialog(QDialog):
    def __init__(self, db, solucion=None, averia_id=None, parent=None):
        """
        Args:
            db: Conexión a base de datos
            solucion: Objeto solución para editar (None si es nueva)
            averia_id: ID de avería preseleccionada (para nuevas soluciones desde reparacion_item_dialog)
            parent: Widget padre
        """
        super().__init__(parent)
        self.db = db
        self.solucion = solucion
        self.averia_id_preseleccionada = averia_id
        self.setWindowTitle(tr("Nueva Solución") if not solucion else tr("Editar Solución"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()

        if solucion:
            self.cargar_datos()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Formulario
        form_layout = QFormLayout()

        # Selector de avería
        self.averia_combo = QComboBox()
        self.cargar_averias()

        # Si es edición o si viene preseleccionada, deshabilitar selector
        if self.solucion or self.averia_id_preseleccionada:
            self.averia_combo.setEnabled(False)
            self.averia_combo.setStyleSheet("""
                QComboBox {
                    background-color: #3B4252;
                    color: #2E3440;
                    border: 1px solid #4C566A;
                    padding: 5px;
                }
            """)

        form_layout.addRow(tr("Avería *:"), self.averia_combo)

        # Campo nombre
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText(tr("Ej: Sustitución de pantalla OLED, Cambio de batería, etc."))
        form_layout.addRow(tr("Nombre *:"), self.nombre_input)

        # Campo descripción
        self.descripcion_input = QTextEdit()
        self.descripcion_input.setPlaceholderText(tr("Descripción opcional de la solución"))
        self.descripcion_input.setMaximumHeight(100)
        form_layout.addRow(tr("Descripción:"), self.descripcion_input)

        layout.addLayout(form_layout)

        # Nota informativa
        nota = QLabel(tr("* Campos obligatorios"))
        nota.setStyleSheet("color: #7B88A0; font-size: 10pt; font-style: italic;")
        layout.addWidget(nota)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        btn_cancelar.setMinimumHeight(35)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton(tr("Guardar"))
        btn_guardar.clicked.connect(self.guardar)
        btn_guardar.setMinimumHeight(35)
        apply_btn_success(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_averias(self):
        """Carga las averías activas en el combo"""
        from app.modules.averia_manager import AveriaManager
        averia_mgr = AveriaManager(self.db)

        averias = averia_mgr.obtener_averias_activas()

        self.averia_combo.clear()
        self.averia_combo.addItem(tr("-- Seleccionar Avería --"), None)

        for averia in averias:
            self.averia_combo.addItem(averia['nombre'], averia['id'])

            # Preseleccionar si corresponde
            if self.averia_id_preseleccionada and averia['id'] == self.averia_id_preseleccionada:
                self.averia_combo.setCurrentIndex(self.averia_combo.count() - 1)

    def cargar_datos(self):
        """Carga los datos de la solución en el formulario"""
        # Seleccionar la avería correspondiente
        for i in range(self.averia_combo.count()):
            if self.averia_combo.itemData(i) == self.solucion['averia_id']:
                self.averia_combo.setCurrentIndex(i)
                break

        self.nombre_input.setText(self.solucion['nombre'])
        self.descripcion_input.setPlainText(self.solucion.get('descripcion') or '')

    def guardar(self):
        """Guarda la solución"""
        averia_id = self.averia_combo.currentData()

        if not averia_id:
            notify_warning(self, tr("Error"), tr("Debe seleccionar una avería"))
            self.averia_combo.setFocus()
            return

        nombre = self.nombre_input.text().strip()

        if not nombre:
            notify_warning(self, tr("Error"), tr("El nombre de la solución es obligatorio"))
            self.nombre_input.setFocus()
            return

        descripcion = self.descripcion_input.toPlainText().strip()

        try:
            from app.modules.solucion_manager import SolucionManager
            solucion_mgr = SolucionManager(self.db)

            if self.solucion:
                # Actualizar solución existente
                if solucion_mgr.actualizar_solucion(self.solucion['id'], nombre, descripcion):
                    notify_success(self, tr("Éxito"), tr("Solución actualizada correctamente"))
                    self.accept()
                else:
                    notify_error(self, tr("Error"), tr("No se pudo actualizar la solución"))
            else:
                # Crear nueva solución
                solucion_id = solucion_mgr.crear_solucion(averia_id, nombre, descripcion)
                if solucion_id:
                    notify_success(self, tr("Éxito"), tr("Solución creada correctamente"))
                    self.accept()
                else:
                    notify_error(self, tr("Error"), tr("No se pudo crear la solución"))

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("Error al guardar la solución:\n{error}", error=str(e)))
