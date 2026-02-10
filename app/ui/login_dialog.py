"""
Ventana de inicio de sesión con sistema de configuración inicial
y recuperación de contraseña mediante llave maestra
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QMessageBox, QFrame, QStackedWidget,
                             QWidget, QTextEdit, QApplication)
from app.ui.transparent_buttons import apply_btn_primary, apply_btn_success, apply_btn_cancel, apply_btn_warning
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
import os
from app.modules.auth_manager import AuthManager
from app.ui.password_strength_widget import PasswordStrengthWidget
from config import COMPANY_INFO, APP_VERSION, APP_NAME
from app.i18n import tr
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
        self.permitir_autologin = permitir_autologin

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - Acceso")
        self.setModal(True)
        self.setWindowFlags(
            Qt.Dialog |
            Qt.MSWindowsFixedSizeDialogHint |
            Qt.WindowTitleHint |
            Qt.WindowCloseButtonHint
        )
        self.setFixedSize(550, 820)
        
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

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Stack para cambiar entre vistas
        self.stack = QStackedWidget()
        
        # Página 0: Login
        self.pagina_login = self.crear_pagina_login()
        self.stack.addWidget(self.pagina_login)
        
        # Página 1: Configuración inicial (primer usuario)
        self.pagina_setup = self.crear_pagina_setup()
        self.stack.addWidget(self.pagina_setup)
        
        # Página 2: Recuperar contraseña
        self.pagina_recovery = self.crear_pagina_recovery()
        self.stack.addWidget(self.pagina_recovery)
        
        # Página 3: Mostrar llave generada
        self.pagina_llave = self.crear_pagina_llave()
        self.stack.addWidget(self.pagina_llave)
        
        layout.addWidget(self.stack)

    def crear_pagina_login(self):
        """Crea la página de login normal"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(15)
        layout.setContentsMargins(40, 30, 40, 30)

        # Header
        self.crear_header(layout, tr("Iniciar Sesión"))

        layout.addSpacing(20)

        # Campo usuario
        user_label = QLabel(tr("Usuario") + ":")
        user_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(user_label)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(tr("Usuario"))
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        layout.addWidget(self.username_input)

        layout.addSpacing(5)

        # Campo contraseña
        password_label = QLabel(tr("Contraseña") + ":")
        password_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText(tr("Contraseña"))
        self.password_input.returnPressed.connect(self.intentar_login)
        layout.addWidget(self.password_input)

        layout.addSpacing(20)

        # Botón login
        btn_login = QPushButton(tr("Iniciar Sesión"))
        # Aplicar estilo inline con fondo transparente
        btn_login.setStyleSheet("""
            QPushButton {
                background-color: transparent !important;
                color: #88C0D0;
                border: 2px solid #88C0D0;
                border-radius: 6px;
                padding: 0 16px;
                font-size: 14px;
                font-weight: 600;
                min-height: 42px;
            }
            QPushButton:hover {
                background-color: rgba(136, 192, 208, 0.1) !important;
                border: 2px solid #88C0D0;
            }
            QPushButton:pressed {
                background-color: rgba(136, 192, 208, 0.2) !important;
            }
        """)
        btn_login.clicked.connect(self.intentar_login)
        layout.addWidget(btn_login)

        # Opciones de recordar
        options_layout = QHBoxLayout()

        from PyQt5.QtWidgets import QCheckBox
        self.check_recordar = QCheckBox(tr("Recordar credenciales"))
        self.check_recordar.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.check_recordar.setToolTip(tr("Recordar credenciales"))
        options_layout.addWidget(self.check_recordar)

        options_layout.addStretch()

        self.check_autologin = QCheckBox(tr("Auto-login"))
        self.check_autologin.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.check_autologin.setToolTip(tr("Auto-login"))
        options_layout.addWidget(self.check_autologin)
        
        layout.addLayout(options_layout)
        
        layout.addSpacing(10)

        # Link recuperar contraseña
        btn_recovery = QPushButton(tr("¿Olvidaste tu contraseña?"))
        btn_recovery.setStyleSheet("""
            QPushButton {
                background: none;
                border: none;
                color: #3498db;
                font-size: 12px;
                text-decoration: underline;
            }
            QPushButton:hover { color: #2980b9; }
        """)
        btn_recovery.setCursor(Qt.PointingHandCursor)
        btn_recovery.clicked.connect(self.mostrar_recovery)
        layout.addWidget(btn_recovery, alignment=Qt.AlignCenter)

        layout.addStretch()

        # Footer
        self.crear_footer(layout)
        
        return page

    def crear_pagina_setup(self):
        """Crea la página de configuración inicial"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(40, 20, 40, 20)

        # Header
        self.crear_header(layout, "Configuración Inicial", 
                         "Bienvenido. Crea el primer usuario administrador.")

        layout.addSpacing(10)

        # Nombre completo
        layout.addWidget(QLabel("Nombre completo:"))
        self.setup_nombre = QLineEdit()
        self.setup_nombre.setPlaceholderText("Ej: Juan García")
        self.setup_nombre.setMinimumHeight(40)
        layout.addWidget(self.setup_nombre)

        # Usuario
        layout.addWidget(QLabel("Nombre de usuario:"))
        self.setup_username = QLineEdit()
        self.setup_username.setPlaceholderText("Ej: admin")
        self.setup_username.setMinimumHeight(40)
        layout.addWidget(self.setup_username)

        # Contraseña
        layout.addWidget(QLabel("Contraseña (mínimo 8 caracteres, mayúscula y número):"))
        self.setup_password = QLineEdit()
        self.setup_password.setEchoMode(QLineEdit.Password)
        self.setup_password.setPlaceholderText("Tu contraseña segura")
        self.setup_password.setMinimumHeight(40)
        self.setup_password.textChanged.connect(self._actualizar_fortaleza_setup)
        layout.addWidget(self.setup_password)

        # Indicador de fortaleza
        self.setup_strength = PasswordStrengthWidget()
        layout.addWidget(self.setup_strength)

        # Confirmar contraseña
        layout.addWidget(QLabel("Confirmar contraseña:"))
        self.setup_password2 = QLineEdit()
        self.setup_password2.setEchoMode(QLineEdit.Password)
        self.setup_password2.setPlaceholderText("Repite la contraseña")
        self.setup_password2.setMinimumHeight(40)
        layout.addWidget(self.setup_password2)

        layout.addSpacing(15)

        # Info importante
        info = QLabel("⚠️ Al crear el usuario se generará una LLAVE DE RECUPERACIÓN.\n"
                     "Guárdala en un lugar seguro, la necesitarás si olvidas tu contraseña.")
        info.setStyleSheet("""
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 12px;
            font-size: 11px;
        """)
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addSpacing(15)

        # Botón crear
        btn_crear = QPushButton("Crear Usuario Administrador")
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
        layout.setContentsMargins(40, 30, 40, 30)

        # Header
        self.crear_header(layout, "Recuperar Contraseña",
                         "Introduce tu usuario y la llave maestra que guardaste.")

        layout.addSpacing(15)

        # Usuario
        layout.addWidget(QLabel("Nombre de usuario:"))
        self.recovery_username = QLineEdit()
        self.recovery_username.setPlaceholderText("Tu usuario")
        self.recovery_username.setMinimumHeight(40)
        layout.addWidget(self.recovery_username)

        # Llave maestra
        layout.addWidget(QLabel("Llave de recuperación:"))
        self.recovery_key = QLineEdit()
        self.recovery_key.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.recovery_key.setMinimumHeight(40)
        layout.addWidget(self.recovery_key)

        # Nueva contraseña
        layout.addWidget(QLabel("Nueva contraseña (mínimo 8 caracteres, mayúscula y número):"))
        self.recovery_password = QLineEdit()
        self.recovery_password.setEchoMode(QLineEdit.Password)
        self.recovery_password.setPlaceholderText("Tu nueva contraseña segura")
        self.recovery_password.setMinimumHeight(40)
        self.recovery_password.textChanged.connect(self._actualizar_fortaleza_recovery)
        layout.addWidget(self.recovery_password)

        # Indicador de fortaleza
        self.recovery_strength = PasswordStrengthWidget()
        layout.addWidget(self.recovery_strength)

        # Confirmar
        layout.addWidget(QLabel("Confirmar nueva contraseña:"))
        self.recovery_password2 = QLineEdit()
        self.recovery_password2.setEchoMode(QLineEdit.Password)
        self.recovery_password2.setMinimumHeight(40)
        layout.addWidget(self.recovery_password2)

        layout.addSpacing(20)

        # Botones
        btn_layout = QHBoxLayout()
        
        btn_volver = QPushButton("← Volver")
        apply_btn_cancel(btn_volver)
        btn_volver.clicked.connect(self.mostrar_login)
        btn_layout.addWidget(btn_volver)

        btn_recuperar = QPushButton("Cambiar Contraseña")
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
        layout.setContentsMargins(40, 30, 40, 30)

        # Header
        self.crear_header(layout, "¡Usuario Creado!", 
                         "Guarda tu llave de recuperación en un lugar seguro.")

        layout.addSpacing(20)

        # Icono éxito
        success_icon = QLabel("✅")
        success_icon.setStyleSheet("font-size: 50px;")
        success_icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(success_icon)

        layout.addSpacing(10)

        # Caja con la llave
        layout.addWidget(QLabel("Tu LLAVE DE RECUPERACIÓN es:"))
        
        self.lbl_llave = QLabel("")
        self.lbl_llave.setStyleSheet("""
            background-color: #2c3e50;
            color: #2ecc71;
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
            "⚠️ IMPORTANTE:\n\n"
            "• Esta llave es ÚNICA y no se puede recuperar.\n"
            "• Si la pierdes, no podrás recuperar tu contraseña.\n"
            "• Guárdala en un lugar seguro (papel, gestor de contraseñas, etc.)\n"
            "• NO la compartas con nadie."
        )
        warning.setStyleSheet("""
            background-color: #ffeaa7;
            color: #2d3436;
            border: 2px solid #fdcb6e;
            border-radius: 8px;
            padding: 15px;
            font-size: 11px;
        """)
        warning.setWordWrap(True)
        layout.addWidget(warning)

        layout.addSpacing(20)

        # Checkbox confirmación
        self.check_guardado = QPushButton("✓ He guardado la llave, continuar al login")
        apply_btn_success(self.check_guardado)
        self.check_guardado.clicked.connect(self.mostrar_login)
        layout.addWidget(self.check_guardado)

        layout.addStretch()
        
        return page

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
        company.setStyleSheet("font-size: 11px; color: #969696;")
        company.setAlignment(Qt.AlignCenter)
        layout.addWidget(company)

        if subtitulo:
            sub = QLabel(subtitulo)
            sub.setStyleSheet("font-size: 11px; color: #95a5a6;")
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
        """Crea el footer común con logo del establecimiento"""
        # Logo del establecimiento (solo si mostrar_logo=True)
        if mostrar_logo:
            logo_path = self._obtener_logo_establecimiento()
            if logo_path and os.path.exists(logo_path):
                logo_label = QLabel()
                logo_label.setAlignment(Qt.AlignCenter)
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    # Escalar manteniendo proporción, máximo 240x160
                    scaled = pixmap.scaled(240, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    logo_label.setPixmap(scaled)
                    logo_label.setStyleSheet("margin-bottom: 10px;")
                    layout.addWidget(logo_label)

        # Copyright
        footer = QLabel(f"© {datetime.now().year} - {APP_NAME} v{APP_VERSION}")
        footer.setStyleSheet("color: #95a5a6; font-size: 10px;")
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

    def apply_styles(self):
        """Aplica estilos globales - DARK MODE"""
        self.setStyleSheet("""
            QDialog { background-color: #1e1e1e; }
            QLabel { color: #cccccc; font-size: 12px; }
            QLineEdit {
                padding: 10px 15px;
                border: 2px solid #3e3e42;
                border-radius: 8px;
                background-color: #3c3c3c;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus { border: 2px solid #007acc; }
            QCheckBox { color: #cccccc; }
        """)

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
            QMessageBox.warning(self, tr("Error"), tr("Usuario") + " / " + tr("Contraseña"))
            return

        exito, mensaje = self.auth_manager.login(username, password)

        if exito:
            self.usuario_logueado = self.auth_manager.obtener_usuario_actual()

            # Verificar si el usuario tiene establecimiento asignado
            if not self.usuario_logueado.get('establecimiento_id'):
                if not self._asignar_establecimiento_usuario(self.usuario_logueado['id']):
                    # Si no se pudo asignar, hacer logout y no continuar
                    self.auth_manager.logout()
                    self.usuario_logueado = None
                    return
                # Recargar usuario con el establecimiento asignado
                self.usuario_logueado = self.auth_manager.obtener_usuario_actual()

            # Guardar preferencias de login
            self.guardar_preferencias_login(username)
            QMessageBox.information(self, tr("Bienvenido"), mensaje)
            self.accept()
        else:
            QMessageBox.critical(self, tr("Error"), mensaje)
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
            nombres.append("➕ Crear nuevo establecimiento")

            seleccion, ok = QInputDialog.getItem(
                self,
                "Seleccionar Establecimiento",
                "Tu usuario no tiene establecimiento asignado.\nSelecciona uno:",
                nombres,
                0,
                False
            )

            if ok and seleccion:
                if seleccion == "➕ Crear nuevo establecimiento":
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
            QMessageBox.information(
                self,
                "Crear Establecimiento",
                "No hay establecimientos configurados.\nDebes crear uno para continuar."
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
            QMessageBox.warning(self, tr("Campos Vacíos"), tr("Completa todos los campos"))
            return

        if password != password2:
            QMessageBox.warning(self, tr("Error"), tr("Las contraseñas no coinciden"))
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
                    QMessageBox.warning(
                        self,
                        "Establecimiento Requerido",
                        "Debes crear un establecimiento para continuar.\n"
                        "Cada usuario debe estar asociado a un establecimiento."
                    )

            # Mostrar la llave de recuperación
            self.mostrar_llave(llave)
        else:
            QMessageBox.critical(self, tr("Error"), mensaje)

    def recuperar_password(self):
        """Recupera la contraseña usando la llave maestra"""
        username = self.recovery_username.text().strip()
        key = self.recovery_key.text().strip()
        password = self.recovery_password.text()
        password2 = self.recovery_password2.text()

        if not username or not key or not password:
            QMessageBox.warning(self, tr("Campos Vacíos"), tr("Completa todos los campos"))
            return

        if password != password2:
            QMessageBox.warning(self, tr("Error"), tr("Las contraseñas no coinciden"))
            return

        exito, mensaje = self.auth_manager.recuperar_password_con_llave(username, key, password)

        if exito:
            QMessageBox.information(self, tr("Éxito"), mensaje)
            self.mostrar_login()
        else:
            QMessageBox.critical(self, tr("Error"), mensaje)

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
                self.usuario_logueado = self.auth_manager.obtener_usuario_actual()
                return True
            else:
                # Si falla, desactivar auto-login pero mantener recordar
                self._set_config('login_autologin', '0')
                return False

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error en autologin: {e}")
            return False
