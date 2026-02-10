"""
Módulo de gestión de base de datos SQLite
Base de datos integrada - NO requiere instalación
"""
import sqlite3
import os
import sys
import bcrypt

# Añadir el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import DB_PATH
from app.utils.logger import get_logger

logger = get_logger('database')


class Database:
    """
    Gestor de base de datos SQLite con patrón Singleton.
    
    Solo existe una instancia de Database en toda la aplicación,
    lo que evita fugas de conexiones y mejora el rendimiento.
    """
    _instance = None
    _shared_connection = None
    
    def __new__(cls):
        """Patrón Singleton: siempre devuelve la misma instancia"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        # Solo inicializar una vez
        if self._initialized:
            return
        self._initialized = True
        self.db_path = DB_PATH
        self._in_transaction = False
        # Usar conexión compartida
        self.connection = Database._shared_connection

    def connect(self):
        """Establece conexión con la base de datos SQLite (reutiliza si existe)"""
        # Si ya hay conexión compartida activa, usarla
        if Database._shared_connection is not None:
            try:
                Database._shared_connection.execute("SELECT 1")
                self.connection = Database._shared_connection
                return True
            except (sqlite3.Error, AttributeError):
                Database._shared_connection = None
        
        try:
            # Crear directorio si no existe
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

            # Conectar a SQLite
            Database._shared_connection = sqlite3.connect(self.db_path, check_same_thread=False)
            Database._shared_connection.row_factory = sqlite3.Row
            Database._shared_connection.execute("PRAGMA foreign_keys = ON")
            
            # Asignar a instancia
            self.connection = Database._shared_connection
            
            logger.info(f"Conexión SQLite establecida: {self.db_path}")
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error al conectar con SQLite: {e}")
            return False

    def disconnect(self):
        """Cierra la conexión con la base de datos"""
        # NO cerrar la conexión compartida para evitar problemas
        # Solo se cierra al salir de la aplicación
        pass

    def create_tables(self):
        """Crea todas las tablas necesarias"""
        if not self.connection:
            self.connect()

        cursor = self.connection.cursor()

        # Tabla de clientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                nif TEXT,
                direccion TEXT,
                codigo_postal TEXT,
                ciudad TEXT,
                telefono TEXT,
                email TEXT,
                dni_imagen TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices para clientes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_nif ON clientes(nif)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_clientes_telefono ON clientes(telefono)")

        # Tabla de categorías
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                descripcion TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_categorias_nombre ON categorias(nombre)")

        # Tabla de marcas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS marcas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_marcas_nombre ON marcas(nombre)")

        # Tabla de modelos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS modelos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                marca_id INTEGER NOT NULL,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (marca_id) REFERENCES marcas(id) ON DELETE CASCADE,
                UNIQUE(nombre, marca_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_modelos_nombre ON modelos(nombre)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_modelos_marca ON modelos(marca_id)")

        # Tabla de productos/servicios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_ean TEXT UNIQUE,
                descripcion TEXT NOT NULL,
                precio REAL NOT NULL,
                categoria_id INTEGER,
                marca_id INTEGER,
                modelo_id INTEGER,
                imei TEXT,
                stock INTEGER DEFAULT 0,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE SET NULL,
                FOREIGN KEY (marca_id) REFERENCES marcas(id) ON DELETE SET NULL,
                FOREIGN KEY (modelo_id) REFERENCES modelos(id) ON DELETE SET NULL
            )
        """)

        # Índices para productos
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_descripcion ON productos(descripcion)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_codigo_ean ON productos(codigo_ean)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_imei ON productos(imei)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_marca ON productos(marca_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_modelo ON productos(modelo_id)")

        # Tabla de facturas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facturas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_factura TEXT UNIQUE NOT NULL,
                cliente_id INTEGER,
                fecha DATE NOT NULL,
                subtotal REAL NOT NULL,
                iva REAL NOT NULL,
                total REAL NOT NULL,
                notas TEXT,
                pdf_path TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL
            )
        """)

        # Índices para facturas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_numero ON facturas(numero_factura)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_fecha ON facturas(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facturas_cliente ON facturas(cliente_id)")

        # Tabla de líneas de factura (items)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS factura_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                factura_id INTEGER NOT NULL,
                producto_id INTEGER,
                descripcion TEXT NOT NULL,
                codigo_ean TEXT,
                imei_sn TEXT,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
            )
        """)

        # Índices para factura_items
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factura_items_factura ON factura_items(factura_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factura_items_producto ON factura_items(producto_id)")

        # Tabla de configuración
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT NOT NULL,
                descripcion TEXT
            )
        """)

        # Tabla de establecimientos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS establecimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                nif TEXT,
                direccion TEXT,
                telefono TEXT,
                email TEXT,
                logo_path TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_establecimientos_nombre ON establecimientos(nombre)")

        # Tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nombre_completo TEXT NOT NULL,
                rol TEXT DEFAULT 'usuario' CHECK(rol IN ('admin', 'usuario')),
                establecimiento_id INTEGER,
                recovery_key TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ultimo_acceso TIMESTAMP,
                FOREIGN KEY (establecimiento_id) REFERENCES establecimientos(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username)")

        # Tabla de compras
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_compra TEXT UNIQUE NOT NULL,
                proveedor_nombre TEXT NOT NULL,
                proveedor_nif TEXT,
                proveedor_direccion TEXT,
                proveedor_codigo_postal TEXT,
                proveedor_ciudad TEXT,
                proveedor_telefono TEXT,
                fecha DATE NOT NULL,
                subtotal REAL NOT NULL,
                iva REAL NOT NULL,
                total REAL NOT NULL,
                dni_imagen TEXT,
                notas TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Índices para compras
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compras_numero ON compras(numero_compra)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compras_fecha ON compras(fecha)")

        # Tabla de items de compra
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compras_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                compra_id INTEGER NOT NULL,
                producto_id INTEGER,
                descripcion TEXT NOT NULL,
                codigo_ean TEXT,
                imei TEXT,
                marca_id INTEGER,
                modelo_id INTEGER,
                ram TEXT,
                almacenamiento TEXT,
                estado TEXT,
                cantidad INTEGER NOT NULL,
                precio_unitario REAL NOT NULL,
                total REAL NOT NULL,
                FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL,
                FOREIGN KEY (marca_id) REFERENCES marcas(id) ON DELETE SET NULL,
                FOREIGN KEY (modelo_id) REFERENCES modelos(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_compras_items_compra ON compras_items(compra_id)")

        # Catálogo de averías (SAT)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS averias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                descripcion TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_averias_activo ON averias(activo)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_averias_nombre ON averias(nombre)")

        # Catálogo de soluciones (SAT)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS soluciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                averia_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (averia_id) REFERENCES averias(id) ON DELETE CASCADE,
                UNIQUE(averia_id, nombre)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_soluciones_averia ON soluciones(averia_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_soluciones_activo ON soluciones(activo)")

        # Tabla de reparaciones (SAT)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reparaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_orden TEXT UNIQUE NOT NULL,
                cliente_id INTEGER,
                cliente_nombre TEXT NOT NULL,
                cliente_nif TEXT,
                cliente_direccion TEXT,
                cliente_codigo_postal TEXT,
                cliente_ciudad TEXT,
                cliente_telefono TEXT,
                dispositivo TEXT NOT NULL,
                imei TEXT,
                problema_descripcion TEXT NOT NULL,
                diagnostico TEXT,
                solucion TEXT,
                costo_estimado REAL,
                costo_final REAL,
                estado TEXT DEFAULT 'pendiente' CHECK(estado IN ('pendiente', 'en_proceso', 'reparado', 'entregado', 'cancelado')),
                fecha_entrada DATE NOT NULL,
                fecha_estimada_entrega DATE,
                fecha_entrega DATE,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (cliente_id) REFERENCES clientes(id) ON DELETE SET NULL
            )
        """)

        # Índices para reparaciones
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_numero ON reparaciones(numero_orden)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_cliente ON reparaciones(cliente_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_estado ON reparaciones(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_fecha_entrada ON reparaciones(fecha_entrada)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_imei ON reparaciones(imei)")

        # Tabla de items de reparación (dispositivos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reparaciones_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reparacion_id INTEGER NOT NULL,
                marca_id INTEGER,
                modelo_id INTEGER,
                imei TEXT,
                averia TEXT,
                patron_codigo TEXT,
                notas TEXT,
                precio_estimado REAL DEFAULT 0,
                precio_final REAL,
                estado TEXT DEFAULT 'pendiente',
                averia_texto TEXT,
                solucion_texto TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reparacion_id) REFERENCES reparaciones(id) ON DELETE CASCADE,
                FOREIGN KEY (marca_id) REFERENCES marcas(id) ON DELETE SET NULL,
                FOREIGN KEY (modelo_id) REFERENCES modelos(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_items_reparacion ON reparaciones_items(reparacion_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_items_imei ON reparaciones_items(imei)")

        # Tabla de averías por item de reparación
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reparaciones_averias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reparacion_item_id INTEGER NOT NULL,
                descripcion_averia TEXT,
                solucion TEXT,
                precio REAL DEFAULT 0,
                orden INTEGER DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reparacion_item_id) REFERENCES reparaciones_items(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_averias_item ON reparaciones_averias(reparacion_item_id)")

        # Tabla de movimientos de caja
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS caja_movimientos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL CHECK(tipo IN ('ingreso', 'egreso')),
                categoria TEXT NOT NULL,
                concepto TEXT NOT NULL,
                monto REAL NOT NULL,
                fecha DATE NOT NULL,
                saldo_anterior REAL,
                saldo_nuevo REAL,
                factura_id INTEGER,
                compra_id INTEGER,
                reparacion_id INTEGER,
                venta_caja_id INTEGER,
                referencia_id INTEGER,
                referencia_tipo TEXT,
                notas TEXT,
                usuario_id INTEGER,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (factura_id) REFERENCES facturas(id) ON DELETE SET NULL,
                FOREIGN KEY (compra_id) REFERENCES compras(id) ON DELETE SET NULL,
                FOREIGN KEY (reparacion_id) REFERENCES reparaciones(id) ON DELETE SET NULL,
                FOREIGN KEY (venta_caja_id) REFERENCES ventas_caja(id) ON DELETE SET NULL,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        """)

        # Índices para caja_movimientos
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_caja_movimientos_fecha ON caja_movimientos(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_caja_movimientos_tipo ON caja_movimientos(tipo)")

        # Tabla de cierres de caja
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS caja_cierres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATE NOT NULL UNIQUE,
                saldo_inicial REAL NOT NULL,
                total_ingresos REAL NOT NULL,
                total_egresos REAL NOT NULL,
                saldo_final REAL NOT NULL,
                saldo_efectivo_contado REAL NOT NULL,
                diferencia REAL NOT NULL,
                notas TEXT,
                usuario_id INTEGER,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_caja_cierres_fecha ON caja_cierres(fecha)")

        # Tabla de ventas de caja/TPV
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_ticket TEXT UNIQUE NOT NULL,
                subtotal REAL NOT NULL,
                iva REAL NOT NULL,
                total REAL NOT NULL,
                metodo_pago TEXT DEFAULT 'efectivo' CHECK(metodo_pago IN ('efectivo', 'tarjeta', 'mixto')),
                cantidad_recibida REAL,
                cambio_devuelto REAL,
                usuario_id INTEGER,
                notas TEXT,
                estado TEXT DEFAULT 'completada' CHECK(estado IN ('completada', 'anulada')),
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_caja_numero ON ventas_caja(numero_ticket)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_caja_fecha ON ventas_caja(fecha)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_caja_estado ON ventas_caja(estado)")

        # Tabla de items de ventas de caja/TPV
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_caja_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_caja_id INTEGER NOT NULL,
                producto_id INTEGER,
                compra_item_id INTEGER,
                nombre_producto TEXT NOT NULL,
                precio_unitario REAL NOT NULL,
                cantidad INTEGER NOT NULL DEFAULT 1,
                subtotal_item REAL NOT NULL,
                iva_item REAL NOT NULL,
                total_item REAL NOT NULL,
                origen TEXT DEFAULT 'productos',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (venta_caja_id) REFERENCES ventas_caja(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL,
                FOREIGN KEY (compra_item_id) REFERENCES compras_items(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_caja_items_venta ON ventas_caja_items(venta_caja_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ventas_caja_items_producto ON ventas_caja_items(producto_id)")

        # Tabla de productos favoritos (TPV)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos_favoritos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                color TEXT DEFAULT '#3498db',
                orden INTEGER DEFAULT 0,
                es_manual INTEGER DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_favoritos_orden ON productos_favoritos(orden)")

        # Migraciones para bases de datos existentes
        self._aplicar_migraciones(cursor)

        # Insertar configuración inicial
        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('ultimo_numero_factura', '15', 'Último número de factura generado')
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('ultimo_codigo_ean', '1000000000', 'Último código EAN generado automáticamente')
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('ultimo_numero_compra', '0', 'Último número de compra generado')
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('ultimo_numero_reparacion', '0', 'Último número de orden de reparación generado')
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('saldo_caja_actual', '0.00', 'Saldo actual de caja')
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('saldo_caja', '0.00', 'Saldo de caja')
        """)

        cursor.execute("""
            INSERT OR IGNORE INTO configuracion (clave, valor, descripcion)
            VALUES ('ultimo_ticket_caja', '0', 'Último número de ticket TPV generado')
        """)

        # Insertar categorías por defecto
        categorias_defecto = [
            ('Móviles', 'Teléfonos móviles y smartphones'),
            ('Accesorios', 'Accesorios para móviles'),
            ('Reparaciones', 'Servicios de reparación'),
            ('Otros', 'Otros productos y servicios')
        ]

        for nombre, descripcion in categorias_defecto:
            cursor.execute("""
                INSERT OR IGNORE INTO categorias (nombre, descripcion)
                VALUES (?, ?)
            """, (nombre, descripcion))

        self.connection.commit()
        cursor.close()
        logger.info("Base de datos SQLite creada exitosamente")
        logger.info(f"Ubicacion: {self.db_path}")

    def _aplicar_migraciones(self, cursor):
        """Aplica migraciones para bases de datos existentes"""
        # Verificar si la columna establecimiento_id existe en usuarios
        cursor.execute("PRAGMA table_info(usuarios)")
        columnas = [col[1] for col in cursor.fetchall()]

        if 'establecimiento_id' not in columnas:
            logger.info("Añadiendo columna establecimiento_id a usuarios...")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN establecimiento_id INTEGER")
            logger.info("Columna establecimiento_id añadida")

        # Añadir columna metodo_pago a caja_movimientos si no existe
        cursor.execute("PRAGMA table_info(caja_movimientos)")
        columnas_caja = [col[1] for col in cursor.fetchall()]
        if 'metodo_pago' not in columnas_caja:
            logger.info("Añadiendo columna metodo_pago a caja_movimientos...")
            cursor.execute("ALTER TABLE caja_movimientos ADD COLUMN metodo_pago TEXT DEFAULT 'efectivo'")
            logger.info("Columna metodo_pago añadida")

        # Crear tabla devoluciones si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devoluciones'")
        if not cursor.fetchone():
            logger.info("Creando tabla devoluciones...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devoluciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    venta_caja_id INTEGER NOT NULL,
                    usuario_id INTEGER,
                    motivo TEXT,
                    monto_devuelto REAL NOT NULL,
                    metodo_devolucion TEXT DEFAULT 'efectivo',
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notas TEXT,
                    FOREIGN KEY (venta_caja_id) REFERENCES ventas_caja(id) ON DELETE CASCADE,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_devoluciones_venta ON devoluciones(venta_caja_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_devoluciones_fecha ON devoluciones(fecha_creacion)")
            logger.info("Tabla devoluciones creada")

        # Crear tabla roles si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='roles'")
        if not cursor.fetchone():
            logger.info("Creando tabla roles...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE NOT NULL,
                    descripcion TEXT,
                    es_sistema INTEGER DEFAULT 0,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Insertar roles por defecto
            cursor.execute("INSERT OR IGNORE INTO roles (nombre, descripcion, es_sistema) VALUES ('admin', 'Administrador del sistema', 1)")
            cursor.execute("INSERT OR IGNORE INTO roles (nombre, descripcion, es_sistema) VALUES ('usuario', 'Usuario estándar', 1)")
            logger.info("Tabla roles creada")

        # Crear tabla permisos si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='permisos'")
        if not cursor.fetchone():
            logger.info("Creando tabla permisos...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS permisos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT UNIQUE NOT NULL,
                    nombre TEXT NOT NULL,
                    modulo TEXT,
                    descripcion TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            logger.info("Tabla permisos creada")

        # Crear tabla rol_permisos si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rol_permisos'")
        if not cursor.fetchone():
            logger.info("Creando tabla rol_permisos...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rol_permisos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rol_id INTEGER NOT NULL,
                    permiso_id INTEGER NOT NULL,
                    FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
                    FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE,
                    UNIQUE(rol_id, permiso_id)
                )
            """)
            logger.info("Tabla rol_permisos creada")

        # Añadir columnas de móviles a productos si no existen
        cursor.execute("PRAGMA table_info(productos)")
        columnas_productos = [col[1] for col in cursor.fetchall()]

        if 'ram' not in columnas_productos:
            logger.info("Añadiendo columna ram a productos...")
            cursor.execute("ALTER TABLE productos ADD COLUMN ram TEXT")
            logger.info("Columna ram añadida")

        if 'almacenamiento' not in columnas_productos:
            logger.info("Añadiendo columna almacenamiento a productos...")
            cursor.execute("ALTER TABLE productos ADD COLUMN almacenamiento TEXT")
            logger.info("Columna almacenamiento añadida")

        if 'estado' not in columnas_productos:
            logger.info("Añadiendo columna estado a productos...")
            cursor.execute("ALTER TABLE productos ADD COLUMN estado TEXT")
            logger.info("Columna estado añadida")

        # Añadir columnas de codigo_postal y ciudad a clientes si no existen
        cursor.execute("PRAGMA table_info(clientes)")
        columnas_clientes = [col[1] for col in cursor.fetchall()]

        if 'codigo_postal' not in columnas_clientes:
            logger.info("Añadiendo columna codigo_postal a clientes...")
            cursor.execute("ALTER TABLE clientes ADD COLUMN codigo_postal TEXT")
            logger.info("Columna codigo_postal añadida")

        if 'ciudad' not in columnas_clientes:
            logger.info("Añadiendo columna ciudad a clientes...")
            cursor.execute("ALTER TABLE clientes ADD COLUMN ciudad TEXT")
            logger.info("Columna ciudad añadida")

        # Añadir columnas a compras
        cursor.execute("PRAGMA table_info(compras)")
        columnas_compras = [col[1] for col in cursor.fetchall()]

        if 'proveedor_codigo_postal' not in columnas_compras:
            logger.info("Añadiendo columna proveedor_codigo_postal a compras...")
            cursor.execute("ALTER TABLE compras ADD COLUMN proveedor_codigo_postal TEXT")
            logger.info("Columna proveedor_codigo_postal añadida")

        if 'proveedor_ciudad' not in columnas_compras:
            logger.info("Añadiendo columna proveedor_ciudad a compras...")
            cursor.execute("ALTER TABLE compras ADD COLUMN proveedor_ciudad TEXT")
            logger.info("Columna proveedor_ciudad añadida")

        # Añadir columnas a reparaciones
        cursor.execute("PRAGMA table_info(reparaciones)")
        columnas_reparaciones = [col[1] for col in cursor.fetchall()]

        if 'cliente_codigo_postal' not in columnas_reparaciones:
            logger.info("Añadiendo columna cliente_codigo_postal a reparaciones...")
            cursor.execute("ALTER TABLE reparaciones ADD COLUMN cliente_codigo_postal TEXT")
            logger.info("Columna cliente_codigo_postal añadida")

        if 'cliente_ciudad' not in columnas_reparaciones:
            logger.info("Añadiendo columna cliente_ciudad a reparaciones...")
            cursor.execute("ALTER TABLE reparaciones ADD COLUMN cliente_ciudad TEXT")
            logger.info("Columna cliente_ciudad añadida")

        if 'qr_code' not in columnas_reparaciones:
            logger.info("Añadiendo columna qr_code a reparaciones...")
            cursor.execute("ALTER TABLE reparaciones ADD COLUMN qr_code TEXT")
            logger.info("Columna qr_code añadida")

        if 'precio_compra' not in columnas_productos:
            logger.info("Añadiendo columna precio_compra a productos...")
            cursor.execute("ALTER TABLE productos ADD COLUMN precio_compra REAL DEFAULT 0")
            logger.info("Columna precio_compra añadida")

        # Crear tabla reparaciones_averias si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reparaciones_averias'")
        if not cursor.fetchone():
            logger.info("Creando tabla reparaciones_averias...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reparaciones_averias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reparacion_item_id INTEGER NOT NULL,
                    descripcion_averia TEXT,
                    solucion TEXT,
                    precio REAL DEFAULT 0,
                    orden INTEGER DEFAULT 0,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reparacion_item_id) REFERENCES reparaciones_items(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_averias_item ON reparaciones_averias(reparacion_item_id)")
            logger.info("Tabla reparaciones_averias creada")

        # Crear tabla aperturas_caja si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='aperturas_caja'")
        if not cursor.fetchone():
            logger.info("Creando tabla aperturas_caja...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS aperturas_caja (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha DATE NOT NULL,
                    saldo_inicial REAL DEFAULT 0,
                    usuario_id INTEGER,
                    notas TEXT,
                    cerrada INTEGER DEFAULT 0,
                    saldo_final REAL,
                    fecha_cierre TIMESTAMP,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_aperturas_caja_fecha ON aperturas_caja(fecha)")
            logger.info("Tabla aperturas_caja creada")

        # MIGRACIÓN: Crear índice UNIQUE en IMEI de productos (evita duplicados)
        # Solo aplicar a IMEIs no vacíos para permitir productos sin IMEI
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_productos_imei_unique'")
            if not cursor.fetchone():
                logger.info("Creando índice UNIQUE para IMEI en productos...")
                # Primero verificar si hay duplicados
                cursor.execute("""
                    SELECT imei, COUNT(*) as cnt FROM productos 
                    WHERE imei IS NOT NULL AND imei != '' 
                    GROUP BY imei HAVING cnt > 1
                """)
                duplicados = cursor.fetchall()
                if duplicados:
                    logger.warning(f"Hay {len(duplicados)} IMEIs duplicados. No se puede crear índice UNIQUE.")
                    logger.warning("Corrija los duplicados manualmente antes de continuar.")
                else:
                    # Crear índice UNIQUE parcial (solo para IMEIs no vacíos)
                    cursor.execute("""
                        CREATE UNIQUE INDEX IF NOT EXISTS idx_productos_imei_unique 
                        ON productos(imei) WHERE imei IS NOT NULL AND imei != ''
                    """)
                    logger.info("Índice UNIQUE para IMEI creado")
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.warning(f"No se pudo crear índice UNIQUE para IMEI: {e}")

        # MIGRACIÓN: Crear trigger para validar stock no negativo
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name='validar_stock_no_negativo'")
            if not cursor.fetchone():
                logger.info("Creando trigger para validar stock no negativo...")
                cursor.execute("""
                    CREATE TRIGGER IF NOT EXISTS validar_stock_no_negativo
                    BEFORE UPDATE OF stock ON productos
                    FOR EACH ROW
                    WHEN NEW.stock < 0
                    BEGIN
                        SELECT RAISE(ABORT, 'Stock no puede ser negativo');
                    END
                """)
                logger.info("Trigger validar_stock_no_negativo creado")
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.warning(f"No se pudo crear trigger de stock: {e}")

        # ========== SISTEMA DE AUDITORÍA DE USUARIOS ==========
        
        # MIGRACIÓN: Crear tabla historial_operaciones
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historial_operaciones'")
        if not cursor.fetchone():
            logger.info("Creando tabla historial_operaciones...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historial_operaciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    tipo_operacion TEXT NOT NULL,
                    tabla TEXT NOT NULL,
                    registro_id INTEGER,
                    descripcion TEXT NOT NULL,
                    datos_anteriores TEXT,
                    datos_nuevos TEXT,
                    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_fecha ON historial_operaciones(fecha)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_usuario ON historial_operaciones(usuario_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_historial_tabla ON historial_operaciones(tabla)")
            logger.info("Tabla historial_operaciones creada")

        # MIGRACIÓN: Añadir columnas de auditoría a tablas principales
        tablas_auditoria = [
            'facturas', 'compras', 'reparaciones', 'ventas_caja', 'devoluciones',
            'productos', 'clientes', 'categorias', 'marcas', 'modelos',
            'averias', 'soluciones', 'productos_favoritos',
            'establecimientos', 'usuarios', 'roles'
        ]
        
        for tabla in tablas_auditoria:
            try:
                # Verificar si la columna ya existe
                cursor.execute(f"PRAGMA table_info({tabla})")
                columnas = [col[1] for col in cursor.fetchall()]
                
                if 'usuario_creacion_id' not in columnas:
                    logger.info(f"Añadiendo columna usuario_creacion_id a {tabla}...")
                    cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN usuario_creacion_id INTEGER REFERENCES usuarios(id)")
                
                # Solo añadir columnas de modificación a tablas editables
                tablas_con_edicion = ['facturas', 'compras', 'reparaciones', 'productos', 'clientes', 
                                      'establecimientos', 'usuarios', 'roles', 'categorias', 'marcas', 'modelos']
                if tabla in tablas_con_edicion:
                    if 'usuario_modificacion_id' not in columnas:
                        logger.info(f"Añadiendo columna usuario_modificacion_id a {tabla}...")
                        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN usuario_modificacion_id INTEGER REFERENCES usuarios(id)")
                    
                    if 'fecha_modificacion' not in columnas:
                        logger.info(f"Añadiendo columna fecha_modificacion a {tabla}...")
                        cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN fecha_modificacion TIMESTAMP")
                        
            except (sqlite3.Error, OSError, ValueError) as e:
                logger.warning(f"Error añadiendo columnas de auditoría a {tabla}: {e}")

        # ========== FIN SISTEMA DE AUDITORÍA ==========

        # MIGRACIÓN: Crear tabla reparaciones_recambios
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='reparaciones_recambios'")
        if not cursor.fetchone():
            logger.info("Creando tabla reparaciones_recambios...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reparaciones_recambios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reparacion_id INTEGER NOT NULL,
                    producto_id INTEGER,
                    descripcion TEXT NOT NULL,
                    cantidad INTEGER DEFAULT 1,
                    precio_unitario REAL DEFAULT 0,
                    codigo_ean TEXT,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (reparacion_id) REFERENCES reparaciones(id) ON DELETE CASCADE,
                    FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE SET NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_recambios_reparacion ON reparaciones_recambios(reparacion_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_recambios_producto ON reparaciones_recambios(producto_id)")
            logger.info("Tabla reparaciones_recambios creada")

        # MIGRACIÓN: Crear tabla devoluciones_items si no existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devoluciones_items'")
        if not cursor.fetchone():
            logger.info("Creando tabla devoluciones_items...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS devoluciones_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    devolucion_id INTEGER NOT NULL,
                    venta_item_id INTEGER NOT NULL,
                    cantidad_devuelta INTEGER NOT NULL,
                    precio_unitario REAL NOT NULL,
                    subtotal REAL NOT NULL,
                    iva REAL NOT NULL,
                    total REAL NOT NULL,
                    FOREIGN KEY (devolucion_id) REFERENCES devoluciones(id) ON DELETE CASCADE,
                    FOREIGN KEY (venta_item_id) REFERENCES ventas_caja_items(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_devoluciones_items_devolucion ON devoluciones_items(devolucion_id)")
            logger.info("Tabla devoluciones_items creada")

        # MIGRACIÓN: Añadir columna cantidad_devuelta a ventas_caja_items
        cursor.execute("PRAGMA table_info(ventas_caja_items)")
        columnas_vci = [col[1] for col in cursor.fetchall()]
        if 'cantidad_devuelta' not in columnas_vci:
            logger.info("Añadiendo columna cantidad_devuelta a ventas_caja_items...")
            cursor.execute("ALTER TABLE ventas_caja_items ADD COLUMN cantidad_devuelta INTEGER DEFAULT 0")
            logger.info("Columna cantidad_devuelta añadida")

        # MIGRACIÓN: Añadir columnas de cliente a tabla facturas (para preservar datos históricos)
        cursor.execute("PRAGMA table_info(facturas)")
        columnas_facturas = [col[1] for col in cursor.fetchall()]
        if 'cliente_nombre' not in columnas_facturas:
            logger.info("Añadiendo columnas de cliente a facturas...")
            cursor.execute("ALTER TABLE facturas ADD COLUMN cliente_nombre TEXT")
            cursor.execute("ALTER TABLE facturas ADD COLUMN cliente_nif TEXT")
            cursor.execute("ALTER TABLE facturas ADD COLUMN cliente_direccion TEXT")
            cursor.execute("ALTER TABLE facturas ADD COLUMN cliente_telefono TEXT")
            cursor.execute("ALTER TABLE facturas ADD COLUMN cliente_codigo_postal TEXT")
            cursor.execute("ALTER TABLE facturas ADD COLUMN cliente_ciudad TEXT")
            
            # Migrar datos existentes desde la tabla clientes
            cursor.execute("""
                UPDATE facturas
                SET cliente_nombre = (SELECT nombre FROM clientes WHERE clientes.id = facturas.cliente_id),
                    cliente_nif = (SELECT nif FROM clientes WHERE clientes.id = facturas.cliente_id),
                    cliente_direccion = (SELECT direccion FROM clientes WHERE clientes.id = facturas.cliente_id),
                    cliente_telefono = (SELECT telefono FROM clientes WHERE clientes.id = facturas.cliente_id),
                    cliente_codigo_postal = (SELECT codigo_postal FROM clientes WHERE clientes.id = facturas.cliente_id),
                    cliente_ciudad = (SELECT ciudad FROM clientes WHERE clientes.id = facturas.cliente_id)
                WHERE cliente_id IS NOT NULL
            """)
            logger.info("Columnas de cliente añadidas a facturas y datos migrados")

        # Migrar datos de empresa desde configuracion a establecimientos
        self._migrar_datos_empresa(cursor)

    def _migrar_datos_empresa(self, cursor):
        """Migra datos de empresa de configuracion a establecimientos"""
        # Añadir permisos de establecimientos si no existen
        self._añadir_permisos_establecimientos(cursor)

        # Verificar si ya hay establecimientos
        cursor.execute("SELECT COUNT(*) as count FROM establecimientos")
        if cursor.fetchone()[0] > 0:
            return  # Ya hay establecimientos, no migrar

    def _añadir_permisos_establecimientos(self, cursor):
        """Añade los permisos de gestión de establecimientos"""
        # Verificar que la tabla permisos existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='permisos'")
        if not cursor.fetchone():
            return  # La tabla no existe aún, se creará después

        permisos_establecimientos = [
            ('establecimientos.ver', 'Ver establecimientos', 'Establecimientos', 'Permite ver la lista de establecimientos'),
            ('establecimientos.crear', 'Crear establecimientos', 'Establecimientos', 'Permite crear nuevos establecimientos'),
            ('establecimientos.editar', 'Editar establecimientos', 'Establecimientos', 'Permite editar establecimientos existentes'),
            ('establecimientos.eliminar', 'Eliminar establecimientos', 'Establecimientos', 'Permite eliminar establecimientos'),
        ]

        for codigo, nombre, modulo, descripcion in permisos_establecimientos:
            cursor.execute("""
                INSERT OR IGNORE INTO permisos (codigo, nombre, modulo, descripcion)
                VALUES (?, ?, ?, ?)
            """, (codigo, nombre, modulo, descripcion))

        # Asignar permisos al rol admin
        cursor.execute("SELECT id FROM roles WHERE nombre = 'admin'")
        admin_row = cursor.fetchone()
        if admin_row:
            admin_id = admin_row[0]
            for codigo, _, _, _ in permisos_establecimientos:
                cursor.execute("SELECT id FROM permisos WHERE codigo = ?", (codigo,))
                perm_row = cursor.fetchone()
                if perm_row:
                    cursor.execute("""
                        INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                        VALUES (?, ?)
                    """, (admin_id, perm_row[0]))

        # Verificar si hay datos de empresa en configuracion
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'empresa_nombre'")
        row = cursor.fetchone()
        if not row or not row[0]:
            return  # No hay datos de empresa para migrar

        logger.info("Migrando datos de empresa a establecimientos...")

        # Obtener datos de empresa
        datos_empresa = {}
        claves = ['empresa_nombre', 'empresa_nif', 'empresa_direccion', 'empresa_telefono', 'empresa_email', 'empresa_logo']
        for clave in claves:
            cursor.execute("SELECT valor FROM configuracion WHERE clave = ?", (clave,))
            row = cursor.fetchone()
            datos_empresa[clave] = row[0] if row else None

        # Insertar en establecimientos
        cursor.execute("""
            INSERT INTO establecimientos (nombre, nif, direccion, telefono, email, logo_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datos_empresa.get('empresa_nombre'),
            datos_empresa.get('empresa_nif'),
            datos_empresa.get('empresa_direccion'),
            datos_empresa.get('empresa_telefono'),
            datos_empresa.get('empresa_email'),
            datos_empresa.get('empresa_logo')
        ))

        establecimiento_id = cursor.lastrowid
        logger.info(f"Establecimiento creado con ID: {establecimiento_id}")

        # Asignar establecimiento a todos los usuarios existentes
        cursor.execute("UPDATE usuarios SET establecimiento_id = ? WHERE establecimiento_id IS NULL", (establecimiento_id,))
        logger.info("Establecimiento asignado a usuarios existentes")

        # Eliminar datos de empresa de configuracion (ya no son necesarios)
        claves_eliminar = [
            'empresa_nombre', 'empresa_nif', 'empresa_direccion',
            'empresa_telefono', 'empresa_email', 'empresa_logo',
            'empresa_ciudad', 'empresa_web'
        ]
        for clave in claves_eliminar:
            cursor.execute("DELETE FROM configuracion WHERE clave = ?", (clave,))
        logger.info("Datos de empresa eliminados de configuracion")

    def execute_query(self, query, params=None):
        """
        Ejecuta una consulta SQL.

        IMPORTANTE: Solo hace commit automático si NO estamos en una transacción explícita.
        Si estamos en transacción (begin_transaction llamado), el commit debe hacerse
        manualmente con commit() o rollback().
        """
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Solo hacer commit si NO estamos en transacción explícita
            if not self._in_transaction:
                self.connection.commit()

            return cursor.lastrowid
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error ejecutando query: {e}")
            logger.debug(f"Query: {query}")
            logger.debug(f"Params: {params}")
            # Si NO estamos en transacción explícita, hacer rollback automático
            if not self._in_transaction:
                self.connection.rollback()
            return None
        finally:
            cursor.close()

    def fetch_all(self, query, params=None):
        """Obtiene todos los resultados de una consulta"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Convertir Row objects a diccionarios
            rows = cursor.fetchall()
            results = []
            for row in rows:
                results.append(dict(row))

            cursor.close()
            return results
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error obteniendo datos: {e}")
            logger.debug(f"Query: {query}")
            return []

    def fetch_one(self, query, params=None):
        """Obtiene un solo resultado de una consulta"""
        try:
            cursor = self.connection.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            row = cursor.fetchone()
            result = dict(row) if row else None

            cursor.close()
            return result
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"Error obteniendo dato: {e}")
            logger.debug(f"Query: {query}")
            return None

    def begin_transaction(self):
        """
        Inicia una transacción explícita.
        Todas las operaciones siguientes serán parte de la transacción
        hasta que se llame a commit() o rollback().

        IMPORTANTE: SQLite usa autocommit por defecto. Este método
        asegura que múltiples operaciones sean atómicas.
        """
        try:
            # Si ya hay una transacción activa, hacer commit primero
            if self._in_transaction:
                self.connection.commit()
                self._in_transaction = False

            self.connection.execute("BEGIN TRANSACTION")
            self._in_transaction = True
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"No se pudo iniciar transacción: {e}")
            # Intentar recuperar haciendo rollback
            try:
                self.connection.rollback()
            except (sqlite3.Error, OSError, ValueError):
                pass
            self._in_transaction = False
            return False

    def commit(self):
        """
        Confirma la transacción actual.
        Guarda todos los cambios realizados desde begin_transaction().
        """
        try:
            self.connection.commit()
            self._in_transaction = False  # Desactivar flag
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"No se pudo confirmar transacción: {e}")
            return False

    def rollback(self):
        """
        Revierte la transacción actual.
        Deshace todos los cambios realizados desde begin_transaction().
        """
        try:
            self.connection.rollback()
            self._in_transaction = False  # Desactivar flag
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            logger.error(f"No se pudo revertir transacción: {e}")
            return False


# Función para inicializar la base de datos
def init_database():
    """Inicializa la base de datos y crea las tablas"""
    db = Database()
    if db.connect():
        logger.info("Conectado a SQLite")
        db.create_tables()
        db.disconnect()
        return True
    else:
        logger.error("No se pudo crear la base de datos SQLite")
        return False


if __name__ == "__main__":
    init_database()
