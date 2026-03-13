"""
Gestor de soluciones para averías del sistema SAT
"""
from app.utils.logger import logger


class SolucionManager:
    def __init__(self, db):
        self.db = db

    def crear_solucion(self, averia_id, nombre, descripcion=''):
        """Crea una nueva solución para una avería específica"""
        try:
            solucion_id = self.db.execute_query(
                "INSERT INTO soluciones (averia_id, nombre, descripcion) VALUES (?, ?, ?)",
                (averia_id, nombre, descripcion)
            )
            return solucion_id
        except sqlite3.Error as e:
            logger.error(f"Error creando solución: {e}")
            return None

    def obtener_soluciones_por_averia(self, averia_id):
        """Obtiene todas las soluciones activas de una avería específica"""
        return self.db.fetch_all(
            """SELECT * FROM soluciones
               WHERE averia_id = ? AND activo = 1
               ORDER BY nombre ASC""",
            (averia_id,)
        )

    def obtener_solucion(self, solucion_id):
        """Obtiene una solución específica por ID"""
        return self.db.fetch_one(
            "SELECT * FROM soluciones WHERE id = ?",
            (solucion_id,)
        )

    def actualizar_solucion(self, solucion_id, nombre, descripcion):
        """Actualiza una solución existente"""
        try:
            self.db.execute_query(
                "UPDATE soluciones SET nombre = ?, descripcion = ? WHERE id = ?",
                (nombre, descripcion, solucion_id)
            )
            return True
        except sqlite3.Error as e:
            logger.error(f"Error actualizando solución: {e}")
            return False

    def eliminar_solucion(self, solucion_id):
        """Elimina una solución (desactiva si hay reparaciones asociadas)"""
        try:
            # Verificar si hay reparaciones que usan esta solución
            reparaciones = self.db.fetch_one(
                "SELECT COUNT(*) as total FROM reparaciones_items WHERE solucion_texto IN (SELECT nombre FROM soluciones WHERE id = ?)",
                (solucion_id,)
            )

            if reparaciones and reparaciones['total'] > 0:
                # Desactivar en lugar de eliminar para mantener historial
                self.db.execute_query(
                    "UPDATE soluciones SET activo = 0 WHERE id = ?",
                    (solucion_id,)
                )
                return True, f"Solución desactivada (hay {reparaciones['total']} reparaciones asociadas)"
            else:
                # Eliminar completamente
                self.db.execute_query(
                    "DELETE FROM soluciones WHERE id = ?",
                    (solucion_id,)
                )
                return True, "Solución eliminada correctamente"

        except sqlite3.Error as e:
            logger.error(f"Error eliminando solución: {e}")
            return False, f"Error: {str(e)}"

    def obtener_soluciones_activas(self):
        """Obtiene todas las soluciones activas con información de su avería"""
        return self.db.fetch_all(
            """SELECT s.*, a.nombre as averia_nombre
               FROM soluciones s
               INNER JOIN averias a ON s.averia_id = a.id
               WHERE s.activo = 1
               ORDER BY a.nombre, s.nombre ASC"""
        )

    def buscar_soluciones(self, termino):
        """Busca soluciones por nombre o descripción"""
        return self.db.fetch_all(
            """SELECT s.*, a.nombre as averia_nombre
               FROM soluciones s
               INNER JOIN averias a ON s.averia_id = a.id
               WHERE s.activo = 1
               AND (s.nombre LIKE ? OR s.descripcion LIKE ?)
               ORDER BY a.nombre, s.nombre ASC""",
            (f"%{termino}%", f"%{termino}%")
        )
