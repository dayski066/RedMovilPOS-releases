"""
Pestaña de Configuración General
Incluye: Establecimiento, Impresoras, Usuarios
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QTabWidget, QFormLayout, QGroupBox,
                             QComboBox, QMessageBox, QFileDialog, QCheckBox)
from PyQt5.QtPrintSupport import QPrinterInfo
from PyQt5.QtCore import Qt
from app.i18n import tr
from app.db.database import Database
from app.ui.usuarios_tab import UsuariosTab
import json
from app.utils.logger import logger

class ConfiguracionTab(QWidget):
    def __init__(self, auth_manager):
        super().__init__()
        self.db = Database()
        self.db.connect()
        self.auth_manager = auth_manager
        self.setup_ui()
        self.cargar_configuracion()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Título
        header = QLabel(tr("Configuración del Sistema"))
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px; color: #ffffff;")
        layout.addWidget(header)

        # Pestañas de configuración
        self.tabs = QTabWidget()

        # 1. Pestaña Establecimientos (gestión de múltiples establecimientos)
        from app.ui.establecimientos_tab import EstablecimientosTab
        self.tab_establecimientos = EstablecimientosTab(self.auth_manager)
        self.tabs.addTab(self.tab_establecimientos, tr("Establecimientos"))

        # 2. Pestaña Impresoras
        self.tab_impresoras = QWidget()
        self.setup_impresoras_tab()
        self.tabs.addTab(self.tab_impresoras, tr("Impresoras"))

        # 3. Pestaña Seguridad/Login
        self.tab_seguridad = QWidget()
        self.setup_seguridad_tab()
        self.tabs.addTab(self.tab_seguridad, tr("Seguridad"))

        # 4. Pestaña Usuarios (Reutilizamos el componente existente)
        self.tab_usuarios = UsuariosTab(self.auth_manager)
        self.tabs.addTab(self.tab_usuarios, tr("Usuarios"))

        # 5. Pestaña Roles y Permisos
        from app.ui.roles_tab import RolesTab
        self.tab_roles = RolesTab(self.db, self.auth_manager)
        self.tabs.addTab(self.tab_roles, tr("Roles"))

        # 6. Pestaña Operaciones (historial de auditoría - solo admin)
        if self.auth_manager:
            usuario = self.auth_manager.obtener_usuario_actual()
            if usuario and usuario.get('rol') == 'admin':
                from app.ui.operaciones_tab import OperacionesTab
                self.tab_operaciones = OperacionesTab(self.auth_manager)
                self.tabs.addTab(self.tab_operaciones, "📋 " + tr("Operaciones"))

        layout.addWidget(self.tabs)

    def setup_impresoras_tab(self):
        layout = QVBoxLayout(self.tab_impresoras)

        group_printers = QGroupBox(tr("Asignación de Dispositivos"))
        form_printers = QFormLayout()
        form_printers.setRowWrapPolicy(QFormLayout.WrapLongRows)

        # Obtener lista de impresoras del sistema
        printers = QPrinterInfo.availablePrinterNames()
        printers.insert(0, "--- " + tr("Seleccionar Impresora") + " ---")  # Opción por defecto

        # 1. Impresora General (A4 - Facturas/Contratos)
        self.printer_general = QComboBox()
        self.printer_general.addItems(printers)
        form_printers.addRow("🖨️ " + tr("General (A4)") + ":", self.printer_general)
        form_printers.addRow(QLabel("<small style='color:gray'>" + tr("Para facturas y contratos PDF") + "</small>"))

        # Opción de doble cara
        self.printer_duplex = QCheckBox(tr("Imprimir a doble cara (si la impresora lo soporta)"))
        self.printer_duplex.setStyleSheet("margin-left: 20px; color: #2c3e50;")
        form_printers.addRow("", self.printer_duplex)

        form_printers.addRow(QLabel(""))  # Separador

        # 2. Impresora Tickets (Termica)
        self.printer_ticket = QComboBox()
        self.printer_ticket.addItems(printers)
        form_printers.addRow("🧾 " + tr("Tickets (Térmica)") + ":", self.printer_ticket)
        form_printers.addRow(QLabel("<small style='color:gray'>" + tr("Para tickets de venta rápida") + "</small>"))

        form_printers.addRow(QLabel(""))  # Separador

        # 3. Impresora Etiquetas (Pegatinas)
        self.printer_labels = QComboBox()
        self.printer_labels.addItems(printers)
        form_printers.addRow("🏷️ " + tr("Etiquetas") + ":", self.printer_labels)
        form_printers.addRow(QLabel("<small style='color:gray'>" + tr("Para códigos de barras y etiquetas de reparación") + "</small>"))

        group_printers.setLayout(form_printers)
        layout.addWidget(group_printers)
        
        # === Grupo Escáneres ===
        group_scanners = QGroupBox(tr("Escáneres de Documentos"))
        form_scanners = QFormLayout()
        form_scanners.setRowWrapPolicy(QFormLayout.WrapLongRows)

        # Escáner principal
        self.scanner_device = QComboBox()
        self.scanner_device.addItem("--- " + tr("Seleccionar Escáner") + " ---")

        # Intentar listar escáneres WIA (Windows)
        scanners = self.listar_escaneres_wia()
        if scanners:
            self.scanner_device.addItems(scanners)
        else:
            self.scanner_device.addItem(tr("No se detectaron escáneres"))

        self.scanner_device.setEditable(True)
        form_scanners.addRow("📄 " + tr("Escáner Principal") + ":", self.scanner_device)

        group_scanners.setLayout(form_scanners)
        layout.addWidget(group_scanners)

        # === Botones de prueba ===
        btn_layout_test = QHBoxLayout()

        btn_test_printer = QPushButton("🖨️ " + tr("Probar Impresora"))
        btn_test_printer.clicked.connect(self.test_impresora)
        btn_layout_test.addWidget(btn_test_printer)

        btn_test_scanner = QPushButton("📄 " + tr("Probar Escáner"))
        btn_test_scanner.clicked.connect(self.test_escaner)
        btn_layout_test.addWidget(btn_test_scanner)

        btn_layout_test.addStretch()
        layout.addLayout(btn_layout_test)

        layout.addStretch()

        # === Botón Guardar Impresoras ===
        btn_layout_save = QHBoxLayout()
        btn_layout_save.addStretch()
        btn_guardar_impresoras = QPushButton(tr("Guardar Configuración de Impresoras"))
        btn_guardar_impresoras.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #A3BE8C; border: 2px solid #A3BE8C;
                font-weight: bold; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #A3BE8C; color: #2E3440; }
        """)
        btn_guardar_impresoras.clicked.connect(self.guardar_impresoras)
        btn_layout_save.addWidget(btn_guardar_impresoras)
        layout.addLayout(btn_layout_save)

    def setup_seguridad_tab(self):
        """Configuración de seguridad y opciones de login"""
        layout = QVBoxLayout(self.tab_seguridad)

        # === Opciones de Login ===
        group_login = QGroupBox(tr("Opciones de Inicio de Sesión"))
        form_login = QFormLayout()
        form_login.setRowWrapPolicy(QFormLayout.WrapLongRows)

        # Recordar usuario
        self.check_recordar_usuario = QCheckBox(tr("Recordar nombre de usuario"))
        self.check_recordar_usuario.setToolTip(tr("Guarda el último usuario para no tener que escribirlo"))
        form_login.addRow(self.check_recordar_usuario)

        # Auto-login
        self.check_autologin = QCheckBox(tr("Inicio de sesión automático"))
        self.check_autologin.setToolTip(tr("Inicia sesión automáticamente al abrir el programa"))
        self.check_autologin.setStyleSheet("color: #e67e22; font-weight: bold;")
        form_login.addRow(self.check_autologin)

        # Advertencia
        warning = QLabel("⚠️ " + tr("El auto-login guarda las credenciales localmente.") + "\n" +
                        tr("No lo actives en ordenadores compartidos."))
        warning.setStyleSheet("""
            background-color: #fff3cd;
            color: #856404;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 10px;
            font-size: 10px;
        """)
        warning.setWordWrap(True)
        form_login.addRow(warning)

        group_login.setLayout(form_login)
        layout.addWidget(group_login)

        # === Protección de Operaciones Críticas ===
        group_proteccion = QGroupBox(tr("Protección de Operaciones Críticas"))
        form_proteccion = QFormLayout()
        form_proteccion.setRowWrapPolicy(QFormLayout.WrapLongRows)

        # Activar/Desactivar protección
        self.check_proteccion_operaciones = QCheckBox(tr("Solicitar contraseña en operaciones críticas"))
        self.check_proteccion_operaciones.setToolTip(tr("Requiere contraseña para eliminar, editar o realizar acciones sensibles"))
        self.check_proteccion_operaciones.setChecked(True)  # Por defecto activado
        # Guardar automáticamente cuando cambia el estado
        self.check_proteccion_operaciones.stateChanged.connect(self._guardar_proteccion_operaciones)
        form_proteccion.addRow(self.check_proteccion_operaciones)

        # Info
        info_proteccion = QLabel("🔒 " + tr("Operaciones protegidas: eliminar ventas, compras, reparaciones, clientes, productos, etc."))
        info_proteccion.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        info_proteccion.setWordWrap(True)
        form_proteccion.addRow(info_proteccion)

        group_proteccion.setLayout(form_proteccion)
        layout.addWidget(group_proteccion)

        # === Llave de Recuperación ===
        group_recovery = QGroupBox(tr("Llave de Recuperación"))
        form_recovery = QVBoxLayout()

        info_recovery = QLabel(
            tr("La llave de recuperación permite restablecer tu contraseña si la olvidas.") + "\n" +
            tr("Guárdala en un lugar seguro.")
        )
        info_recovery.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        info_recovery.setWordWrap(True)
        form_recovery.addWidget(info_recovery)

        # Botón para ver llave actual
        btn_ver_llave = QPushButton("🔑 " + tr("Ver mi Llave de Recuperación"))
        btn_ver_llave.clicked.connect(self.mostrar_llave_actual)
        btn_ver_llave.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #B48EAD; border: 2px solid #B48EAD;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: transparent; color: #B48EAD; border: 2px solid #B48EAD; }
        """)
        form_recovery.addWidget(btn_ver_llave)
        
        # Botón para regenerar llave
        btn_regenerar = QPushButton("🔄 " + tr("Regenerar Llave (genera una nueva)"))
        btn_regenerar.clicked.connect(self.regenerar_llave_actual)
        btn_regenerar.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #BF616A; border: 2px solid #BF616A;
                border: none;
                border-radius: 5px;
                padding: 10px;
            }
            QPushButton:hover { background-color: transparent; color: #BF616A; border: 2px solid #BF616A; }
        """)
        form_recovery.addWidget(btn_regenerar)
        
        group_recovery.setLayout(form_recovery)
        layout.addWidget(group_recovery)
        
        # === Preferencias Regionales ===
        group_regional = QGroupBox(tr("Preferencias Regionales"))
        form_regional = QFormLayout()
        form_regional.setRowWrapPolicy(QFormLayout.WrapLongRows)

        self.combo_idioma = QComboBox()
        self.combo_idioma.addItem(tr("Español"), "es")
        self.combo_idioma.addItem(tr("English"), "en")
        self.combo_idioma.addItem(tr("Français"), "fr")
        form_regional.addRow(tr("Idioma") + ":", self.combo_idioma)
        
        group_regional.setLayout(form_regional)
        layout.addWidget(group_regional)

        layout.addStretch()

        # === Botón Guardar Seguridad ===
        btn_layout_save = QHBoxLayout()
        btn_layout_save.addStretch()
        btn_guardar_seguridad = QPushButton(tr("Guardar Configuración de Seguridad"))
        btn_guardar_seguridad.setStyleSheet("""
            QPushButton {
                background-color: transparent; color: #A3BE8C; border: 2px solid #A3BE8C;
                font-weight: bold; padding: 10px 20px; border-radius: 5px;
            }
            QPushButton:hover { background-color: #A3BE8C; color: #2E3440; }
        """)
        btn_guardar_seguridad.clicked.connect(self.guardar_seguridad)
        btn_layout_save.addWidget(btn_guardar_seguridad)
        layout.addLayout(btn_layout_save)

    def mostrar_llave_actual(self):
        """Muestra la llave de recuperación del usuario actual"""
        if not self.auth_manager.usuario_actual:
            QMessageBox.warning(self, tr("Error"), tr("No hay usuario logueado"))
            return

        llave = self.auth_manager.obtener_llave_usuario(self.auth_manager.usuario_actual['id'])
        if llave:
            QMessageBox.information(self, tr("Tu Llave de Recuperación"),
                f"🔑 {tr('Tu llave es')}:\n\n{llave}\n\n" +
                tr("Guárdala en un lugar seguro.") + "\n" +
                tr("La necesitarás si olvidas tu contraseña."))
        else:
            QMessageBox.warning(self, tr("Sin Llave"), tr("No tienes llave de recuperación configurada"))

    def regenerar_llave_actual(self):
        """Regenera la llave de recuperación del usuario actual"""
        if not self.auth_manager.usuario_actual:
            QMessageBox.warning(self, tr("Error"), tr("No hay usuario logueado"))
            return

        respuesta = QMessageBox.question(self, tr("Confirmar"),
            tr("¿Regenerar tu llave de recuperación?") + "\n\n" +
            tr("La llave anterior dejará de funcionar."),
            QMessageBox.Yes | QMessageBox.No)

        if respuesta == QMessageBox.Yes:
            exito, nueva_llave, msg = self.auth_manager.regenerar_llave(
                self.auth_manager.usuario_actual['id'])
            if exito:
                QMessageBox.information(self, tr("Nueva Llave"),
                    f"🔑 {tr('Tu NUEVA llave es')}:\n\n{nueva_llave}\n\n" +
                    tr("¡Guárdala ahora! La llave anterior ya no funciona."))
            else:
                QMessageBox.critical(self, tr("Error"), msg)

    def listar_escaneres_wia(self):
        """Intenta listar escáneres usando WIA (Windows Image Acquisition)"""
        try:
            import win32com.client
            device_manager = win32com.client.Dispatch("WIA.DeviceManager")
            scanners = []
            for i in range(1, device_manager.DeviceInfos.Count + 1):
                device = device_manager.DeviceInfos(i)
                scanners.append(device.Properties("Name").Value)
            return scanners
        except (OSError, ValueError, RuntimeError) as e:
            logger.warning(f"WIA no disponible o error al listar escáneres: {e}")
            return []

    def cargar_configuracion(self):
        """Carga los valores desde la base de datos"""
        try:
            # Cargar Impresoras
            self._set_combo_text(self.printer_general, self._get_config('printer_general'))
            self._set_combo_text(self.printer_ticket, self._get_config('printer_ticket'))
            self._set_combo_text(self.printer_labels, self._get_config('printer_labels'))
            self.printer_duplex.setChecked(self._get_config('printer_duplex') == '1')
            
            # Cargar Escáner
            self._set_combo_text(self.scanner_device, self._get_config('scanner_device'))

            # Cargar Seguridad
            self.check_recordar_usuario.setChecked(self._get_config('login_recordar_usuario') == '1')
            self.check_autologin.setChecked(self._get_config('login_autologin') == '1')

            # Cargar Protección de Operaciones (por defecto activado si no existe)
            # Bloquear señales para evitar guardado innecesario durante la carga
            self.check_proteccion_operaciones.blockSignals(True)
            proteccion = self._get_config('seguridad_proteccion_operaciones')
            self.check_proteccion_operaciones.setChecked(proteccion != '0')  # Por defecto True
            self.check_proteccion_operaciones.blockSignals(False)

            # Cargar Idioma
            idioma = self._get_config('idioma') or 'es'
            idx = self.combo_idioma.findData(idioma)
            if idx >= 0:
                self.combo_idioma.setCurrentIndex(idx)
            
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error cargando configuración: {e}")

    def guardar_impresoras(self):
        """Guarda la configuración de impresoras y escáner"""
        try:
            self._set_config('printer_general', self.printer_general.currentText())
            self._set_config('printer_ticket', self.printer_ticket.currentText())
            self._set_config('printer_labels', self.printer_labels.currentText())
            self._set_config('printer_duplex', '1' if self.printer_duplex.isChecked() else '0')
            self._set_config('scanner_device', self.scanner_device.currentText())

            QMessageBox.information(self, tr("Guardado"),
                tr("Configuración de impresoras guardada correctamente."))

        except (OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, tr("Error"), tr("Error al guardar") + f": {e}")

    def guardar_seguridad(self):
        """Guarda la configuración de seguridad e idioma - requiere contraseña si protección activa"""
        try:
            # Verificar si la protección está activada - pedir contraseña
            proteccion_actual = self._get_config('seguridad_proteccion_operaciones')
            if proteccion_actual == '1':
                from app.ui.confirmar_accion_dialog import ConfirmarAccionDialog
                dialog = ConfirmarAccionDialog(
                    self.auth_manager,
                    'configuracion.seguridad',
                    tr("Guardar Configuración de Seguridad"),
                    tr("¿Confirmar los cambios en la configuración de seguridad?"),
                    self
                )
                if dialog.exec_() != 1 or not dialog.accion_confirmada:
                    return  # Cancelado

            self._set_config('login_recordar_usuario', '1' if self.check_recordar_usuario.isChecked() else '0')

            # Si se desactiva recordar usuario, también desactivar autologin
            if not self.check_recordar_usuario.isChecked():
                self.check_autologin.setChecked(False)
                self._set_config('login_autologin', '0')
                self._set_config('login_autologin_pwd', '')
            else:
                self._set_config('login_autologin', '1' if self.check_autologin.isChecked() else '0')

            # Guardar Protección de Operaciones
            self._set_config('seguridad_proteccion_operaciones', '1' if self.check_proteccion_operaciones.isChecked() else '0')

            # Guardar Idioma
            from app.i18n import get_translator
            idioma_code = self.combo_idioma.currentData()
            self._set_config('idioma', idioma_code)

            # Aplicar cambio de idioma inmediato
            translator = get_translator()
            config_cambio = False
            if translator.get_language() != idioma_code:
                translator.set_language(idioma_code)
                config_cambio = True

            msg = tr("Configuración de seguridad guardada correctamente.")
            if config_cambio:
                msg += "\n\n" + tr("El idioma ha sido actualizado. Reinicia la aplicación para ver todos los cambios.")

            QMessageBox.information(self, tr("Guardado"), msg)

        except (OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, tr("Error"), tr("Error al guardar") + f": {e}")

    def _guardar_proteccion_operaciones(self, state):
        """Guarda la configuración de protección - requiere contraseña si está activada"""
        try:
            # Verificar si la protección está actualmente activada en BD
            proteccion_actual = self._get_config('seguridad_proteccion_operaciones')

            # Si la protección está activada, pedir contraseña antes de cambiar
            if proteccion_actual == '1':
                from app.ui.confirmar_accion_dialog import ConfirmarAccionDialog
                dialog = ConfirmarAccionDialog(
                    self.auth_manager,
                    'configuracion.seguridad',
                    tr("Cambiar Configuración de Seguridad"),
                    tr("¿Confirmar cambio en la protección de operaciones críticas?"),
                    self
                )
                if dialog.exec_() != 1 or not dialog.accion_confirmada:
                    # Revertir el checkbox al estado anterior
                    self.check_proteccion_operaciones.blockSignals(True)
                    self.check_proteccion_operaciones.setChecked(True)
                    self.check_proteccion_operaciones.blockSignals(False)
                    return

            # Guardar el nuevo valor
            valor = '1' if state == Qt.Checked else '0'
            self._set_config('seguridad_proteccion_operaciones', valor)

            # Feedback visual
            estado = tr("activada") if state == Qt.Checked else tr("desactivada")
            self.check_proteccion_operaciones.setToolTip(
                tr("Requiere contraseña para eliminar, editar o realizar acciones sensibles") +
                f"\n\n✓ {tr('Protección')} {estado}"
            )
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error guardando protección: {e}")

    def test_impresora(self):
        """Imprime una prueba en la impresora seleccionada"""
        printer_name = self.printer_general.currentText()
        if "---" in printer_name:
            QMessageBox.warning(self, tr("Aviso"), tr("Selecciona una impresora general primero"))
            return

        QMessageBox.information(self, tr("Test"), tr("Enviando prueba a") + f": {printer_name}\n(" + tr("Funcionalidad simulada") + ")")

    def refrescar_escaneres(self):
        """Refresca la lista de escáneres disponibles"""
        current = self.scanner_device.currentText()
        self.scanner_device.clear()
        self.scanner_device.addItem("--- " + tr("Seleccionar Escáner") + " ---")

        scanners = self.listar_escaneres_wia()
        if scanners:
            self.scanner_device.addItems(scanners)
            QMessageBox.information(self, tr("Escáneres"), tr("Se detectaron") + f" {len(scanners)} " + tr("escáner(es)"))
        else:
            self.scanner_device.addItem(tr("No se detectaron escáneres"))
            QMessageBox.warning(self, tr("Escáneres"),
                tr("No se detectaron escáneres.") + "\n\n" +
                tr("Asegúrate de que") + ":\n" +
                "• " + tr("El escáner está encendido y conectado") + "\n" +
                "• " + tr("Los drivers están instalados") + "\n" +
                "• " + tr("El servicio WIA de Windows está activo"))

        # Restaurar selección si existe
        self._set_combo_text(self.scanner_device, current)

    def seleccionar_carpeta_escaneo(self):
        """Abre diálogo para seleccionar carpeta de escaneos"""
        folder = QFileDialog.getExistingDirectory(
            self, tr("Seleccionar Carpeta de Escaneos"),
            self.scanner_folder.text() or "data/escaneos"
        )
        if folder:
            self.scanner_folder.setText(folder)

    def test_escaner(self):
        """Prueba el escáner seleccionado"""
        scanner_name = self.scanner_device.currentText()
        if "---" in scanner_name or tr("No se detectaron") in scanner_name:
            QMessageBox.warning(self, tr("Aviso"), tr("Selecciona un escáner primero"))
            return

        try:
            import win32com.client

            # Intentar conectar con el escáner
            device_manager = win32com.client.Dispatch("WIA.DeviceManager")

            # Buscar el dispositivo por nombre
            device = None
            for i in range(1, device_manager.DeviceInfos.Count + 1):
                info = device_manager.DeviceInfos(i)
                if info.Properties("Name").Value == scanner_name:
                    device = info.Connect()
                    break

            if device:
                QMessageBox.information(self, tr("Escáner OK"),
                    f"✅ {tr('Conexión exitosa con')}:\n{scanner_name}\n\n" +
                    tr("El escáner está listo para usar."))
            else:
                QMessageBox.warning(self, tr("Error"),
                    tr("No se pudo conectar con el escáner") + f":\n{scanner_name}")

        except (OSError, ValueError, RuntimeError) as e:
            QMessageBox.critical(self, tr("Error"),
                tr("Error al probar escáner") + f":\n{str(e)}\n\n" +
                tr("Asegúrate de que el escáner está conectado y encendido."))

    # Helpers BD
    def _get_config(self, clave):
        res = self.db.fetch_one("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
        return res['valor'] if res else ""

    def _set_config(self, clave, valor):
        # Upsert (Insert or Update)
        self.db.execute_query(
            "INSERT OR REPLACE INTO configuracion (clave, valor) VALUES (?, ?)",
            (clave, valor)
        )

    def _set_combo_text(self, combo, text):
        index = combo.findText(text)
        if index >= 0:
            combo.setCurrentIndex(index)


    def closeEvent(self, event):
        """Cierra la conexión a la base de datos al cerrar el tab"""
        if hasattr(self, 'db') and self.db:
            self.db.disconnect()
        super().closeEvent(event)
