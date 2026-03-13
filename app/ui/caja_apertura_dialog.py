"""
Diálogo para solicitar apertura de caja diaria
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
                             QPushButton, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QDate
from app.utils.notify import notify_warning, ask_confirm
from app.i18n import tr
from app.ui.transparent_buttons import apply_btn_success, apply_btn_cancel, apply_btn_info


class CajaAperturaDialog(QDialog):
    def __init__(self, fecha, es_primera_vez=False, parent=None):
        """
        Args:
            fecha: Fecha de la apertura (YYYY-MM-DD)
            es_primera_vez: Si True, es la primera venta ever (no cancelable)
            parent: Widget padre
        """
        super().__init__(parent)
        self.fecha = fecha
        self.es_primera_vez = es_primera_vez
        self.saldo_inicial = 0.0
        self.notas = ""
        self.saldo_sugerido = None

        self.setWindowTitle(tr("Apertura de Caja"))
        self.setModal(True)
        self.setMinimumWidth(500)

        # Si es primera vez, no se puede cerrar
        if es_primera_vez:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)

        # Obtener saldo sugerido del último cierre
        self.obtener_saldo_sugerido()

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)

        # Header con icono
        icon = QLabel("💰")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # Título
        title = QLabel(tr("Apertura de Caja"))
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Subtítulo
        if self.es_primera_vez:
            subtitle = QLabel(
                tr("Es necesario establecer el saldo inicial de caja") + "\\n" +
                tr("antes de realizar la primera venta del día.")
            )
        else:
            subtitle = QLabel(
                f"{tr('Registra el saldo inicial para el día')} {self.fecha}\\n"
                f"{tr('Este será el dinero con el que inicia la caja.')}"
            )
        subtitle.setStyleSheet("font-size: 12px; color: #D8DEE9;")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Info visual
        if self.es_primera_vez:
            info_frame = QLabel(
                "⚠️  " + tr("IMPORTANTE") + "\\n\\n" +
                tr("Esta es la primera operación del día.") + "\\n" +
                tr("Debes ingresar el saldo con el que abres la caja.")
            )
            info_frame.setStyleSheet("""
                background-color: rgba(235, 203, 139, 0.12);
                color: #EBCB8B;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid #EBCB8B;
                font-weight: bold;
            """)
            info_frame.setWordWrap(True)
            info_frame.setAlignment(Qt.AlignCenter)
            layout.addWidget(info_frame)
            layout.addSpacing(10)

        # Campo saldo inicial
        saldo_label = QLabel(tr("Saldo Inicial en Caja") + ":")
        saldo_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff;")
        layout.addWidget(saldo_label)

        self.saldo_input = QDoubleSpinBox()
        self.saldo_input.setMinimum(0)
        self.saldo_input.setMaximum(999999.99)
        self.saldo_input.setDecimals(2)
        self.saldo_input.setSuffix(" €")
        self.saldo_input.setValue(0.00)
        self.saldo_input.setMinimumHeight(45)
        self.saldo_input.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 18px;
                font-weight: bold;
                padding: 10px;
                background-color: #3B4252;
                color: #88C0D0;
                border: 2px solid #4C566A;
                border-radius: 5px;
            }
            QDoubleSpinBox:focus {
                border: 2px solid #88C0D0;
            }
        """)
        layout.addWidget(self.saldo_input)

        layout.addSpacing(5)

        # Sugerencia basada en último cierre
        if self.saldo_sugerido is not None:
            sugerencia_layout = QHBoxLayout()
            sugerencia_label = QLabel(f"💡 {tr('Último cierre')}: {self.saldo_sugerido:.2f} €")
            sugerencia_label.setStyleSheet("font-size: 12px; color: #88C0D0; font-style: italic;")
            sugerencia_layout.addWidget(sugerencia_label)

            btn_usar_sugerido = QPushButton(tr("Usar este saldo"))
            btn_usar_sugerido.clicked.connect(self.usar_saldo_sugerido)
            apply_btn_info(btn_usar_sugerido)
            sugerencia_layout.addWidget(btn_usar_sugerido)
            sugerencia_layout.addStretch()
            layout.addLayout(sugerencia_layout)
            layout.addSpacing(5)

        # Ayuda
        hint = QLabel(
            f"💡 {tr('Consejo')}: {tr('Cuenta el efectivo físico que hay en caja')}\\n"
            f"   ({tr('billetes + monedas + fondo de cambio')})"
        )
        hint.setStyleSheet("font-size: 11px; color: #7B88A0; font-style: italic;")
        layout.addWidget(hint)

        layout.addSpacing(10)

        # Notas opcionales
        notas_header = QHBoxLayout()
        notas_label = QLabel(tr("Notas / Observaciones (opcional)") + ":")
        notas_label.setStyleSheet("font-size: 12px; color: #D8DEE9;")
        notas_header.addWidget(notas_label)
        notas_header.addStretch()
        self.notas_contador = QLabel("0/500")
        self.notas_contador.setStyleSheet("font-size: 11px; color: #7B88A0;")
        notas_header.addWidget(self.notas_contador)
        layout.addLayout(notas_header)

        self.notas_input = QTextEdit()
        self.notas_input.setMaximumHeight(80)
        self.notas_input.setPlaceholderText(tr("Ej") + ": " + tr("Fondo inicial 100€, resto del cierre anterior") + "...")
        self.notas_input.textChanged.connect(self.actualizar_contador_notas)
        self.notas_input.setStyleSheet("""
            QTextEdit {
                background-color: #3B4252;
                color: #ECEFF4;
                border: 1px solid #4C566A;
                border-radius: 5px;
                padding: 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #88C0D0;
            }
        """)
        layout.addWidget(self.notas_input)

        layout.addSpacing(15)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        if not self.es_primera_vez:
            # Solo mostrar cancelar si NO es primera vez
            btn_cancelar = QPushButton(tr("Cancelar"))
            btn_cancelar.clicked.connect(self.reject)
            apply_btn_cancel(btn_cancelar)
            btn_layout.addWidget(btn_cancelar)

        btn_guardar = QPushButton(tr("Registrar Apertura"))
        btn_guardar.clicked.connect(self.guardar)
        apply_btn_success(btn_guardar)
        btn_layout.addWidget(btn_guardar)

        layout.addLayout(btn_layout)

        # Focus inicial en el input de saldo
        self.saldo_input.setFocus()
        self.saldo_input.selectAll()

    def obtener_saldo_sugerido(self):
        """Obtiene el saldo final del último cierre para sugerencia"""
        try:
            from app.db.database import Database
            db = Database()
            db.connect()

            # Buscar el último cierre
            ultimo_cierre = db.fetch_one("""
                SELECT saldo_final, fecha
                FROM caja_cierres
                ORDER BY fecha DESC, id DESC
                LIMIT 1
            """)

            if ultimo_cierre:
                self.saldo_sugerido = ultimo_cierre['saldo_final']

            db.disconnect()
        except (OSError, ValueError, RuntimeError) as e:
            # Si hay error, simplemente no mostrar sugerencia
            self.saldo_sugerido = None

    def usar_saldo_sugerido(self):
        """Aplica el saldo sugerido al campo de entrada"""
        if self.saldo_sugerido is not None:
            self.saldo_input.setValue(self.saldo_sugerido)

    def actualizar_contador_notas(self):
        """Actualiza el contador de caracteres y limita la longitud de notas"""
        MAX_CARACTERES = 500
        texto = self.notas_input.toPlainText()
        longitud = len(texto)

        if longitud > MAX_CARACTERES:
            # Truncar el texto
            cursor = self.notas_input.textCursor()
            pos = cursor.position()
            self.notas_input.setPlainText(texto[:MAX_CARACTERES])
            # Restaurar posición del cursor
            cursor.setPosition(min(pos, MAX_CARACTERES))
            self.notas_input.setTextCursor(cursor)
            longitud = MAX_CARACTERES

        # Actualizar contador con color según uso
        self.notas_contador.setText(f"{longitud}/{MAX_CARACTERES}")
        if longitud > MAX_CARACTERES * 0.9:  # >90% usado
            self.notas_contador.setStyleSheet("font-size: 11px; color: #BF616A; font-weight: bold;")
        elif longitud > MAX_CARACTERES * 0.7:  # >70% usado
            self.notas_contador.setStyleSheet("font-size: 11px; color: #EBCB8B;")
        else:
            self.notas_contador.setStyleSheet("font-size: 11px; color: #7B88A0;")

    def guardar(self):
        """Valida y guarda la apertura"""
        self.saldo_inicial = self.saldo_input.value()

        if self.saldo_inicial < 0:
            notify_warning(
                self,
                tr("Error"),
                tr("El saldo inicial no puede ser negativo.")
            )
            return

        # Advertencia si el saldo es 0
        if self.saldo_inicial == 0:
            respuesta = ask_confirm(self, tr("Confirmar Saldo Cero"), tr("¿Estás seguro de abrir la caja con saldo inicial de 0.00 €?") + "\\n\\n" +
                tr("Es recomendable tener un fondo de cambio."))
            if not respuesta:
                return

        self.notas = self.notas_input.toPlainText().strip()

        self.accept()

    def obtener_datos(self):
        """Retorna los datos de la apertura"""
        return {
            'saldo_inicial': self.saldo_inicial,
            'notas': self.notas
        }
