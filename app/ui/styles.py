"""Módulo de estilos unificados para la aplicación (Nord Theme)"""

import qtawesome as qta
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QApplication
from app.utils.logger import logger

# DEBUG: Confirmar que este archivo se está cargando
logger.debug("Cargando versión actualizada con botones transparentes")

# ============================================================
# PALETA DE COLORES NORD (Profesional, Mate, Elegante)
# ============================================================

# Nord Polar Night (Fondos Oscuros)
NORD0 = "#2E3440"
NORD1 = "#3B4252"
NORD2 = "#434C5E"
NORD3 = "#4C566A"

# Nord Snow Storm (Fondos Claros / Texto)
NORD4 = "#D8DEE9"
NORD5 = "#E5E9F0"
NORD6 = "#ECEFF4"

# Nord Frost (Acentos Azules/Cian)
NORD7 = "#8FBCBB" # Verde azulado
NORD8 = "#88C0D0" # Cian claro
NORD9 = "#81A1C1" # Azul glaciar
NORD10 = "#5E81AC" # Azul profundo (Primary)

# Nord Aurora (Colores Funcionales)
NORD11 = "#BF616A" # Rojo (Danger)
NORD12 = "#D08770" # Naranja
NORD13 = "#EBCB8B" # Amarillo (Warning)
NORD14 = "#A3BE8C" # Verde (Success)
NORD15 = "#B48EAD" # Violeta

# Asignación de Roles
PRIMARY_COLOR = NORD10
PRIMARY_HOVER = NORD9
PRIMARY_PRESSED = "#4C6B91" # Darker NORD10
PRIMARY_TEXT = "#ffffff"

SUCCESS_COLOR = NORD14
SUCCESS_HOVER = "#8FBC8B" # Slightly darker/saturated variant
SUCCESS_TEXT = "#2E3440" # Nord dark text for contrast on light green

WARNING_COLOR = NORD13
WARNING_HOVER = "#D1B174"
WARNING_TEXT = "#2E3440"

DANGER_COLOR = NORD11
DANGER_HOVER = "#A64F58"
DANGER_TEXT = "#ffffff"

INFO_COLOR = NORD8
INFO_HOVER = NORD7
INFO_TEXT = "#2E3440"

# Altura estándar global para inputs y botones
COMMON_HEIGHT = "42px"

# Definición de Temas
THEMES = {
    "dark": {
        "bg_main": NORD0,
        "bg_secondary": NORD1,
        "bg_tertiary": NORD2,
        "bg_input": NORD1,     # Inputs un poco más claros que el fondo base, o igual
        "bg_selected": NORD3,
        "text_main": NORD6,
        "text_secondary": NORD4,
        "text_disabled": NORD3,
        "border": NORD2,
        "border_focus": NORD9,
        "neutral_btn_bg": NORD2,
        "neutral_btn_hover": NORD3,
        "neutral_btn_text": NORD6,
        "cancel_btn_bg": NORD2,
        "cancel_btn_hover": NORD3,
        "bg_header": "#252526",
    },
    "light": {
        "bg_main": NORD6,      # Snow Storm White
        "bg_secondary": NORD5, # Slightly darker
        "bg_tertiary": NORD4,
        "bg_input": "#FFFFFF",
        "bg_selected": NORD4,
        "text_main": NORD0,
        "text_secondary": NORD2,
        "text_disabled": NORD3,
        "border": "#D8DEE9", # NORD4
        "border_focus": NORD10,
        "neutral_btn_bg": NORD4,
        "neutral_btn_hover": "#C8D0E0",
        "neutral_btn_text": NORD0,
        "cancel_btn_bg": "#D8DEE9",
        "cancel_btn_hover": "#C2CBD9",
        "bg_header": "#FFFFFF",
    }
}

# Icon color helper
def get_icon_color(theme_name):
    return NORD4 if theme_name == "dark" else NORD2

# ============================================================
# HELPERS DE INSTALACIÓN DE TEMA
# ============================================================

