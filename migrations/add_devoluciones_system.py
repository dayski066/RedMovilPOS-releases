"""
Migracion para crear el sistema de devoluciones/reembolsos
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def migrate():
    """Crea las tablas necesarias para el sistema de devoluciones"""
    print("=" * 50)
    print("Migrando: Sistema de Devoluciones")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Tabla de devoluciones
        print("\n[1/4] Creando tabla 'devoluciones'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devoluciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_caja_id INTEGER NOT NULL,
                motivo TEXT NOT NULL,
                monto_total_devuelto REAL NOT NULL,
                metodo_devolucion TEXT NOT NULL,
                usuario_id INTEGER,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (venta_caja_id) REFERENCES ventas_caja(id) ON DELETE CASCADE,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        """)

        # 2. Indices para devoluciones
        print("[2/4] Creando indices en devoluciones...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_devoluciones_venta
            ON devoluciones(venta_caja_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_devoluciones_fecha
            ON devoluciones(fecha_creacion)
        """)

        # 3. Tabla de items devueltos
        print("[3/4] Creando tabla 'devoluciones_items'...")
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

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_devoluciones_items_devolucion
            ON devoluciones_items(devolucion_id)
        """)

        # 4. Modificar ventas_caja_items para tracking de devoluciones
        print("[4/4] Anadiendo columna cantidad_devuelta a ventas_caja_items...")

        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(ventas_caja_items)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'cantidad_devuelta' not in columns:
            cursor.execute("""
                ALTER TABLE ventas_caja_items
                ADD COLUMN cantidad_devuelta INTEGER DEFAULT 0
            """)
            print("    - Columna cantidad_devuelta anadida")
        else:
            print("    - Columna cantidad_devuelta ya existe")

        conn.commit()

        print("\n" + "=" * 50)
        print("[OK] Sistema de Devoluciones creado correctamente")
        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
