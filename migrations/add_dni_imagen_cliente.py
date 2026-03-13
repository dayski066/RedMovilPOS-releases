"""
Migración para agregar columna dni_imagen a la tabla clientes
"""
import sqlite3
import os
import sys

# Añadir directorio raíz
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def migrate():
    """Ejecuta la migración"""
    print("Migrando base de datos: Añadiendo columna dni_imagen a clientes...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(clientes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'dni_imagen' not in columns:
            cursor.execute("ALTER TABLE clientes ADD COLUMN dni_imagen TEXT")
            conn.commit()
            print("[OK] Columna 'dni_imagen' añadida a la tabla 'clientes'")
        else:
            print("[INFO] La columna 'dni_imagen' ya existe en clientes")
            
    except Exception as e:
        print(f"[ERROR] Error en migración: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()