def apply_theme(app: QApplication, theme_name: str = "dark"):
    """Aplica el tema seleccionado a la aplicación (Palette + Stylesheet)"""
    
    # Fallback si el tema no existe
    if theme_name not in THEMES:
        theme_name = "dark"
        
    theme = THEMES[theme_name]
    
    # 1. Configurar QPalette
    palette = QPalette()
    
    c_bg_main = QColor(theme["bg_main"])
    c_bg_sec = QColor(theme["bg_secondary"])
    c_text_main = QColor(theme["text_main"])
    c_text_sec = QColor(theme["text_secondary"])
    c_bg_input = QColor(theme["bg_input"])
    c_border = QColor(theme["border"])
    c_selected = QColor(theme["bg_selected"])
    
    palette.setColor(QPalette.Window, c_bg_main)
    palette.setColor(QPalette.WindowText, c_text_main)
    palette.setColor(QPalette.Base, c_bg_input)
    palette.setColor(QPalette.AlternateBase, c_bg_sec)
    palette.setColor(QPalette.ToolTipBase, c_bg_sec)
    palette.setColor(QPalette.ToolTipText, c_text_main)
    palette.setColor(QPalette.Text, c_text_main)
    palette.setColor(QPalette.Button, c_bg_sec)
    palette.setColor(QPalette.ButtonText, c_text_main)
    palette.setColor(QPalette.BrightText, QColor("#ffffff"))
    palette.setColor(QPalette.Link, QColor(NORD9))
    palette.setColor(QPalette.Highlight, c_selected)
    palette.setColor(QPalette.HighlightedText, c_text_main)
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(theme["text_disabled"]))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(theme["text_disabled"]))

    app.setPalette(palette)
    app.setStyle("Fusion") 

    # 2. Generar Stylesheet Global
    stylesheet = _generate_stylesheet(theme)
    app.setStyleSheet(stylesheet)
    
    app.setProperty("theme", theme_name)


