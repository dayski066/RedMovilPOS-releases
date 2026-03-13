"""
Módulo de gestión de base de datos MySQL
"""
import mysql.connector
from mysql.connector import Error
import sys
import os

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import DB_CONFIG


class Database:
    def __init__(self):
        self.connection = None

    def connect(self):
        """Establece conexión con la base de datos"""
        try:
            # Primero conectar sin especificar la base de datos
            temp_config = DB_CONFIG.copy()
            database = temp_config.pop('database')

            self.connection = mysql.connector.connect(**temp_config)

            if self.connection.is_connected():
                cursor = self.connection.cursor()
                # Crear la base de datos si no existe
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database}")
                cursor.execute(f"USE {database}")
                cursor.close()
                return True
        except Error as e:
            print(f"Error al conectar con MySQL: {e}")
            return False

    def disconnect(self):
        """Cierra la conexión con la base de datos"""
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def create_tables(self):
        """Crea todas las tablas necesarias"""
        if not self.connection or not self.connection.is_connected():
            self.connect()

        cursor = self.connection.cursor()

        # Tabla de clientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(255) NOT NULL,
                nif VARCHAR(50),
                direccion TEXT,
                telefono VARCHAR(50),
                email VARCHAR(100),
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_nombre (nombre),
                INDEX idx_nif (nif),
                INDEX idx_telefono (telefono)
            )
        """)

        # Tabla de categorías
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INT AUTO_INCREMENT PRIMARY KEY,
                nombre VARCHAR(100) NOT NULL UNIQUE,
                descripcion TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_nombre (nombre)
            )
        """)

        # Tabla de productos/servicios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo_ean VARCHAR(50) UNIQUE,
                descripcion VARCHAR(255) NOT NULL,
                precio DECIMAL(10, 2) NOT NULL,
                categoria_id INT,
                imei VARCHAR(100),
                stock INT DEFAULT 0,
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL,
                INDEX idx_descripcion (descripcion),
                INDEX idx_codigo_ean (codigo_ean),
                INDEX idx_imei (imei),
                INDEX idx_categoria (categoria_id)
            )
        """)

        # Tabla de facturas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                numero_factura VARCHAR(50) UNIQUE NOT NULL,
                cliente_id INT,
                fecha DATE NOT NULL,
                subtotal DECIMAL(10, 2) NOT NULL,
                iva DECIMAL(10, 2) NOT NULL,
                total DECIMAL(10, 2) NOT NULL,
                notas TEXT,
                pdf_path VARCHAR(500),
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL,
                INDEX idx_numero (numero_factura),
                INDEX idx_fecha (fecha),
                INDEX idx_cliente (cliente_id)
            )
        """)

        # Tabla de líneas de factura (items)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factura_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                factura_id INT NOT NULL,
                producto_id INT,
                descripcion VARCHAR(255) NOT NULL,
                codigo_ean VARCHAR(50),
                imei_sn VARCHAR(100),
                cantidad INT NOT NULL,
                precio_unitario DECIMAL(10, 2) NOT NULL,
                total DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL,
                INDEX idx_factura (factura_id),
                INDEX idx_producto (producto_id)
            )
        """)

        # Tabla de configuración (para números de factura, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave VARCHAR(50) PRIMARY KEY,
                valor VARCHAR(255) NOT NULL,
                descripcion TEXT
            )
        """)

        # Insertar configuración inicial si no existe
        cursor.execute("""
            INSERT IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('ultimo_numero_factura', '15', 'Último número de factura generado')
        """)

        cursor.execute("""
            INSERT IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('ultimo_codigo_ean', '1000000000', 'Último código EAN generado automáticamente')
        """)

        # Tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                nombre_completo VARCHAR(255) NOT NULL,
                rol ENUM('admin', 'usuario') DEFAULT 'usuario',
                activo BOOLEAN DEFAULT TRUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TIMESTAMP NULL,
                INDEX idx_username (username)
            )
        """)

        # Insertar categorías por defecto
        cursor.execute("""
            INSERT IGNORE INTO categorias (nombre, descripcion)
            VALUES
                ('Móviles', 'Teléfonos móviles y smartphones'),
                ('Accesorios', 'Accesorios para móviles'),
                ('Reparaciones', 'Servicios de reparación'),
                ('Otros', 'Otros productos y servicios')
        """)

        # Crear super usuario por defecto (admin/admin123)
        # Hash de 'admin123' con bcrypt
        cursor.execute("""
            INSERT IGNORE INTO usuarios (username, password_hash, nombre_completo, rol)
            VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqYQk7Y9ue', 'Administrador', 'admin')
        """)

        self.connection.commit()
        cursor.close()
        print("✓ Tablas creadas exitosamente")
        print("✓ Usuario por defecto: admin / admin123")

    def execute_query(self, query, params=None):
        """Ejecuta una consulta SQL"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Error ejecutando query: {e}")
            return None
        finally:
            cursor.close()

    def fetch_all(self, query, params=None):
        """Obtiene todos los resultados de una consulta"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            print(f"Error obteniendo datos: {e}")
            return []

    def fetch_one(self, query, params=None):
        """Obtiene un solo resultado de una consulta"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            print(f"Error obteniendo dato: {e}")
            return None


# Función para inicializar la base de datos
def init_database():
    """Inicializa la base de datos y crea las tablas"""
    db = Database()
    if db.connect():
        print("✓ Conectado a MySQL")
        db.create_tables()
        db.disconnect()
        return True
    else:
        print("✗ No se pudo conectar a MySQL")
        return False


if __name__ == "__main__":
    init_database()
