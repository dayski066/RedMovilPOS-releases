"""
Gestor de categorías de productos
"""
from app.utils.logger import logger


class CategoriaManager:
    def __init__(self, db):
        self.db = db

    def obtener_todas(self):
        """Obtiene todas las categorías"""
        return self.db.fetch_all("SELECT * FROM categorias ORDER BY nombre")

    def obtener_por_id(self, categoria_id):
        """Obtiene una categoría por ID"""
        return self.db.fetch_one("SELECT * FROM categorias WHERE id = ?", (categoria_id,))

    def crear(self, nombre, descripcion=None):
        """Crea una nueva categoría"""
        try:
            categoria_id = self.db.execute_query(
                "INSERT INTO categorias (nombre, descripcion) VALUES (?, ?)",
                (nombre, descripcion)
            )
            return categoria_id
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error al crear categoría: {e}")
            return None

    def actualizar(self, categoria_id, nombre, descripcion=None):
        """Actualiza una categoría existente"""
        return self.db.execute_query(
            "UPDATE categorias SET nombre = ?, descripcion = ? WHERE id = ?",
            (nombre, descripcion, categoria_id)
        )

    def eliminar(self, categoria_id):
        """Elimina una categoría (verifica que no tenga productos)"""
        # Verificar si tiene productos
        productos = self.db.fetch_one(
            "SELECT COUNT(*) as total FROM productos WHERE categoria_id = ? AND activo = 1",
            (categoria_id,)
        )

        if productos and productos['total'] > 0:
            return False, "No se puede eliminar: tiene productos asociados"

        # Eliminar categoría
        result = self.db.execute_query("DELETE FROM categorias WHERE id = ?", (categoria_id,))
        if result is not None:
            return True, "Categoría eliminada correctamente"
        return False, "Error al eliminar categoría"

    def contar_productos(self, categoria_id):
        """Cuenta los productos de una categoría"""
        result = self.db.fetch_one(
            "SELECT COUNT(*) as total FROM productos WHERE categoria_id = ? AND activo = 1",
            (categoria_id,)
        )
        return result['total'] if result else 0
