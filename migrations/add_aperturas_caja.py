"""
Migración para crear el sistema de apertura de caja diaria
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def migrate():
    """Crea la tabla de aperturas de caja y modifica caja_cierres"""
    print("=" * 50)
    print("Migrando: Sistema de Apertura de Caja")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # 1. Crear tabla de aperturas de caja
        print("\n[1/3] Creando tabla 'aperturas_caja'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS aperturas_caja (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha DATE NOT NULL UNIQUE,
                saldo_inicial REAL NOT NULL,
                usuario_id INTEGER,
                notas TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
            )
        """)

        # 2. Crear índice en fecha para búsquedas rápidas
        print("[2/3] Creando índice en aperturas_caja.fecha...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_aperturas_fecha
            ON aperturas_caja(fecha)
        """)

        # 3. Añadir columna apertura_id a caja_cierres
        print("[3/3] Añadiendo columna apertura_id a caja_cierres...")

        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(caja_cierres)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'apertura_id' not in columns:
            cursor.execute("""
                ALTER TABLE caja_cierres
                ADD COLUMN apertura_id INTEGER REFERENCES aperturas_caja(id) ON DELETE SET NULL
            """)
            print("    - Columna apertura_id anadida")
        else:
            print("    - Columna apertura_id ya existe")

        conn.commit()

        print("\n" + "=" * 50)
        print("[OK] Sistema de Apertura de Caja creado correctamente")
        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
