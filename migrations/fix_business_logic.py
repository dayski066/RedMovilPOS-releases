"""
Migración para corregir problemas de lógica de negocio:
1. Añadir columnas origen y compra_item_id a ventas_caja_items
2. Añadir columnas saldo_anterior y saldo_nuevo a caja_movimientos si no existen
3. Añadir columna referencia para ventas_caja en caja_movimientos
"""
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def run_migration():
    """Ejecuta la migración"""
    print(f"Conectando a: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Añadir columnas a ventas_caja_items para rastrear origen
        print("\n1. Añadiendo columnas origen y compra_item_id a ventas_caja_items...")

        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(ventas_caja_items)")
        columnas = [col[1] for col in cursor.fetchall()]

        if 'origen' not in columnas:
            cursor.execute("""
                ALTER TABLE ventas_caja_items
                ADD COLUMN origen TEXT DEFAULT 'productos'
            """)
            print("   - Columna 'origen' añadida")
        else:
            print("   - Columna 'origen' ya existe")

        if 'compra_item_id' not in columnas:
            cursor.execute("""
                ALTER TABLE ventas_caja_items
                ADD COLUMN compra_item_id INTEGER
            """)
            print("   - Columna 'compra_item_id' añadida")
        else:
            print("   - Columna 'compra_item_id' ya existe")

        # 2. Añadir columnas a caja_movimientos para saldo y referencia a ventas TPV
        print("\n2. Verificando columnas en caja_movimientos...")

        cursor.execute("PRAGMA table_info(caja_movimientos)")
        columnas_caja = [col[1] for col in cursor.fetchall()]

        if 'saldo_anterior' not in columnas_caja:
            cursor.execute("""
                ALTER TABLE caja_movimientos
                ADD COLUMN saldo_anterior REAL DEFAULT 0
            """)
            print("   - Columna 'saldo_anterior' añadida")
        else:
            print("   - Columna 'saldo_anterior' ya existe")

        if 'saldo_nuevo' not in columnas_caja:
            cursor.execute("""
                ALTER TABLE caja_movimientos
                ADD COLUMN saldo_nuevo REAL DEFAULT 0
            """)
            print("   - Columna 'saldo_nuevo' añadida")
        else:
            print("   - Columna 'saldo_nuevo' ya existe")

        if 'referencia_id' not in columnas_caja:
            cursor.execute("""
                ALTER TABLE caja_movimientos
                ADD COLUMN referencia_id INTEGER
            """)
            print("   - Columna 'referencia_id' añadida")
        else:
            print("   - Columna 'referencia_id' ya existe")

        if 'referencia_tipo' not in columnas_caja:
            cursor.execute("""
                ALTER TABLE caja_movimientos
                ADD COLUMN referencia_tipo TEXT
            """)
            print("   - Columna 'referencia_tipo' añadida")
        else:
            print("   - Columna 'referencia_tipo' ya existe")

        if 'venta_caja_id' not in columnas_caja:
            cursor.execute("""
                ALTER TABLE caja_movimientos
                ADD COLUMN venta_caja_id INTEGER REFERENCES ventas_caja(id)
            """)
            print("   - Columna 'venta_caja_id' añadida")
        else:
            print("   - Columna 'venta_caja_id' ya existe")

        # 3. Crear índice para venta_caja_id
        print("\n3. Creando índices...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_caja_movimientos_venta_caja
            ON caja_movimientos(venta_caja_id)
        """)
        print("   - Índice idx_caja_movimientos_venta_caja creado")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_caja_items_origen
            ON ventas_caja_items(origen)
        """)
        print("   - Índice idx_ventas_caja_items_origen creado")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_caja_items_compra_item
            ON ventas_caja_items(compra_item_id)
        """)
        print("   - Índice idx_ventas_caja_items_compra_item creado")

        conn.commit()
        print("\n[OK] Migración completada exitosamente")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error en la migración: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
