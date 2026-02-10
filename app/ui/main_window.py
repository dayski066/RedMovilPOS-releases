"""
Ventana principal de la aplicación con navegación por sidebar
Incluye verificación automática de sesión y registro de actividad
"""
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QTabWidget, QLabel, QMessageBox, QStackedWidget,
                             QSizePolicy, QFrame, QMenu, QAction, QActionGroup, QApplication,
                             QSystemTrayIcon, QToolButton, QScrollArea)
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor
from app.ui.factura_tab_mejorada import FacturaTabMejorada
from app.ui.clientes_tab import ClientesTab
from app.ui.productos_tab_nuevo import ProductosTabNuevo
from app.ui.categorias_tab import CategoriasTab
from app.ui.historial_tab import HistorialTab
from app.ui.estadisticas_tab import EstadisticasTab
from app.ui.usuarios_tab import UsuariosTab
from app.ui.configuracion_tab import ConfiguracionTab
from app.ui.compras_nueva_tab import ComprasNuevaTab
from app.ui.compras_historial_tab import ComprasHistorialTab
from app.ui.reparaciones_nueva_tab import ReparacionesNuevaTab
from app.ui.reparaciones_historial_tab import ReparacionesHistorialTab
from app.ui.caja_movimientos_tab import CajaMovimientosTab
from app.ui.caja_cierre_tab import CajaCierreTab
from app.ui.caja_historial_tab import CajaHistorialTab
from app.ui.caja_tpv_tab import CajaTPVTab
from app.ui.caja_devoluciones_tab import CajaDevolucionesTab
from app.ui.caja_devoluciones_tab import CajaDevolucionesTab
from app.ui.styles import app_icon, apply_theme, get_icon_color, THEMES, NORD0, NORD8
from app.db.database import Database
from app.modules.caja_manager import CajaManager
from config import APP_VERSION, APP_NAME
from app.i18n import tr
from app.modules.updater import get_updater
from app.ui.update_dialog import UpdateDialog, comprobar_actualizaciones_silencioso
from app.ui.changelog_dialog import mostrar_changelog_si_necesario
from app.utils.logger import logger


