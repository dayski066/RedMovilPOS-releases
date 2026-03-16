"""
Ventana de inicio de sesión con sistema de configuración inicial
y recuperación de contraseña mediante llave maestra
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QFrame, QStackedWidget, QScrollArea,
                             QWidget, QTextEdit, QApplication)
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_success, apply_btn_cancel, apply_btn_warning
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
import os
from app.modules.auth_manager import AuthManager
from app.ui.password_strength_widget import PasswordStrengthWidget
from config import COMPANY_INFO, APP_VERSION, APP_NAME
from app.i18n import tr
from app.utils.notify import notify_success, notify_error, notify_warning
from datetime import datetime
from app.utils.logger import logger


class LoginDialog(QDialog):
    def __init__(self, db, auth_manager=None, parent=None, permitir_autologin=True):
        """
        Args:
            permitir_autologin: Si es True, intenta auto-login al abrir.
                               Pasar False cuando se cierra sesión desde dentro del programa.
        """
        super().__init__(parent)
        self.db = db
        self.auth_manager = auth_manager if auth_manager else AuthManager(db)
        self.usuario_logueado = None
        self.llave_generada = None  # Para mostrar al crear usuario
        self._pendiente_2fa = None  # Datos del usuario pendiente de verificación 2FA
        self.permitir_autologin = permitir_autologin
        self._setup_complete = False  # Guard para evitar que resizeEvent oculte el logo antes de mostrarse

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - Acceso")
        self.setModal(True)
        self.setWindowFlags(
            Qt.Dialog |
            Qt.WindowTitleHint |
            Qt.WindowCloseButtonHint
        )
        screen = QApplication.primaryScreen().availableGeometry()
        w = min(520, int(screen.width() * 0.85))
        h = min(580, int(screen.height() * 0.92))
        self.setFixedSize(w, h)
        
        self.setup_ui()
        
        # self.apply_styles() # Eliminado para permitir tema global
        
        # Detectar si hay usuarios
        if not self.auth_manager.hay_usuarios():
            self.mostrar_configuracion_inicial()
        else:
            self.mostrar_login()
            self.cargar_preferencias_login()
            
            # Marcar si se debe intentar auto-login al mostrar el diálogo
            self._pendiente_autologin = self.permitir_autologin
    
    def showEvent(self, event):
        """Se ejecuta cuando el diálogo se muestra"""
        super().showEvent(event)

        # Forzar repintado moviendo la ventana (simula lo que hace el usuario)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(50, self._forzar_repintado_con_movimiento)

        # Marcar setup completo para que resizeEvent pueda ocultar/mostrar el logo
        self._setup_complete = True

        # Intentar auto-login DESPUÉS de que el diálogo se haya mostrado
        if hasattr(self, '_pendiente_autologin') and self._pendiente_autologin:
            self._pendiente_autologin = False
            QTimer.singleShot(150, self._ejecutar_autologin)

    def _forzar_repintado_con_movimiento(self):
        """Fuerza el repintado moviendo la ventana ligeramente"""
        # Mover 1 pixel y volver - esto fuerza Windows a repintar
        pos = self.pos()
        self.move(pos.x() + 1, pos.y())
        QApplication.processEvents()
        self.move(pos)
    
    def _ejecutar_autologin(self):
        """Ejecuta el auto-login"""
        if self.intentar_autologin_silencioso():
            self.accept()

    def _make_scroll_page(self, widget):
        """Envuelve un widget en QScrollArea para páginas largas"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(widget)
        return scroll

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Stack para cambiar entre vistas
        self.stack = QStackedWidget()

        # Página 0: Login — sin scroll, cabe perfectamente
        self.pagina_login = self.crear_pagina_login()
        self.stack.addWidget(self.pagina_login)

        # Página 1: Configuración inicial — más larga, scroll interno
        _setup_widget = self.crear_pagina_setup()
        self.pagina_setup = _setup_widget
        self.stack.addWidget(self._make_scroll_page(_setup_widget))

        # Página 2: Recuperar contraseña — scroll interno
        _recovery_widget = self.crear_pagina_recovery()
        self.pagina_recovery = _recovery_widget
        self.stack.addWidget(self._make_scroll_page(_recovery_widget))

        # Página 3: Mostrar llave — scroll interno
        _llave_widget = self.crear_pagina_llave()
        self.pagina_llave = _llave_widget
        self.stack.addWidget(self._make_scroll_page(_llave_widget))

        # Página 4: Verificación TOTP 2FA
        self.pagina_totp = self.crear_pagina_totp()
        self.stack.addWidget(self.pagina_totp)

        layout.addWidget(self.stack)

    def crear_pagina_login(self):
        """Crea la página de login normal"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(0)
        h, v = self._margenes_responsivos()
        layout.setContentsMargins(h, v, h, v)

        # ── Logo adaptativo: banner fino que se oculta en pantallas pequeñas ──
        self._logo_banner = self._crear_logo_banner()
        if self._logo_banner:
            layout.addWidget(self._logo_banner)
            layout.addSpacing(2)

        title = QLabel(tr("Iniciar Sesión"))
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(3)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        layout.addSpacing(10)

        # ── Tarjeta de diseño moderno ──
        card_frame = QFrame()
        card_frame.setObjectName("cardPanel")
        card_frame.setStyleSheet("""
            #cardPanel {
                background-color: #3B4252;
                border-radius: 12px;
                border: 1px solid #4C566A;
            }
            QLineEdit {
                background-color: #2E3440;
                border: 1px solid #434C5E;
                border-radius: 8px;
                padding: 10px 15px;
                font-size: 14px;
                color: #ECEFF4;
            }
            QLineEdit:focus {
                border: 1px solid #88C0D0;
                background-color: #3B4252;
            }
            QCheckBox {
                color: #D8DEE9;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid #4C566A;
                background-color: #2E3440;
            }
            QCheckBox::indicator:checked {
                background-color: #88C0D0;
                border: 1px solid #88C0D0;
            }
            QPushButton#btnRecovery {
                background: none; border: none;
                color: #88C0D0; font-size: 12px;
                text-align: right; margin-top: 5px;
            }
            QPushButton#btnRecovery:hover { color: #8FBCBB; text-decoration: underline; }
        """)
        card_layout = QVBoxLayout(card_frame)
        card_layout.setSpacing(12)
        ch = max(20, int(self.width() * 0.08))
        card_layout.setContentsMargins(ch, 20, ch, 20)

        # Usuario Input
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(tr("Usuario"))
        self.username_input.setMinimumHeight(48)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        card_layout.addWidget(self.username_input)

        # Contraseña Input
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(tr("Contraseña"))
        self.password_input.setMinimumHeight(48)
        self.password_input.returnPressed.connect(self.intentar_login)
        card_layout.addWidget(self.password_input)

        # Opciones Checkboxes
        from PyQt5.QtWidgets import QCheckBox
        options_layout = QHBoxLayout()
        self.check_recordar = QCheckBox(tr("Recordar credenciales"))
        self.check_recordar.setToolTip(tr("Recuerda tu usuario la próxima vez"))
        options_layout.addWidget(self.check_recordar)
        
        options_layout.addStretch()
        
        self.check_autologin = QCheckBox(tr("Auto-login"))
        self.check_autologin.setToolTip(tr("Entrar automáticamente si las credenciales están guardadas"))
        options_layout.addWidget(self.check_autologin)
        
        card_layout.addLayout(options_layout)

        # Botón Login
        card_layout.addSpacing(4)
        btn_login = QPushButton(tr("Iniciar Sesión"))
        btn_login.setMinimumHeight(48)
        btn_login.setCursor(Qt.PointingHandCursor)
        apply_btn_primary(btn_login)
        # Asegurar estilo consistente para el botón con el borde redondeado del card
        btn_login.setStyleSheet(btn_login.styleSheet() + "QPushButton { font-size: 15px; font-weight: bold; border-radius: 8px; }")
        btn_login.clicked.connect(self.intentar_login)
        card_layout.addWidget(btn_login)

        # Recuperar Contraseña Link
        btn_recovery = QPushButton(tr("¿Olvidaste tu contraseña?"))
        btn_recovery.setObjectName("btnRecovery")
        btn_recovery.setCursor(Qt.PointingHandCursor)
        btn_recovery.clicked.connect(self.mostrar_recovery)
        card_layout.addWidget(btn_recovery)

        layout.addWidget(card_frame)
        layout.addSpacing(5)

        # ── Copyright ──
        footer = QLabel(f"© {datetime.now().year} - {APP_NAME} v{APP_VERSION}")
        footer.setStyleSheet("color: #4C566A; font-size: 10px;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

        return page

    def crear_pagina_setup(self):
        """Crea la página de configuración inicial"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        h, v = self._margenes_responsivos()
        layout.setContentsMargins(h, v, h, v)

        # Header
        self.crear_header(layout, tr("Configuración Inicial"), 
                         tr("Bienvenido. Crea el primer usuario administrador."))

        layout.addSpacing(10)

        # Nombre completo
        layout.addWidget(QLabel(tr("Nombre completo:")))
        self.setup_nombre = QLineEdit()
        self.setup_nombre.setPlaceholderText(tr("Ej: Juan García"))
        self.setup_nombre.setMinimumHeight(40)
        layout.addWidget(self.setup_nombre)

        # Usuario
        layout.addWidget(QLabel(tr("Nombre de usuario:")))
        self.setup_username = QLineEdit()
        self.setup_username.setPlaceholderText(tr("Ej: admin"))
        self.setup_username.setMinimumHeight(40)
        layout.addWidget(self.setup_username)

        # Contraseña
        layout.addWidget(QLabel(tr("Contraseña (mínimo 8 caracteres, mayúscula y número):")))
        self.setup_password = QLineEdit()
        self.setup_password.setEchoMode(QLineEdit.Password)
        self.setup_password.setPlaceholderText(tr("Tu contraseña segura"))
        self.setup_password.setMinimumHeight(40)
        self.setup_password.textChanged.connect(self._actualizar_fortaleza_setup)
        layout.addWidget(self.setup_password)

        # Indicador de fortaleza
        self.setup_strength = PasswordStrengthWidget()
        layout.addWidget(self.setup_strength)

        # Confirmar contraseña
        layout.addWidget(QLabel(tr("Confirmar contraseña:")))
        self.setup_password2 = QLineEdit()
        self.setup_password2.setEchoMode(QLineEdit.Password)
        self.setup_password2.setPlaceholderText(tr("Repite la contraseña"))
        self.setup_password2.setMinimumHeight(40)
        layout.addWidget(self.setup_password2)

        layout.addSpacing(15)

        # Info importante
        info = QLabel(tr("⚠️ Al crear el usuario se generará una LLAVE DE RECUPERACIÓN.") + "\n" +
                     tr("Guárdala en un lugar seguro, la necesitarás si olvidas tu contraseña."))
        info.setStyleSheet("""
            background-color: rgba(235, 203, 139, 0.15);
            color: #EBCB8B;
            border: 1px solid #EBCB8B;
            border-radius: 5px;
            padding: 12px;
            font-size: 11px;
        """)
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(15)

        # Botón crear
        btn_crear = QPushButton(tr("Crear Usuario Administrador"))
        apply_btn_success(btn_crear)
        btn_crear.clicked.connect(self.crear_usuario_inicial)
        layout.addWidget(btn_crear)

        layout.addStretch()
        self.crear_footer(layout)
        
        return page

    def crear_pagina_recovery(self):
        """Crea la página de recuperación de contraseña"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)
        h, v = self._margenes_responsivos()
        layout.setContentsMargins(h, v, h, v)

        # Header
        self.crear_header(layout, tr("Recuperar Contraseña"),
                         tr("Introduce tu usuario y la llave maestra que guardaste."))

        layout.addSpacing(15)

        # Usuario
        layout.addWidget(QLabel(tr("Nombre de usuario:")))
        self.recovery_username = QLineEdit()
        self.recovery_username.setPlaceholderText(tr("Tu usuario"))
        self.recovery_username.setMinimumHeight(40)
        layout.addWidget(self.recovery_username)

        # Llave maestra
        layout.addWidget(QLabel(tr("Llave de recuperación:")))
        self.recovery_key = QLineEdit()
        self.recovery_key.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.recovery_key.setMinimumHeight(40)
        layout.addWidget(self.recovery_key)

        # Nueva contraseña
        layout.addWidget(QLabel(tr("Nueva contraseña (mínimo 8 caracteres, mayúscula y número):")))
        self.recovery_password = QLineEdit()
        self.recovery_password.setEchoMode(QLineEdit.Password)
        self.recovery_password.setPlaceholderText(tr("Tu nueva contraseña segura"))
        self.recovery_password.setMinimumHeight(40)
        self.recovery_password.textChanged.connect(self._actualizar_fortaleza_recovery)
        layout.addWidget(self.recovery_password)

        # Indicador de fortaleza
        self.recovery_strength = PasswordStrengthWidget()
        layout.addWidget(self.recovery_strength)

        # Confirmar
        layout.addWidget(QLabel(tr("Confirmar nueva contraseña:")))
        self.recovery_password2 = QLineEdit()
        self.recovery_password2.setEchoMode(QLineEdit.Password)
        self.recovery_password2.setMinimumHeight(40)
        layout.addWidget(self.recovery_password2)

        layout.addSpacing(20)

        # Botones
        btn_layout = QHBoxLayout()
        
        btn_volver = QPushButton(tr("← Volver"))
        apply_btn_cancel(btn_volver)
        btn_volver.clicked.connect(self.mostrar_login)
        btn_layout.addWidget(btn_volver)

        btn_recuperar = QPushButton(tr("Cambiar Contraseña"))
        apply_btn_warning(btn_recuperar)
        btn_recuperar.clicked.connect(self.recuperar_password)
        btn_layout.addWidget(btn_recuperar)

        layout.addLayout(btn_layout)

        layout.addStretch()
        self.crear_footer(layout)
        
        return page

    def crear_pagina_llave(self):
        """Crea la página que muestra la llave generada"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        h, v = self._margenes_responsivos()
        layout.setContentsMargins(h, v, h, v)

        # Header
        self.crear_header(layout, tr("¡Usuario Creado!"), 
                         tr("Guarda tu llave de recuperación en un lugar seguro."))

        layout.addSpacing(20)

        # Icono éxito
        success_icon = QLabel("✅")
        success_icon.setStyleSheet("font-size: 50px;")
        success_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(success_icon)

        layout.addSpacing(10)

        # Caja con la llave
        layout.addWidget(QLabel(tr("Tu LLAVE DE RECUPERACIÓN es:")))
        
        self.lbl_llave = QLabel("")
        self.lbl_llave.setStyleSheet("""
            background-color: #2E3440;
            color: #A3BE8C;
            font-size: 22px;
            font-weight: bold;
            font-family: 'Consolas', 'Courier New', monospace;
            padding: 20px;
            border-radius: 8px;
            letter-spacing: 2px;
        """)
        self.lbl_llave.setAlignment(Qt.AlignCenter)
        self.lbl_llave.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.lbl_llave)

        layout.addSpacing(10)

        # Advertencia
        warning = QLabel(
            tr("⚠️ IMPORTANTE:") + "\n\n" +
            tr("• Esta llave es ÚNICA y no se puede recuperar.") + "\n" +
            tr("• Si la pierdes, no podrás recuperar tu contraseña.") + "\n" +
            tr("• Guárdala en un lugar seguro (papel, gestor de contraseñas, etc.)") + "\n" +
            tr("• NO la compartas con nadie.")
        )
        warning.setStyleSheet("""
            background-color: rgba(235, 203, 139, 0.15);
            color: #EBCB8B;
            border: 2px solid #EBCB8B;
            border-radius: 8px;
            padding: 15px;
            font-size: 11px;
        """)
        warning.setWordWrap(True)
        layout.addWidget(warning)

        layout.addSpacing(20)

        # Checkbox confirmación
        self.check_guardado = QPushButton(tr("✓ He guardado la llave, continuar al login"))
        apply_btn_success(self.check_guardado)
        self.check_guardado.clicked.connect(self.mostrar_login)
        layout.addWidget(self.check_guardado)

        layout.addStretch()
        
        return page

    def crear_pagina_totp(self):
        """Crea la página de verificación TOTP 2FA"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        h, v = self._margenes_responsivos()
        layout.setContentsMargins(h, v, h, v)

        self.crear_header(layout, tr("Verificación en Dos Pasos"),
                         tr("Introduce el código de 6 dígitos de tu app de autenticación"))

        layout.addSpacing(30)

        # Icono escudo
        shield_icon = QLabel("🛡️")
        shield_icon.setStyleSheet("font-size: 50px;")
        shield_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(shield_icon)

        layout.addSpacing(20)

        # Campo de código TOTP
        self.totp_input = QLineEdit()
        self.totp_input.setPlaceholderText("000000")
        self.totp_input.setMaxLength(6)
        self.totp_input.setAlignment(Qt.AlignCenter)
        self.totp_input.setStyleSheet("""
            QLineEdit {
                font-size: 32px;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
                letter-spacing: 10px;
                padding: 15px;
                border: 2px solid #5E81AC;
                border-radius: 8px;
                background-color: #2E3440;
                color: #ECEFF4;
                max-width: 250px;
            }
            QLineEdit:focus {
                border: 2px solid #88C0D0;
            }
        """)
        self.totp_input.returnPressed.connect(self._verificar_totp)

        # Centrar el input
        input_layout = QHBoxLayout()
        input_layout.addStretch()
        input_layout.addWidget(self.totp_input)
        input_layout.addStretch()
        layout.addLayout(input_layout)

        layout.addSpacing(10)

        # Info
        info = QLabel(tr("El código cambia cada 30 segundos"))
        info.setStyleSheet("color: #7B88A0; font-size: 11px;")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        layout.addSpacing(20)

        # Botones
        btns_layout = QHBoxLayout()
        btns_layout.addStretch()

        btn_cancelar = QPushButton(tr("Cancelar"))
        btn_cancelar.clicked.connect(self._cancelar_totp)
        apply_btn_cancel(btn_cancelar)
        btns_layout.addWidget(btn_cancelar)

        btn_verificar = QPushButton(tr("Verificar"))
        btn_verificar.clicked.connect(self._verificar_totp)
        apply_btn_primary(btn_verificar)
        btns_layout.addWidget(btn_verificar)

        btns_layout.addStretch()
        layout.addLayout(btns_layout)

        layout.addStretch()
        return page

    def _verificar_totp(self):
        """Verifica el código TOTP introducido"""
        codigo = self.totp_input.text().strip()

        if not codigo or len(codigo) != 6 or not codigo.isdigit():
            notify_warning(self, tr("Error"), tr("Introduce un código de 6 dígitos"))
            return

        usuario_id = self._pendiente_2fa.get('id') if self._pendiente_2fa else None
        if not usuario_id:
            notify_error(self, tr("Error"), tr("Error de sesión. Inténtalo de nuevo."))
            self._cancelar_totp()
            return

        if self.auth_manager.verificar_totp(usuario_id, codigo):
            # Re-login (la sesión fue cerrada temporalmente)
            usuario = self.db.fetch_one(
                "SELECT * FROM usuarios WHERE id = ? AND activo = 1",
                (usuario_id,)
            )
            if usuario:
                self.auth_manager.usuario_actual = {
                    'id': usuario['id'],
                    'username': usuario['username'],
                    'nombre_completo': usuario['nombre_completo'],
                    'rol': usuario['rol'],
                    'establecimiento_id': usuario.get('establecimiento_id')
                }
                from datetime import datetime
                self.auth_manager.ultima_actividad = datetime.now()

            self.usuario_logueado = self.auth_manager.obtener_usuario_actual()
            self._pendiente_2fa = None
            notify_success(self, tr("Bienvenido"), tr("Verificación 2FA correcta"))
            self.accept()
        else:
            notify_error(self, tr("Error"), tr("Código incorrecto. Inténtalo de nuevo."))
            self.totp_input.clear()
            self.totp_input.setFocus()

    def _cancelar_totp(self):
        """Cancela la verificación TOTP y vuelve al login"""
        self._pendiente_2fa = None
        self.auth_manager.logout()
        self.totp_input.clear()
        self.stack.setCurrentIndex(0)
        self.password_input.clear()
        self.password_input.setFocus()

    def crear_header(self, layout, titulo, subtitulo=None):
        """Crea el header común para todas las páginas"""
        # Logo/Icono
        icon = QLabel("🔐")
        icon.setStyleSheet("font-size: 45px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        # Título
        title = QLabel(titulo)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Empresa
        company = QLabel(COMPANY_INFO['name'])
        company.setStyleSheet("font-size: 11px; color: #7B88A0;")
        company.setAlignment(Qt.AlignCenter)
        layout.addWidget(company)

        if subtitulo:
            sub = QLabel(subtitulo)
            sub.setStyleSheet("font-size: 11px; color: #D8DEE9;")
            sub.setAlignment(Qt.AlignCenter)
            sub.setWordWrap(True)
            layout.addWidget(sub)

        # Separador
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: transparent; color: #88C0D0; border: 2px solid #88C0D0; border-radius: 6px;")
        line.setFixedHeight(1)
        layout.addWidget(line)

    def crear_footer(self, layout, mostrar_logo=True):
        """Crea el footer común (logo ahora se muestra como fondo del diálogo)"""
        # Copyright
        footer = QLabel(f"© {datetime.now().year} - {APP_NAME} v{APP_VERSION}")
        footer.setStyleSheet("color: #D8DEE9; font-size: 10px;")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)

    def _obtener_logo_establecimiento(self):
        """Obtiene la ruta del logo del establecimiento activo"""
        try:
            # Buscar establecimiento activo con logo
            result = self.db.fetch_one(
                "SELECT logo_path FROM establecimientos WHERE activo = 1 AND logo_path IS NOT NULL AND logo_path != '' LIMIT 1"
            )
            if result and result.get('logo_path'):
                return result['logo_path']
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error obteniendo logo: {e}")
        return None

    def _margenes_responsivos(self):
        """Calcula márgenes proporcionales al ancho actual del diálogo"""
        w = self.width()
        h_margin = max(20, int(w * 0.06))
        v_margin = max(14, int(w * 0.03))
        return h_margin, v_margin

    def resizeEvent(self, event):
        """Actualiza márgenes y visibilidad del logo cuando la ventana cambia"""
        super().resizeEvent(event)
        self._actualizar_margenes()

    def _actualizar_margenes(self):
        """Recalcula y aplica márgenes proporcionales a las páginas directas (no scroll)"""
        h, v = self._margenes_responsivos()
        # Solo actualizar páginas que son QWidget directo (no QScrollArea)
        for page in (self.pagina_login, self.pagina_totp):
            if hasattr(page, 'layout') and page.layout():
                page.layout().setContentsMargins(h, v, h, v)
        # Ocultar logo en pantallas pequeñas (< 550px alto), solo después de showEvent
        if self._setup_complete and hasattr(self, '_logo_banner') and self._logo_banner:
            self._logo_banner.setVisible(self.height() >= 550)

    def _crear_logo_banner(self):
        """Crea un banner fino (48px) con el logo del establecimiento, o None si no hay logo"""
        logo_path = self._obtener_logo_establecimiento()
        if not logo_path or not os.path.exists(logo_path):
            return None

        pixmap = QPixmap(logo_path)
        if pixmap.isNull():
            return None

        banner = QFrame()
        banner.setFixedHeight(100)
        banner.setStyleSheet("QFrame { background: transparent; }")
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(0, 0, 0, 0)
        banner_layout.setAlignment(Qt.AlignCenter)

        logo_label = QLabel()
        logo_label.setAlignment(Qt.AlignCenter)
        scaled = pixmap.scaled(380, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(scaled)
        logo_label.setStyleSheet("background: transparent;")
        banner_layout.addWidget(logo_label)

        # Ocultar en pantallas pequeñas
        screen = QApplication.primaryScreen().availableGeometry()
        banner.setVisible(screen.height() >= 550)

        return banner

    def apply_styles(self):
        """Aplica estilos globales - Nord theme (inherited from app stylesheet)"""
        pass

    # === Navegación ===
    def mostrar_login(self):
        self.stack.setCurrentIndex(0)
        self.username_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()

    def mostrar_configuracion_inicial(self):
        self.stack.setCurrentIndex(1)
        self.setup_nombre.setFocus()

    def mostrar_recovery(self):
        self.stack.setCurrentIndex(2)
        self.recovery_username.clear()
        self.recovery_key.clear()
        self.recovery_password.clear()
        self.recovery_password2.clear()
        self.recovery_username.setFocus()

    def mostrar_llave(self, llave):
        self.lbl_llave.setText(llave)
        self.stack.setCurrentIndex(3)

    # === Acciones ===
    def intentar_login(self):
        """Intenta hacer login"""
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            notify_warning(self, tr("Error"), tr("Usuario") + " / " + tr("Contraseña"))
            return

        exito, mensaje = self.auth_manager.login(username, password)

        if exito:
            self.usuario_logueado = self.auth_manager.obtener_usuario_actual()

            # Verificar si el usuario tiene 2FA activado
            if self.auth_manager.tiene_totp(self.usuario_logueado['id']):
                # Guardar datos pendientes y cerrar sesión temporal
                self._pendiente_2fa = dict(self.usuario_logueado)
                self.auth_manager.logout()
                self.usuario_logueado = None
                # Mostrar página de verificación TOTP
                self.totp_input.clear()
                self.stack.setCurrentIndex(4)
                self.totp_input.setFocus()
                return

            # Verificar si el usuario tiene establecimiento asignado
            if not self.usuario_logueado.get('establecimiento_id'):
                if not self._asignar_establecimiento_usuario(self.usuario_logueado['id']):
                    self.auth_manager.logout()
                    self.usuario_logueado = None
                    return
                self.usuario_logueado = self.auth_manager.obtener_usuario_actual()

            # Guardar preferencias de login
            self.guardar_preferencias_login(username)
            notify_success(self, tr("Bienvenido"), mensaje)
            self.accept()
        else:
            notify_error(self, tr("Error"), mensaje)
            self.password_input.clear()
            self.password_input.setFocus()

    def _asignar_establecimiento_usuario(self, usuario_id):
        """Pide al usuario seleccionar o crear un establecimiento"""
        from app.ui.establecimiento_dialog import EstablecimientoDialog

        # Verificar si hay establecimientos existentes
        establecimientos = self.db.fetch_all(
            "SELECT id, nombre FROM establecimientos WHERE activo = 1"
        )

        if establecimientos:
            # Hay establecimientos, preguntar si quiere usar uno existente o crear nuevo
            from PyQt5.QtWidgets import QInputDialog
            nombres = [f"{e['id']} - {e['nombre']}" for e in establecimientos]
            nombres.append(tr("➕ Crear nuevo establecimiento"))

            seleccion, ok = QInputDialog.getItem(
                self,
                tr("Seleccionar Establecimiento"),
                tr("Tu usuario no tiene establecimiento asignado.") + "\n" + tr("Selecciona uno:"),
                nombres,
                0,
                False
            )

            if ok and seleccion:
                if seleccion == tr("➕ Crear nuevo establecimiento"):
                    # Crear nuevo
                    dialog = EstablecimientoDialog(self.db, es_inicial=False, parent=self)
                    if dialog.exec_():
                        establecimiento_id = dialog.obtener_establecimiento_id()
                        if establecimiento_id:
                            self.auth_manager.asignar_establecimiento_usuario(usuario_id, establecimiento_id)
                            return True
                else:
                    # Usar existente
                    establecimiento_id = int(seleccion.split(" - ")[0])
                    self.auth_manager.asignar_establecimiento_usuario(usuario_id, establecimiento_id)
                    return True
            return False
        else:
            # No hay establecimientos, crear uno nuevo obligatoriamente
            notify_success(
                self,
                tr("Crear Establecimiento"),
                tr("No hay establecimientos configurados.") + "\n" + tr("Debes crear uno para continuar.")
            )

            dialog = EstablecimientoDialog(self.db, es_inicial=True, parent=self)
            if dialog.exec_():
                establecimiento_id = dialog.obtener_establecimiento_id()
                if establecimiento_id:
                    self.auth_manager.asignar_establecimiento_usuario(usuario_id, establecimiento_id)
                    return True
            return False

    def _actualizar_fortaleza_setup(self, password):
        """Actualiza el indicador de fortaleza cuando cambia la contraseña"""
        if hasattr(self, 'setup_strength'):
            self.setup_strength.evaluar_password(password)

    def _actualizar_fortaleza_recovery(self, password):
        """Actualiza el indicador de fortaleza en recuperación"""
        if hasattr(self, 'recovery_strength'):
            self.recovery_strength.evaluar_password(password)

    def crear_usuario_inicial(self):
        """Crea el primer usuario administrador"""
        nombre = self.setup_nombre.text().strip()
        username = self.setup_username.text().strip()
        password = self.setup_password.text()
        password2 = self.setup_password2.text()

        # Validaciones
        if not nombre or not username or not password:
            notify_warning(self, tr("Campos Vacíos"), tr("Completa todos los campos"))
            return

        if password != password2:
            notify_warning(self, tr("Error"), tr("Las contraseñas no coinciden"))
            return

        # Crear usuario
        exito, llave, mensaje, usuario_id = self.auth_manager.crear_usuario_inicial(username, password, nombre)

        if exito:
            self.llave_generada = llave
            self.usuario_inicial_id = usuario_id

            # Mostrar diálogo para crear establecimiento (obligatorio)
            from app.ui.establecimiento_dialog import EstablecimientoDialog

            establecimiento_creado = False
            while not establecimiento_creado:
                dialog = EstablecimientoDialog(self.db, es_inicial=True, parent=self)

                if dialog.exec_():
                    establecimiento_id = dialog.obtener_establecimiento_id()
                    if establecimiento_id:
                        # Asignar establecimiento al usuario
                        self.auth_manager.asignar_establecimiento_usuario(usuario_id, establecimiento_id)
                        establecimiento_creado = True
                else:
                    # El usuario intentó cancelar, avisar que es obligatorio
                    notify_warning(
                        self,
                        tr("Establecimiento Requerido"),
                        tr("Debes crear un establecimiento para continuar.") + "\n" +
                        tr("Cada usuario debe estar asociado a un establecimiento.")
                    )

            # Mostrar la llave de recuperación
            self.mostrar_llave(llave)
        else:
            notify_error(self, tr("Error"), mensaje)

    def recuperar_password(self):
        """Recupera la contraseña usando la llave maestra"""
        username = self.recovery_username.text().strip()
        key = self.recovery_key.text().strip()
        password = self.recovery_password.text()
        password2 = self.recovery_password2.text()

        if not username or not key or not password:
            notify_warning(self, tr("Campos Vacíos"), tr("Completa todos los campos"))
            return

        if password != password2:
            notify_warning(self, tr("Error"), tr("Las contraseñas no coinciden"))
            return

        exito, mensaje = self.auth_manager.recuperar_password_con_llave(username, key, password)

        if exito:
            notify_success(self, tr("Éxito"), mensaje)
            self.mostrar_login()
        else:
            notify_error(self, tr("Error"), mensaje)

    def obtener_usuario_logueado(self):
        """Retorna el usuario que hizo login correctamente"""
        return self.usuario_logueado

    # === Preferencias de Login ===
    def _get_config(self, clave):
        """Obtiene un valor de configuración"""
        res = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
        return res['valor'] if res else None

    def _set_config(self, clave, valor):
        """Guarda un valor de configuración"""
        self.db.execute_query(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
            (clave, valor)
        )

    def cargar_preferencias_login(self):
        """Carga las preferencias de login guardadas"""
        try:
            # Recordar usuario (incluye contraseña)
            recordar = self._get_config('login_recordar_usuario')
            self.check_recordar.setChecked(recordar == '1')

            if recordar == '1':
                # Cargar usuario
                usuario_guardado = self._get_config('login_ultimo_usuario')
                if usuario_guardado:
                    self.username_input.setText(usuario_guardado)

                # Cargar contraseña (recordar = usuario + contraseña)
                pwd_encrypted = self._get_config('login_pwd_guardada')
                if pwd_encrypted:
                    try:
                        from app.modules.crypto_manager import CryptoManager
                        crypto = CryptoManager(self.db)
                        password = crypto.desencriptar(pwd_encrypted)
                        self.password_input.setText(password)
                    except (OSError, ValueError, RuntimeError) as e:
                        logger.error(f"Error desencriptando contraseña: {e}")
                        pass

            # Auto-login (login automático sin pulsar botón)
            autologin = self._get_config('login_autologin')
            self.check_autologin.setChecked(autologin == '1')

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error cargando preferencias: {e}")

    def guardar_preferencias_login(self, username):
        """Guarda las preferencias de login"""
        try:
            # Recordar usuario (incluye contraseña)
            self._set_config('login_recordar_usuario', '1' if self.check_recordar.isChecked() else '0')

            if self.check_recordar.isChecked():
                # Guardar usuario
                self._set_config('login_ultimo_usuario', username)
                # Guardar contraseña encriptada (Fernet + DPAPI)
                from app.modules.crypto_manager import CryptoManager
                crypto = CryptoManager(self.db)
                pwd_encrypted = crypto.encriptar(self.password_input.text())
                self._set_config('login_pwd_guardada', pwd_encrypted)
            else:
                # Limpiar datos guardados
                self._set_config('login_ultimo_usuario', '')
                self._set_config('login_pwd_guardada', '')

            # Auto-login (solo funciona si recordar está activo)
            if self.check_autologin.isChecked() and self.check_recordar.isChecked():
                self._set_config('login_autologin', '1')
            else:
                self._set_config('login_autologin', '0')

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error guardando preferencias: {e}")

    def intentar_autologin_silencioso(self):
        """Intenta hacer login automático si está configurado"""
        try:
            autologin = self._get_config('login_autologin')
            if autologin != '1':
                return False

            username = self._get_config('login_ultimo_usuario')
            pwd_encrypted = self._get_config('login_pwd_guardada')

            if not username or not pwd_encrypted:
                return False

            from app.modules.crypto_manager import CryptoManager
            crypto = CryptoManager(self.db)
            password = crypto.desencriptar(pwd_encrypted)

            # Intentar login silencioso
            exito, mensaje = self.auth_manager.login(username, password)

            if exito:
                usuario = self.auth_manager.obtener_usuario_actual()
                # Si tiene 2FA, no se puede hacer autologin
                if self.auth_manager.tiene_totp(usuario['id']):
                    self.auth_manager.logout()
                    self._set_config('login_autologin', '0')
                    return False
                self.usuario_logueado = usuario
                return True
            else:
                self._set_config('login_autologin', '0')
                return False

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error en autologin: {e}")
            return False
