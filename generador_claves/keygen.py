"""
GENERADOR DE CLAVES DE LICENCIA - RedMovilPOS
=============================================
IMPORTANTE: Este archivo es CONFIDENCIAL y debe mantenerse
solo en poder del desarrollador. NO incluir en la distribución.

Uso:
    python keygen.py

El programa solicita el ID de máquina del cliente y genera
la clave de licencia correspondiente.
"""
import sys
import os

# Añadir el directorio raíz al path para importar módulos de la app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar la función de generación de licencias desde el módulo compartido
from app.modules.license_secret import generar_hash_licencia_keygen


def generar_clave(machine_id):
    """
    Genera la clave de licencia para un ID de máquina dado.
    Usa PBKDF2 directo para compatibilidad con instalaciones nuevas.

    Args:
        machine_id: ID de máquina (formato: RMPV-XXXX-XXXX-XXXX-XXXX)

    Returns:
        str: Clave de licencia (formato: XXXX-XXXX-XXXX-XXXX)
    """
    return generar_hash_licencia_keygen(machine_id)


def main():
    print("=" * 60)
    print("  GENERADOR DE CLAVES - RedMovilPOS")
    print("  HERRAMIENTA CONFIDENCIAL DEL DESARROLLADOR")
    print("=" * 60)
    print()

    while True:
        print("-" * 60)
        machine_id = input("Introduce el ID de Máquina del cliente\n(o 'salir' para terminar): ").strip()

        if machine_id.lower() in ['salir', 'exit', 'q', 'quit']:
            print("\nHasta luego!")
            break

        if not machine_id:
            print("\n[ERROR] Debes introducir un ID de máquina\n")
            continue

        # Validar formato básico
        if not machine_id.startswith("RMPV-"):
            print("\n[AVISO] El ID no empieza con 'RMPV-'. ¿Estás seguro de que es correcto?")
            confirmar = input("¿Continuar de todos modos? (s/n): ").strip().lower()
            if confirmar != 's':
                continue

        # Generar clave
        clave = generar_clave(machine_id)

        print()
        print("=" * 60)
        print(f"  ID de Máquina: {machine_id}")
        print(f"  CLAVE DE LICENCIA: {clave}")
        print("=" * 60)
        print()
        print("Proporciona esta clave al cliente para activar el programa.")
        print()


if __name__ == "__main__":
    main()
