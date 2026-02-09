"""
Gestor de productos
"""
import sqlite3


class ProductoManager:
    def __init__(self, db):
        self.db = db

    def generar_codigo_ean(self):
        """Genera un código EAN automático de forma atómica"""
        if not self.db.begin_transaction():
            return "1000000000001"
        try:
            self.db.execute_query(
                """UPDATE configuracion
                   SET valor = CAST(CAST(valor AS INTEGER) + 1 AS TEXT)
                   WHERE clave = 'ultimo_codigo_ean'"""
            )
            config = self.db.fetch_one(
                "SELECT valor FROM configuracion WHERE clave = 'ultimo_codigo_ean'"
            )
            self.db.commit()
            if config:
                return str(int(config['valor'])).zfill(13)
            return "1000000000001"
        except (sqlite3.Error, OSError, ValueError):
            self.db.rollback()
            return "1000000000001"

    def buscar_por_ean(self, codigo_ean):
        """Busca un producto por código EAN"""
        return self.db.fetch_one(
            """SELECT p.*, c.nombre as categoria_nombre, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
               FROM productos p
               LEFT JOIN categorias c ON p.categoria_id = c.id
               LEFT JOIN marcas ma ON p.marca_id = ma.id
               LEFT JOIN modelos mo ON p.modelo_id = mo.id
               WHERE p.codigo_ean = ? AND p.activo = 1 AND p.stock > 0""",
            (codigo_ean,)
        )

    def buscar_por_imei(self, imei):
        """Busca un producto por IMEI"""
        return self.db.fetch_one(
            """SELECT p.*, c.nombre as categoria_nombre, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
               FROM productos p
               LEFT JOIN categorias c ON p.categoria_id = c.id
               LEFT JOIN marcas ma ON p.marca_id = ma.id
               LEFT JOIN modelos mo ON p.modelo_id = mo.id
               WHERE p.imei = ? AND p.activo = 1 AND p.stock > 0""",
            (imei,)
        )

    def verificar_duplicado(self, codigo_ean, imei=None):
        """
        Verifica si ya existe un producto con el mismo EAN o IMEI.
        
        Returns:
            dict con keys:
            - 'existe': bool
            - 'activo': bool (si existe)
            - 'producto': dict (si existe)
            - 'tipo': 'ean' o 'imei' (qué campo está duplicado)
        """
        # Verificar por EAN
        if codigo_ean:
            producto = self.db.fetch_one(
                """SELECT p.*, c.nombre as categoria_nombre, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
                   FROM productos p
                   LEFT JOIN categorias c ON p.categoria_id = c.id
                   LEFT JOIN marcas ma ON p.marca_id = ma.id
                   LEFT JOIN modelos mo ON p.modelo_id = mo.id
                   WHERE p.codigo_ean = ?""",
                (codigo_ean,)
            )
            if producto:
                return {
                    'existe': True,
                    'activo': producto['activo'] == 1,
                    'producto': producto,
                    'tipo': 'ean'
                }
        
        # Verificar por IMEI (si se proporciona)
        if imei:
            producto = self.db.fetch_one(
                """SELECT p.*, c.nombre as categoria_nombre, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
                   FROM productos p
                   LEFT JOIN categorias c ON p.categoria_id = c.id
                   LEFT JOIN marcas ma ON p.marca_id = ma.id
                   LEFT JOIN modelos mo ON p.modelo_id = mo.id
                   WHERE p.imei = ?""",
                (imei,)
            )
            if producto:
                return {
                    'existe': True,
                    'activo': producto['activo'] == 1,
                    'producto': producto,
                    'tipo': 'imei'
                }
        
        return {'existe': False}

    def reactivar_producto(self, producto_id):
        """Solo reactiva un producto sin modificar sus datos"""
        return self.db.execute_query(
            "UPDATE productos SET activo = 1 WHERE id = ?",
            (producto_id,)
        )

    def crear_producto(self, datos):
        """Crea un nuevo producto o reactiva uno desactivado con el mismo EAN"""
        # Si no tiene código EAN, generar uno
        if not datos.get('codigo_ean'):
            datos['codigo_ean'] = self.generar_codigo_ean()

        # Verificar si existe un producto desactivado con este EAN
        producto_existente = self.db.fetch_one(
            "SELECT id FROM productos WHERE codigo_ean = ? AND activo = 0",
            (datos['codigo_ean'],)
        )

        if producto_existente:
            # Reactivar el producto existente y actualizar sus datos
            self.db.execute_query(
                """UPDATE productos
                   SET descripcion = ?, precio = ?, precio_compra = ?, categoria_id = ?, 
                       marca_id = ?, modelo_id = ?, imei = ?, ram = ?, almacenamiento = ?, 
                       estado = ?, stock = ?, activo = 1
                   WHERE id = ?""",
                (datos['descripcion'], datos['precio'], datos.get('precio_compra', 0),
                 datos.get('categoria_id'), datos.get('marca_id'), datos.get('modelo_id'),
                 datos.get('imei'), datos.get('ram'), datos.get('almacenamiento'), 
                 datos.get('estado'), datos.get('stock', 0), producto_existente['id'])
            )
            return producto_existente['id']

        # Crear nuevo producto
        producto_id = self.db.execute_query(
            """INSERT INTO productos (codigo_ean, descripcion, precio, precio_compra, categoria_id, marca_id, modelo_id, imei, ram, almacenamiento, estado, stock)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (datos['codigo_ean'], datos['descripcion'], datos['precio'], datos.get('precio_compra', 0),
             datos.get('categoria_id'), datos.get('marca_id'), datos.get('modelo_id'),
             datos.get('imei'), datos.get('ram'), datos.get('almacenamiento'), datos.get('estado'), datos.get('stock', 0))
        )
        return producto_id

    def actualizar_producto(self, producto_id, datos):
        """Actualiza un producto existente"""
        return self.db.execute_query(
            """UPDATE productos
               SET codigo_ean = ?, descripcion = ?, precio = ?, precio_compra = ?, categoria_id = ?, marca_id = ?, modelo_id = ?, imei = ?, ram = ?, almacenamiento = ?, estado = ?, stock = ?
               WHERE id = ?""",
            (datos['codigo_ean'], datos['descripcion'], datos['precio'], datos.get('precio_compra', 0),
             datos.get('categoria_id'), datos.get('marca_id'), datos.get('modelo_id'),
             datos.get('imei'), datos.get('ram'), datos.get('almacenamiento'), datos.get('estado'), datos.get('stock', 0), producto_id)
        )

    def desactivar_producto(self, producto_id):
        """Desactiva un producto (no lo elimina)"""
        return self.db.execute_query("UPDATE productos SET activo = 0 WHERE id = ?", (producto_id,))

    def buscar_productos(self, filtro=None, categoria_id=None):
        """Busca productos con filtros"""
        query = """
            SELECT p.*, c.nombre as categoria_nombre, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            LEFT JOIN marcas ma ON p.marca_id = ma.id
            LEFT JOIN modelos mo ON p.modelo_id = mo.id
            WHERE p.activo = 1
        """
        params = []

        if filtro:
            query += " AND (p.descripcion LIKE ? OR p.codigo_ean LIKE ? OR p.imei LIKE ?)"
            params.extend([f"%{filtro}%", f"%{filtro}%", f"%{filtro}%"])

        if categoria_id:
            query += " AND p.categoria_id = ?"
            params.append(categoria_id)

        query += " ORDER BY p.descripcion"

        return self.db.fetch_all(query, params if params else None)

    def obtener_producto(self, producto_id):
        """Obtiene un producto por ID"""
        return self.db.fetch_one(
            """SELECT p.*, c.nombre as categoria_nombre, ma.nombre as marca_nombre, mo.nombre as modelo_nombre
               FROM productos p
               LEFT JOIN categorias c ON p.categoria_id = c.id
               LEFT JOIN marcas ma ON p.marca_id = ma.id
               LEFT JOIN modelos mo ON p.modelo_id = mo.id
               WHERE p.id = ?""",
            (producto_id,)
        )

    def actualizar_stock(self, producto_id, cantidad):
        """Actualiza el stock de un producto (resta cantidad)"""
        return self.db.execute_query(
            "UPDATE productos SET stock = stock - ? WHERE id = ?",
            (cantidad, producto_id)
        )
