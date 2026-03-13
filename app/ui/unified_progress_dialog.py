"""
Diálogo unificado de progreso para operaciones de guardado e impresión.
Una sola ventana que maneja todo el proceso con monitoreo en tiempo real.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont
import platform
import os
from app.utils.logger import logger
from app.i18n import tr


class UnifiedProgressDialog(QDialog):
    """
    Diálogo unificado que maneja:
    - Modo COMPLETO: Guardar → Generar PDF → Imprimir → Monitorear
    - Modo SOLO_IMPRIMIR: Imprimir → Monitorear
    """

    # Modos de operación
    MODE_FULL = "full"  # Guardar + PDF + Imprimir
    MODE_PRINT_ONLY = "print_only"  # Solo imprimir

    # Estados
    STATE_IDLE = 0
    STATE_SAVING = 1
    STATE_GENERATING_PDF = 2
    STATE_SENDING = 3
    STATE_IN_QUEUE = 4
    STATE_PRINTING = 5
    STATE_COMPLETED = 6
    STATE_ERROR = -1

    # Constantes de Windows para estado de impresión
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

    def __init__(self, parent=None, mode=MODE_FULL, title=None):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle(title or tr("Procesando"))
        self.setModal(True)
        self.setFixedSize(500, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        # Estado interno
        self.current_state = self.STATE_IDLE
        self.printer_name = None
        self.job_id = None
        self.pdf_path = None
        self.delete_after = True
        self.error_message = None

        # Callbacks para operaciones
        self.save_callback = None  # Función que guarda y retorna ID
        self.pdf_callback = None   # Función que genera PDF y retorna path
        self.saved_id = None       # ID retornado por save_callback
        self.save_completed = False  # Flag: indica si ya se guardó en BD

        # Configuración de impresora
        self.duplex_enabled = False
        self.es_ticket = False

        # Timer para monitoreo
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self._check_print_status)
        self.check_count = 0
        self.max_checks = 240  # 2 minutos

        # Resultado de la operación
        self.operation_success = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Título
        self.title_label = QLabel(tr("Iniciando..."))
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
                border: 2px solid #4C566A;
                border-radius: 12px;
                background-color: #3B4252;
            }
            QProgressBar::chunk {
                background-color: #5E81AC;
                border-radius: 10px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Frame de etapas
        stages_frame = QFrame()
        stages_frame.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px; padding: 10px;")
        stages_layout = QVBoxLayout(stages_frame)
        stages_layout.setSpacing(8)

        # Definir etapas según el modo
        self.stage_labels = []

        if self.mode == self.MODE_FULL:
            stages = [
                (tr("1. Guardando en base de datos"), self.STATE_SAVING),
                (tr("2. Generando documento PDF"), self.STATE_GENERATING_PDF),
                (tr("3. Enviando a impresora"), self.STATE_SENDING),
                (tr("4. En cola de impresión"), self.STATE_IN_QUEUE),
                (tr("5. Imprimiendo"), self.STATE_PRINTING),
                (tr("6. Completado"), self.STATE_COMPLETED)
            ]
        else:  # MODE_PRINT_ONLY
            stages = [
                (tr("1. Enviando a impresora"), self.STATE_SENDING),
                (tr("2. En cola de impresión"), self.STATE_IN_QUEUE),
                (tr("3. Imprimiendo"), self.STATE_PRINTING),
                (tr("4. Completado"), self.STATE_COMPLETED)
            ]

        for text, state_id in stages:
            label = QLabel(text)
            label.setFont(QFont("", 10))
            label.state_id = state_id
            label.original_text = text
            self.stage_labels.append(label)
            stages_layout.addWidget(label)

        layout.addWidget(stages_frame)

        # Estado detallado
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #4C566A; font-style: italic;")
        layout.addWidget(self.status_label)

        # Botones (ocultos inicialmente)
        self.buttons_layout = QHBoxLayout()
        self.buttons_layout.setSpacing(10)

        self.btn_retry = QPushButton("Reintentar")
        self.btn_retry.setFixedSize(120, 35)
        self.btn_retry.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #5E81AC;
                border: 2px solid #5E81AC;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(94, 129, 172, 40); color: #5E81AC; border: 2px solid #5E81AC; }
        """)
        self.btn_retry.clicked.connect(self._on_retry)
        self.btn_retry.hide()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setFixedSize(120, 35)
        self.btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #BF616A;
                border: 2px solid #BF616A;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(191, 97, 106, 40); color: #BF616A; border: 2px solid #BF616A; }
        """)
        self.btn_cancel.clicked.connect(self._on_cancel)
        self.btn_cancel.hide()

        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.btn_retry)
        self.buttons_layout.addWidget(self.btn_cancel)
        self.buttons_layout.addStretch()
        layout.addLayout(self.buttons_layout)

    def _update_display(self):
        """Actualiza la visualización de las etapas"""
        total_stages = len(self.stage_labels)
        current_index = 0

        for i, label in enumerate(self.stage_labels):
            if label.state_id < self.current_state:
                # Completada
                label.setStyleSheet("color: #A3BE8C; font-weight: bold;")
                text = label.original_text
                num = text.split(".")[0]
                rest = text.split(".", 1)[1] if "." in text else text
                label.setText(f"✓{rest}")
                current_index = i + 1
            elif label.state_id == self.current_state:
                # Actual
                if self.current_state == self.STATE_ERROR:
                    label.setStyleSheet("color: #BF616A; font-weight: bold;")
                else:
                    label.setStyleSheet("color: #5E81AC; font-weight: bold;")
                current_index = i
            else:
                # Pendiente
                label.setStyleSheet("color: #7B88A0;")
                label.setText(label.original_text)

        # Barra de progreso
        if self.current_state >= 0 and total_stages > 0:
            progress = int((current_index / total_stages) * 100)
            self.progress_bar.setValue(min(100, progress))

        # Color de barra según estado
        if self.current_state == self.STATE_ERROR:
            self.progress_bar.setStyleSheet(self._get_progress_style("#BF616A"))
        elif self.current_state == self.STATE_COMPLETED:
            self.progress_bar.setStyleSheet(self._get_progress_style("#A3BE8C"))
            self.progress_bar.setValue(100)
        else:
            self.progress_bar.setStyleSheet(self._get_progress_style("#5E81AC"))

    def _get_progress_style(self, color):
        return f"""
            QProgressBar {{
                border: 2px solid #4C566A;
                border-radius: 12px;
                background-color: #3B4252;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 10px;
            }}
        """

    def set_state(self, state, status_text=""):
        """Establece el estado actual"""
        self.current_state = state
        self.status_label.setText(status_text)

        titles = {
            self.STATE_SAVING: "Guardando...",
            self.STATE_GENERATING_PDF: "Generando PDF...",
            self.STATE_SENDING: "Enviando a impresora...",
            self.STATE_IN_QUEUE: "En cola de impresión...",
            self.STATE_PRINTING: "Imprimiendo...",
            self.STATE_COMPLETED: "¡Completado!",
            self.STATE_ERROR: "Error"
        }
        self.title_label.setText(titles.get(state, "Procesando..."))
        self._update_display()

    # === Configuración ===

    def set_save_callback(self, callback):
        """Establece la función que guarda en BD y retorna el ID"""
        self.save_callback = callback

    def set_pdf_callback(self, callback):
        """Establece la función que genera el PDF y retorna el path"""
        self.pdf_callback = callback

    def set_pdf_path(self, path):
        """Establece el path del PDF directamente (para modo PRINT_ONLY)"""
        self.pdf_path = path

    def set_printer_config(self, printer_name, duplex=False, es_ticket=False):
        """Configura la impresora"""
        self.printer_name = printer_name
        self.duplex_enabled = duplex
        self.es_ticket = es_ticket

    def set_delete_after(self, delete):
        """Si debe borrar el PDF después de imprimir"""
        self.delete_after = delete

    # === Ejecución ===

    def execute(self):
        """
        Ejecuta toda la operación y retorna True si fue exitosa.
        Este método bloquea hasta que la operación termine.
        """
        # Iniciar la operación
        QTimer.singleShot(100, self._start_operation)

        # Mostrar diálogo (bloquea)
        self.exec_()

        return self.operation_success

    def _start_operation(self):
        """Inicia la secuencia de operaciones"""
        try:
            if self.mode == self.MODE_FULL:
                self._do_save()
            else:
                self._do_print()
        except (OSError, ValueError, RuntimeError) as e:
            self._show_error(str(e))

    def _do_save(self):
        """Ejecuta el guardado en BD"""
        self.set_state(self.STATE_SAVING, "Guardando datos...")

        try:
            if self.save_callback:
                self.saved_id = self.save_callback()
                if not self.saved_id:
                    self._show_error("No se pudo guardar en la base de datos")
                    return
                # Marcar que ya se guardó en BD
                self.save_completed = True

            # Continuar con PDF
            QTimer.singleShot(100, self._do_generate_pdf)

        except (OSError, ValueError, RuntimeError) as e:
            self._show_error(f"Error al guardar: {str(e)}")

    def _do_generate_pdf(self):
        """Genera el PDF"""
        self.set_state(self.STATE_GENERATING_PDF, "Creando documento...")

        try:
            if self.pdf_callback:
                self.pdf_path = self.pdf_callback(self.saved_id)
                if not self.pdf_path:
                    self._show_error("No se pudo generar el documento PDF")
                    return

            # Continuar con impresión
            QTimer.singleShot(100, self._do_print)

        except (OSError, ValueError, RuntimeError) as e:
            self._show_error(f"Error al generar PDF: {str(e)}")

    def _do_print(self):
        """Envía a la impresora"""
        self.set_state(self.STATE_SENDING, "Enviando a impresora...")

        if not self.printer_name:
            self._show_error("No hay impresora configurada")
            return

        if not self.pdf_path or not os.path.exists(self.pdf_path):
            self._show_error("El archivo PDF no existe")
            return

        try:
            if platform.system() == 'Windows':
                result = self._print_windows()
                if result[0]:
                    self.job_id = result[1]
                    self._start_monitoring()
                else:
                    self._show_error("Error al enviar a la impresora")
            else:
                self._print_linux()

        except (OSError, ValueError, RuntimeError) as e:
            self._show_error(f"Error de impresión: {str(e)}")

    def _print_windows(self):
        """Imprime en Windows y retorna (success, job_id)"""
        try:
            import fitz
            import win32print
            import win32ui
            from PIL import Image, ImageWin
        except ImportError as e:
            return (False, None)

        doc = None
        hdc = None

        try:
            doc = fitz.open(self.pdf_path)
            num_pages = len(doc)

            if num_pages == 0:
                return (False, None)

            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(self.printer_name)

            printable_width = hdc.GetDeviceCaps(8)
            printable_height = hdc.GetDeviceCaps(10)
            printer_dpi_x = hdc.GetDeviceCaps(88)
            printer_dpi_y = hdc.GetDeviceCaps(90)

            job_id = hdc.StartDoc(os.path.basename(self.pdf_path))

            for page_num in range(num_pages):
                page = doc.load_page(page_num)
                pdf_width_pts = page.rect.width
                pdf_height_pts = page.rect.height

                pdf_width_inches = pdf_width_pts / 72.0
                pdf_height_inches = pdf_height_pts / 72.0

                target_width_px = int(pdf_width_inches * printer_dpi_x)
                target_height_px = int(pdf_height_inches * printer_dpi_y)

                zoom = printer_dpi_x / 72.0
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)

                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

                if img.width != target_width_px or img.height != target_height_px:
                    img = img.resize((target_width_px, target_height_px), Image.Resampling.LANCZOS)

                new_width, new_height = target_width_px, target_height_px

                if new_width > printable_width or new_height > printable_height:
                    scale = min(printable_width / new_width, printable_height / new_height)
                    new_width = int(new_width * scale)
                    new_height = int(new_height * scale)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                x_pos = (printable_width - new_width) // 2
                y_pos = 0 if self.es_ticket else (printable_height - new_height) // 2

                hdc.StartPage()
                dib = ImageWin.Dib(img)
                dib.draw(hdc.GetHandleOutput(), (x_pos, y_pos, x_pos + new_width, y_pos + new_height))
                hdc.EndPage()

            hdc.EndDoc()
            return (True, job_id)

        except Exception as e:
            # Capturar TODAS las excepciones para mejor diagnóstico
            logger.error(f"Error impresión: {type(e).__name__}: {e}")
            return (False, None)

        finally:
            if doc:
                doc.close()
            if hdc:
                try:
                    hdc.DeleteDC()
                except OSError:
                    pass

    def _print_linux(self):
        """Imprime en Linux"""
        import subprocess
        result = subprocess.call(['lp', '-d', self.printer_name, self.pdf_path])
        if result == 0:
            self._show_success()
        else:
            self._show_error("Error al enviar a la impresora")

    def _start_monitoring(self):
        """Inicia el monitoreo del trabajo de impresión"""
        self.set_state(self.STATE_IN_QUEUE, f"Trabajo #{self.job_id} en cola")
        self.check_count = 0
        self.monitor_timer.start(500)

    def _check_print_status(self):
        """Verifica el estado del trabajo en la cola de Windows"""
        self.check_count += 1

        if self.check_count > self.max_checks:
            self.monitor_timer.stop()
            self._show_error("Tiempo de espera agotado")
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

                        # Errores
                        if status & self.JOB_STATUS_ERROR:
                            self.monitor_timer.stop()
                            self._show_error("Error en la impresora")
                            return

                        if status & self.JOB_STATUS_OFFLINE:
                            self.set_state(self.STATE_IN_QUEUE, "Impresora desconectada...")
                            return

                        if status & self.JOB_STATUS_PAPEROUT:
                            self.set_state(self.STATE_IN_QUEUE, "Sin papel...")
                            return

                        if status & self.JOB_STATUS_USER_INTERVENTION:
                            self.set_state(self.STATE_IN_QUEUE, "Verificar impresora...")
                            return

                        # Completado
                        if status & self.JOB_STATUS_PRINTED or status & self.JOB_STATUS_COMPLETE:
                            self.monitor_timer.stop()
                            self._show_success()
                            return

                        # Imprimiendo
                        if status & self.JOB_STATUS_PRINTING:
                            self.set_state(self.STATE_PRINTING, "Imprimiendo documento...")
                            return

                        # En cola
                        self.set_state(self.STATE_IN_QUEUE, "Esperando impresora...")
                        break

                if not job_found:
                    # Trabajo terminado (ya no está en cola)
                    self.monitor_timer.stop()
                    self._show_success()

            finally:
                win32print.ClosePrinter(hPrinter)

        except Exception as e:
            logger.error(f"Error verificando cola: {e}")

    def _show_success(self):
        """Muestra éxito y cierra"""
        self.set_state(self.STATE_COMPLETED, "")
        self.title_label.setStyleSheet("color: #A3BE8C;")
        self.status_label.setText("Operación completada correctamente")
        self.operation_success = True

        # PDF se borra en closeEvent, no aquí
        # Cerrar automáticamente
        QTimer.singleShot(1500, self.accept)

    def _show_error(self, message):
        """Muestra error con opciones"""
        self.monitor_timer.stop()
        self.current_state = self.STATE_ERROR
        self.error_message = message
        self.title_label.setText("Error")
        self.title_label.setStyleSheet("color: #BF616A;")
        self.status_label.setText(message)
        self._update_display()

        self.btn_retry.show()
        self.btn_cancel.show()

    def _on_retry(self):
        """Reintenta la operación"""
        self.btn_retry.hide()
        self.btn_cancel.hide()
        self.title_label.setStyleSheet("")
        self.check_count = 0

        # Reiniciar desde impresión (no volver a guardar)
        if self.pdf_path and os.path.exists(self.pdf_path):
            self._do_print()
        else:
            self._show_error("El archivo PDF ya no existe")

    def _on_cancel(self):
        """Cancela la operación"""
        self.monitor_timer.stop()
        self.operation_success = False
        # PDF se borra en closeEvent, no aquí (permite reimprimir desde historial)
        self.reject()

    def closeEvent(self, event):
        """Al cerrar la ventana, borrar el PDF temporal"""
        self.monitor_timer.stop()
        
        # Borrar PDF temporal al cerrar la ventana
        if self.delete_after and self.pdf_path and os.path.exists(self.pdf_path):
            try:
                os.remove(self.pdf_path)
            except OSError:
                pass
        
        super().closeEvent(event)
