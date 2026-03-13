"""
Migración para añadir índices que mejoran el rendimiento de búsquedas frecuentes
"""
import sqlite3
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def run_migration():
    """Añade índices para optimizar consultas frecuentes"""
    print(f"Conectando a: {DB_PATH}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("\n=== Añadiendo índices de rendimiento ===\n")

        # Índices para búsquedas en ventas_caja
        print("1. Índices para ventas_caja...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_caja_fecha_estado
            ON ventas_caja(fecha, estado)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_caja_metodo_pago
            ON ventas_caja(metodo_pago)
        """)
        print("   [OK] Indices de ventas_caja creados")

        # Índices compuestos para filtros frecuentes
        print("\n2. Índices compuestos para filtros...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_productos_activo_stock
            ON productos(activo, stock)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clientes_activo_nombre
            ON clientes(nombre, nif)
        """)
        print("   [OK] Indices compuestos creados")

        # Índices para ordenamiento común
        print("\n3. Indices para ordenamiento...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_facturas_fecha_desc
            ON facturas(fecha DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_compras_fecha_desc
            ON compras(fecha DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_reparaciones_fecha_estado
            ON reparaciones(fecha_entrada DESC, estado)
        """)
        print("   [OK] Indices de ordenamiento creados")

        # Índices para JOINs frecuentes
        print("\n4. Indices para JOINs...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_caja_items_venta
            ON ventas_caja_items(venta_caja_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_caja_usuario
            ON ventas_caja(usuario_id)
        """)
        print("   [OK] Indices de JOIN creados")

        # Índices específicos del sistema de caja
        print("\n4b. Indices del sistema de caja...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_movimientos_metodo_pago
            ON caja_movimientos(metodo_pago)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_movimientos_fecha
            ON caja_movimientos(fecha)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_movimientos_referencia
            ON caja_movimientos(referencia_tipo, referencia_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_numero_ticket
            ON ventas_caja(numero_ticket)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_ventas_estado
            ON ventas_caja(estado)
        """)
        print("   [OK] Indices del sistema de caja creados")

        # Índices para búsquedas LIKE frecuentes
        print("\n5. Indices para busquedas LIKE...")
        # Nota: SQLite no puede usar índices en LIKE '%texto%' pero sí en LIKE 'texto%'
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_productos_descripcion_collate
            ON productos(descripcion COLLATE NOCASE)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_clientes_nombre_collate
            ON clientes(nombre COLLATE NOCASE)
        """)
        print("   [OK] Indices para LIKE creados")

        # Analizar tablas para actualizar estadísticas
        print("\n6. Analizando tablas para optimizar query planner...")
        tablas = ['productos', 'clientes', 'facturas', 'compras', 'ventas_caja',
                  'reparaciones', 'caja_movimientos']
        for tabla in tablas:
            cursor.execute(f"ANALYZE {tabla}")
        print("   [OK] Analisis completado")

        conn.commit()
        print("\n[OK] Migracion de indices completada exitosamente")
        print("\n=== Resumen ===")
        print("[OK] 13 indices creados/verificados")
        print("[OK] 7 tablas analizadas")
        print("[OK] Consultas frecuentes optimizadas")

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Error en la migración: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_migration()
