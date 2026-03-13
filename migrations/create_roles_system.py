"""
Migración para crear el sistema de roles y permisos
"""
import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import DB_PATH


def migrate():
    """Ejecuta la migración del sistema de roles"""
    print("=" * 50)
    print("Migrando: Sistema de Roles y Permisos")
    print("=" * 50)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Crear tabla de roles
        print("\n[1/6] Creando tabla 'roles'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE NOT NULL,
                descripcion TEXT,
                es_sistema INTEGER DEFAULT 0,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Crear tabla de permisos
        print("[2/6] Creando tabla 'permisos'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permisos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                modulo TEXT NOT NULL,
                descripcion TEXT
            )
        """)
        
        # 3. Crear tabla de relación rol-permisos
        print("[3/6] Creando tabla 'rol_permisos'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rol_permisos (
                rol_id INTEGER NOT NULL,
                permiso_id INTEGER NOT NULL,
                PRIMARY KEY (rol_id, permiso_id),
                FOREIGN KEY (rol_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permiso_id) REFERENCES permisos(id) ON DELETE CASCADE
            )
        """)
        
        # 4. Insertar permisos predefinidos
        print("[4/6] Insertando permisos predefinidos...")
        permisos = [
            # Ventas
            ('ventas.ver', 'Ver historial de ventas', 'Ventas', 'Permite ver el historial de facturas'),
            ('ventas.crear', 'Crear ventas', 'Ventas', 'Permite crear nuevas facturas'),
            ('ventas.eliminar', 'Eliminar ventas', 'Ventas', 'Permite eliminar facturas'),
            ('ventas.imprimir', 'Imprimir facturas', 'Ventas', 'Permite imprimir facturas'),
            # Compras
            ('compras.ver', 'Ver historial de compras', 'Compras', 'Permite ver el historial de compras'),
            ('compras.crear', 'Crear compras', 'Compras', 'Permite crear nuevas compras'),
            ('compras.eliminar', 'Eliminar compras', 'Compras', 'Permite eliminar compras'),
            ('compras.imprimir', 'Imprimir contratos', 'Compras', 'Permite imprimir contratos de compra'),
            # SAT
            ('sat.ver', 'Ver historial SAT', 'SAT', 'Permite ver órdenes de reparación'),
            ('sat.crear', 'Crear órdenes SAT', 'SAT', 'Permite crear órdenes de reparación'),
            ('sat.eliminar', 'Eliminar órdenes SAT', 'SAT', 'Permite eliminar órdenes'),
            ('sat.estado', 'Cambiar estado SAT', 'SAT', 'Permite cambiar estado de órdenes'),
            ('sat.imprimir', 'Imprimir órdenes SAT', 'SAT', 'Permite imprimir órdenes'),
            # Clientes
            ('clientes.ver', 'Ver clientes', 'Clientes', 'Permite ver la lista de clientes'),
            ('clientes.editar', 'Crear/Editar clientes', 'Clientes', 'Permite crear y editar clientes'),
            ('clientes.eliminar', 'Eliminar clientes', 'Clientes', 'Permite eliminar clientes'),
            # Inventario
            ('inventario.ver', 'Ver inventario', 'Inventario', 'Permite ver productos y categorías'),
            ('inventario.editar', 'Editar inventario', 'Inventario', 'Permite crear y editar productos'),
            ('inventario.eliminar', 'Eliminar del inventario', 'Inventario', 'Permite eliminar productos'),
            # Caja
            ('caja.ver', 'Ver caja', 'Caja', 'Permite ver movimientos de caja'),
            ('caja.crear', 'Registrar movimientos', 'Caja', 'Permite registrar ingresos/egresos'),
            ('caja.cerrar', 'Cerrar caja', 'Caja', 'Permite realizar cierre de caja'),
            # Usuarios
            ('usuarios.ver', 'Ver usuarios', 'Usuarios', 'Permite ver la lista de usuarios'),
            ('usuarios.editar', 'Crear/Editar usuarios', 'Usuarios', 'Permite crear y editar usuarios'),
            ('usuarios.eliminar', 'Eliminar usuarios', 'Usuarios', 'Permite eliminar usuarios'),
            ('usuarios.password', 'Cambiar contraseñas', 'Usuarios', 'Permite cambiar contraseñas'),
            # Ajustes
            ('ajustes.ver', 'Ver ajustes', 'Ajustes', 'Permite ver la configuración'),
            ('ajustes.editar', 'Modificar ajustes', 'Ajustes', 'Permite modificar configuración'),
            ('ajustes.roles', 'Gestionar roles', 'Ajustes', 'Permite crear y editar roles'),
        ]
        
        for codigo, nombre, modulo, descripcion in permisos:
            cursor.execute("""
                INSERT OR IGNORE INTO permisos (codigo, nombre, modulo, descripcion)
                VALUES (?, ?, ?, ?)
            """, (codigo, nombre, modulo, descripcion))
        
        # 5. Insertar roles predefinidos
        print("[5/6] Insertando roles predefinidos...")
        
        # Admin (rol del sistema, no eliminable)
        cursor.execute("""
            INSERT OR IGNORE INTO roles (nombre, descripcion, es_sistema)
            VALUES ('admin', 'Administrador con acceso total', 1)
        """)
        
        # Vendedor
        cursor.execute("""
            INSERT OR IGNORE INTO roles (nombre, descripcion, es_sistema)
            VALUES ('vendedor', 'Gestión de ventas y clientes', 0)
        """)
        
        # Técnico
        cursor.execute("""
            INSERT OR IGNORE INTO roles (nombre, descripcion, es_sistema)
            VALUES ('tecnico', 'Gestión de reparaciones SAT', 0)
        """)
        
        # Consulta
        cursor.execute("""
            INSERT OR IGNORE INTO roles (nombre, descripcion, es_sistema)
            VALUES ('consulta', 'Solo lectura', 0)
        """)
        
        conn.commit()
        
        # 6. Asignar permisos a roles
        print("[6/6] Asignando permisos a roles...")
        
        # Admin: TODOS los permisos
        cursor.execute("SELECT id FROM roles WHERE nombre = 'admin'")
        admin_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM permisos")
        todos_permisos = cursor.fetchall()
        for (permiso_id,) in todos_permisos:
            cursor.execute("""
                INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                VALUES (?, ?)
            """, (admin_id, permiso_id))
        
        # Vendedor: ventas, clientes, caja básico
        cursor.execute("SELECT id FROM roles WHERE nombre = 'vendedor'")
        vendedor_id = cursor.fetchone()[0]
        permisos_vendedor = [
            'ventas.ver', 'ventas.crear', 'ventas.imprimir',
            'clientes.ver', 'clientes.editar',
            'caja.ver', 'caja.crear',
            'inventario.ver'
        ]
        for codigo in permisos_vendedor:
            cursor.execute("SELECT id FROM permisos WHERE codigo = ?", (codigo,))
            result = cursor.fetchone()
            if result:
                cursor.execute("""
                    INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                    VALUES (?, ?)
                """, (vendedor_id, result[0]))
        
        # Técnico: SAT, clientes ver, inventario ver
        cursor.execute("SELECT id FROM roles WHERE nombre = 'tecnico'")
        tecnico_id = cursor.fetchone()[0]
        permisos_tecnico = [
            'sat.ver', 'sat.crear', 'sat.estado', 'sat.imprimir',
            'clientes.ver', 'clientes.editar',
            'inventario.ver'
        ]
        for codigo in permisos_tecnico:
            cursor.execute("SELECT id FROM permisos WHERE codigo = ?", (codigo,))
            result = cursor.fetchone()
            if result:
                cursor.execute("""
                    INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                    VALUES (?, ?)
                """, (tecnico_id, result[0]))
        
        # Consulta: solo ver
        cursor.execute("SELECT id FROM roles WHERE nombre = 'consulta'")
        consulta_id = cursor.fetchone()[0]
        permisos_consulta = [
            'ventas.ver', 'compras.ver', 'sat.ver',
            'clientes.ver', 'inventario.ver', 'caja.ver'
        ]
        for codigo in permisos_consulta:
            cursor.execute("SELECT id FROM permisos WHERE codigo = ?", (codigo,))
            result = cursor.fetchone()
            if result:
                cursor.execute("""
                    INSERT OR IGNORE INTO rol_permisos (rol_id, permiso_id)
                    VALUES (?, ?)
                """, (consulta_id, result[0]))
        
        conn.commit()
        
        print("\n" + "=" * 50)
        print("[OK] Sistema de roles creado correctamente")
        print("=" * 50)
        
        # Mostrar resumen
        cursor.execute("SELECT COUNT(*) FROM roles")
        num_roles = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM permisos")
        num_permisos = cursor.fetchone()[0]
        print(f"  - Roles creados: {num_roles}")
        print(f"  - Permisos creados: {num_permisos}")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()












