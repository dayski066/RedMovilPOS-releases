"""
Diálogo de actualización OTA para RedMovilPOS
Muestra información de nueva versión y gestiona el proceso de actualización
"""
import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QProgressBar, QTextEdit, QFrame, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont
from app.utils.notify import notify_success, notify_error, notify_warning, ask_confirm
from app.i18n import tr

from app.modules.updater import Updater, UpdateInfo, get_updater
from app.utils.logger import get_logger
from app.ui.transparent_buttons import apply_btn_cancel, apply_btn_success

logger = get_logger('update_dialog')


class DownloadThread(QThread):
    """Hilo para descargar actualización sin bloquear la UI"""
    progress = pyqtSignal(int, int)  # bytes_descargados, bytes_totales
    finished = pyqtSignal(bool, str)  # exito, ruta_o_error

    def __init__(self, updater: Updater):
        super().__init__()
        self.updater = updater

    def run(self):
        try:
            # Primero backup
            backup_ok, backup_result = self.updater.crear_backup_preactualizacion()
            if not backup_ok:
                self.finished.emit(False, f"Error en backup: {backup_result}")
                return

            # Luego descargar
            def on_progress(downloaded, total):
                self.progress.emit(downloaded, total)

            installer_path = self.updater.descargar_actualizacion(on_progress)

            if installer_path:
                self.finished.emit(True, installer_path)
            else:
                self.finished.emit(False, "Error descargando actualización")

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error en hilo de descarga: {e}", exc_info=True)
            self.finished.emit(False, str(e))


