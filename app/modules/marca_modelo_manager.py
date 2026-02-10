"""
Gestor de marcas y modelos
"""
from app.utils.logger import logger


class MarcaModeloManager:
    def __init__(self, db):
        self.db = db

    # ==================== MARCAS ====================

    def obtener_todas_marcas(self):
        """Obtiene todas las marcas ordenadas por nombre"""
        return self.db.fetch_all("SELECT * FROM marcas ORDER BY nombre")

    def obtener_marca(self, marca_id):
        """Obtiene una marca por ID"""
        return self.db.fetch_one("SELECT * FROM marcas WHERE id = ?", (marca_id,))

    def crear_marca(self, nombre):
        """Crea una nueva marca"""
        try:
            marca_id = self.db.execute_query(
                "INSERT INTO marcas (nombre) VALUES (?)",
                (nombre.strip(),)
            )
            return marca_id
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error al crear marca: {e}")
            return None

    def actualizar_marca(self, marca_id, nombre):
        """Actualiza una marca existente"""
        try:
            self.db.execute_query(
                "UPDATE marcas SET nombre = ? WHERE id = ?",
                (nombre.strip(), marca_id)
            )
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error al actualizar marca: {e}")
            return False

    def eliminar_marca(self, marca_id):
        """Elimina una marca y todos sus modelos (CASCADE)"""
        try:
            # Verificar si hay productos usando esta marca
            productos = self.db.fetch_one(
                "SELECT COUNT(*) as total FROM productos WHERE marca_id = ?",
                (marca_id,)
            )

            if productos['total'] > 0:
                return False, f"No se puede eliminar. Hay {productos['total']} producto(s) usando esta marca."

            # Eliminar marca (los modelos se eliminan automáticamente por CASCADE)
            self.db.execute_query("DELETE FROM marcas WHERE id = ?", (marca_id,))
            return True, "Marca eliminada correctamente"
        except (sqlite3.Error, OSError, ValueError) as e:
            return False, f"Error al eliminar marca: {str(e)}"

    # ==================== MODELOS ====================

    def obtener_todos_modelos(self, marca_id=None):
        """Obtiene todos los modelos, opcionalmente filtrados por marca"""
        if marca_id:
            query = """
                SELECT m.*, ma.nombre as marca_nombre
                FROM modelos m
                LEFT JOIN marcas ma ON m.marca_id = ma.id
                WHERE m.marca_id = ?
                ORDER BY m.nombre
            """
            return self.db.fetch_all(query, (marca_id,))
        else:
            query = """
                SELECT m.*, ma.nombre as marca_nombre
                FROM modelos m
                LEFT JOIN marcas ma ON m.marca_id = ma.id
                ORDER BY ma.nombre, m.nombre
            """
            return self.db.fetch_all(query)

    def obtener_modelo(self, modelo_id):
        """Obtiene un modelo por ID"""
        query = """
            SELECT m.*, ma.nombre as marca_nombre
            FROM modelos m
            LEFT JOIN marcas ma ON m.marca_id = ma.id
            WHERE m.id = ?
        """
        return self.db.fetch_one(query, (modelo_id,))

    def crear_modelo(self, nombre, marca_id):
        """Crea un nuevo modelo"""
        try:
            modelo_id = self.db.execute_query(
                "INSERT INTO modelos (nombre, marca_id) VALUES (?, ?)",
                (nombre.strip(), marca_id)
            )
            return modelo_id
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error al crear modelo: {e}")
            return None

    def actualizar_modelo(self, modelo_id, nombre, marca_id):
        """Actualiza un modelo existente"""
        try:
            self.db.execute_query(
                "UPDATE modelos SET nombre = ?, marca_id = ? WHERE id = ?",
                (nombre.strip(), marca_id, modelo_id)
            )
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error al actualizar modelo: {e}")
            return False

    def eliminar_modelo(self, modelo_id):
        """Elimina un modelo"""
        try:
            # Verificar si hay productos usando este modelo
            productos = self.db.fetch_one(
                "SELECT COUNT(*) as total FROM productos WHERE modelo_id = ?",
                (modelo_id,)
            )

            if productos['total'] > 0:
                return False, f"No se puede eliminar. Hay {productos['total']} producto(s) usando este modelo."

            # Eliminar modelo
            self.db.execute_query("DELETE FROM modelos WHERE id = ?", (modelo_id,))
            return True, "Modelo eliminado correctamente"
        except (sqlite3.Error, OSError, ValueError) as e:
            return False, f"Error al eliminar modelo: {str(e)}"
