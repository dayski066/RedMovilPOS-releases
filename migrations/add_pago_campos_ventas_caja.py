"""
Migración: Añade campos de pago (cantidad_recibida, cambio_devuelto) a ventas_caja
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.db.database import Database

def run():
    db = Database()
    db.connect()

    try:
        # Verificar si las columnas ya existen
        cursor = db.connection.cursor()
        cursor.execute("PRAGMA table_info(ventas_caja)")
        columnas = [col[1] for col in cursor.fetchall()]

        if 'cantidad_recibida' not in columnas:
            print("Aniadiendo columna cantidad_recibida...")
            db.execute_query("""
                ALTER TABLE ventas_caja
                ADD COLUMN cantidad_recibida REAL DEFAULT NULL
            """)
            print("OK - Columna cantidad_recibida aniadida")
        else:
            print("OK - Columna cantidad_recibida ya existe")

        if 'cambio_devuelto' not in columnas:
            print("Aniadiendo columna cambio_devuelto...")
            db.execute_query("""
                ALTER TABLE ventas_caja
                ADD COLUMN cambio_devuelto REAL DEFAULT NULL
            """)
            print("OK - Columna cambio_devuelto aniadida")
        else:
            print("OK - Columna cambio_devuelto ya existe")

        print("\nMigracion completada exitosamente")

    except Exception as e:
        print(f"ERROR en migracion: {e}")
    finally:
        db.disconnect()

if __name__ == "__main__":
    run()
