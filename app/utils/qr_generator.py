"""
Generador de códigos QR para REDMOVILPOS
Crea QR codes para órdenes de reparación SAT
"""
# sqlite3 no se usa en este módulo
import qrcode
import io
from PIL import Image
from app.utils.logger import logger


class QRGenerator:
    """
    Genera códigos QR para identificación única de órdenes.

    El código QR contiene el número de orden en formato:
    SAT:O00001 (para orden O00001)

    Esto permite escanear el QR y localizar rápidamente la orden.
    """

    def __init__(self):
        """Inicializa el generador de QR"""
        self.version = 1  # Tamaño del QR (1-40, 1 es el más pequeño)
        self.error_correction = qrcode.constants.ERROR_CORRECT_M  # Corrección de errores media
        self.box_size = 10  # Tamaño de cada "caja" del QR en píxeles
        self.border = 2  # Tamaño del borde en cajas

    def generar_qr_reparacion(self, numero_orden: str) -> str:
        """
        Genera el código QR para una orden de reparación.

        Args:
            numero_orden: Número de orden (ej: "O00001")

        Returns:
            str: Código QR en formato de texto (para guardar en BD)
        """
        # Formato del QR: SAT:numero_orden
        # Esto permite identificar que es una orden de reparación
        qr_data = f"SAT:{numero_orden}"
        return qr_data

    def generar_imagen_qr(self, numero_orden: str, size: int = 200) -> Image.Image:
        """
        Genera una imagen PIL del código QR.

        Args:
            numero_orden: Número de orden (ej: "O00001")
            size: Tamaño en píxeles del QR (default: 200x200)

        Returns:
            PIL.Image: Imagen del QR code
        """
        qr_data = self.generar_qr_reparacion(numero_orden)

        # Crear QR code
        qr = qrcode.QRCode(
            version=self.version,
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )

        qr.add_data(qr_data)
        qr.make(fit=True)

        # Generar imagen en blanco y negro
        img = qr.make_image(fill_color="black", back_color="white")

        # Redimensionar si es necesario
        if img.size[0] != size or img.size[1] != size:
            img = img.resize((size, size), Image.Resampling.LANCZOS)

        return img

    def generar_qr_bytes(self, numero_orden: str, size: int = 200, format: str = 'PNG') -> bytes:
        """
        Genera el código QR como bytes (útil para insertar en PDFs).

        Args:
            numero_orden: Número de orden
            size: Tamaño en píxeles
            format: Formato de imagen ('PNG', 'JPEG', etc.)

        Returns:
            bytes: Imagen del QR en bytes
        """
        img = self.generar_imagen_qr(numero_orden, size)

        # Convertir a bytes
        buffer = io.BytesIO()
        img.save(buffer, format=format)
        buffer.seek(0)

        return buffer.getvalue()

    def guardar_qr_archivo(self, numero_orden: str, filepath: str, size: int = 200):
        """
        Guarda el código QR como archivo de imagen.

        Args:
            numero_orden: Número de orden
            filepath: Ruta donde guardar el archivo
            size: Tamaño en píxeles

        Returns:
            bool: True si se guardó correctamente
        """
        try:
            img = self.generar_imagen_qr(numero_orden, size)
            img.save(filepath)
            return True
        except OSError as e:
            logger.error(f"Error guardando QR: {e}")
            return False

    @staticmethod
    def extraer_numero_orden(qr_data: str) -> str:
        """
        Extrae el número de orden desde los datos del QR.

        Args:
            qr_data: Datos leídos del QR (ej: "SAT:O00001")

        Returns:
            str: Número de orden (ej: "O00001") o None si no es válido
        """
        if not qr_data:
            return None

        # Verificar formato SAT:numero
        if qr_data.startswith("SAT:"):
            return qr_data[4:]  # Retornar número de orden sin prefijo

        # Si no tiene prefijo, asumir que es el número directo
        return qr_data if qr_data.startswith("O") else None

    @staticmethod
    def validar_qr_reparacion(qr_data: str) -> bool:
        """
        Valida que un código QR sea de una reparación.

        Args:
            qr_data: Datos del QR

        Returns:
            bool: True si es un QR de reparación válido
        """
        if not qr_data:
            return False

        # Debe empezar con SAT: o ser un número de orden válido
        if qr_data.startswith("SAT:"):
            numero = qr_data[4:]
            return numero.startswith("O") and len(numero) >= 6
        elif qr_data.startswith("O"):
            return len(qr_data) >= 6

        return False


# Ejemplo de uso
if __name__ == "__main__":
    generator = QRGenerator()

    # Generar QR para orden O00001
    qr_code = generator.generar_qr_reparacion("O00001")
    print(f"Código QR: {qr_code}")

    # Guardar imagen
    generator.guardar_qr_archivo("O00001", "test_qr.png", size=300)
    print("QR guardado en test_qr.png")

    # Validar
    print(f"¿Es válido 'SAT:O00001'? {QRGenerator.validar_qr_reparacion('SAT:O00001')}")
    print(f"Número extraído: {QRGenerator.extraer_numero_orden('SAT:O00001')}")