def _generate_stylesheet(t):
    """Genera la hoja de estilos CSS basada en el diccionario de tema"""
    return f"""
    /* ===== ESTILOS GLOBALES ===== */
    QWidget {{
        background-color: {t["bg_main"]};
        color: {t["text_main"]};
        font-family: "Segoe UI", sans-serif;
        font-size: 14px; /* Un poco más grande para legibilidad */
    }}

    /* ===== HEADER ===== */
    QWidget#header {{
        background-color: {t["bg_header"]};
        border-bottom: 1px solid {t["border"]};
    }}

    /* ===== VENTANAS Y DIÁLOGOS ===== */
    QMainWindow, QDialog {{
        background-color: {t["bg_main"]};
    }}

    /* ===== SIDEBAR & NAVIGATION ===== */
    QWidget#sidebar {{
        background-color: {t["bg_secondary"]};
        border-right: 1px solid {t["border"]};
    }}

    /* Sidebar Title */
    QLabel#sidebarTitle {{
        color: {t["text_secondary"]};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 2px;
        text-transform: uppercase;
        padding: 22px 20px 10px 20px;
        border-bottom: 1px solid {t["border"]};
        margin: 0;
    }}

    /* Sidebar Divider */
    QFrame#divider {{
        background-color: {t["border"]};
        min-height: 1px;
        max-height: 1px;
        margin: 10px 18px;
        border-radius: 1px;
    }}

    /* Container for buttons in ScrollArea */
    QWidget#navContainer {{
        background: transparent;
        border: none;
    }}

    /* Sidebar Buttons */
    QPushButton#navButton {{
        background-color: transparent;
        color: {t["text_secondary"]};
        text-align: left;
        padding: 14px 20px;
        border: none;
        border-radius: 12px;
        margin: 6px 12px;
        font-size: 15px;
        font-weight: 600;
        min-height: 46px;
    }}

    QPushButton#navButton:hover {{
        background-color: {t["bg_tertiary"]};
        color: {t["text_main"]};
        border: 2px solid {t["border"]};
        padding: 12px 18px;
    }}
    
    QPushButton#navButton:checked {{
        background-color: rgba(136, 192, 208, 0.15);
        color: #88C0D0;
        border: 2px solid #88C0D0;
        border-radius: 12px;
        padding: 12px 18px;
        font-weight: bold;
    }}

    /* ===== FRAMES & PANELS (GENERIC) ===== */
    QFrame#panel {{
        background-color: {t["bg_secondary"]};
        border-right: 1px solid {t["border"]};
    }}
    
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{ /* Lines */
        color: {t["border"]};
    }}

    /* ===== LABELS ===== */
    QLabel {{
        background-color: transparent;
        color: {t["text_main"]};
        border: none;
    }}
    
    QLabel#subtitle, QLabel#infoLabel {{
        color: {t["text_secondary"]};
    }}

    /* ===== GROUP BOXES ===== */
    QGroupBox {{
        background-color: {t["bg_secondary"]};
        border: 1px solid {t["border"]};
        border-radius: 8px;
        margin-top: 20px;
        padding: 24px 12px 12px 12px;
        font-weight: bold;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        left: 12px;
        top: 2px;
        padding: 2px 8px;
        background-color: {t["bg_secondary"]}; 
        color: {PRIMARY_COLOR};
    }}

    /* ===== INPUTS & CONTROLS (UNIFIED HEIGHT) ===== */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QTimeEdit, QComboBox {{
        background-color: {t["bg_input"]};
        border: 1px solid {t["border"]};
        border-radius: 6px;
        padding: 0 12px; /* Padding horizontal */
        color: {t["text_main"]};
        selection-background-color: {t["bg_selected"]};
        selection-color: {t["text_main"]};
        min-height: {COMMON_HEIGHT}; /* ALTURA ESTÁNDAR 42px */
    }}

    QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 2px solid {t["border_focus"]};
        padding: 0 11px; /* Ajuste por borde */
    }}
    
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QLineEdit[readOnly="true"] {{
        background-color: {t["bg_tertiary"]}; /* Light Mode: Gray, Dark Mode: Darker Gray */
        color: {t["text_disabled"]};      /* Light Mode: Dark Gray, Dark Mode: Light Gray */
        border-color: {t["border"]};
    }}

    /* ===== DROPDOWNS ===== */
    QComboBox::drop-down {{
        border: none;
        width: 30px;
    }}
    
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {t["text_secondary"]};
        margin-right: 10px;
    }}

    /* ===== BOTONES (GLOBAL DEFAULT) ===== */
    /* Botones primarios con borde turquesa */
    QPushButton {{
        min-height: {COMMON_HEIGHT};
        border-radius: 6px;
        padding: 0 16px;
        font-weight: 600;
        background-color: transparent;
        color: {NORD8}; /* Texto turquesa */
        border: 2px solid {NORD8}; /* Borde turquesa */
    }}
    
    QPushButton:hover {{
        background-color: rgba(136, 192, 208, 0.1); /* Fondo turquesa suave al hover */
        border: 2px solid {NORD8};
    }}
    
    QPushButton:pressed {{
        background-color: rgba(136, 192, 208, 0.2);
    }}
    
    /* Botones de cancelar - sin fondo, marco gris */
    QPushButton[objectName="cancelButton"],
    QPushButton[text="Cancelar"],
    QPushButton[text="Cancel"] {{
        background-color: transparent;
        color: {t["text_secondary"]};
        border: 2px solid #5E6B7D; /* Gris más claro que border normal */
    }}
    
    QPushButton[objectName="cancelButton"]:hover,
    QPushButton[text="Cancelar"]:hover,
    QPushButton[text="Cancel"]:hover {{
        background-color: rgba(94, 107, 125, 0.1);
        color: {t["text_main"]};
        border: 2px solid #6E7B8D;
    }}
    
    /* ===== TABLAS ===== */
    QTableWidget, QTableView {{
        background-color: {t["bg_input"]};
        alternate-background-color: {t["bg_secondary"]};
        gridline-color: {t["border"]};
        border: 1px solid {t["border"]};
        border-radius: 6px;
    }}

    QHeaderView::section {{
        background-color: {t["bg_tertiary"]};
        color: {t["text_main"]};
        padding: 10px;
        border: none;
        border-bottom: 2px solid {t["border"]};
        font-weight: bold;
    }}
    
    QTableCornerButton::section {{
        background-color: {t["bg_tertiary"]};
        border: 1px solid {t["border"]};
    }}

    /* ===== PESTAÑAS (TABS) ===== */
    QTabWidget::pane {{
        border: 1px solid {t["border"]};
        background-color: {t["bg_main"]};
        border-radius: 6px;
    }}

    QTabBar::tab {{
        background-color: {t["bg_tertiary"]};
        color: {t["text_main"]};
        padding: 10px 25px;
        margin-right: 4px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        font-weight: 600;
        min-width: 120px;
    }}

    QTabBar::tab:selected {{
        background-color: {t["bg_main"]};
        color: {NORD8}; /* Bright Cyan for better visibility */
        border-bottom: 3px solid {NORD8};
    }}

    QTabBar::tab:hover {{
        background-color: {t["bg_selected"]};
        color: {t["text_main"]};
    }}
    
    /* ===== MENUS ===== */
    QMenu {{
        background-color: {t["bg_secondary"]};
        border: 1px solid {t["border"]};
        padding: 5px 0;
        border-radius: 6px;
    }}
    
    QMenu::item {{
        padding: 8px 30px 8px 20px;
        background-color: transparent;
        color: {t["text_main"]};
    }}
    
    QMenu::item:selected {{
        background-color: {t["bg_selected"]};
    }}
    
    QMenuBar {{
        background-color: {t["bg_secondary"]};
        border-bottom: 1px solid {t["border"]};
    }}
    
    QMenuBar::item:selected {{
        background-color: {t["bg_tertiary"]};
    }}

    /* ===== SCROLLBARS ===== */
    QScrollBar:vertical {{
        background-color: {t["bg_main"]};
        width: 14px;
    }}
    
    QScrollBar::handle:vertical {{
        background-color: {t["border"]};
        min-height: 20px;
        border-radius: 7px;
        border: 3px solid {t["bg_main"]};
    }}
    
    QScrollBar::handle:vertical:hover {{
        background-color: {t["text_secondary"]};
    }}
    
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0px; }}

    /* ===== MESSAGE BOX ===== */
    QMessageBox {{
        background-color: {t["bg_main"]};
    }}
    
    /* ===== CHECKBOX / RADIO ===== */
    QRadioButton, QCheckBox {{
        spacing: 8px;
        color: {t["text_main"]};
    }}
    
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 18px; 
        height: 18px;
        border: 1px solid {t["border"]};
        background-color: {t["bg_input"]};
        border-radius: 4px;
    }}
    
    QRadioButton::indicator {{
        border-radius: 10px;
    }}
    
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {NORD10};
        border-color: {NORD10};
        image: url("no-image-handled-by-qt");
    }}
    """

