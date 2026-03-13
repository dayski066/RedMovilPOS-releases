"""
Migración para crear el sistema de Caja/TPV para ventas rápidas
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def migrate():
    """Crea las tablas necesarias para el TPV de caja"""
    print("=" * 50)
    print("Migrando: Sistema de Caja/TPV")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Tabla de ventas de caja (tickets)
        print("\n[1/3] Creando tabla 'ventas_caja'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_ticket TEXT UNIQUE NOT NULL,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                subtotal REAL DEFAULT 0,
                iva REAL DEFAULT 0,
                total REAL DEFAULT 0,
                metodo_pago TEXT DEFAULT 'efectivo',
                estado TEXT DEFAULT 'completada',
                usuario_id INTEGER,
                notas TEXT,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
            )
        """)
        
        # 2. Tabla de items de ventas de caja
        print("[2/3] Creando tabla 'ventas_caja_items'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ventas_caja_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_caja_id INTEGER NOT NULL,
                producto_id INTEGER,
                nombre_producto TEXT NOT NULL,
                precio_unitario REAL NOT NULL,
                cantidad INTEGER DEFAULT 1,
                iva_porcentaje REAL DEFAULT 21,
                subtotal_item REAL,
                iva_item REAL,
                total_item REAL,
                FOREIGN KEY (venta_caja_id) REFERENCES ventas_caja(id) ON DELETE CASCADE,
                FOREIGN KEY (producto_id) REFERENCES productos(id)
            )
        """)
        
        # 3. Tabla de productos favoritos para acceso rápido
        print("[3/3] Creando tabla 'productos_favoritos'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos_favoritos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                producto_id INTEGER,
                nombre TEXT NOT NULL,
                precio REAL NOT NULL,
                color TEXT DEFAULT '#5E81AC',
                orden INTEGER DEFAULT 0,
                es_manual INTEGER DEFAULT 0,
                FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        
        print("\n" + "=" * 50)
        print("[OK] Sistema de Caja/TPV creado correctamente")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()












