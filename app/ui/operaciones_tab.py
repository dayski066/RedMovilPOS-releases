"""
Pestaña de Operaciones - Historial de operaciones del sistema
Solo visible para administradores y con acceso protegido por contraseña
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QLabel, QComboBox,
                             QDateEdit, QHeaderView, QGroupBox,
                             QFrame)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor, QBrush
from app.utils.notify import notify_warning
from app.db.database import Database
from app.modules.auditoria_manager import AuditoriaManager
from app.i18n import tr
from app.ui.transparent_buttons import set_btn_icon
from qfluentwidgets import FluentIcon
import json


class OperacionesTab(QWidget):
    """Tab de historial de operaciones (solo admin, acceso con contraseña)"""
    
    def __init__(self, auth_manager=None):
        super().__init__()
        self.auth_manager = auth_manager
        self.db = Database()
        self.db.connect()
        self.auditoria_manager = AuditoriaManager(self.db)
        self.acceso_verificado = False
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("📋 " + tr("Historial de Operaciones"))
        header.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px; color: #ffffff;")
        layout.addWidget(header)
        
        # Aviso de seguridad
        aviso = QLabel("🔒 " + tr("Este historial requiere autenticación para acceder"))
        aviso.setStyleSheet("color: #EBCB8B; font-size: 12px; padding: 5px;")
        layout.addWidget(aviso)
        
        # Panel de bloqueo (se muestra hasta verificar contraseña)
        self.panel_bloqueo = QFrame()
        self.panel_bloqueo.setStyleSheet("""
            QFrame {
                background-color: #3B4252;
                border: 2px solid #4C566A;
                border-radius: 10px;
                padding: 30px;
            }
        """)
        bloqueo_layout = QVBoxLayout(self.panel_bloqueo)
        
        icono_candado = QLabel("🔐")
        icono_candado.setStyleSheet("font-size: 60px;")
        icono_candado.setAlignment(Qt.AlignCenter)
        bloqueo_layout.addWidget(icono_candado)
        
        texto_bloqueo = QLabel(tr("Acceso restringido a administradores"))
        texto_bloqueo.setStyleSheet("font-size: 14px; color: #D8DEE9;")
        texto_bloqueo.setAlignment(Qt.AlignCenter)
        bloqueo_layout.addWidget(texto_bloqueo)
        
        btn_desbloquear = QPushButton("🔓 " + tr("Desbloquear con Contraseña"))
        btn_desbloquear.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #88C0D0;
                border: 2px solid #88C0D0;
                border-radius: 6px;
                padding: 12px 30px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: rgba(136, 192, 208, 0.1);
            }
        """)
        btn_desbloquear.clicked.connect(self.solicitar_acceso)
        bloqueo_layout.addWidget(btn_desbloquear, alignment=Qt.AlignCenter)
        
        layout.addWidget(self.panel_bloqueo)
        
        # Panel de contenido (oculto hasta verificar)
        self.panel_contenido = QWidget()
        self.panel_contenido.setVisible(False)
        contenido_layout = QVBoxLayout(self.panel_contenido)
        contenido_layout.setContentsMargins(0, 0, 0, 0)
        
        # Filtros
        filtros_group = QGroupBox(tr("Filtros"))
        filtros_layout = QHBoxLayout(filtros_group)
        
        # Fecha desde
        filtros_layout.addWidget(QLabel(tr("Desde") + ":"))
        self.fecha_desde = QDateEdit()
        self.fecha_desde.setDate(QDate.currentDate().addDays(-30))
        self.fecha_desde.setCalendarPopup(True)
        self.fecha_desde.setMaximumWidth(130)
        filtros_layout.addWidget(self.fecha_desde)
        
        # Fecha hasta
        filtros_layout.addWidget(QLabel(tr("Hasta") + ":"))
        self.fecha_hasta = QDateEdit()
        self.fecha_hasta.setDate(QDate.currentDate())
        self.fecha_hasta.setCalendarPopup(True)
        self.fecha_hasta.setMaximumWidth(130)
        filtros_layout.addWidget(self.fecha_hasta)
        
        # Tipo operación
        filtros_layout.addWidget(QLabel(tr("Tipo") + ":"))
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem(tr("Todos"), None)
        self.combo_tipo.addItem("➕ " + tr("Crear"), "crear")
        self.combo_tipo.addItem("✏️ " + tr("Editar"), "editar")
        self.combo_tipo.addItem("🗑️ " + tr("Eliminar"), "eliminar")
        self.combo_tipo.setMaximumWidth(150)
        filtros_layout.addWidget(self.combo_tipo)
        
        # Tabla
        filtros_layout.addWidget(QLabel(tr("Tabla") + ":"))
        self.combo_tabla = QComboBox()
        self.combo_tabla.addItem(tr("Todas"), None)
        self.combo_tabla.setMaximumWidth(150)
        filtros_layout.addWidget(self.combo_tabla)
        
        # Usuario
        filtros_layout.addWidget(QLabel(tr("Usuario") + ":"))
        self.combo_usuario = QComboBox()
        self.combo_usuario.addItem(tr("Todos"), None)
        self.combo_usuario.setMaximumWidth(150)
        filtros_layout.addWidget(self.combo_usuario)
        
        filtros_layout.addStretch()
        
        # Botón buscar
        btn_buscar = QPushButton(tr("Buscar"))
        btn_buscar.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #5E81AC;
                border: 2px solid #5E81AC;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(94, 129, 172, 0.1);
            }
        """)
        set_btn_icon(btn_buscar, FluentIcon.SEARCH, color="#5E81AC")
        btn_buscar.clicked.connect(self.cargar_historial)
        filtros_layout.addWidget(btn_buscar)
        
        contenido_layout.addWidget(filtros_group)
        
        # Tabla de resultados
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            tr("Fecha/Hora"), tr("Usuario"), tr("Operación"), 
            tr("Tabla"), tr("ID"), tr("Descripción")
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        contenido_layout.addWidget(self.tabla)
        
        # Contador
        self.label_contador = QLabel(tr("Mostrando 0 registros"))
        self.label_contador.setStyleSheet("color: #7B88A0; font-size: 11px;")
        contenido_layout.addWidget(self.label_contador)
        
        layout.addWidget(self.panel_contenido)
    
    def solicitar_acceso(self):
        """Solicita contraseña para acceder al historial"""
        if not self.auth_manager:
            notify_warning(
                self,
                tr("Error"),
                tr("Sistema de autenticación no disponible")
            )
            return
        
        # Verificar que sea admin
        usuario = self.auth_manager.obtener_usuario_actual()
        if not usuario or usuario.get('rol') != 'admin':
            notify_warning(
                self,
                tr("Acceso Denegado"),
                tr("Solo los administradores pueden acceder al historial de operaciones.")
            )
            return
        
        # Solicitar contraseña
        from app.ui.confirmar_accion_dialog import confirmar_accion_sensible
        
        if confirmar_accion_sensible(
            self.auth_manager,
            'historial.ver',
            tr('Ver Historial de Operaciones'),
            tr("Para acceder al historial de operaciones debe confirmar su identidad."),
            self
        ):
            self.acceso_verificado = True
            self.panel_bloqueo.setVisible(False)
            self.panel_contenido.setVisible(True)
            self.cargar_filtros()
            self.cargar_historial()
    
    def cargar_filtros(self):
        """Carga las opciones de los filtros"""
        # Tablas disponibles
        tablas = self.auditoria_manager.obtener_tablas_disponibles()
        self.combo_tabla.clear()
        self.combo_tabla.addItem(tr("Todas"), None)
        for tabla in tablas:
            self.combo_tabla.addItem(tabla, tabla)
        
        # Usuarios
        usuarios = self.auditoria_manager.obtener_usuarios_con_operaciones()
        self.combo_usuario.clear()
        self.combo_usuario.addItem(tr("Todos"), None)
        for u in usuarios:
            self.combo_usuario.addItem(u['nombre_completo'], u['id'])
    
    def cargar_historial(self):
        """Carga el historial de operaciones"""
        if not self.acceso_verificado:
            return
        
        fecha_desde = self.fecha_desde.date().toString('yyyy-MM-dd')
        fecha_hasta = self.fecha_hasta.date().toString('yyyy-MM-dd')
        tipo = self.combo_tipo.currentData()
        tabla = self.combo_tabla.currentData()
        usuario_id = self.combo_usuario.currentData()
        
        historial = self.auditoria_manager.obtener_historial(
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            tipo=tipo,
            tabla=tabla,
            usuario_id=usuario_id,
            limite=500
        )
        
        self.tabla.setRowCount(len(historial))
        
        colores_tipo = {
            'crear': QColor('#A3BE8C'),
            'editar': QColor('#EBCB8B'),
            'eliminar': QColor('#BF616A')
        }
        
        iconos_tipo = {
            'crear': '➕',
            'editar': '✏️',
            'eliminar': '🗑️'
        }
        
        for row, registro in enumerate(historial):
            # Fecha
            fecha_item = QTableWidgetItem(str(registro['fecha']))
            self.tabla.setItem(row, 0, fecha_item)
            
            # Usuario
            usuario_item = QTableWidgetItem(registro['nombre_completo'])
            self.tabla.setItem(row, 1, usuario_item)
            
            # Tipo operación
            tipo_op = registro['tipo_operacion']
            icono = iconos_tipo.get(tipo_op, '')
            tipo_item = QTableWidgetItem(f"{icono} {tipo_op.upper()}")
            tipo_item.setForeground(QBrush(colores_tipo.get(tipo_op, QColor('#D8DEE9'))))
            self.tabla.setItem(row, 2, tipo_item)
            
            # Tabla
            tabla_item = QTableWidgetItem(registro['tabla'])
            self.tabla.setItem(row, 3, tabla_item)
            
            # ID registro
            id_item = QTableWidgetItem(str(registro['registro_id'] or '-'))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(row, 4, id_item)
            
            # Descripción
            desc_item = QTableWidgetItem(registro['descripcion'])
            self.tabla.setItem(row, 5, desc_item)
        
        self.label_contador.setText(tr("Mostrando") + f" {len(historial)} " + tr("registros"))
    
    def showEvent(self, event):
        """Al mostrar la pestaña, resetear a bloqueado si no está verificado"""
        super().showEvent(event)
        if not self.acceso_verificado:
            self.panel_bloqueo.setVisible(True)
            self.panel_contenido.setVisible(False)
