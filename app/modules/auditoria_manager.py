"""
Manager de Auditoría - Registra todas las operaciones del sistema
"""
import sqlite3
import json
from datetime import datetime
from app.db.database import Database
from app.utils.logger import get_logger

logger = get_logger('auditoria')


class AuditoriaManager:
    """Gestiona el registro de operaciones para auditoría"""
    
    def __init__(self, db=None):
        self.db = db if db else Database()
        if not db:
            self.db.connect()
    
    def registrar_operacion(self, usuario_id, tipo_operacion, tabla, registro_id, 
                           descripcion, datos_anteriores=None, datos_nuevos=None):
        """
        Registra una operación en el historial
        
        Args:
            usuario_id: ID del usuario que realizó la operación
            tipo_operacion: 'crear', 'editar', 'eliminar'
            tabla: Nombre de la tabla afectada
            registro_id: ID del registro afectado
            descripcion: Descripción legible de la operación
            datos_anteriores: Dict con valores antes del cambio (para editar/eliminar)
            datos_nuevos: Dict con valores después del cambio (para crear/editar)
        
        Returns:
            ID del registro de historial o None si falla
        """
        try:
            datos_ant_json = json.dumps(datos_anteriores, ensure_ascii=False, default=str) if datos_anteriores else None
            datos_new_json = json.dumps(datos_nuevos, ensure_ascii=False, default=str) if datos_nuevos else None
            
            historial_id = self.db.execute_query("""
                INSERT INTO historial_operaciones 
                (usuario_id, tipo_operacion, tabla, registro_id, descripcion, datos_anteriores, datos_nuevos)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (usuario_id, tipo_operacion, tabla, registro_id, descripcion, datos_ant_json, datos_new_json))
            
            return historial_id
        except sqlite3.Error as e:
            logger.error(f"Error registrando operación: {e}")
            return None
    
    def registrar_creacion(self, usuario_id, tabla, registro_id, descripcion, datos=None):
        """Atajo para registrar una creación"""
        return self.registrar_operacion(
            usuario_id=usuario_id,
            tipo_operacion='crear',
            tabla=tabla,
            registro_id=registro_id,
            descripcion=descripcion,
            datos_nuevos=datos
        )
    
    def registrar_edicion(self, usuario_id, tabla, registro_id, descripcion, 
                         datos_anteriores=None, datos_nuevos=None):
        """Atajo para registrar una edición"""
        return self.registrar_operacion(
            usuario_id=usuario_id,
            tipo_operacion='editar',
            tabla=tabla,
            registro_id=registro_id,
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )
    
    def registrar_eliminacion(self, usuario_id, tabla, registro_id, descripcion, datos=None):
        """Atajo para registrar una eliminación"""
        return self.registrar_operacion(
            usuario_id=usuario_id,
            tipo_operacion='eliminar',
            tabla=tabla,
            registro_id=registro_id,
            descripcion=descripcion,
            datos_anteriores=datos
        )
    
    def obtener_historial(self, fecha_desde=None, fecha_hasta=None, tipo=None, 
                         tabla=None, usuario_id=None, limite=100):
        """
        Obtiene el historial de operaciones con filtros
        
        Returns:
            Lista de registros del historial
        """
        query = """
            SELECT h.*, u.username, u.nombre_completo
            FROM historial_operaciones h
            JOIN usuarios u ON h.usuario_id = u.id
            WHERE 1=1
        """
        params = []
        
        if fecha_desde:
            query += " AND h.fecha >= ?"
            params.append(fecha_desde)
        
        if fecha_hasta:
            query += " AND h.fecha <= ?"
            params.append(fecha_hasta + " 23:59:59")
        
        if tipo:
            query += " AND h.tipo_operacion = ?"
            params.append(tipo)
        
        if tabla:
            query += " AND h.tabla = ?"
            params.append(tabla)
        
        if usuario_id:
            query += " AND h.usuario_id = ?"
            params.append(usuario_id)
        
        query += " ORDER BY h.fecha DESC LIMIT ?"
        params.append(limite)
        
        return self.db.fetch_all(query, tuple(params))
    
    def obtener_tablas_disponibles(self):
        """Obtiene lista de tablas con operaciones registradas"""
        result = self.db.fetch_all("""
            SELECT DISTINCT tabla FROM historial_operaciones ORDER BY tabla
        """)
        return [r['tabla'] for r in result] if result else []
    
    def obtener_usuarios_con_operaciones(self):
        """Obtiene lista de usuarios que han realizado operaciones"""
        return self.db.fetch_all("""
            SELECT DISTINCT u.id, u.username, u.nombre_completo
            FROM historial_operaciones h
            JOIN usuarios u ON h.usuario_id = u.id
            ORDER BY u.nombre_completo
        """)