class UpdateDialog(QDialog):
    """
    Diálogo que muestra información de actualización disponible
    y gestiona el proceso de descarga e instalación.
    """

    def __init__(self, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self.update_info = update_info
        self.updater = get_updater()
        self.download_thread = None
        self.installer_path = None

        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle(tr("Actualización Disponible"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Cabecera ===
        header_layout = QHBoxLayout()

        icon_label = QLabel("🔄")
        icon_label.setFont(QFont("", 32))
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_label = QLabel(tr("Nueva Versión Disponible"))
        title_label.setFont(QFont("", 16, QFont.Bold))
        title_label.setStyleSheet("color: #A3BE8C;")
        title_layout.addWidget(title_label)

        version_label = QLabel(f"v{self.updater.current_version}  →  v{self.update_info.version}")
        version_label.setFont(QFont("", 12))
        version_label.setStyleSheet("color: #7B88A0;")
        title_layout.addWidget(version_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # === Separador ===
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #434C5E;")
        layout.addWidget(line)

        # === Info de la actualización ===
        info_layout = QHBoxLayout()

        if self.update_info.file_size > 0:
            size_mb = self.update_info.file_size / (1024 * 1024)
            size_label = QLabel(tr("Tamaño: {size_mb} MB", size_mb=f"{size_mb:.1f}"))
            size_label.setStyleSheet("color: #7B88A0;")
            info_layout.addWidget(size_label)

        if self.update_info.published_at:
            # Formatear fecha
            try:
                from datetime import datetime
                fecha = datetime.fromisoformat(self.update_info.published_at.replace('Z', '+00:00'))
                fecha_str = fecha.strftime('%d/%m/%Y')
                date_label = QLabel(tr("Publicado: {fecha}", fecha=fecha_str))
                date_label.setStyleSheet("color: #7B88A0;")
                info_layout.addWidget(date_label)
            except (OSError, ValueError, RuntimeError):
                pass

        info_layout.addStretch()
        layout.addLayout(info_layout)

        # === Changelog ===
        changelog_label = QLabel(tr("Novedades:"))
        changelog_label.setFont(QFont("", 10, QFont.Bold))
        layout.addWidget(changelog_label)

        self.changelog_text = QTextEdit()
        self.changelog_text.setReadOnly(True)
        self.changelog_text.setPlainText(self.update_info.changelog or tr("Sin descripción"))
        self.changelog_text.setMaximumHeight(150)
        self.changelog_text.setStyleSheet("""
            QTextEdit {
                background-color: #3B4252;
                border: 1px solid #434C5E;
                border-radius: 5px;
                padding: 10px;
                color: #D8DEE9;
            }
        """)
        layout.addWidget(self.changelog_text)

        # === Barra de progreso (oculta inicialmente) ===
        self.progress_container = QFrame()
        progress_layout = QVBoxLayout(self.progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel(tr("Preparando actualización..."))
        self.status_label.setStyleSheet("color: #5E81AC;")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #434C5E;
                border-radius: 5px;
                text-align: center;
                background-color: #3B4252;
            }
            QProgressBar::chunk {
                background-color: #A3BE8C;
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        self.progress_container.hide()
        layout.addWidget(self.progress_container)

        # === Advertencia backup ===
        warning_frame = QFrame()
        warning_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(94, 129, 172, 0.15);
                border: 1px solid #81A1C1;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        warning_layout = QVBoxLayout(warning_frame)
        warning_layout.setContentsMargins(10, 10, 10, 10)

        warning_label = QLabel(tr("Se creará una copia de seguridad automática de la base de datos antes de actualizar."))
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("color: #5E81AC; border: none;")
        warning_layout.addWidget(warning_label)

        layout.addWidget(warning_frame)

        layout.addStretch()

        # === Botones ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(tr("Más tarde"))
        self.btn_cancel.clicked.connect(self.reject)
        apply_btn_cancel(self.btn_cancel)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_update = QPushButton(tr("Actualizar Ahora"))
        self.btn_update.clicked.connect(self.iniciar_actualizacion)
        apply_btn_success(self.btn_update)
        btn_layout.addWidget(self.btn_update)

        layout.addLayout(btn_layout)

    def iniciar_actualizacion(self):
        """Inicia el proceso de descarga e instalación"""
        self.btn_update.setEnabled(False)
        self.btn_cancel.setText(tr("Cancelar"))
        self.progress_container.show()
        self.status_label.setText(tr("Creando copia de seguridad..."))
        self.progress_bar.setValue(5)

        # Iniciar hilo de descarga
        self.download_thread = DownloadThread(self.updater)
        self.download_thread.progress.connect(self.on_download_progress)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.start()

    def on_download_progress(self, downloaded: int, total: int):
        """Actualiza la barra de progreso durante la descarga"""
        if total > 0:
            percent = int((downloaded / total) * 100)
            self.progress_bar.setValue(percent)

            # Mostrar MB descargados
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.status_label.setText(tr("Descargando... {descargado} MB / {total} MB", descargado=f"{mb_downloaded:.1f}", total=f"{mb_total:.1f}"))

    def on_download_finished(self, success: bool, result: str):
        """Callback cuando termina la descarga"""
        if success:
            self.installer_path = result
            self.progress_bar.setValue(100)
            self.status_label.setText(tr("Descarga completada"))
            self.status_label.setStyleSheet("color: #A3BE8C;")

            # Preguntar si instalar ahora
            if ask_confirm(self, tr("Instalación"), tr("La actualización se ha descargado correctamente.\n\n"
                "Se ha creado un backup de seguridad de la base de datos.\n\n"
                "¿Desea instalar ahora?\n"
                "(La aplicación se cerrará para completar la instalación)")):
                self.ejecutar_instalador()
            else:
                self.btn_cancel.setText(tr("Cerrar"))
                self.btn_update.setText(tr("Instalar"))
                self.btn_update.setEnabled(True)
                self.btn_update.clicked.disconnect()
                self.btn_update.clicked.connect(self.ejecutar_instalador)
        else:
            self.progress_bar.setValue(0)
            self.status_label.setText(tr("Error: {detalle}", detalle=result))
            self.status_label.setStyleSheet("color: #BF616A;")
            self.btn_update.setEnabled(True)
            self.btn_cancel.setText(tr("Cerrar"))

            notify_error(
                self,
                tr("Error"),
                tr("No se pudo descargar la actualización:\n\n{detalle}", detalle=result)
            )

    def ejecutar_instalador(self):
        """Ejecuta el instalador y cierra la aplicación"""
        if not self.installer_path:
            notify_warning(self, tr("Error"), tr("No hay instalador disponible"))
            return

        if self.updater.instalar_actualizacion(self.installer_path):
            notify_success(
                self,
                tr("Actualización"),
                tr("El instalador se está ejecutando.\n\n"
                "La aplicación se cerrará ahora.")
            )
            # Cerrar la aplicación
            QApplication.instance().quit()
        else:
            notify_error(
                self,
                tr("Error"),
                tr("No se pudo iniciar el instalador.\n\n"
                "Puede ejecutarlo manualmente desde:\n"
                "{ruta}", ruta=self.installer_path)
            )


class CheckUpdateThread(QThread):
    """Hilo para comprobar actualizaciones sin bloquear la UI"""
    finished = pyqtSignal(object)  # UpdateInfo o None

    def run(self):
        try:
            updater = get_updater()
            result = updater.comprobar_actualizacion()
            self.finished.emit(result)
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error comprobando actualizaciones: {e}")
            self.finished.emit(None)


def mostrar_dialogo_actualizacion(update_info: UpdateInfo, parent=None) -> bool:
    """
    Muestra el diálogo de actualización.

    Args:
        update_info: Información de la actualización
        parent: Widget padre

    Returns:
        bool: True si el usuario aceptó actualizar
    """
    dialog = UpdateDialog(update_info, parent)
    result = dialog.exec_()
    return result == QDialog.Accepted


def comprobar_actualizaciones_silencioso(callback, parent=None):
    """
    Comprueba actualizaciones en segundo plano.
    Si hay actualización, llama al callback con UpdateInfo.

    Args:
        callback: Función a llamar con UpdateInfo si hay actualización
        parent: Widget padre (para mantener referencia al thread)
    """
    thread = CheckUpdateThread()

    def on_finished(result):
        if result:
            callback(result)

    thread.finished.connect(on_finished)
    thread.start()

    # Guardar referencia para evitar que el thread sea eliminado
    if parent:
        if not hasattr(parent, '_update_threads'):
            parent._update_threads = []
        parent._update_threads.append(thread)

    return thread
