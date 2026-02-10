"""
Diálogo de progreso de impresión con monitoreo en tiempo real
Muestra el estado real del trabajo en la cola de Windows
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette
import platform
from app.utils.logger import logger


class PrintProgressDialog(QDialog):
    """
    Diálogo que muestra el progreso real de impresión monitoreando
    la cola de Windows en tiempo real.
    """
    # Señales
    print_success = pyqtSignal()
    print_failed = pyqtSignal(str)  # error message

    # Estados del trabajo de impresión
    STAGE_PREPARING = 0
    STAGE_SENDING = 1
    STAGE_IN_QUEUE = 2
    STAGE_PRINTING = 3
    STAGE_COMPLETED = 4
    STAGE_ERROR = -1

    # Constantes de estado de Windows
    JOB_STATUS_PAUSED = 0x00000001
    JOB_STATUS_ERROR = 0x00000002
    JOB_STATUS_DELETING = 0x00000004
    JOB_STATUS_SPOOLING = 0x00000008
    JOB_STATUS_PRINTING = 0x00000010
    JOB_STATUS_OFFLINE = 0x00000020
    JOB_STATUS_PAPEROUT = 0x00000040
    JOB_STATUS_PRINTED = 0x00000080
    JOB_STATUS_DELETED = 0x00000100
    JOB_STATUS_BLOCKED_DEVQ = 0x00000200
    JOB_STATUS_USER_INTERVENTION = 0x00000400
    JOB_STATUS_RESTART = 0x00000800
    JOB_STATUS_COMPLETE = 0x00001000

    def __init__(self, parent=None, titulo="Imprimiendo"):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setFixedSize(450, 280)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Estado interno
        self.printer_name = None
        self.job_id = None
        self.pdf_path = None
        self.current_stage = self.STAGE_PREPARING
        self.error_message = None
        self.check_count = 0
        self.max_checks = 240  # 2 minutos máximo (240 * 500ms)

        # Timer para monitoreo
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._check_job_status)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Título
        self.title_label = QLabel("Preparando impresión...")
        self.title_label.setFont(QFont("", 14, QFont.Bold))
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 12px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Frame de etapas
        stages_frame = QFrame()
        stages_frame.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px; padding: 10px;")
        stages_layout = QVBoxLayout(stages_frame)
        stages_layout.setSpacing(8)

        # Etapas
        self.stage_labels = []
        stages = [
            ("1. Preparando documento", self.STAGE_PREPARING),
            ("2. Enviando a impresora", self.STAGE_SENDING),
            ("3. En cola de impresión", self.STAGE_IN_QUEUE),
            ("4. Imprimiendo...", self.STAGE_PRINTING),
            ("5. Impresión completada", self.STAGE_COMPLETED)
        ]

        for text, stage_id in stages:
            label = QLabel(text)
            label.setFont(QFont("", 10))
            label.stage_id = stage_id
            self.stage_labels.append(label)
            stages_layout.addWidget(label)

        layout.addWidget(stages_frame)

        # Estado actual detallado
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.status_label)

        # Botones (ocultos inicialmente)
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(10)

        self.btn_retry = QPushButton("Reintentar")
        self.btn_retry.setFixedSize(120, 35)
        self.btn_retry.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #5E81AC; border: 2px solid #5E81AC;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: transparent; color: #5E81AC; border: 2px solid #5E81AC;
            }
        """)
        self.btn_retry.clicked.connect(self._on_retry)
        self.btn_retry.hide()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFixedSize(120, 35)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #BF616A; border: 2px solid #BF616A;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: transparent; color: #BF616A; border: 2px solid #BF616A;
            }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.hide()

        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.btn_retry)
        self.buttons_layout.addWidget(self.btn_cancel)
        self.buttons_layout.addStretch()

        layout.addLayout(self.buttons_layout)

        self._update_stage_display()

    def _update_stage_display(self):
        """Actualiza la visualización de las etapas"""
        for label in self.stage_labels:
            if label.stage_id < self.current_stage:
                # Etapa completada
                label.setStyleSheet("color: #27ae60; font-weight: bold;")
                label.setText("✓ " + label.text().split(". ", 1)[1] if ". " in label.text() else label.text())
            elif label.stage_id == self.current_stage:
                # Etapa actual
                if self.current_stage == self.STAGE_ERROR:
                    label.setStyleSheet("color: #e74c3c; font-weight: bold;")
                else:
                    label.setStyleSheet("color: #3498db; font-weight: bold;")
            else:
                # Etapa pendiente
                label.setStyleSheet("color: #999;")

        # Actualizar barra de progreso
        if self.current_stage >= 0:
            progress = min(100, (self.current_stage + 1) * 20)
            self.progress_bar.setValue(progress)

        # Actualizar color de la barra según estado
        if self.current_stage == self.STAGE_ERROR:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #ddd;
                    border-radius: 12px;
                    background-color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #e74c3c;
                    border-radius: 10px;
                }
            """)
        elif self.current_stage == self.STAGE_COMPLETED:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: 2px solid #ddd;
                    border-radius: 12px;
                    background-color: #f0f0f0;
                }
                QProgressBar::chunk {
                    background-color: #27ae60;
                    border-radius: 10px;
                }
            """)

    def set_stage(self, stage, status_text=""):
        """Establece la etapa actual"""
        self.current_stage = stage
        self.status_label.setText(status_text)

        titles = {
            self.STAGE_PREPARING: "Preparando impresión...",
            self.STAGE_SENDING: "Enviando a impresora...",
            self.STAGE_IN_QUEUE: "Documento en cola...",
            self.STAGE_PRINTING: "Imprimiendo documento...",
            self.STAGE_COMPLETED: "¡Impresión completada!",
            self.STAGE_ERROR: "Error de impresión"
        }
        self.title_label.setText(titles.get(stage, "Procesando..."))
        self._update_stage_display()

    def start_monitoring(self, printer_name, job_id, pdf_path):
        """Inicia el monitoreo del trabajo de impresión"""
        self.printer_name = printer_name
        self.job_id = job_id
        self.pdf_path = pdf_path
        self.check_count = 0

        self.set_stage(self.STAGE_IN_QUEUE, f"Trabajo #{job_id} en cola")

        # Iniciar timer de monitoreo (cada 500ms)
        self.monitor_timer.start(500)

    def _check_job_status(self):
        """Verifica el estado del trabajo en la cola de Windows"""
        self.check_count += 1

        if self.check_count > self.max_checks:
            self.monitor_timer.stop()
            self._show_error("Tiempo de espera agotado. La impresora no responde.")
            return

        if platform.system() != 'Windows':
            # En otros sistemas, asumir éxito después de unos segundos
            if self.check_count > 6:
                self._show_success()
            return

        try:
            import win32print

            hPrinter = win32print.OpenPrinter(self.printer_name)
            try:
                jobs = win32print.EnumJobs(hPrinter, 0, 100, 1)

                job_found = False
                for job in jobs:
                    if job.get('JobId') == self.job_id:
                        job_found = True
                        status = job.get('Status', 0)
                        status_text = self._get_status_text(status)

                        # Verificar errores
                        if status & self.JOB_STATUS_ERROR:
                            self.monitor_timer.stop()
                            self._show_error("Error en la impresora")
                            return

                        if status & self.JOB_STATUS_OFFLINE:
                            self.set_stage(self.STAGE_IN_QUEUE, "Impresora desconectada - esperando...")
                            return

                        if status & self.JOB_STATUS_PAPEROUT:
                            self.set_stage(self.STAGE_IN_QUEUE, "Sin papel - esperando...")
                            return

                        if status & self.JOB_STATUS_USER_INTERVENTION:
                            self.set_stage(self.STAGE_IN_QUEUE, "Requiere atención - verificar impresora")
                            return

                        if status & self.JOB_STATUS_PAUSED:
                            self.set_stage(self.STAGE_IN_QUEUE, "Trabajo pausado")
                            return

                        # Estados de progreso
                        if status & self.JOB_STATUS_PRINTED or status & self.JOB_STATUS_COMPLETE:
                            self.monitor_timer.stop()
                            self._show_success()
                            return

                        if status & self.JOB_STATUS_PRINTING:
                            self.set_stage(self.STAGE_PRINTING, status_text)
                            return

                        if status & self.JOB_STATUS_SPOOLING:
                            self.set_stage(self.STAGE_SENDING, "Procesando documento...")
                            return

                        # En cola esperando
                        self.set_stage(self.STAGE_IN_QUEUE, status_text)
                        break

                # Si el trabajo ya no está en la cola
                if not job_found:
                    self.monitor_timer.stop()
                    # Si desapareció rápido, probablemente se imprimió
                    self._show_success()

            finally:
                win32print.ClosePrinter(hPrinter)

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error verificando cola: {e}")
            # No fallar inmediatamente, seguir intentando
            if self.check_count > 10:
                self.monitor_timer.stop()
                self._show_error(f"Error al verificar estado: {e}")

    def _get_status_text(self, status):
        """Convierte el código de estado a texto legible"""
        if status == 0:
            return "En cola - esperando impresora"

        texts = []
        if status & self.JOB_STATUS_PRINTING:
            texts.append("Imprimiendo")
        if status & self.JOB_STATUS_SPOOLING:
            texts.append("Procesando")
        if status & self.JOB_STATUS_PAUSED:
            texts.append("Pausado")
        if status & self.JOB_STATUS_ERROR:
            texts.append("Error")
        if status & self.JOB_STATUS_OFFLINE:
            texts.append("Impresora desconectada")
        if status & self.JOB_STATUS_PAPEROUT:
            texts.append("Sin papel")
        if status & self.JOB_STATUS_PRINTED:
            texts.append("Impreso")
        if status & self.JOB_STATUS_COMPLETE:
            texts.append("Completado")

        return " - ".join(texts) if texts else "Procesando..."

    def _show_success(self):
        """Muestra el estado de éxito"""
        self.set_stage(self.STAGE_COMPLETED, "")
        self.progress_bar.setValue(100)
        self.title_label.setStyleSheet("color: #27ae60;")
        self.status_label.setText("El documento se ha impreso correctamente")

        # Cerrar automáticamente después de 1.5 segundos
        QTimer.singleShot(1500, self._close_success)

    def _close_success(self):
        """Cierra el diálogo con éxito"""
        self.print_success.emit()
        self.accept()

    def _show_error(self, message):
        """Muestra el estado de error con opciones"""
        self.current_stage = self.STAGE_ERROR
        self.error_message = message
        self.title_label.setText("Error de impresión")
        self.title_label.setStyleSheet("color: #e74c3c;")
        self.status_label.setText(message)
        self._update_stage_display()

        # Mostrar botones
        self.btn_retry.show()
        self.btn_cancel.show()

    def _on_retry(self):
        """Maneja el botón de reintentar"""
        self.btn_retry.hide()
        self.btn_cancel.hide()
        self.title_label.setStyleSheet("")

        # Reiniciar estado
        self.current_stage = self.STAGE_PREPARING
        self.check_count = 0
        self._update_stage_display()

        # Emitir señal para reintentar (el padre manejará esto)
        self.print_failed.emit("RETRY")
        self.reject()

    def _on_cancel(self):
        """Maneja el botón de cancelar"""
        self.print_failed.emit("CANCEL")
        self.reject()

    def closeEvent(self, event):
        """Maneja el cierre del diálogo"""
        self.monitor_timer.stop()
        super().closeEvent(event)