# ============================================================
# HELPERS DE ICONOS
# ============================================================

def app_icon(name, color=None, size=18):
    normalized = name
    if name.startswith("fa."):
        normalized = f"fa5s.{name[3:]}"
    elif "." not in name:
        normalized = f"fa5s.{name}"
        
    if color is None:
        color = "#808080" # Default neutral
        
    return qta.icon(normalized, color=color, scale_factor=size / 16)


# ============================================================
# HELPERS DE BOTONES (Nord Style - 42px)
# ============================================================

_BTN_COMMON = """
QPushButton {{
    background-color: transparent !important;
    color: {text};
    border: 2px solid {border};
    border-radius: 6px;
    padding: 0 16px;
    font-size: 14px;
    font-weight: 600;
    min-height: {height};
}}
QPushButton:hover {{
    background-color: {hover_bg} !important;
    border: 2px solid {border};
}}
QPushButton:pressed {{
    background-color: {pressed_bg} !important;
}}
QPushButton:disabled {{
    background-color: transparent !important;
    color: #5E6B7D;
    border: 2px solid #4C566A;
}}
"""

def set_btn_primary(btn):
    css = _BTN_COMMON.format(
        border=PRIMARY_COLOR,
        text=PRIMARY_COLOR, 
        hover_bg="rgba(94, 129, 172, 0.1)",
        pressed_bg="rgba(94, 129, 172, 0.2)",
        height=COMMON_HEIGHT
    )
    logger.debug(f"set_btn_primary CSS:\n{css}")
    btn.setStyleSheet(css)

