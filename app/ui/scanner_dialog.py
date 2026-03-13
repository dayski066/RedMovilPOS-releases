"""
Diálogo para escanear documentos usando el escáner configurado
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QRubberBand,
                             QComboBox, QFormLayout, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from app.utils.scanner import escanear_documento, obtener_escaner_configurado, obtener_config_escaneo
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_success, apply_btn_warning, apply_btn_danger, apply_btn_cancel
from app.utils.notify import notify_success, notify_error, notify_warning
from app.i18n import tr
from PIL import Image
import os


class CropLabel(QLabel):
    """Label que permite seleccionar un área para recortar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.rubberBand = None
        self.origin = QPoint()
        self.crop_rect = None
        self.original_image_size = None  # Tamaño de la imagen original

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.pixmap():
            self.origin = event.pos()
            if not self.rubberBand:
                self.rubberBand = QRubberBand(QRubberBand.Rectangle, self)
            self.rubberBand.setGeometry(QRect(self.origin, QPoint()))
            self.rubberBand.show()

    def mouseMoveEvent(self, event):
        if self.rubberBand:
            self.rubberBand.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rubberBand:
            self.crop_rect = self.rubberBand.geometry()

    def set_original_image_size(self, width, height):
        """Guarda el tamaño de la imagen original"""
        self.original_image_size = (width, height)

    def get_crop_rect(self):
        """Obtiene el rectángulo de recorte en coordenadas de la imagen original"""
        if not self.crop_rect or not self.pixmap() or not self.original_image_size:
            return None

        # Tamaños
        label_width = self.width()
        label_height = self.height()
        orig_width, orig_height = self.original_image_size

        # Calcular el tamaño de la imagen escalada dentro del label (manteniendo aspect ratio)
        orig_aspect = orig_width / orig_height
        label_aspect = label_width / label_height

        if orig_aspect > label_aspect:
            # La imagen se ajusta al ancho del label
            scaled_width = label_width
            scaled_height = label_width / orig_aspect
            offset_x = 0
            offset_y = (label_height - scaled_height) / 2
        else:
            # La imagen se ajusta a la altura del label
            scaled_height = label_height
            scaled_width = label_height * orig_aspect
            offset_x = (label_width - scaled_width) / 2
            offset_y = 0

        # Convertir coordenadas del rectángulo de selección
        # Restar el offset y luego escalar a coordenadas originales
        sel_x = self.crop_rect.x() - offset_x
        sel_y = self.crop_rect.y() - offset_y
        sel_w = self.crop_rect.width()
        sel_h = self.crop_rect.height()

        # Escalar a coordenadas de imagen original
        scale_x = orig_width / scaled_width
        scale_y = orig_height / scaled_height

        x = max(0, int(sel_x * scale_x))
        y = max(0, int(sel_y * scale_y))
        w = int(sel_w * scale_x)
        h = int(sel_h * scale_y)

        # Asegurar que no se salga de los límites
        x = min(x, orig_width - 1)
        y = min(y, orig_height - 1)
        w = min(w, orig_width - x)
        h = min(h, orig_height - y)

        return (x, y, x + w, y + h)

    def clear_selection(self):
        """Limpia la selección de recorte"""
        if self.rubberBand:
            self.rubberBand.hide()
        self.crop_rect = None


class ScanThread(QThread):
    """Thread para escanear sin bloquear la UI"""
    finished = pyqtSignal(str)  # Emite la ruta del archivo escaneado
    error = pyqtSignal(str)  # Emite mensaje de error

    def __init__(self, scanner_name, dpi, color_mode):
        super().__init__()
        self.scanner_name = scanner_name
        self.dpi = dpi
        self.color_mode = color_mode

    def run(self):
        try:
            # Inicializar COM para este thread
            import pythoncom
            pythoncom.CoInitialize()

            try:
                image_path = escanear_documento(self.scanner_name, self.dpi, self.color_mode)
                if image_path:
                    self.finished.emit(image_path)
                else:
                    self.error.emit(tr("No se pudo escanear el documento"))
            finally:
                # Limpiar COM al finalizar
                pythoncom.CoUninitialize()

        except (OSError, ValueError, RuntimeError) as e:
            self.error.emit(str(e))


