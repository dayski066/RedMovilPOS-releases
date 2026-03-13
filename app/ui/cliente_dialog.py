"""
Diálogo para crear/editar clientes
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFormLayout, QGroupBox, QFileDialog)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from app.utils.notify import notify_success, notify_error, notify_warning
from app.ui.scanner_dialog import ScannerDialog
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel, apply_btn_primary
from app.i18n import tr
import os


class ClienteDialog(QDialog):
    def __init__(self, db, cliente=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.cliente = cliente
        self.dni_imagen_path = None  # Ruta de la imagen del DNI
        self.setWindowTitle(tr("Nuevo Cliente") if not cliente else tr("Editar Cliente"))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setup_ui()

        if cliente:
            self.cargar_datos()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # Formulario
        form_layout = QFormLayout()

        self.nombre_input = QLineEdit()
        self.nif_input = QLineEdit()
        self.direccion_input = QLineEdit()
        self.cp_input = QLineEdit()
        self.ciudad_input = QLineEdit()
        self.provincia_input = QLineEdit()
        self.telefono_input = QLineEdit()
        self.email_input = QLineEdit()

        form_layout.addRow(tr("Nombre") + ":", self.nombre_input)
        form_layout.addRow(tr("NIF/CIF") + ":", self.nif_input)
        form_layout.addRow(tr("Dirección") + ":", self.direccion_input)

        # Fila para CP, Ciudad y Provincia (Verticalmente)
        form_layout.addRow(tr("C.P.") + ":", self.cp_input)
        form_layout.addRow(tr("Ciudad") + ":", self.ciudad_input)
        form_layout.addRow(tr("Provincia:"), self.provincia_input)

        form_layout.addRow(tr("Teléfono") + ":", self.telefono_input)
        form_layout.addRow(tr("Email") + ":", self.email_input)

        layout.addLayout(form_layout)

        # Sección DNI
        dni_group = QGroupBox(tr("DNI/Documento de Identidad"))
        dni_layout = QVBoxLayout()

        # Vista previa del DNI
        self.dni_preview = QLabel()
        self.dni_preview.setAlignment(Qt.AlignCenter)
        self.dni_preview.setMinimumSize(300, 200)
        self.dni_preview.setMaximumSize(400, 250)
        self.dni_preview.setStyleSheet("""
            QLabel {
                border: 2px dashed #4C566A;
                background-color: #3B4252;
                color: #7B88A0;
            }
        """)
        self.dni_preview.setText(tr("Sin imagen de DNI"))
        dni_layout.addWidget(self.dni_preview)

        # Botón escanear
        btn_escanear_dni = QPushButton("📄 " + tr("Escanear DNI"))
        btn_escanear_dni.clicked.connect(self.escanear_dni)
        apply_btn_primary(btn_escanear_dni)
        dni_layout.addWidget(btn_escanear_dni)

        # Botón subir foto
        btn_subir_dni = QPushButton("📂 " + tr("Subir ID"))
        btn_subir_dni.clicked.connect(self.subir_dni)
        apply_btn_primary(btn_subir_dni)
        # Opcional: usar otro color para distinguir, por ahora primary está bien
        dni_layout.addWidget(btn_subir_dni)

        dni_group.setLayout(dni_layout)
        layout.addWidget(dni_group)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self.reject)
        apply_btn_cancel(btn_cancelar)

        btn_guardar = QPushButton(tr("Guardar"))
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)

        btn_layout.addWidget(btn_cancelar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

    def cargar_datos(self):
        """Carga los datos del cliente en el formulario"""
        self.nombre_input.setText(self.cliente['nombre'])
        self.nif_input.setText(self.cliente['nif'] or '')
        self.direccion_input.setText(self.cliente['direccion'] or '')
        self.cp_input.setText(self.cliente.get('codigo_postal') or '')
        self.ciudad_input.setText(self.cliente.get('ciudad') or '')
        self.provincia_input.setText(self.cliente.get('provincia') or '')

        self.telefono_input.setText(self.cliente['telefono'] or '')
        self.email_input.setText(self.cliente.get('email') or '')

        # Cargar imagen DNI si existe
        dni_path = self.cliente.get('dni_imagen')
        if dni_path and os.path.exists(dni_path):
            self.dni_imagen_path = dni_path
            pixmap = QPixmap(dni_path)
            scaled_pixmap = pixmap.scaled(
                self.dni_preview.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.dni_preview.setPixmap(scaled_pixmap)
            self.dni_preview.setText("")

    def guardar(self):
        """Guarda el cliente"""
        nombre = self.nombre_input.text().strip()

        if not nombre:
            notify_warning(self, tr("Error"), tr("El nombre es obligatorio"))
            return

        nif = self.nif_input.text().strip()
        direccion = self.direccion_input.text().strip()
        codigo_postal = self.cp_input.text().strip()
        ciudad = self.ciudad_input.text().strip()
        provincia = self.provincia_input.text().strip()
        telefono = self.telefono_input.text().strip()
        email = self.email_input.text().strip()

        try:
            if self.cliente:
                # Al actualizar, verificar que el NIF no pertenezca a OTRO cliente
                if nif:
                    existente = self.db.fetch_one(
                        "SELECT id, nombre FROM clientes WHERE UPPER(nif) = UPPER(?) AND id != ?",
                        (nif, self.cliente['id'])
                    )
                    if existente:
                        notify_warning(
                            self, tr("Error"),
                            tr("Ya existe un cliente con ese NIF/DNI") + f": {existente['nombre']}"
                        )
                        return

                # Actualizar
                self.db.execute_query(
                    """UPDATE clientes
                       SET nombre = ?, nif = ?, direccion = ?, codigo_postal = ?, ciudad = ?, provincia = ?, telefono = ?, email = ?, dni_imagen = ?
                       WHERE id = ?""",
                    (nombre, nif, direccion, codigo_postal, ciudad, provincia, telefono, email, self.dni_imagen_path, self.cliente['id'])
                )
                notify_success(self, tr("Éxito"), tr("Cliente actualizado correctamente"))
            else:
                # Al crear nuevo, verificar que el NIF no exista
                if nif:
                    existente = self.db.fetch_one(
                        "SELECT id, nombre FROM clientes WHERE UPPER(nif) = UPPER(?)",
                        (nif,)
                    )
                    if existente:
                        notify_warning(
                            self, tr("Error"),
                            tr("Ya existe un cliente con ese NIF/DNI") + f": {existente['nombre']}"
                        )
                        return

                # Insertar nuevo
                self.db.execute_query(
                    """INSERT INTO clientes (nombre, nif, direccion, codigo_postal, ciudad, provincia, telefono, email, dni_imagen)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (nombre, nif, direccion, codigo_postal, ciudad, provincia, telefono, email, self.dni_imagen_path)
                )
                notify_success(self, tr("Éxito"), tr("Cliente creado correctamente"))

            self.accept()
        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), f"{tr('No se pudo guardar el cliente')}:\n{str(e)}")

    def escanear_dni(self):
        """Abre el diálogo para escanear el DNI"""
        dialog = ScannerDialog(self.db, parent=self)
        if dialog.exec_():
            # Obtener la ruta de la imagen escaneada
            image_path = dialog.get_image_path()
            if image_path and os.path.exists(image_path):
                self.dni_imagen_path = image_path

                # Mostrar vista previa
                pixmap = QPixmap(image_path)
                scaled_pixmap = pixmap.scaled(
                    self.dni_preview.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
                self.dni_preview.setPixmap(scaled_pixmap)
                self.dni_preview.setText("")

    def subir_dni(self):
        """Abre un diálogo para seleccionar una imagen y luego el editor"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Seleccionar Imagen"),
            "",
            f"{tr('Archivos de Imagen')} (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            # Abrir ScannerDialog en modo edición con la imagen seleccionada
            dialog = ScannerDialog(self.db, parent=self, image_path=file_path)
            if dialog.exec_():
                # Obtener la ruta de la imagen editada (recortada)
                # OJO: ScannerDialog sobrescribe image_path con la recortada si se recorta,
                # pero mejor nos aseguramos de usar la que devuelve
                final_path = dialog.get_image_path()
                
                if final_path and os.path.exists(final_path):
                    self.dni_imagen_path = final_path

                    # Mostrar vista previa
                    pixmap = QPixmap(final_path)
                    scaled_pixmap = pixmap.scaled(
                        self.dni_preview.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.dni_preview.setPixmap(scaled_pixmap)
                    self.dni_preview.setText("")
