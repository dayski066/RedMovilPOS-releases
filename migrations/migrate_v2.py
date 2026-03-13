"""
Migración v2.0 - Agregar tablas faltantes y columnas nuevas

Este script actualiza bases de datos existentes con:
- Tabla reparaciones_items
- Tabla ventas_caja
- Tabla ventas_caja_items
- Tabla productos_favoritos
- Columnas adicionales en caja_movimientos
- Configuración para TPV

Ejecutar: python migrations/migrate_v2.py
"""
import sqlite3
import os
import sys

# Agregar path raíz al sistema
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH


def get_existing_tables(cursor):
    """Obtiene lista de tablas existentes"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    return [row[0] for row in cursor.fetchall()]


def get_table_columns(cursor, table_name):
    """Obtiene lista de columnas de una tabla"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def migrate():
    """Ejecuta la migración"""
    print("=" * 60)
    print("  MIGRACIÓN v2.0 - RedMovilpos")
    print("=" * 60)
    print(f"\nBase de datos: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print("\n[ERROR] La base de datos no existe.")
        print("Ejecuta primero la aplicación para crearla.")
        return False

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    existing_tables = get_existing_tables(cursor)
    print(f"\nTablas existentes: {len(existing_tables)}")

    changes_made = 0

    # 1. Tabla reparaciones_items
    if 'reparaciones_items' not in existing_tables:
        print("\n[+] Creando tabla reparaciones_items...")
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
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (reparacion_id) REFERENCES reparaciones(id) ON DELETE CASCADE,
                FOREIGN KEY (marca_id) REFERENCES marcas(id) ON DELETE SET NULL,
                FOREIGN KEY (modelo_id) REFERENCES modelos(id) ON DELETE SET NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_items_reparacion ON reparaciones_items(reparacion_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reparaciones_items_imei ON reparaciones_items(imei)")
        changes_made += 1
        print("    [OK] Tabla reparaciones_items creada")
    else:
        print("\n[=] Tabla reparaciones_items ya existe")

    # 2. Columnas adicionales en caja_movimientos
    if 'caja_movimientos' in existing_tables:
        caja_columns = get_table_columns(cursor, 'caja_movimientos')
        new_columns = [
            ('saldo_anterior', 'REAL'),
            ('saldo_nuevo', 'REAL'),
            ('venta_caja_id', 'INTEGER'),
            ('referencia_id', 'INTEGER'),
            ('referencia_tipo', 'TEXT')
        ]

        for col_name, col_type in new_columns:
            if col_name not in caja_columns:
                print(f"\n[+] Agregando columna {col_name} a caja_movimientos...")
                cursor.execute(f"ALTER TABLE caja_movimientos ADD COLUMN {col_name} {col_type}")
                changes_made += 1
                print(f"    [OK] Columna {col_name} agregada")

    # 3. Tabla ventas_caja
    if 'ventas_caja' not in existing_tables:
        print("\n[+] Creando tabla ventas_caja...")
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
        changes_made += 1
        print("    [OK] Tabla ventas_caja creada")
    else:
        print("\n[=] Tabla ventas_caja ya existe")

    # 4. Tabla ventas_caja_items
    if 'ventas_caja_items' not in existing_tables:
        print("\n[+] Creando tabla ventas_caja_items...")
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
        changes_made += 1
        print("    [OK] Tabla ventas_caja_items creada")
    else:
        print("\n[=] Tabla ventas_caja_items ya existe")

    # 5. Tabla productos_favoritos
    if 'productos_favoritos' not in existing_tables:
        print("\n[+] Creando tabla productos_favoritos...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos_favoritos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                color TEXT DEFAULT '#5E81AC',
                orden INTEGER DEFAULT 0,
                es_manual INTEGER DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_productos_favoritos_orden ON productos_favoritos(orden)")
        changes_made += 1
        print("    [OK] Tabla productos_favoritos creada")
    else:
        print("\n[=] Tabla productos_favoritos ya existe")

    # 6. Configuración adicional
    print("\n[+] Verificando configuración...")

    configs = [
        ('saldo_caja', '0.00', 'Saldo de caja'),
        ('ultimo_ticket_caja', '0', 'Último número de ticket TPV generado')
    ]

    for clave, valor, descripcion in configs:
        cursor.execute("SELECT 1 FROM configuracion WHERE clave = ?", (clave,))
        if not cursor.fetchone():
            cursor.execute(
                "INSERT INTO configuracion (clave, valor, descripcion) VALUES (?, ?, ?)",
                (clave, valor, descripcion)
            )
            changes_made += 1
            print(f"    [OK] Configuración '{clave}' agregada")

    # Guardar cambios
    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    if changes_made > 0:
        print(f"  MIGRACIÓN COMPLETADA - {changes_made} cambios aplicados")
    else:
        print("  BASE DE DATOS YA ACTUALIZADA - Sin cambios necesarios")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n[ERROR] Error durante la migración: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