class ScannerDialog(QDialog):
    """Diálogo para escanear documentos"""

    def __init__(self, db, parent=None, image_path=None):
        super().__init__(parent)
        self.db = db
        self.image_path = image_path
        self.setWindowTitle(tr("Escanear Documento") if not image_path else tr("Editar Imagen"))
        self.setMinimumSize(600, 500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Información del escáner
        if not self.image_path:
            info_label = QLabel(tr("Escaneando con el dispositivo configurado"))
            info_label.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
            layout.addWidget(info_label)

            # Obtener escáner configurado
            scanner_name = obtener_escaner_configurado(self.db)

            if scanner_name:
                device_label = QLabel(f"📄 {tr('Escáner')}: {scanner_name}")
                device_label.setStyleSheet("margin-left: 10px; margin-bottom: 10px;")
                layout.addWidget(device_label)
            else:
                error_label = QLabel("⚠️ " + tr("No hay ningún escáner configurado"))
                error_label.setStyleSheet("color: red; margin: 10px; font-size: 12px;")
                layout.addWidget(error_label)

                help_label = QLabel(tr("Por favor, configura un escáner en Ajustes > Impresoras y Escáner"))
                help_label.setStyleSheet("margin-left: 10px; margin-bottom: 15px;")
                layout.addWidget(help_label)

            # Configuración de escaneo
            config_group = QGroupBox(tr("Configuración de Escaneo"))
            config_layout = QFormLayout()

            # Resolución
            self.combo_dpi = QComboBox()
            self.combo_dpi.addItems(["150 DPI (" + tr("Rápido") + ")", "200 DPI (" + tr("Normal") + ")", "300 DPI (" + tr("Alta calidad") + ")", "600 DPI (" + tr("Máxima") + ")"])
            self.combo_dpi.setCurrentIndex(1)  # 200 DPI por defecto
            config_layout.addRow(tr("Resolución:"), self.combo_dpi)

            # Modo de color
            self.combo_color = QComboBox()
            self.combo_color.addItems([tr("Color"), tr("Escala de Grises"), tr("Blanco y Negro")])
            self.combo_color.setCurrentIndex(0)  # Color por defecto
            config_layout.addRow(tr("Modo:"), self.combo_color)

            config_group.setLayout(config_layout)
            layout.addWidget(config_group)
        else:
            scanner_name = None  # No necesario en modo edición

        # Vista previa con capacidad de recorte
        self.preview_label = CropLabel()
        self.preview_label.setText(tr("Vista previa del escaneo") + "\n\n" + tr("Después de escanear, arrastra para seleccionar el área a recortar"))
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(550, 350)
        self.preview_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #4C566A;
                background-color: #3B4252;
                color: #7B88A0;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.preview_label)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        # Botones
        buttons_layout = QHBoxLayout()

        if not self.image_path:
            self.scan_button = QPushButton("🖨️ " + tr("Escanear"))
            apply_btn_primary(self.scan_button)
            self.scan_button.clicked.connect(self.iniciar_escaneo)
            self.scan_button.setEnabled(scanner_name is not None)
            buttons_layout.addWidget(self.scan_button)

        self.crop_button = QPushButton("✂️ " + tr("Recortar"))
        # Usar Warning o Info para acciones secundarias destacadas
        apply_btn_warning(self.crop_button)
        self.crop_button.clicked.connect(self.recortar_imagen)
        self.crop_button.setEnabled(False) # Se activará al cargar imagen
        buttons_layout.addWidget(self.crop_button)

        self.accept_button = QPushButton(tr("Aceptar"))
        apply_btn_success(self.accept_button)
        self.accept_button.clicked.connect(self.accept)
        self.accept_button.setEnabled(False)
        buttons_layout.addWidget(self.accept_button)

        cancel_button = QPushButton("✗ " + tr("Cancelar"))
        apply_btn_danger(cancel_button)
        cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_button)

        layout.addLayout(buttons_layout)

        # Si hay imagen inicial, cargarla
        if self.image_path:
            self.preview_label.setText(tr("Cargando imagen..."))
            # Usar QTimer para dar tiempo a que la UI se muestre antes de procesar imagen grande
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, lambda: self.escaneo_completado(self.image_path))

    def iniciar_escaneo(self):
        """Inicia el proceso de escaneo"""
        scanner_name = obtener_escaner_configurado(self.db)
        if not scanner_name:
            notify_warning(self, tr("Error"), tr("No hay escáner configurado"))
            return

        # Obtener valores de los combos
        dpi_text = self.combo_dpi.currentText()
        dpi = int(dpi_text.split()[0])  # Extraer el número (150, 200, etc.)

        color_mode = self.combo_color.currentText()

        # Deshabilitar botón y mostrar progreso
        self.scan_button.setEnabled(False)
        self.progress_bar.show()
        self.preview_label.setText(tr("Escaneando... Por favor espera"))

        # Crear thread de escaneo
        self.scan_thread = ScanThread(scanner_name, dpi, color_mode)
        self.scan_thread.finished.connect(self.escaneo_completado)
        self.scan_thread.error.connect(self.escaneo_error)
        self.scan_thread.start()

    def escaneo_completado(self, image_path):
        """Se llama cuando el escaneo termina exitosamente"""
        self.image_path = image_path
        self.progress_bar.hide()
        if hasattr(self, 'scan_button'):
            self.scan_button.setEnabled(True)

        # Mostrar vista previa
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)

            # Guardar tamaño original de la imagen
            self.preview_label.set_original_image_size(pixmap.width(), pixmap.height())

            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            self.preview_label.setText("")
            self.accept_button.setEnabled(True)
            self.crop_button.setEnabled(True)  # Habilitar botón de recorte
        else:
            self.preview_label.setText(tr("Error: No se pudo cargar la imagen"))

    def escaneo_error(self, error_msg):
        """Se llama cuando hay un error en el escaneo"""
        self.progress_bar.hide()
        if hasattr(self, 'scan_button'):
            self.scan_button.setEnabled(True)
        self.preview_label.setText(tr("Error al escanear"))
        notify_error(self, tr("Error de escaneo"), tr("No se pudo escanear:\n\n{error}", error=error_msg))

    def recortar_imagen(self):
        """Recorta la imagen según el área seleccionada"""
        if not self.image_path or not os.path.exists(self.image_path):
            notify_warning(self, tr("Error"), tr("No hay imagen para recortar"))
            return

        # Obtener rectángulo de recorte
        crop_rect = self.preview_label.get_crop_rect()
        if not crop_rect:
            notify_warning(self, tr("Error"), tr("Por favor, selecciona un área para recortar"))
            return

        try:
            # Abrir imagen original
            imagen = Image.open(self.image_path)

            # Recortar imagen
            imagen_recortada = imagen.crop(crop_rect)

            # Generar nombre para imagen recortada
            base, ext = os.path.splitext(self.image_path)
            cropped_path = f"{base}_recortado{ext}"

            # Guardar imagen recortada
            imagen_recortada.save(cropped_path)

            # Actualizar ruta de imagen
            self.image_path = cropped_path

            # Actualizar vista previa
            pixmap = QPixmap(cropped_path)

            # Actualizar tamaño original con la imagen recortada
            self.preview_label.set_original_image_size(pixmap.width(), pixmap.height())

            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)

            # Limpiar selección
            self.preview_label.clear_selection()

            # Habilitar botón de aceptar
            self.accept_button.setEnabled(True)

            notify_success(self, tr("Éxito"), tr("Imagen recortada correctamente"))

        except (OSError, ValueError, RuntimeError) as e:
            notify_error(self, tr("Error"), tr("No se pudo recortar la imagen:\n\n{error}", error=str(e)))

    def get_image_path(self):
        """Devuelve la ruta de la imagen escaneada"""
        return self.image_path
