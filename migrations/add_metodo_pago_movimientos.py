"""
Migracion para agregar metodo_pago a caja_movimientos
Solo los egresos en efectivo deben afectar el saldo de caja
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def migrate():
    """Agrega campo metodo_pago a caja_movimientos"""
    print("=" * 50)
    print("Migrando: Metodo de Pago en Movimientos")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(caja_movimientos)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'metodo_pago' not in columns:
            print("\n[1/2] Anadiendo columna metodo_pago...")
            cursor.execute("""
                ALTER TABLE caja_movimientos
                ADD COLUMN metodo_pago TEXT DEFAULT 'efectivo'
            """)
            print("    - Columna metodo_pago anadida")
        else:
            print("\n[1/2] Columna metodo_pago ya existe")

        # Actualizar movimientos existentes
        print("[2/2] Actualizando movimientos existentes...")
        cursor.execute("""
            UPDATE caja_movimientos
            SET metodo_pago = 'efectivo'
            WHERE metodo_pago IS NULL
        """)
        print("    - Movimientos actualizados")

        conn.commit()

        print("\n" + "=" * 50)
        print("[OK] Metodo de Pago agregado correctamente")
        print("=" * 50)

    except Exception as e:
        print(f"[ERROR] {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
