"""
Widget de paginación reutilizable para tablas.
Proporciona controles de navegación por páginas con info de registros.
"""
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QPushButton, QLabel,
                             QComboBox)
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from app.i18n import tr
from app.ui.styles import app_icon


class PaginationWidget(QWidget):
    """Widget de paginación con botones prev/next y selector de tamaño de página"""

    # Señal emitida cuando cambia la página: (offset, limit)
    page_changed = pyqtSignal(int, int)

    DEFAULT_PAGE_SIZE = 50
    PAGE_SIZE_OPTIONS = [25, 50, 100, 200]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_page = 0
        self._total_records = 0
        self._page_size = self.DEFAULT_PAGE_SIZE
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        # Info de registros (izquierda)
        self.info_label = QLabel()
        self.info_label.setStyleSheet("color: #D8DEE9; font-size: 12px;")
        layout.addWidget(self.info_label)

        layout.addStretch()

        # Selector de registros por página
        lbl_size = QLabel(tr("Mostrar") + ":")
        lbl_size.setStyleSheet("color: #D8DEE9; font-size: 12px;")
        layout.addWidget(lbl_size)

        self.page_size_combo = QComboBox()
        self.page_size_combo.setFixedWidth(70)
        for size in self.PAGE_SIZE_OPTIONS:
            self.page_size_combo.addItem(str(size), size)
        # Seleccionar el default
        idx = self.PAGE_SIZE_OPTIONS.index(self.DEFAULT_PAGE_SIZE)
        self.page_size_combo.setCurrentIndex(idx)
        self.page_size_combo.currentIndexChanged.connect(self._on_page_size_changed)
        layout.addWidget(self.page_size_combo)

        layout.addSpacing(15)

        # Botones de navegación con iconos qtawesome
        self.btn_first = QPushButton()
        self.btn_first.setIcon(app_icon("fa5s.angle-double-left", color="#88C0D0", size=14))
        self.btn_first.setIconSize(QSize(14, 14))
        self.btn_first.setFixedWidth(36)
        self.btn_first.setToolTip(tr("Primera página"))
        self.btn_first.clicked.connect(self._go_first)
        layout.addWidget(self.btn_first)

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(app_icon("fa5s.angle-left", color="#88C0D0", size=14))
        self.btn_prev.setIconSize(QSize(14, 14))
        self.btn_prev.setFixedWidth(36)
        self.btn_prev.setToolTip(tr("Anterior"))
        self.btn_prev.clicked.connect(self._go_prev)
        layout.addWidget(self.btn_prev)

        # Indicador de página
        self.page_label = QLabel("1 / 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setMinimumWidth(80)
        self.page_label.setStyleSheet("color: #ECEFF4; font-weight: bold; font-size: 12px;")
        layout.addWidget(self.page_label)

        self.btn_next = QPushButton()
        self.btn_next.setIcon(app_icon("fa5s.angle-right", color="#88C0D0", size=14))
        self.btn_next.setIconSize(QSize(14, 14))
        self.btn_next.setFixedWidth(36)
        self.btn_next.setToolTip(tr("Siguiente"))
        self.btn_next.clicked.connect(self._go_next)
        layout.addWidget(self.btn_next)

        self.btn_last = QPushButton()
        self.btn_last.setIcon(app_icon("fa5s.angle-double-right", color="#88C0D0", size=14))
        self.btn_last.setIconSize(QSize(14, 14))
        self.btn_last.setFixedWidth(36)
        self.btn_last.setToolTip(tr("Última página"))
        self.btn_last.clicked.connect(self._go_last)
        layout.addWidget(self.btn_last)

        self._update_ui()

    @property
    def total_pages(self):
        if self._total_records == 0:
            return 1
        return max(1, (self._total_records + self._page_size - 1) // self._page_size)

    @property
    def offset(self):
        return self._current_page * self._page_size

    @property
    def limit(self):
        return self._page_size

    def update_total(self, total_records):
        """Actualiza el total de registros y refresca la UI"""
        self._total_records = total_records
        # Si la página actual excede el total, ir a la última
        if self._current_page >= self.total_pages:
            self._current_page = max(0, self.total_pages - 1)
        self._update_ui()

    def reset(self):
        """Reinicia a la primera página"""
        self._current_page = 0
        self._update_ui()

    def _update_ui(self):
        total_pages = self.total_pages
        page_display = self._current_page + 1

        self.page_label.setText(f"{page_display} / {total_pages}")

        self.btn_first.setEnabled(self._current_page > 0)
        self.btn_prev.setEnabled(self._current_page > 0)
        self.btn_next.setEnabled(self._current_page < total_pages - 1)
        self.btn_last.setEnabled(self._current_page < total_pages - 1)

        # Info de registros
        if self._total_records == 0:
            self.info_label.setText(tr("Sin registros"))
        else:
            inicio = self._current_page * self._page_size + 1
            fin = min(inicio + self._page_size - 1, self._total_records)
            self.info_label.setText(
                f"{inicio}-{fin} {tr('de')} {self._total_records} {tr('registros')}"
            )

    def _go_first(self):
        self._current_page = 0
        self._emit_change()

    def _go_prev(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._emit_change()

    def _go_next(self):
        if self._current_page < self.total_pages - 1:
            self._current_page += 1
            self._emit_change()

    def _go_last(self):
        self._current_page = self.total_pages - 1
        self._emit_change()

    def _on_page_size_changed(self, index):
        new_size = self.page_size_combo.currentData()
        if new_size and new_size != self._page_size:
            self._page_size = new_size
            self._current_page = 0
            self._emit_change()

    def _emit_change(self):
        self._update_ui()
        self.page_changed.emit(self.offset, self.limit)
