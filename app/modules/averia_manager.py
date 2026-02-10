"""
Gestor de averías para el sistema SAT
"""
from app.utils.logger import logger


class AveriaManager:
    def __init__(self, db):
        self.db = db

    def crear_averia(self, nombre, descripcion=''):
        """Crea una nueva avería en el catálogo"""
        try:
            averia_id = self.db.execute_query(
                "INSERT INTO averias (nombre, descripcion) VALUES (?, ?)",
                (nombre, descripcion)
            )
            return averia_id
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error creando avería: {e}")
            return None

    def obtener_averias_activas(self):
        """Obtiene lista de averías activas ordenadas alfabéticamente"""
        return self.db.fetch_all(
            "SELECT * FROM averias WHERE activo = 1 ORDER BY nombre ASC"
        )

    def obtener_averia(self, averia_id):
        """Obtiene una avería específica por ID"""
        return self.db.fetch_one(
            "SELECT * FROM averias WHERE id = ?",
            (averia_id,)
        )

    def actualizar_averia(self, averia_id, nombre, descripcion):
        """Actualiza una avería existente"""
        try:
            self.db.execute_query(
                "UPDATE averias SET nombre = ?, descripcion = ? WHERE id = ?",
                (nombre, descripcion, averia_id)
            )
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error actualizando avería: {e}")
            return False

    def eliminar_averia(self, averia_id):
        """
        Elimina una avería (desactiva).
        Las soluciones relacionadas se eliminarán automáticamente (CASCADE)
        """
        try:
            # Verificar si hay reparaciones que usan esta avería
            reparaciones = self.db.fetch_one(
                "SELECT COUNT(*) as total FROM reparaciones_items WHERE averia_texto IN (SELECT nombre FROM averias WHERE id = ?)",
                (averia_id,)
            )

            if reparaciones and reparaciones['total'] > 0:
                # Desactivar en lugar de eliminar para mantener historial
                self.db.execute_query(
                    "UPDATE averias SET activo = 0 WHERE id = ?",
                    (averia_id,)
                )
                return True, f"Avería desactivada (hay {reparaciones['total']} reparaciones asociadas)"
            else:
                # Eliminar completamente (las soluciones se eliminan por CASCADE)
                self.db.execute_query(
                    "DELETE FROM averias WHERE id = ?",
                    (averia_id,)
                )
                return True, "Avería eliminada correctamente"

        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error eliminando avería: {e}")
            return False, f"Error: {str(e)}"

    def buscar_averias(self, termino):
        """Busca averías por nombre o descripción"""
        return self.db.fetch_all(
            """SELECT * FROM averias
               WHERE activo = 1
               AND (nombre LIKE ? OR descripcion LIKE ?)
               ORDER BY nombre ASC""",
            (f"%{termino}%", f"%{termino}%")
        )