class MainWindow(QMainWindow):
    # Señal para cerrar sesión (se conectará desde main.py)
    sesion_expirada = None  # Se definirá como pyqtSignal si se necesita

    def __init__(self, auth_manager):
        super().__init__()
        self.auth_manager = auth_manager
        self.usuario = auth_manager.obtener_usuario_actual()

        # Cargar datos de empresa desde BD
        self.company_info = self._cargar_datos_empresa()

        nombre_empresa = self.company_info['name'] or APP_NAME
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - {nombre_empresa} - {self.usuario['nombre_completo']}")
        self.setGeometry(50, 50, 1280, 1000)
        self.setMinimumSize(1280, 1000)
        self.setup_ui()
        self.apply_styles()

        # Timer para verificar sesión cada 5 minutos
        self.session_timer = QTimer(self)
        self.session_timer.timeout.connect(self._verificar_sesion)
        self.session_timer.start(5 * 60 * 1000)  # 5 minutos en milisegundos

        # Registrar actividad inicial
        self.auth_manager.registrar_actividad()

        # Bandera para evitar doble confirmación al cerrar sesión
        self._cerrando_sesion = False

        # Mostrar changelog si es versión nueva (después de 500ms para que cargue la UI)
        QTimer.singleShot(500, self._mostrar_changelog_si_nuevo)

        # Comprobar actualizaciones después de 3 segundos (no bloquear inicio)
        QTimer.singleShot(3000, self._comprobar_actualizaciones_inicio)

    def _mostrar_changelog_si_nuevo(self):
        """Muestra el diálogo de novedades si es una versión nueva"""
        try:
            db = Database()
            db.connect()
            mostrar_changelog_si_necesario(db, self)
            db.disconnect()
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error mostrando changelog: {e}")

    def _comprobar_actualizaciones_inicio(self):
        """Comprueba actualizaciones en segundo plano al iniciar"""
        def on_update_available(update_info):
            if update_info:
                # Mostrar diálogo de actualización
                dialog = UpdateDialog(update_info, self)
                dialog.exec_()

        comprobar_actualizaciones_silencioso(on_update_available, self)

    def showEvent(self, event):
        """Se ejecuta cuando la ventana se muestra por primera vez"""
        super().showEvent(event)
        # Verificar caja pendiente DESPUÉS de que la ventana esté visible
        # Usar bandera para ejecutar solo una vez
        if not hasattr(self, '_caja_verificada'):
            self._caja_verificada = True
            # Pequeño delay para asegurar que la UI esté completamente renderizada
            QTimer.singleShot(300, self._verificar_caja_pendiente)

    def _verificar_caja_pendiente(self):
        """Verifica si hay una caja de día anterior sin cerrar y muestra aviso"""
        try:
            from datetime import date
            db = Database()
            db.connect()
            caja_manager = CajaManager(db)

            fecha_hoy = date.today().strftime('%Y-%m-%d')
            apertura_pendiente = caja_manager.obtener_apertura_sin_cierre()

            if apertura_pendiente and apertura_pendiente['fecha'] != fecha_hoy:
                fecha_pendiente = apertura_pendiente['fecha']
                QMessageBox.warning(
                    self,
                    tr("Cierre de Caja Pendiente"),
                    tr("Hay una caja del día") + f" {fecha_pendiente} " + tr("sin cerrar.") + "\n\n" +
                    tr("Debe cerrar esa caja antes de continuar.") + "\n\n" +
                    "👉 " + tr("Vaya a") + ": " + tr("Caja") + " → " + tr("Movimientos") + "\n" +
                    "👉 " + tr("Use el botón") + " 🔒 " + tr("Cerrar Caja")
                )

            db.disconnect()
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error verificando caja pendiente: {e}")

    def _comprobar_actualizaciones_manual(self):
        """Comprueba actualizaciones manualmente desde el menú"""
        from PyQt5.QtWidgets import QProgressDialog
        from PyQt5.QtCore import Qt

        # Mostrar diálogo de progreso
        progress = QProgressDialog(tr("Comprobando actualizaciones..."), None, 0, 0, self)
        progress.setWindowTitle(tr("Actualización"))
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()
        QApplication.processEvents()

        try:
            updater = get_updater()
            update_info = updater.comprobar_actualizacion()

            progress.close()

            if update_info:
                dialog = UpdateDialog(update_info, self)
                dialog.exec_()
            else:
                QMessageBox.information(
                    self,
                    tr("Actualización"),
                    tr("Ya tienes la última versión.") + f"\n\n{tr('Versión actual')}: {APP_VERSION}",
                    QMessageBox.Ok
                )
        except (OSError, ValueError, RuntimeError) as e:
            progress.close()
            QMessageBox.warning(
                self,
                tr("Error"),
                tr("No se pudo comprobar actualizaciones.") + f"\n\n{str(e)}",
                QMessageBox.Ok
            )

    def _verificar_sesion(self):
        """Verifica si la sesión sigue activa, si no, cierra la aplicación"""
        if not self.auth_manager.verificar_sesion_activa():
            self.session_timer.stop()
            QMessageBox.warning(
                self,
                tr("Sesión Expirada"),
                tr("Tu sesión ha expirado por inactividad.") + "\n" +
                tr("Por favor, inicia sesión nuevamente."),
                QMessageBox.Ok
            )
            # Marcar para evitar diálogo de confirmación en closeEvent
            self._cerrando_sesion = True
            self.close()

    def registrar_actividad_usuario(self):
        """Registra actividad del usuario para renovar tiempo de sesión"""
        self.auth_manager.registrar_actividad()

    def mousePressEvent(self, event):
        """Registra actividad en cada clic del mouse"""
        self.registrar_actividad_usuario()
        super().mousePressEvent(event)

    def keyPressEvent(self, event):
        """Registra actividad en cada tecla presionada"""
        self.registrar_actividad_usuario()
        super().keyPressEvent(event)

    def _cargar_datos_empresa(self):
        """Carga los datos del establecimiento del usuario actual"""
        datos = {
            'name': '',
            'nif': '',
            'address': '',
            'city': '',
            'phone': '',
            'logo_path': ''
        }

        try:
            db = Database()
            db.connect()

            # Obtener establecimiento del usuario actual
            establecimiento_id = self.usuario.get('establecimiento_id')

            if establecimiento_id:
                establecimiento = db.fetch_one(
                    "SELECT * FROM establecimientos WHERE id = ? AND activo = 1",
                    (establecimiento_id,)
                )

                if establecimiento:
                    datos['name'] = establecimiento.get('nombre') or ''
                    datos['nif'] = establecimiento.get('nif') or ''
                    datos['address'] = establecimiento.get('direccion') or ''
                    datos['city'] = ''  # No hay campo ciudad en establecimientos
                    datos['phone'] = establecimiento.get('telefono') or ''
                    datos['logo_path'] = establecimiento.get('logo_path') or ''

            # Si no hay establecimiento, intentar con el primero disponible
            if not datos['name']:
                establecimiento = db.fetch_one(
                    "SELECT * FROM establecimientos WHERE activo = 1 ORDER BY id LIMIT 1"
                )
                if establecimiento:
                    datos['name'] = establecimiento.get('nombre') or ''
                    datos['nif'] = establecimiento.get('nif') or ''
                    datos['address'] = establecimiento.get('direccion') or ''
                    datos['phone'] = establecimiento.get('telefono') or ''
                    datos['logo_path'] = establecimiento.get('logo_path') or ''

            db.disconnect()
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error cargando datos de establecimiento: {e}")

        return datos

    def setup_ui(self):
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header
        header = self.create_header()
        main_layout.addWidget(header)

        # Contenedor para sidebar + contenido
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self.sidebar = self.create_sidebar()
        content_layout.addWidget(self.sidebar)

        # Contenido (páginas)
        self.stacked_widget = QStackedWidget()
        self.create_content_pages()
        content_layout.addWidget(self.stacked_widget)

        main_layout.addLayout(content_layout)

        # Establecer página inicial (Home)
        self.switch_page(0)

    def create_sidebar(self):
        """Crea la barra lateral de navegación con diseño responsivo"""
        sidebar_widget = QWidget()
        sidebar_widget.setFixedWidth(250)
        sidebar_widget.setObjectName("sidebar")
        
        # Layout principal del sidebar (Vertical)
        main_sidebar_layout = QVBoxLayout(sidebar_widget)
        main_sidebar_layout.setContentsMargins(0, 0, 0, 0)
        main_sidebar_layout.setSpacing(0)

        # 1. Título del sidebar (Fijo arriba)
        sidebar_title = QLabel(tr("NAVEGACIÓN"))
        sidebar_title.setObjectName("sidebarTitle")
        sidebar_title.setAlignment(Qt.AlignCenter)
        sidebar_title.setMinimumHeight(40)
        main_sidebar_layout.addWidget(sidebar_title)

        # 2. Área de Scroll para los botones de navegación
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        # Contenedor para los botones
        nav_container = QWidget()
        nav_container.setObjectName("navContainer")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        def add_divider(layout):
            line = QFrame()
            line.setObjectName("divider")
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            layout.addWidget(line)

        # Datos de navegación
        sections = [
            [("mdi.home-variant-outline", tr("Home"), 0)],
            [("mdi.cash-register", tr("Ventas"), 1)],
            [("mdi.cart-outline", tr("Compras"), 2)],
            [("mdi.account-group-outline", tr("Clientes"), 3)],
            [("mdi.tools", tr("SAT"), 4)],
            [("mdi.wallet", tr("Caja"), 5)],
            [("mdi.warehouse", tr("Inventario"), 6)]
        ]

        if self.auth_manager.is_admin():
            sections.append([("mdi.cog-outline", tr("Ajustes"), 7)])

        self.nav_buttons = []
        current_theme = QApplication.instance().property("theme") or "dark"
        icon_color = get_icon_color(current_theme)

        for sec_index, items in enumerate(sections):
            if sec_index > 0:
                add_divider(nav_layout)
            for icon_name, label, page_index in items:
                btn = QPushButton(label)
                btn.setObjectName("navButton")
                btn.setIcon(app_icon(icon_name, color=icon_color, size=20))
                btn.setIconSize(QSize(20, 20))
                btn.setCheckable(True)
                btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                btn.setMinimumHeight(45)
                btn.setProperty("icon_name", icon_name)
                
                # Aplicar estilo inline para forzar el borde en estado checked
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #D8DEE9;
                        text-align: left;
                        padding: 14px 20px;
                        border: none;
                        border-radius: 12px;
                        margin: 6px 12px;
                        font-size: 15px;
                        font-weight: 600;
                        min-height: 46px;
                    }
                    QPushButton:hover {
                        background-color: #3B4252;
                        color: #ECEFF4;
                        border: 2px solid #4C566A;
                        padding: 12px 18px;
                    }
                    QPushButton:checked {
                        background-color: rgba(136, 192, 208, 0.15);
                        color: #88C0D0;
                        border: 2px solid #88C0D0;
                        border-radius: 12px;
                        padding: 12px 18px;
                        font-weight: bold;
                    }
                """)
                
                btn.clicked.connect(lambda checked, idx=page_index: self.switch_page(idx))
                nav_layout.addWidget(btn)
                self.nav_buttons.append(btn)

        nav_layout.addStretch()
        scroll.setWidget(nav_container)
        main_sidebar_layout.addWidget(scroll, 1) # Factor 1 para que ocupe el centro

        # 3. Logo de la empresa en el pie (Fijo abajo)
        self.logo_container = QWidget()
        self.logo_container.setObjectName("logoContainer")
        logo_layout = QVBoxLayout(self.logo_container)
        logo_layout.setContentsMargins(5, 10, 5, 10)
        logo_layout.setSpacing(0)

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setMaximumHeight(160) # Restaurado para evitar recortes
        self.logo_label.setStyleSheet("border: none; padding: 0px;")
        logo_layout.addWidget(self.logo_label)

        main_sidebar_layout.addWidget(self.logo_container, 0) # Factor 0 para que no sea aplastado

        # Cargar logo
        self.cargar_logo_sidebar()

        return sidebar_widget

    def create_content_pages(self):
        """Crea las páginas de contenido"""
        # Página 0: Home (Estadísticas)
        self.estadisticas_tab = EstadisticasTab()
        self.stacked_widget.addWidget(self.estadisticas_tab)

        # Página 1: Ventas (Tabs: Nueva Venta + Historial)
        ventas_widget = QWidget()
        ventas_layout = QVBoxLayout(ventas_widget)
        ventas_tabs = QTabWidget()
        self.factura_tab = FacturaTabMejorada()
        self.historial_tab = HistorialTab(self.auth_manager)
        ventas_tabs.addTab(self.factura_tab, tr("Nueva Venta"))
        ventas_tabs.addTab(self.historial_tab, tr("Historial"))
        ventas_layout.addWidget(ventas_tabs)
        self.stacked_widget.addWidget(ventas_widget)

        # Página 2: Compras (Tabs: Nueva Compra + Historial)
        compras_widget = QWidget()
        compras_layout = QVBoxLayout(compras_widget)
        compras_tabs = QTabWidget()
        self.compras_nueva_tab = ComprasNuevaTab()
        self.compras_historial_tab = ComprasHistorialTab(self.auth_manager)
        compras_tabs.addTab(self.compras_nueva_tab, tr("Nueva Compra"))
        compras_tabs.addTab(self.compras_historial_tab, tr("Historial"))
        compras_tabs.currentChanged.connect(lambda index: self.compras_historial_tab.limpiar_filtros() if index == 1 else None)
        compras_layout.addWidget(compras_tabs)
        self.stacked_widget.addWidget(compras_widget)

        # Página 3: Clientes
        self.clientes_tab = ClientesTab(self.auth_manager)
        self.stacked_widget.addWidget(self.clientes_tab)

        # Página 4: SAT (Tabs: Nueva Reparación + Historial)
        sat_widget = QWidget()
        sat_layout = QVBoxLayout(sat_widget)
        sat_tabs = QTabWidget()
        self.reparaciones_nueva_tab = ReparacionesNuevaTab()
        self.reparaciones_historial_tab = ReparacionesHistorialTab(self.auth_manager)
        sat_tabs.addTab(self.reparaciones_nueva_tab, tr("Nueva Reparación"))
        sat_tabs.addTab(self.reparaciones_historial_tab, tr("Historial"))
        sat_layout.addWidget(sat_tabs)
        self.stacked_widget.addWidget(sat_widget)

        # Página 5: Caja (Tabs: TPV + Historial + Movimientos + Devoluciones + Cierre)
        caja_widget = QWidget()
        caja_layout = QVBoxLayout(caja_widget)
        caja_tabs = QTabWidget()
        self.caja_tpv_tab = CajaTPVTab()
        self.caja_historial_tab = CajaHistorialTab()
        self.caja_movimientos_tab = CajaMovimientosTab(self.auth_manager)
        self.caja_devoluciones_tab = CajaDevolucionesTab()
        self.caja_cierre_tab = CajaCierreTab(self.auth_manager)
        caja_tabs.addTab(self.caja_tpv_tab, tr("TPV"))
        caja_tabs.addTab(self.caja_historial_tab, tr("Historial"))
        caja_tabs.addTab(self.caja_movimientos_tab, tr("Movimientos"))
        caja_tabs.addTab(self.caja_devoluciones_tab, tr("Devoluciones"))
        caja_tabs.addTab(self.caja_cierre_tab, tr("Cierre Diario"))
        caja_layout.addWidget(caja_tabs)
        self.stacked_widget.addWidget(caja_widget)

        # Página 6: Inventario (Tabs: Productos + Categorías)
        inventario_widget = QWidget()
        inventario_layout = QVBoxLayout(inventario_widget)
        inventario_tabs = QTabWidget()
        self.productos_tab = ProductosTabNuevo(self.auth_manager)
        self.categorias_tab = CategoriasTab()
        inventario_tabs.addTab(self.productos_tab, tr("Productos"))
        inventario_tabs.addTab(self.categorias_tab, tr("Categorías"))
        inventario_layout.addWidget(inventario_tabs)
        self.stacked_widget.addWidget(inventario_widget)

        # Página 7: Ajustes (solo admin)
        if self.auth_manager.is_admin():
            # Usar directamente ConfiguracionTab que ya tiene todo integrado
            self.configuracion_tab = ConfiguracionTab(self.auth_manager)
            self.stacked_widget.addWidget(self.configuracion_tab)

    def switch_page(self, index):
        """Cambia a la página indicada y actualiza iconos"""
        current_theme = QApplication.instance().property("theme") or "dark"
        icon_color = get_icon_color(current_theme)
        
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(False)
            icon_name = btn.property("icon_name")
            if icon_name:
                btn.setIcon(app_icon(icon_name, color=icon_color, size=20))

        if index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)
            icon_name = self.nav_buttons[index].property("icon_name")
            if icon_name:
                # Usar color turquesa (NORD8) para el icono seleccionado
                from app.ui.styles import NORD8
                self.nav_buttons[index].setIcon(app_icon(icon_name, color=NORD8, size=20))

        # Refrescar estadísticas si vamos a Home (índice 0)
        if index == 0:
            self.estadisticas_tab.cargar_estadisticas()

        self.stacked_widget.setCurrentIndex(index)

    def create_header(self):
        """Crea el header con información de la empresa (alto contraste)"""
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(20, 14, 20, 14)
        header_layout.setSpacing(14)

        # Botón menú hamburguesa (3 barras)
        self.btn_menu = QPushButton()
        self.btn_menu.setIcon(app_icon("mdi.menu", color="#ffffff", size=24))
        self.btn_menu.setIconSize(QSize(24, 24))
        self.btn_menu.setObjectName("btnHamburger")
        self.btn_menu.setFixedSize(44, 44)
        self.btn_menu.setCursor(Qt.PointingHandCursor)
        self.btn_menu.clicked.connect(self._mostrar_menu_principal)
        header_layout.addWidget(self.btn_menu)

        # Logo/Título - usar datos de BD o nombre por defecto
        nombre_empresa = self.company_info['name'] or APP_NAME
        title = QLabel(f"{nombre_empresa} v{APP_VERSION}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #ffffff;")

        # Información - mostrar solo si hay datos configurados
        if self.company_info['nif'] or self.company_info['city'] or self.company_info['phone']:
            partes = []
            if self.company_info['nif']:
                partes.append(f"NIF: {self.company_info['nif']}")
            if self.company_info['city']:
                partes.append(self.company_info['city'])
            if self.company_info['phone']:
                partes.append(f"Tel: {self.company_info['phone']}")
            info_text = " • ".join(partes)
            info = QLabel(info_text)
            info.setStyleSheet("color: #cccccc; font-size: 13px;")
        else:
            info = QLabel(tr("Configure su empresa en Ajustes"))
            info.setStyleSheet("color: #969696; font-size: 12px; font-style: italic;")

        # Info usuario (alto contraste)
        usuario_info = QLabel(f"👤 {self.usuario['nombre_completo']} ({self.usuario['rol'].upper()})")
        usuario_info.setObjectName("usuarioInfo")

        # Botón cerrar sesión (alto contraste)
        btn_logout = QPushButton("🚪 " + tr("Cerrar Sesión"))
        btn_logout.setObjectName("btnLogout")
        btn_logout.clicked.connect(self.cerrar_sesion)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(info)
        header_layout.addSpacing(14)
        header_layout.addWidget(usuario_info)
        header_layout.addWidget(btn_logout)

        # Header con estilo dinámico desde styles.py
        header_widget.setObjectName("header")


        return header_widget

    def _mostrar_menu_principal(self):
        """Muestra el menú principal desplegable"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d30;
                border: 1px solid #3e3e42;
                border-radius: 8px;
                padding: 8px 0;
            }
            QMenu::item {
                background-color: transparent;
                color: #cccccc;
                padding: 10px 20px;
                font-size: 13px;
            }
            QMenu::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #3e3e42;
                margin: 6px 12px;
            }
            QMenu::item:disabled {
                color: #6e6e6e;
            }
        """)

        # Acción: Acerca de
        action_about = QAction(app_icon("mdi.information-outline", color="#cccccc", size=16), tr("Acerca de..."), self)
        action_about.triggered.connect(self._mostrar_acerca_de)
        menu.addAction(action_about)

        # Acción: Información de Licencia
        action_license = QAction(app_icon("mdi.license", color="#cccccc", size=16), tr("Información de Licencia"), self)
        action_license.triggered.connect(self._mostrar_info_licencia)
        menu.addAction(action_license)

        # Acción: Buscar Actualizaciones
        action_update = QAction(app_icon("mdi.update", color="#cccccc", size=16), tr("Buscar Actualizaciones"), self)
        action_update.triggered.connect(self._comprobar_actualizaciones_manual)
        menu.addAction(action_update)

        menu.addSeparator()

        # Acción: Cambiar Tema (Luz / Oscuridad)
        tema_actual = QApplication.instance().property("theme") or "dark"
        icon_theme = "mdi.weather-sunny" if tema_actual == "dark" else "mdi.weather-night"
        text_theme = tr("Activar Modo Claro") if tema_actual == "dark" else tr("Activar Modo Oscuro")
        
        action_theme = QAction(app_icon(icon_theme, color="#cccccc", size=16), text_theme, self)
        action_theme.triggered.connect(self._cambiar_tema)
        menu.addAction(action_theme)

        menu.addSeparator()

        # Submenú: Idioma
        idioma_menu = menu.addMenu(app_icon("mdi.translate", color="#cccccc", size=16), tr("Idioma"))
        idioma_menu.setStyleSheet(menu.styleSheet())

        idiomas = [
            ("es", "Español"),
            ("en", "English"),
            ("fr", "Français"),
            ("pt", "Português")
        ]

        idioma_group = QActionGroup(self)
        idioma_group.setExclusive(True)

        # Obtener idioma actual (por defecto español)
        idioma_actual = self._obtener_idioma_actual()

        for codigo, nombre in idiomas:
            action = QAction(nombre, self)
            action.setCheckable(True)
            action.setChecked(codigo == idioma_actual)
            action.setData(codigo)
            action.triggered.connect(lambda checked, c=codigo: self._cambiar_idioma(c))
            idioma_group.addAction(action)
            idioma_menu.addAction(action)

        menu.addSeparator()

        # Acción: Cerrar Sesión
        action_logout = QAction(app_icon("mdi.logout", color="#cccccc", size=16), tr("Cerrar Sesión"), self)
        action_logout.triggered.connect(self.cerrar_sesion)
        menu.addAction(action_logout)

        # Mostrar menú debajo del botón
        menu.exec_(self.btn_menu.mapToGlobal(self.btn_menu.rect().bottomLeft()))

    def _obtener_idioma_actual(self):
        """Obtiene el idioma actual desde la configuración"""
        try:
            db = Database()
            db.connect()
            result = db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'idioma'"
            )
            db.disconnect()
            if result:
                return result['valor']
        except (OSError, ValueError, RuntimeError):
            pass
        return "es"  # Español por defecto

    def _cambiar_idioma(self, codigo):
        """Cambia el idioma de la aplicación"""
        try:
            db = Database()
            db.connect()
            # Verificar si existe la configuración
            existe = db.fetch_all(
                "SELECT clave FROM configuracion WHERE clave = 'idioma'"
            )
            if existe:
                db.execute_query(
                    "UPDATE configuracion SET valor = ? WHERE clave = 'idioma'",
                    (codigo,)
                )
            else:
                db.execute_query(
                    "INSERT INTO configuracion (clave, valor) VALUES ('idioma', ?)",
                    (codigo,)
                )
            db.disconnect()

            # Refrescar el traductor inmediatamente
            from app.i18n import get_translator
            get_translator().refresh_language()

            QMessageBox.information(
                self,
                tr("Idioma"),
                tr("El idioma se ha actualizado. Los cambios se aplicarán completamente al cerrar sesión o reiniciar."),
                QMessageBox.Ok
            )
        except (OSError, ValueError, RuntimeError) as e:
            QMessageBox.warning(
                self,
                tr("Error"),
                f"{tr('Error')}: {e}",
                QMessageBox.Ok
            )


    def _cambiar_tema(self):
        """Alterna entre tema claro y oscuro"""
        app = QApplication.instance()
        tema_actual = app.property("theme") or "dark"
        nuevo_tema = "light" if tema_actual == "dark" else "dark"
        
        try:
            # Guardar preferencia
            db = Database()
            db.connect()
            
            # Upsert configuración tema
            existe = db.fetch_all("SELECT clave FROM configuracion WHERE clave = 'tema'")
            if existe:
                db.execute_query("UPDATE configuracion SET valor = ? WHERE clave = 'tema'", (nuevo_tema,))
            else:
                db.execute_query("INSERT INTO configuracion (clave, valor) VALUES ('tema', ?)", (nuevo_tema,))
                
            db.disconnect()
            
            # Aplicar tema
            apply_theme(app, nuevo_tema)
            
            # Forzar actualización de iconos del sidebar
            # Simplemente llamando a switch_page con el índice actual recreará los iconos con el color correcto
            current_index = self.stacked_widget.currentIndex()
            self.switch_page(current_index)
            
            # Notificar (opcional, el cambio es visual inmediato)
            # QMessageBox.information(self, tr("Tema Cambiado"), tr("El tema se ha actualizado."))
            
        except (OSError, ValueError, RuntimeError) as e:
            QMessageBox.warning(self, tr("Error"), f"Error cambiando tema: {e}")
    def _mostrar_acerca_de(self):
        """Muestra el diálogo Acerca de"""
        from app.ui.about_dialog import AboutDialog
        dialog = AboutDialog(self)
        dialog.exec_()

    def _mostrar_info_licencia(self):
        """Muestra el diálogo de información de licencia"""
        from app.ui.license_info_dialog import LicenseInfoDialog
        dialog = LicenseInfoDialog(self)
        dialog.exec_()

    def cerrar_sesion(self):
        """Cierra la sesión del usuario actual"""
        respuesta = QMessageBox.question(
            self,
            tr("Cerrar Sesión"),
            tr("¿Deseas cerrar sesión?"),
            QMessageBox.Yes | QMessageBox.No
        )

        if respuesta == QMessageBox.Yes:
            self._cerrando_sesion = True  # Evitar doble confirmación
            self.auth_manager.logout()
            self.close()

    def cargar_logo_sidebar(self):
        """Carga el logo del establecimiento en el sidebar"""
        from PyQt5.QtGui import QPixmap
        import os

        try:
            logo_path = self.company_info.get('logo_path', '')

            if logo_path and os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    # Calcular escala para maximizar el ancho
                    ancho_original = pixmap.width()
                    alto_original = pixmap.height()

                    # Siempre escalar al ancho máximo (240px)
                    ancho_objetivo = 240
                    factor_escala = ancho_objetivo / ancho_original if ancho_original > 0 else 1
                    alto_objetivo = int(alto_original * factor_escala)

                    # Limitar la altura si es demasiado grande
                    if alto_objetivo > 150:
                        alto_objetivo = 150
                        factor_escala = alto_objetivo / alto_original if alto_original > 0 else 1
                        ancho_objetivo = int(ancho_original * factor_escala)

                    scaled_pixmap = pixmap.scaled(
                        ancho_objetivo, alto_objetivo,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    self.logo_label.setPixmap(scaled_pixmap)
                    self.logo_container.setVisible(True)
                else:
                    self.logo_container.setVisible(False)
            else:
                self.logo_container.setVisible(False)

        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error cargando logo: {e}")
            self.logo_container.setVisible(False)

    def apply_styles(self):
        """Aplica estilos modernos DARK MODE"""
        # Los estilos principales vienen del stylesheet global en main.py
        # Aquí solo añadimos ajustes específicos si es necesario
        pass

    def closeEvent(self, event):
        """Muestra confirmación antes de cerrar la aplicación"""
        # Si ya se confirmó cierre de sesión, no preguntar de nuevo
        if self._cerrando_sesion:
            event.accept()
            return

        respuesta = QMessageBox.question(
            self,
            tr("Confirmar Cierre"),
            tr("¿Estás seguro de que deseas salir de la aplicación?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No  # Botón por defecto = No (previene cierre accidental)
        )

        if respuesta == QMessageBox.Yes:
            event.accept()  # Permite cerrar
        else:
            event.ignore()  # Cancela el cierre
