"""
Migración: Agregar campos de móviles a la tabla productos
Fecha: 2025-01-01
Descripción: Agrega columnas RAM, Almacenamiento y Estado para productos móviles
"""

def migrate(cursor):
    """Ejecuta la migración"""
    print("Agregando campos de móviles a tabla productos...")

    # Agregar columna RAM
    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN ram TEXT")
        print("✓ Columna 'ram' agregada")
    except Exception as e:
        if "duplicate column name" not in str(e).lower():
            print(f"⚠ Error al agregar columna 'ram': {e}")

    # Agregar columna Almacenamiento
    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN almacenamiento TEXT")
        print("✓ Columna 'almacenamiento' agregada")
    except Exception as e:
        if "duplicate column name" not in str(e).lower():
            print(f"⚠ Error al agregar columna 'almacenamiento': {e}")

    # Agregar columna Estado
    try:
        cursor.execute("ALTER TABLE productos ADD COLUMN estado TEXT")
        print("✓ Columna 'estado' agregada")
    except Exception as e:
        if "duplicate column name" not in str(e).lower():
            print(f"⚠ Error al agregar columna 'estado': {e}")

    print("Migración completada: Campos de móviles agregados a productos")
    return True
