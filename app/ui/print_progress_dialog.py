"""
Diálogo de progreso de impresión con monitoreo en tiempo real
Muestra el estado real del trabajo en la cola de Windows
Diseño premium con indicadores de etapas circulares
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QWidget
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush
import platform
from app.utils.logger import logger
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_cancel
from app.i18n import tr


class StepIndicator(QWidget):
    """Indicador circular de paso con estado visual"""

    STATE_PENDING = 0
    STATE_ACTIVE = 1
    STATE_COMPLETED = 2
    STATE_ERROR = 3

    def __init__(self, number, text, parent=None):
        super().__init__(parent)
        self.number = number
        self.text = text
        self.state = self.STATE_PENDING
        self.setFixedHeight(36)

    def set_state(self, state):
        self.state = state
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        circle_size = 26
        x_circle = 8
        y_circle = (self.height() - circle_size) // 2

        colors = {
            self.STATE_PENDING: ("#4C566A", "#4C566A", "#4C566A"),    # (circle_bg, border, text)
            self.STATE_ACTIVE: ("#5E81AC", "#81A1C1", "#ECEFF4"),
            self.STATE_COMPLETED: ("#A3BE8C", "#A3BE8C", "#2E3440"),
            self.STATE_ERROR: ("#BF616A", "#BF616A", "#ECEFF4"),
        }
        circle_bg, border_color, inner_text = colors.get(self.state, colors[self.STATE_PENDING])

        # Dibujar circulo
        painter.setPen(QPen(QColor(border_color), 2))
        painter.setBrush(QBrush(QColor(circle_bg)))
        painter.drawEllipse(x_circle, y_circle, circle_size, circle_size)

        # Contenido del circulo
        center_x = x_circle + circle_size // 2
        center_y = y_circle + circle_size // 2

        if self.state == self.STATE_COMPLETED:
            # Checkmark
            painter.setPen(QPen(QColor(inner_text), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawLine(center_x - 5, center_y, center_x - 1, center_y + 4)
            painter.drawLine(center_x - 1, center_y + 4, center_x + 6, center_y - 4)
        elif self.state == self.STATE_ERROR:
            # X mark
            painter.setPen(QPen(QColor(inner_text), 2.5, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(center_x - 4, center_y - 4, center_x + 4, center_y + 4)
            painter.drawLine(center_x + 4, center_y - 4, center_x - 4, center_y + 4)
        else:
            # Numero
            painter.setPen(QColor(inner_text))
            font = QFont("", 10, QFont.Bold)
            painter.setFont(font)
            painter.drawText(x_circle, y_circle, circle_size, circle_size, Qt.AlignCenter, str(self.number))

        # Texto de la etapa
        text_x = x_circle + circle_size + 12
        text_colors = {
            self.STATE_PENDING: "#4C566A",
            self.STATE_ACTIVE: "#ECEFF4",
            self.STATE_COMPLETED: "#A3BE8C",
            self.STATE_ERROR: "#BF616A",
        }
        text_color = text_colors.get(self.state, "#4C566A")
        painter.setPen(QColor(text_color))

        font_weight = QFont.Bold if self.state in (self.STATE_ACTIVE, self.STATE_COMPLETED) else QFont.Normal
        font = QFont("", 11, font_weight)
        painter.setFont(font)
        painter.drawText(text_x, 0, self.width() - text_x, self.height(), Qt.AlignVCenter, self.text)


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

    def __init__(self, parent=None, titulo=None):
        super().__init__(parent)
        self.setWindowTitle(titulo or tr("Imprimiendo"))
        self.setModal(True)
        self.setFixedSize(480, 380)
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
        layout.setSpacing(12)
        layout.setContentsMargins(30, 25, 30, 25)

        # Icono de impresora + Título
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        printer_icon = QLabel("\U0001F5A8")
        printer_icon.setStyleSheet("font-size: 28px; background: transparent;")
        header_layout.addWidget(printer_icon)

        self.title_label = QLabel(tr("Preparando impresión..."))
        self.title_label.setFont(QFont("", 15, QFont.Bold))
        self.title_label.setStyleSheet("color: #ECEFF4;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Barra de progreso slim
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #3B4252;
            }
            QProgressBar::chunk {
                background-color: #5E81AC;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(8)

        # Indicadores de pasos
        stages_container = QWidget()
        stages_container.setStyleSheet("""
            QWidget {
                background-color: #3B4252;
                border-radius: 10px;
            }
        """)
        stages_layout = QVBoxLayout(stages_container)
        stages_layout.setContentsMargins(15, 15, 15, 15)
        stages_layout.setSpacing(4)

        self.step_indicators = []
        steps = [
            (1, tr("Preparando documento")),
            (2, tr("Enviando a impresora")),
            (3, tr("En cola de impresión")),
            (4, tr("Imprimiendo")),
            (5, tr("Completado")),
        ]

        for num, text in steps:
            indicator = StepIndicator(num, text)
            indicator.stage_id = num - 1  # 0-based
            self.step_indicators.append(indicator)
            stages_layout.addWidget(indicator)

        layout.addWidget(stages_container)

        # Estado actual detallado
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7B88A0; font-style: italic; font-size: 11px;")
        layout.addWidget(self.status_label)

        # Botones (ocultos inicialmente)
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(10)

        self.btn_retry = QPushButton(tr("Reintentar"))
        self.btn_retry.setFixedSize(130, 38)
        apply_btn_primary(self.btn_retry)
        self.btn_retry.clicked.connect(self._on_retry)
        self.btn_retry.hide()

        self.btn_cancel = QPushButton(tr("Cancelar"))
        self.btn_cancel.setFixedSize(130, 38)
        apply_btn_cancel(self.btn_cancel)
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
        for indicator in self.step_indicators:
            if indicator.stage_id < self.current_stage:
                indicator.set_state(StepIndicator.STATE_COMPLETED)
            elif indicator.stage_id == self.current_stage:
                if self.current_stage == self.STAGE_ERROR:
                    indicator.set_state(StepIndicator.STATE_ERROR)
                else:
                    indicator.set_state(StepIndicator.STATE_ACTIVE)
            else:
                indicator.set_state(StepIndicator.STATE_PENDING)

        # Actualizar barra de progreso
        if self.current_stage >= 0:
            progress = min(100, (self.current_stage + 1) * 20)
            self.progress_bar.setValue(progress)

        # Color de la barra según estado
        if self.current_stage == self.STAGE_ERROR:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 3px;
                    background-color: #3B4252;
                }
                QProgressBar::chunk {
                    background-color: #BF616A;
                    border-radius: 3px;
                }
            """)
        elif self.current_stage == self.STAGE_COMPLETED:
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    border-radius: 3px;
                    background-color: #3B4252;
                }
                QProgressBar::chunk {
                    background-color: #A3BE8C;
                    border-radius: 3px;
                }
            """)

    def set_stage(self, stage, status_text=""):
        """Establece la etapa actual"""
        self.current_stage = stage
        self.status_label.setText(status_text)

        titles = {
            self.STAGE_PREPARING: tr("Preparando impresión..."),
            self.STAGE_SENDING: tr("Enviando a impresora..."),
            self.STAGE_IN_QUEUE: tr("Documento en cola..."),
            self.STAGE_PRINTING: tr("Imprimiendo documento..."),
            self.STAGE_COMPLETED: tr("Impresión completada"),
            self.STAGE_ERROR: tr("Error de impresión")
        }
        self.title_label.setText(titles.get(stage, tr("Procesando...")))
        self._update_stage_display()

    def start_monitoring(self, printer_name, job_id, pdf_path):
        """Inicia el monitoreo del trabajo de impresión"""
        self.printer_name = printer_name
        self.job_id = job_id
        self.pdf_path = pdf_path
        self.check_count = 0

        self.set_stage(self.STAGE_IN_QUEUE, tr("Trabajo #{job_id} en cola", job_id=job_id))

        # Iniciar timer de monitoreo (cada 500ms)
        self.monitor_timer.start(500)

    def _check_job_status(self):
        """Verifica el estado del trabajo en la cola de Windows"""
        self.check_count += 1

        if self.check_count > self.max_checks:
            self.monitor_timer.stop()
            self._show_error(tr("Tiempo de espera agotado. La impresora no responde."))
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
                            self._show_error(tr("Error en la impresora"))
                            return

                        if status & self.JOB_STATUS_OFFLINE:
                            self.set_stage(self.STAGE_IN_QUEUE, tr("Impresora desconectada - esperando..."))
                            return

                        if status & self.JOB_STATUS_PAPEROUT:
                            self.set_stage(self.STAGE_IN_QUEUE, tr("Sin papel - esperando..."))
                            return

                        if status & self.JOB_STATUS_USER_INTERVENTION:
                            self.set_stage(self.STAGE_IN_QUEUE, tr("Requiere atención - verificar impresora"))
                            return

                        if status & self.JOB_STATUS_PAUSED:
                            self.set_stage(self.STAGE_IN_QUEUE, tr("Trabajo pausado"))
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
                            self.set_stage(self.STAGE_SENDING, tr("Procesando documento..."))
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
                self._show_error(tr("Error al verificar estado: {error}", error=e))

    def _get_status_text(self, status):
        """Convierte el código de estado a texto legible"""
        if status == 0:
            return tr("En cola - esperando impresora")

        texts = []
        if status & self.JOB_STATUS_PRINTING:
            texts.append(tr("Imprimiendo"))
        if status & self.JOB_STATUS_SPOOLING:
            texts.append(tr("Procesando"))
        if status & self.JOB_STATUS_PAUSED:
            texts.append(tr("Pausado"))
        if status & self.JOB_STATUS_ERROR:
            texts.append(tr("Error"))
        if status & self.JOB_STATUS_OFFLINE:
            texts.append(tr("Impresora desconectada"))
        if status & self.JOB_STATUS_PAPEROUT:
            texts.append(tr("Sin papel"))
        if status & self.JOB_STATUS_PRINTED:
            texts.append(tr("Impreso"))
        if status & self.JOB_STATUS_COMPLETE:
            texts.append(tr("Completado"))

        return " - ".join(texts) if texts else tr("Procesando...")

    def _show_success(self):
        """Muestra el estado de éxito"""
        self.set_stage(self.STAGE_COMPLETED, "")
        self.progress_bar.setValue(100)
        self.title_label.setStyleSheet("color: #A3BE8C;")
        self.status_label.setText(tr("El documento se ha impreso correctamente"))

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
        self.title_label.setText(tr("Error de impresión"))
        self.title_label.setStyleSheet("color: #BF616A;")
        self.status_label.setText(message)
        self._update_stage_display()

        # Mostrar botones
        self.btn_retry.show()
        self.btn_cancel.show()

    def _on_retry(self):
        """Maneja el botón de reintentar"""
        self.btn_retry.hide()
        self.btn_cancel.hide()
        self.title_label.setStyleSheet("color: #ECEFF4;")

        # Reiniciar estado
        self.current_stage = self.STAGE_PREPARING
        self.check_count = 0
        self._update_stage_display()

        # Resetear barra de progreso al estilo normal
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 3px;
                background-color: #3B4252;
            }
            QProgressBar::chunk {
                background-color: #5E81AC;
                border-radius: 3px;
            }
        """)

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