def set_btn_success(btn):
    btn.setStyleSheet(_BTN_COMMON.format(
        border=SUCCESS_COLOR,
        text=SUCCESS_COLOR,
        hover_bg="rgba(163, 190, 140, 0.1)",
        pressed_bg="rgba(163, 190, 140, 0.2)",
        height=COMMON_HEIGHT
    ))

def set_btn_warning(btn):
    btn.setStyleSheet(_BTN_COMMON.format(
        border=WARNING_COLOR,
        text=WARNING_COLOR,
        hover_bg="rgba(235, 203, 139, 0.1)",
        pressed_bg="rgba(235, 203, 139, 0.2)",
        height=COMMON_HEIGHT
    ))

def set_btn_danger(btn):
    btn.setStyleSheet(_BTN_COMMON.format(
        border=DANGER_COLOR,
        text=DANGER_COLOR,
        hover_bg="rgba(191, 97, 106, 0.1)",
        pressed_bg="rgba(191, 97, 106, 0.2)",
        height=COMMON_HEIGHT
    ))

def set_btn_info(btn):
    btn.setStyleSheet(_BTN_COMMON.format(
        border=INFO_COLOR,
        text=INFO_COLOR,
        hover_bg="rgba(129, 161, 193, 0.1)",
        pressed_bg="rgba(129, 161, 193, 0.2)",
        height=COMMON_HEIGHT
    ))

def set_btn_secondary(btn):
    # Neutral button
    btn.setStyleSheet(_BTN_COMMON.format(
        border="#5E6B7D",
        text="#D8DEE9",
        hover_bg="rgba(94, 107, 125, 0.1)",
        pressed_bg="rgba(94, 107, 125, 0.2)",
        height=COMMON_HEIGHT
    ))

def set_btn_cancel(btn):
    # Cancel button (gris más claro)
    btn.setStyleSheet(_BTN_COMMON.format(
        border="#5E6B7D",
        text="#D8DEE9",
        hover_bg="rgba(94, 107, 125, 0.1)",
        pressed_bg="rgba(94, 107, 125, 0.2)",
        height=COMMON_HEIGHT
    ))


# ============================================================
# HELPERS DE ACCIONES COMPACTAS
# Este tipo de botones son pequeños por definición (iconos en tablas)
# ============================================================

_ACTION_BTN = """
QPushButton {{
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 0;
}}
QPushButton:hover {{
    background-color: rgba(136, 192, 208, 0.2);
}}
"""

def _set_action_icon(btn, icon_name, color):
    btn.setStyleSheet(_ACTION_BTN)
    btn.setFixedSize(36, 36)
    btn.setIcon(app_icon(icon_name, color=color, size=16))
    btn.setIconSize(QSize(16, 16))

def estilizar_btn_ver(btn):
    _set_action_icon(btn, "fa5s.eye", NORD15)

def estilizar_btn_editar(btn):
    _set_action_icon(btn, "fa5s.edit", PRIMARY_COLOR)

def estilizar_btn_eliminar(btn):
    _set_action_icon(btn, "fa5s.trash", DANGER_COLOR)

def estilizar_btn_imprimir(btn):
    _set_action_icon(btn, "fa5s.print", SUCCESS_COLOR)

def estilizar_btn_estado(btn):
    _set_action_icon(btn, "fa5s.sync-alt", WARNING_COLOR)

def estilizar_btn_password(btn):
    _set_action_icon(btn, "fa5s.key", WARNING_COLOR)

def estilizar_btn_activar(btn):
    _set_action_icon(btn, "fa5s.check-circle", SUCCESS_COLOR)

def estilizar_btn_desactivar(btn):
    _set_action_icon(btn, "fa5s.times-circle", DANGER_COLOR)

def estilizar_btn_descargar(btn):
    _set_action_icon(btn, "fa5s.download", PRIMARY_COLOR)

def estilizar_btn_permisos(btn):
    _set_action_icon(btn, "fa5s.shield-alt", PRIMARY_COLOR)

def estilizar_btn_factura(btn):
    _set_action_icon(btn, "fa5s.file-invoice-dollar", NORD8)  # Cian para factura
