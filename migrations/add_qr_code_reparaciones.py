"""
Migración: Añade columna qr_code a tabla reparaciones
Permite localizar órdenes escaneando QR
"""
import sqlite3
import os
import sys

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_PATH


def migrate():
    """Ejecuta la migración"""
    print("\n" + "="*60)
    print("MIGRACIÓN: Añadir QR Code a Reparaciones")
    print("="*60)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(reparaciones)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'qr_code' in columns:
            print("[INFO] La columna 'qr_code' ya existe en reparaciones")
            return True

        # Añadir columna qr_code
        print("[1/2] Añadiendo columna qr_code...")
        cursor.execute("""
            ALTER TABLE reparaciones
            ADD COLUMN qr_code TEXT
        """)

        # Crear índice para búsquedas rápidas por QR
        print("[2/2] Creando índice idx_reparaciones_qr...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reparaciones_qr
            ON reparaciones(qr_code)
        """)

        conn.commit()
        print("[OK] Migración completada exitosamente")
        print("    - Columna 'qr_code' añadida")
        print("    - Índice creado para búsquedas por QR")

        return True

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Error en migración: {e}")
        return False

    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
