"""
Gestor de permisos y roles
Verifica si un usuario tiene permiso para realizar una acción
"""
import sqlite3


class PermissionManager:
    """Gestiona los permisos de usuarios según su rol"""
    
    def __init__(self, db):
        self.db = db
        self._permisos_usuario = set()  # Cache de permisos del usuario actual
        self._rol_usuario = None
        self._usuario_id = None
    
    def cargar_permisos_usuario(self, usuario_id):
        """Carga los permisos del usuario según su rol"""
        self._usuario_id = usuario_id
        self._permisos_usuario = set()
        
        # Obtener el rol del usuario
        usuario = self.db.fetch_one(
            "SELECT rol FROM usuarios WHERE id = ?", 
            (usuario_id,)
        )
        
        if not usuario:
            return
        
        rol_nombre = usuario['rol']
        self._rol_usuario = rol_nombre
        
        # Obtener el ID del rol
        rol = self.db.fetch_one(
            "SELECT id FROM roles WHERE nombre = ?",
            (rol_nombre,)
        )
        
        if not rol:
            # Si el rol no existe en la tabla, verificar si es admin por compatibilidad
            if rol_nombre == 'admin':
                # Admin tiene todos los permisos
                permisos = self.db.fetch_all("SELECT codigo FROM permisos")
                self._permisos_usuario = {p['codigo'] for p in permisos}
            return
        
        # Cargar permisos del rol
        permisos = self.db.fetch_all("""
            SELECT p.codigo 
            FROM permisos p
            JOIN rol_permisos rp ON p.id = rp.permiso_id
            WHERE rp.rol_id = ?
        """, (rol['id'],))
        
        self._permisos_usuario = {p['codigo'] for p in permisos}
    
    def tiene_permiso(self, codigo_permiso):
        """Verifica si el usuario actual tiene un permiso específico"""
        # Admin siempre tiene todos los permisos
        if self._rol_usuario == 'admin':
            return True
        return codigo_permiso in self._permisos_usuario
    
    def tiene_alguno(self, *codigos_permisos):
        """Verifica si el usuario tiene al menos uno de los permisos"""
        if self._rol_usuario == 'admin':
            return True
        return any(codigo in self._permisos_usuario for codigo in codigos_permisos)
    
    def tiene_todos(self, *codigos_permisos):
        """Verifica si el usuario tiene todos los permisos indicados"""
        if self._rol_usuario == 'admin':
            return True
        return all(codigo in self._permisos_usuario for codigo in codigos_permisos)
    
    def es_admin(self):
        """Verifica si el usuario es administrador"""
        return self._rol_usuario == 'admin'
    
    def get_rol(self):
        """Devuelve el nombre del rol actual"""
        return self._rol_usuario
    
    def get_permisos(self):
        """Devuelve el conjunto de permisos del usuario"""
        return self._permisos_usuario.copy()
    
    # === Métodos de gestión de roles ===
    
    def obtener_roles(self):
        """Obtiene todos los roles"""
        return self.db.fetch_all("""
            SELECT r.*, 
                   (SELECT COUNT(*) FROM usuarios u WHERE u.rol = r.nombre) as num_usuarios
            FROM roles r
            ORDER BY r.es_sistema DESC, r.nombre
        """)
    
    def obtener_rol(self, rol_id):
        """Obtiene un rol por ID con sus permisos"""
        rol = self.db.fetch_one("SELECT * FROM roles WHERE id = ?", (rol_id,))
        if rol:
            permisos = self.db.fetch_all("""
                SELECT p.* FROM permisos p
                JOIN rol_permisos rp ON p.id = rp.permiso_id
                WHERE rp.rol_id = ?
            """, (rol_id,))
            rol['permisos'] = [p['codigo'] for p in permisos]
        return rol
    
    def obtener_todos_permisos(self):
        """Obtiene todos los permisos agrupados por módulo"""
        permisos = self.db.fetch_all("SELECT * FROM permisos ORDER BY modulo, nombre")
        
        # Agrupar por módulo
        por_modulo = {}
        for p in permisos:
            modulo = p['modulo']
            if modulo not in por_modulo:
                por_modulo[modulo] = []
            por_modulo[modulo].append(p)
        
        return por_modulo
    
    def crear_rol(self, nombre, descripcion, permisos_codigos):
        """Crea un nuevo rol con los permisos indicados"""
        try:
            # Insertar rol
            rol_id = self.db.execute_query(
                "INSERT INTO roles (nombre, descripcion) VALUES (?, ?)",
                (nombre.lower(), descripcion)
            )
            
            if rol_id:
                # Asignar permisos
                for codigo in permisos_codigos:
                    permiso = self.db.fetch_one(
                        "SELECT id FROM permisos WHERE codigo = ?", 
                        (codigo,)
                    )
                    if permiso:
                        self.db.execute_query(
                            "INSERT INTO rol_permisos (rol_id, permiso_id) VALUES (?, ?)",
                            (rol_id, permiso['id'])
                        )
                return rol_id
            return None
        except (sqlite3.Error, OSError, ValueError) as e:
            print(f"Error creando rol: {e}")
            return None
    
    def actualizar_rol(self, rol_id, nombre, descripcion, permisos_codigos):
        """Actualiza un rol existente"""
        try:
            # Verificar que no sea rol del sistema si se cambia el nombre
            rol = self.db.fetch_one("SELECT * FROM roles WHERE id = ?", (rol_id,))
            if not rol:
                return False
            
            # Actualizar datos básicos
            if rol['es_sistema'] and nombre.lower() != rol['nombre']:
                # No permitir cambiar nombre de rol del sistema
                pass
            else:
                self.db.execute_query(
                    "UPDATE roles SET nombre = ?, descripcion = ? WHERE id = ?",
                    (nombre.lower(), descripcion, rol_id)
                )
            
            # Eliminar permisos actuales
            self.db.execute_query(
                "DELETE FROM rol_permisos WHERE rol_id = ?",
                (rol_id,)
            )
            
            # Asignar nuevos permisos
            for codigo in permisos_codigos:
                permiso = self.db.fetch_one(
                    "SELECT id FROM permisos WHERE codigo = ?",
                    (codigo,)
                )
                if permiso:
                    self.db.execute_query(
                        "INSERT INTO rol_permisos (rol_id, permiso_id) VALUES (?, ?)",
                        (rol_id, permiso['id'])
                    )
            
            return True
        except (sqlite3.Error, OSError, ValueError) as e:
            print(f"Error actualizando rol: {e}")
            return False
    
    def eliminar_rol(self, rol_id):
        """Elimina un rol (si no es del sistema y no tiene usuarios)"""
        rol = self.db.fetch_one("SELECT * FROM roles WHERE id = ?", (rol_id,))
        
        if not rol:
            return False, "Rol no encontrado"
        
        if rol['es_sistema']:
            return False, "No se puede eliminar un rol del sistema"
        
        # Verificar si hay usuarios con este rol
        usuarios = self.db.fetch_one(
            "SELECT COUNT(*) as count FROM usuarios WHERE rol = ?",
            (rol['nombre'],)
        )
        
        if usuarios and usuarios['count'] > 0:
            return False, f"Hay {usuarios['count']} usuario(s) con este rol"
        
        # Eliminar
        self.db.execute_query("DELETE FROM rol_permisos WHERE rol_id = ?", (rol_id,))
        self.db.execute_query("DELETE FROM roles WHERE id = ?", (rol_id,))
        
        return True, "Rol eliminado correctamente"












